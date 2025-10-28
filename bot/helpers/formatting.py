import httpx
import html

from config import settings
from bot.services.http_clients import http_client, jellyseerr_headers

TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def format_media_item(item: dict, current_index: int, total_results: int) -> (str, str):
    title = item.get("title") or item.get("name") or "Unknown Title"
    year_str = item.get("releaseDate") or item.get("firstAirDate", "N/A")
    year = year_str.split("-")[0] if isinstance(year_str, str) else "N/A"
    media_type = item.get("mediaType", "N/A").capitalize()
    overview = item.get("overview", "No overview available.")

    title = html.escape(title)
    overview = html.escape(overview)

    text = f"<b>{title} ({year})</b>\n"
    text += f"<i>{media_type}</i>\n\n"
    text += f"{overview}\n\n"
    text += f"Result {current_index + 1} of {total_results}"

    photo_url = ""
    if poster_path := item.get("posterPath"):
        photo_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}"

    return text, photo_url


def get_status_emoji(status_id):
    return {
        1: "⏳ Pending",
        2: "✅ Approved",
        3: "⚙️ Processing",
        4: "🗂️ Partially Available",
        5: "🎬 Available",
    }.get(status_id, "❓ Unknown")


async def format_request_item(
    request: dict, current_index: int, total_results: int
) -> (str, str):
    """
    Formats a request item.
    NOTE: This function is modified to use the centralized http_client
    and settings instead of receiving them as arguments.
    """
    media = request.get("media", {})
    media_type = media.get("mediaType", "unknown")
    tmdb_id = media.get("tmdbId")

    if not tmdb_id:
        return "<b>Error</b>: Request is missing a TMDB ID.", ""

    try:
        endpoint = "tv" if media_type == "tv" else "movie"
        media_info_url = f"{settings.JELLYSEERR_URL}/api/v1/{endpoint}/{tmdb_id}"
        response = await http_client.get(media_info_url, headers=jellyseerr_headers)
        response.raise_for_status()
        media_info = response.json()
    except httpx.RequestError as e:
        print(f"Error fetching media details: {e}")
        return "<b>Error</b>: Could not fetch details for this request.", ""

    if media_type == "tv":
        title = media_info.get("name", "Unknown Title")
        date_str = media_info.get("firstAirDate", "")
    else:
        title = media_info.get("title", "Unknown Title")
        date_str = media_info.get("releaseDate", "")

    year = date_str.split("-")[0] if date_str else "Unknown Year"
    status = get_status_emoji(request.get("status"))
    requested_date = request.get("createdAt", "N/A").split("T")[0]
    poster_path = media_info.get("posterPath")

    title = html.escape(title)

    text = f"<b>{title} ({year})</b>\n\n"
    text += f"<b>Status:</b> {status}\n"
    text += f"<b>Type:</b> {media_type.capitalize()}\n"
    text += f"<b>Requested On:</b> {requested_date}\n\n"
    text += f"Request {current_index + 1} of {total_results}"

    photo_url = ""
    if poster_path := media_info.get("posterPath"):
        photo_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}"

    return text, photo_url
