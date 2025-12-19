import re
import httpx
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from bot import app
from config import settings
from bot.services.http_clients import http_client, jellyseerr_headers
from bot.helpers.formatting import format_media_item
from bot.helpers.markup import create_media_pagination_markup
from bot.state import requested_items

logger = logging.getLogger(__name__)

# Regex pattern for TMDB URLs
TMDB_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:themoviedb\.org|tmdb\.org)/(movie|tv)/(\d+)(?:-[^\s/]+)?(?:/)?",
    re.IGNORECASE,
)

TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def extract_tmdb_info(text: str) -> tuple[str, str] | None:
    """Extract TMDB media type and ID from text."""
    match = TMDB_URL_PATTERN.search(text)
    if match:
        media_type = match.group(1)  # 'movie' or 'tv'
        tmdb_id = match.group(2)
        return media_type, tmdb_id
    return None


async def lookup_by_tmdb_id(media_type: str, tmdb_id: str) -> dict | None:
    """Lookup media by TMDB ID using Jellyseerr API."""
    try:
        url = f"{settings.JELLYSEERR_URL}/api/v1/{media_type}/{tmdb_id}"

        response = await http_client.get(url, headers=jellyseerr_headers)
        response.raise_for_status()
        data = response.json()

        # Fix: mediaType - Jellyseerr API returns "unknown" for direct lookups
        # Override with the actual media type we know from the URL
        original_mediatype = data.get("mediaType", "unknown")
        if original_mediatype == "unknown":
            data["mediaType"] = media_type
            logger.info(
                f"Fixed mediaType from '{original_mediatype}' to '{media_type}' for TMDB ID {tmdb_id}"
            )
            logger.info(f"Final mediaType: {data.get('mediaType')}")
        else:
            logger.info(f"mediaType was already correct: {original_mediatype}")

        return data
    except httpx.RequestError as e:
        logger.error(f"Error looking up TMDB ID {tmdb_id}: {e}")
        return None


@app.on_message(
    filters.private
    & ~filters.command(
        [
            "start",
            "help",
            "request",
            "discover",
            "requests",
            "watch",
            "link",
            "unlink",
            "invite",
            "trial",
            "vip",
            "deleteuser",
            "listusers",
        ]
    )
)
async def handle_url_links(client: Client, message: Message):
    """Handle messages containing TMDB URLs."""
    text = message.text or message.caption
    if not text:
        return

    media_info = None

    # Check for TMDB URL
    if tmdb_info := extract_tmdb_info(text):
        media_type, tmdb_id = tmdb_info
        logger.info(f"Found TMDB {media_type} ID: {tmdb_id}")
        looking_up_message = await message.reply("🔍 Looking up TMDB link...")
        media_info = await lookup_by_tmdb_id(media_type, tmdb_id)

    if not media_info:
        # If no URL found, don't respond
        # Delete the looking up message if it exists
        if "looking_up_message" in locals():
            await looking_up_message.delete()
        return

    # Format the response
    text, photo_url = format_media_item(media_info, 0, 1)
    is_requested = (
        media_info.get("mediaType"),
        media_info.get("id"),
    ) in requested_items
    markup = create_media_pagination_markup(
        query="url_lookup",
        current_index=0,
        total_results=1,
        media_type=media_info.get("mediaType", ""),
        tmdb_id=media_info.get("id", 0),
        is_requested=is_requested,
    )

    if photo_url:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=photo_url,
            caption=text,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply(text, reply_markup=markup, parse_mode=ParseMode.HTML)

    # Delete the "🔍 Looking up TMDB link..." message
    if "looking_up_message" in locals():
        await looking_up_message.delete()
