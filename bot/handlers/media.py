import httpx
import logging

from urllib.parse import urlencode, quote
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from pyrogram.enums import ParseMode

from bot import app

from config import settings
from bot.services.http_clients import http_client, jellyseerr_headers
from bot.services.database import get_linked_user
from bot.helpers.formatting import format_media_item
from bot.helpers.markup import create_media_pagination_markup

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600  # 1 hour
# Import shared state for tracking requested items
from bot.state import requested_items


async def _search_jellyseerr(query: str):
    if not hasattr(http_client, "search_cache"):
        http_client.search_cache = {}

    if query in http_client.search_cache:
        results, timestamp = http_client.search_cache[query]
        if (datetime.utcnow() - timestamp).total_seconds() < CACHE_TTL_SECONDS:
            logger.info(f"Returning cached search results for: {query}")
            return results

    search_url = f"{settings.JELLYSEERR_URL}/api/v1/search"
    params = urlencode({"query": query}, quote_via=quote)
    try:
        response = await http_client.get(
            f"{search_url}?{params}", headers=jellyseerr_headers
        )
        response.raise_for_status()
        all_results = response.json().get("results", [])

        # Filter to only include movies and TV shows
        results = [
            item for item in all_results if item.get("mediaType") in ["movie", "tv"]
        ]

        http_client.search_cache[query] = (results, datetime.utcnow())
        return results
    except httpx.RequestError as e:
        logger.error(f"Error searching Jellyseerr: {e}")
        return []


async def _discover_jellyseerr():
    if hasattr(http_client, "discover_cache"):
        results, timestamp = http_client.discover_cache
        if (datetime.utcnow() - timestamp).total_seconds() < CACHE_TTL_SECONDS:
            logger.info("Returning cached discover results.")
            return results

    try:
        movies_url = f"{settings.JELLYSEERR_URL}/api/v1/discover/movies"
        tv_url = f"{settings.JELLYSEERR_URL}/api/v1/discover/tv"

        movie_response = await http_client.get(movies_url, headers=jellyseerr_headers)
        tv_response = await http_client.get(tv_url, headers=jellyseerr_headers)

        movie_response.raise_for_status()
        tv_response.raise_for_status()

        results = movie_response.json().get("results", []) + tv_response.json().get(
            "results", []
        )

        http_client.discover_cache = (results, datetime.utcnow())
        return results
    except httpx.RequestError as e:
        logger.error(f"Error discovering media: {e}")
        return []


@app.on_message(filters.command("request", prefixes="/"))
async def request_cmd(client: Client, message: Message):
    try:
        query = message.text.split(maxsplit=1)[1]
    except IndexError:
        await message.reply(
            "Please provide a search query. Usage: `/request movie/show name`",
        )
        return

    sent_message = await message.reply("Searching...")

    results = await _search_jellyseerr(query)
    if not results:
        await sent_message.edit("No results found for your query.")
        return

    item = results[0]
    text, photo_url = format_media_item(item, 0, len(results))
    markup = create_media_pagination_markup(
        query=query,
        current_index=0,
        total_results=len(results),
        media_type=item.get("mediaType"),
        tmdb_id=item.get("id"),
    )

    if photo_url:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=photo_url,
            caption=text,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
        )
        await sent_message.delete()
    else:
        await sent_message.edit(text, reply_markup=markup, parse_mode=ParseMode.HTML)


@app.on_message(filters.command("discover", prefixes="/"))
async def discover_cmd(client: Client, message: Message):
    sent_message = await message.reply("Discovering popular items...")

    results = await _discover_jellyseerr()
    if not results:
        await sent_message.edit("No popular items found to discover.")
        return

    query = "discover"
    item = results[0]
    text, photo_url = format_media_item(item, 0, len(results))
    is_requested = (item.get("mediaType"), item.get("id")) in requested_items
    markup = create_media_pagination_markup(
        query=query,
        current_index=0,
        total_results=len(results),
        media_type=item.get("mediaType"),
        tmdb_id=item.get("id"),
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
        await sent_message.delete()
    else:
        await sent_message.edit(text, reply_markup=markup, parse_mode=ParseMode.HTML)


@app.on_callback_query(filters.regex(r"media_nav:(prev|next):(\d+):(.+)"))
async def media_pagination_handler(client: Client, callback_query: CallbackQuery):
    match = callback_query.matches[0]
    direction, current_index_str, query = match.groups()
    current_index = int(current_index_str)

    results = []
    if query == "discover":
        cached_data = getattr(http_client, "discover_cache", None)
        if cached_data:
            results, _ = cached_data
        else:
            results = await _discover_jellyseerr()

    elif query == "url_lookup":
        await callback_query.answer("No more results to navigate.")
        return

    else:
        cached_data = getattr(http_client, "search_cache", {}).get(query)
        if cached_data:
            results, _ = cached_data
        else:
            results = await _search_jellyseerr(query)

    if not results:
        await callback_query.answer(
            "Error: Search results expired or not found. Please try searching again.",
            show_alert=True,
        )
        await callback_query.message.delete()
        return

    new_index = current_index + (1 if direction == "next" else -1)
    if not (0 <= new_index < len(results)):
        await callback_query.answer("You are at the end of the list.")
        return

    item = results[new_index]
    text, photo_url = format_media_item(item, new_index, len(results))
    is_requested = (item.get("mediaType"), item.get("id")) in requested_items
    markup = create_media_pagination_markup(
        query=query,
        current_index=new_index,
        total_results=len(results),
        media_type=item.get("mediaType"),
        tmdb_id=item.get("id"),
        is_requested=is_requested,
    )

    if photo_url:
        try:
            await callback_query.edit_message_media(
                media=InputMediaPhoto(
                    media=photo_url,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=markup,
            )
        except Exception as e:
            logger.error(f"Error updating poster in media pagination: {e}")
            await callback_query.edit_message_caption(
                caption=text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
    else:
        await callback_query.edit_message_caption(
            caption=text, reply_markup=markup, parse_mode=ParseMode.HTML
        )

    await callback_query.answer()


@app.on_callback_query(filters.regex(r"media_req:(\w+):(\d+)"))
async def media_request_handler(client: Client, callback_query: CallbackQuery):
    match = callback_query.matches[0]
    media_type, tmdb_id = match.groups()
    tmdb_id = int(tmdb_id)
    user_id = str(callback_query.from_user.id)

    linked_user_data = await get_linked_user(user_id)
    if not linked_user_data or not linked_user_data[0]:
        await callback_query.answer(
            "⚠️ You must link your account first using /link", show_alert=True
        )
        return

    jellyseerr_user_id = int(linked_user_data[0])

    request_url = f"{settings.JELLYSEERR_URL}/api/v1/request"
    payload = {
        "mediaType": media_type,
        "mediaId": tmdb_id,
        "userId": jellyseerr_user_id,
    }
    if media_type == "tv":
        payload["seasons"] = "all"

    try:
        response = await http_client.post(
            request_url, headers=jellyseerr_headers, json=payload
        )
        response.raise_for_status()

        # Mark this item as requested
        requested_items.add((media_type, tmdb_id))

        # Update the button to show "Requested"
        try:
            # Get the request button index (last button in keyboard)
            keyboard = callback_query.message.reply_markup.inline_keyboard
            request_button_row = keyboard[-1]
            request_button = request_button_row[0]

            # Create new keyboard with updated button
            new_keyboard = keyboard.copy()
            new_keyboard[-1] = [
                InlineKeyboardButton(
                    text="✅ Requested",
                    callback_data=f"requested:{media_type}:{tmdb_id}",
                )
            ]

            new_markup = InlineKeyboardMarkup(inline_keyboard=new_keyboard)
            await callback_query.edit_message_reply_markup(reply_markup=new_markup)
        except Exception as e:
            logger.error(f"Error updating request button: {e}")

        await callback_query.answer("✅ Request successful!", show_alert=True)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            # Already requested - update button state
            requested_items.add((media_type, tmdb_id))
            try:
                keyboard = callback_query.message.reply_markup.inline_keyboard
                request_button_row = keyboard[-1]
                request_button = request_button_row[0]

                new_keyboard = keyboard.copy()
                new_keyboard[-1] = [
                    InlineKeyboardButton(
                        text="✅ Requested",
                        callback_data=f"requested:{media_type}:{tmdb_id}",
                    )
                ]

                new_markup = InlineKeyboardMarkup(inline_keyboard=new_keyboard)
                await callback_query.edit_message_reply_markup(reply_markup=new_markup)
            except Exception as e:
                logger.error(f"Error updating request button for duplicate: {e}")

            await callback_query.answer(
                "⚠️ Already available or requested.", show_alert=True
            )
        else:
            await callback_query.answer(
                f"❌ Error: {e.response.status_code}", show_alert=True
            )
    except httpx.RequestError as e:
        await callback_query.answer(f"❌ Network error: {e}", show_alert=True)


@app.on_callback_query(filters.regex(r"requested:(\w+):(\d+)"))
async def requested_handler(client: Client, callback_query: CallbackQuery):
    """Handle clicks on already requested items."""
    await callback_query.answer(
        "⚠️ This item has already been requested.", show_alert=True
    )
