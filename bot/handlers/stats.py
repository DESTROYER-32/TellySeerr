import httpx
import html
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from bot import app

from config import settings
from bot.services.http_clients import http_client, jellyfin_headers
from bot.services.database import get_linked_user


@app.on_message(filters.command("watch", prefixes="/"))
async def watch_stats_cmd(client: Client, message: Message):
    sent_message = await message.reply("Fetching your watch stats...")

    linked_user = await get_linked_user(str(message.from_user.id))
    if not linked_user:
        await sent_message.edit(
            "⚠️ You haven't linked your account yet. Use `/link` to get started."
        )
        return

    _, jellyfin_user_id, username = linked_user[:3]
    if not jellyfin_user_id:
        await sent_message.edit(
            "⚠️ Your Jellyfin User ID is not found. Please try linking again."
        )
        return

    items_url = f"{settings.JELLYFIN_URL}/Users/{jellyfin_user_id}/Items"
    params = {
        "Recursive": "true",
        "IncludeItemTypes": "Movie,Episode",
        "Filters": "IsPlayed",
        "Fields": "RunTimeTicks,UserData,SeriesName",
    }

    try:
        response = await http_client.get(
            items_url, headers=jellyfin_headers, params=params
        )
        response.raise_for_status()
        items = response.json().get("Items", [])
    except httpx.RequestError as e:
        await sent_message.edit(f"❌ Failed to fetch watch data from Jellyfin: {e}")
        return

    watched_count = len(items)
    total_ticks = sum(
        item.get("RunTimeTicks", 0) for item in items if item.get("RunTimeTicks")
    )
    total_seconds = total_ticks / 10_000_000

    days, remainder_seconds = divmod(total_seconds, 86400)
    hours, remainder_seconds = divmod(remainder_seconds, 3600)
    minutes, _ = divmod(remainder_seconds, 60)

    last_watched_title = "No specific last watched item found."
    if items:
        valid_items = [
            i
            for i in items
            if i.get("UserData") and i.get("UserData").get("LastPlayedDate")
        ]
        if valid_items:
            last_watched_item = max(
                valid_items, key=lambda x: x["UserData"]["LastPlayedDate"]
            )
            title = last_watched_item.get("Name", "Unknown Title")
            if last_watched_item.get("Type") == "Episode" and last_watched_item.get(
                "SeriesName"
            ):
                title = f"{last_watched_item.get('SeriesName')} - {title}"
            last_watched_title = html.escape(title)

    username_html = html.escape(message.from_user.first_name)
    text = f"📊 <b>{username_html}'s Watch Statistics</b>\n\n"
    text += f"<b>📺 Total Watched Items:</b> {watched_count}\n"
    text += f"<b>⏱️ Total Watch Time:</b> {int(days)}d {int(hours)}h {int(minutes)}m\n"
    text += f"<b>👀 Last Watched:</b> {last_watched_title}"

    await sent_message.edit(text, parse_mode=ParseMode.HTML)
