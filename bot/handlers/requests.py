import httpx
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ParseMode

from bot import app

from config import settings
from bot.services.http_clients import http_client, jellyseerr_headers
from bot.services.database import get_linked_user
from bot.helpers.formatting import format_request_item
from bot.helpers.markup import create_requests_pagination_markup


@app.on_message(filters.command("requests", prefixes="/"))
async def my_requests_cmd(client: Client, message: Message):
    sent_message = await message.reply("Fetching your requests...")

    user_id = str(message.from_user.id)
    linked_user = await get_linked_user(user_id)
    if not linked_user or not linked_user[0]:
        await sent_message.edit("⚠️ You need to link your account first using `/link`.")
        return

    jellyseerr_user_id = linked_user[0]

    try:
        request_api_url = f"{settings.JELLYSEERR_URL}/api/v1/request"
        params = {
            "take": 100,
            "skip": 0,
            "sort": "added",
            "filter": "all",
            "requestedBy": jellyseerr_user_id,
        }

        response = await http_client.get(
            request_api_url, headers=jellyseerr_headers, params=params
        )
        response.raise_for_status()
        user_requests_data = response.json().get("results", [])

    except httpx.RequestError as e:
        await sent_message.edit(
            f"❌ An error occurred while fetching your requests: {e}"
        )
        return

    if not user_requests_data:
        await sent_message.edit("You have no pending or completed requests.")
        return

    user_requests_data.sort(key=lambda r: r.get("createdAt", ""), reverse=True)

    if not hasattr(client, "request_cache"):
        client.request_cache = {}
    client.request_cache[user_id] = user_requests_data

    text, photo_url = await format_request_item(
        user_requests_data[0], 0, len(user_requests_data)
    )
    markup = create_requests_pagination_markup(int(user_id), 0, len(user_requests_data))

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


@app.on_callback_query(filters.regex(r"req_nav:(prev|next):(\d+):(\d+)"))
async def requests_pagination_handler(client: Client, callback_query: CallbackQuery):
    match = callback_query.matches[0]
    direction, current_index_str, user_id_str = match.groups()
    current_index = int(current_index_str)
    user_id = str(user_id_str)

    if str(callback_query.from_user.id) != user_id:
        await callback_query.answer("This is not for you.", show_alert=True)
        return

    user_requests_data = getattr(client, "request_cache", {}).get(user_id)

    if not user_requests_data:
        linked_user = await get_linked_user(user_id)
        if not linked_user:
            await callback_query.answer(
                "Error: Could not find your linked account.", show_alert=True
            )
            return

        request_api_url = f"{settings.JELLYSEERR_URL}/api/v1/request"
        params = {
            "take": 100,
            "skip": 0,
            "sort": "added",
            "filter": "all",
            "requestedBy": linked_user[0],
        }
        try:
            response = await http_client.get(
                request_api_url, headers=jellyseerr_headers, params=params
            )
            response.raise_for_status()
            user_requests_data = response.json().get("results", [])
            user_requests_data.sort(key=lambda r: r.get("createdAt", ""), reverse=True)
            if not hasattr(client, "request_cache"):
                client.request_cache = {}
            client.request_cache[user_id] = user_requests_data
        except Exception as e:
            print(f"Error re-fetching requests: {e}")
            await callback_query.answer("Error re-fetching requests.", show_alert=True)
            return

    if not user_requests_data:
        await callback_query.answer("You have no requests.", show_alert=True)
        return

    new_index = current_index + (1 if direction == "next" else -1)
    if not (0 <= new_index < len(user_requests_data)):
        await callback_query.answer("You are at the end of the list.")
        return

    item = user_requests_data[new_index]
    text, photo_url = await format_request_item(
        item, new_index, len(user_requests_data)
    )
    markup = create_requests_pagination_markup(
        int(user_id), new_index, len(user_requests_data)
    )

    try:
        await callback_query.edit_message_media(
            media={
                "type": "photo",
                "media": photo_url,
                "caption": text,
                "parse_mode": ParseMode.HTML,
            },
            reply_markup=markup,
        )
    except Exception:
        await callback_query.edit_message_caption(
            caption=text, reply_markup=markup, parse_mode=ParseMode.HTML
        )

    await callback_query.answer()
