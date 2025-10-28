import httpx
from pyrogram import Client, filters
from pyrogram.types import Message

from bot import app

from config import settings
from bot.services.http_clients import http_client, jellyfin_headers, jellyseerr_headers
from bot.services.database import store_linked_user, get_linked_user, delete_linked_user


@app.on_message(filters.command("link", prefixes="/") & filters.private)
async def link_cmd(client: Client, message: Message):
    try:
        _, jellyfin_username, password = message.text.split(maxsplit=2)
    except ValueError:
        await message.reply(
            "Usage: `/link <jellyfin_username> <password>`", parse_mode=None
        )
        return

    sent_message = await message.reply("Linking your account...")

    jellyfin_url = settings.JELLYFIN_URL
    jellyseerr_url = settings.JELLYSEERR_URL

    # 1. Authenticate with Jellyfin
    jellyfin_user_id = None
    try:
        auth_payload = {"Username": jellyfin_username, "Pw": password}
        jellyfin_auth_url = f"{jellyfin_url}/Users/AuthenticateByName"
        auth_response = await http_client.post(
            jellyfin_auth_url, json=auth_payload, headers=jellyfin_headers
        )

        if auth_response.status_code == 401:
            await sent_message.edit(
                "❌ **Authentication Failed:** Invalid Jellyfin username or password."
            )
            return
        auth_response.raise_for_status()
        jellyfin_user_id = auth_response.json().get("User", {}).get("Id")
    except httpx.RequestError as e:
        await sent_message.edit(
            f"❌ An error occurred while authenticating with Jellyfin: {e}"
        )
        return

    if not jellyfin_user_id:
        await sent_message.edit("❌ **Error:** Could not retrieve Jellyfin User ID.")
        return

    # 2. Find corresponding Jellyseerr user
    try:
        seerr_users_url = f"{jellyseerr_url}/api/v1/user?take=1000"
        seerr_response = await http_client.get(
            seerr_users_url, headers=jellyseerr_headers
        )
        seerr_response.raise_for_status()
        seerr_users = seerr_response.json().get("results", [])

        found_seerr_user = next(
            (
                u
                for u in seerr_users
                if str(u.get("jellyfinUserId")) == str(jellyfin_user_id)
            ),
            None,
        )

        if not found_seerr_user:
            await sent_message.edit(
                f"⚠️ **Account Not Found in Jellyseerr.**\n"
                f"Your Jellyfin login is correct, but your account ('{jellyfin_username}') "
                f"is not in Jellyseerr. Please contact an admin."
            )
            return
        jellyseerr_user_id_for_link = found_seerr_user.get("id")
        jellyseerr_username = found_seerr_user.get("username") or jellyfin_username

    except httpx.RequestError as e:
        await sent_message.edit(f"❌ Failed to fetch users from Jellyseerr: {e}")
        return

    # 3. Store the link
    await store_linked_user(
        telegram_id=str(message.from_user.id),
        jellyseerr_user_id=str(jellyseerr_user_id_for_link),
        jellyfin_user_id=str(jellyfin_user_id),
        username=jellyseerr_username,
    )
    await sent_message.edit(
        f"✅ **Success!** Your account is now linked to '{jellyseerr_username}'."
    )

    await message.delete()


@app.on_message(filters.command("unlink", prefixes="/") & filters.private)
async def unlink_cmd(client: Client, message: Message):
    linked_user = await get_linked_user(str(message.from_user.id))
    if not linked_user:
        await message.reply("⚠️ You haven't linked your account yet.")
        return

    await delete_linked_user(str(message.from_user.id))
    await message.reply("✅ Unlinked your account successfully.")
