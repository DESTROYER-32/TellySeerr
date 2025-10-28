import httpx
import re
import secrets
import logging
import html
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from bot import app

from config import settings
from bot.services.http_clients import http_client, jellyfin_headers, jellyseerr_headers
from bot.services.database import (
    store_linked_user,
    delete_linked_user,
    get_user_by_username,
)

logger = logging.getLogger(__name__)

ADMIN_USER_IDS = settings.ADMIN_USER_IDS


async def _create_user(
    app_client: Client,
    reply_message: Message,
    telegram_user_id: int,
    telegram_username: str,
    duration_days: int = None,
    role_name_to_assign: str = None,
):
    jellyfin_url = settings.JELLYFIN_URL
    jellyseerr_url = settings.JELLYSEERR_URL

    username = re.sub(r"[^a-zA-Z0-9.-]", "", telegram_username)
    if not username:
        username = f"tg_user_{telegram_user_id}"

    temp_password = secrets.token_urlsafe(12)
    jellyfin_user_id = None
    jellyfin_user_created = False

    try:
        users_url = f"{jellyfin_url}/Users"
        users_response = await http_client.get(
            users_url, headers=jellyfin_headers, timeout=10
        )
        users_response.raise_for_status()
        jellyfin_users = users_response.json()

        existing_user = next(
            (
                u
                for u in jellyfin_users
                if u.get("Name", "").lower() == username.lower()
            ),
            None,
        )

        if existing_user:
            await reply_message.edit(
                f"⚠️ **User Already Exists!**\n"
                f"User '{html.escape(username)}' (ID: `{existing_user.get('Id')}`) already exists in Jellyfin."
            )
            return

    except httpx.HTTPStatusError as e:
        await reply_message.edit(
            f"❌ Failed to check for existing users (HTTP {e.response.status_code}): {e.response.text}"
        )
        return
    except httpx.RequestError as e:
        await reply_message.edit(
            f"❌ Failed to check for existing users (Network Error): {e}"
        )
        return

    # 1. Create Jellyfin User
    try:
        jellyfin_user_payload = {
            "Name": username,
            "Password": temp_password,
            "Policy": {
                "IsAdministrator": False,
                "EnableUserPreferenceAccess": True,
                "EnableMediaPlayback": True,
                "EnableLiveTvAccess": False,
                "EnableLiveTvManagement": False,
            },
        }
        response_fin = await http_client.post(
            f"{jellyfin_url}/Users/New",
            headers=jellyfin_headers,
            json=jellyfin_user_payload,
        )

        response_fin.raise_for_status()

        jellyfin_user_id = response_fin.json().get("Id")
        jellyfin_user_created = True

    except httpx.HTTPStatusError as e:
        await reply_message.edit(
            f"❌ Failed to create Jellyfin user (HTTP {e.response.status_code}): {e.response.text}"
        )
        return
    except httpx.RequestError as e:
        await reply_message.edit(
            f"❌ Failed to create Jellyfin user (Network Error): {e}"
        )
        return

    if not jellyfin_user_id:
        await reply_message.edit("❌ Failed to get Jellyfin User ID after creation.")
        return

    # 2. Import User to Jellyseerr
    jellyseerr_user = None
    try:
        response_seerr_import = await http_client.post(
            f"{jellyseerr_url}/api/v1/user/import-from-jellyfin",
            headers=jellyseerr_headers,
            json={"jellyfinUserIds": [jellyfin_user_id]},
        )
        response_seerr_import.raise_for_status()
        jellyseerr_user = response_seerr_import.json()[0]

    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning(
            f"Failed to auto-import {username} to Jellyseerr: {e}. Trying to find them..."
        )

        # Wait 2 seconds in case Jellyseerr is just slow to index
        await asyncio.sleep(2)

        try:
            seerr_users_url = f"{jellyseerr_url}/api/v1/user?take=1000"
            seerr_response = await http_client.get(
                seerr_users_url, headers=jellyseerr_headers
            )
            seerr_response.raise_for_status()
            seerr_users = seerr_response.json().get("results", [])

            jellyseerr_user = next(
                (
                    u
                    for u in seerr_users
                    if str(u.get("jellyfinUserId")) == str(jellyfin_user_id)
                ),
                None,
            )
            if not jellyseerr_user:
                raise Exception("User not found in Jellyseerr after failed import.")

        except (httpx.HTTPStatusError, httpx.RequestError, Exception) as search_e:
            logger.error(f"Failed to find user in Jellyseerr: {search_e}")
            # Rollback: Delete the Jellyfin user we just created
            if jellyfin_user_created:
                await http_client.delete(
                    f"{jellyfin_url}/Users/{jellyfin_user_id}", headers=jellyfin_headers
                )
            await reply_message.edit(
                f"❌ Failed to import/find in Jellyseerr ({e}). Rolled back Jellyfin user creation."
            )
            return

    if role_name_to_assign:
        logger.info(f"User {username} assigned virtual role '{role_name_to_assign}'.")

    # 4. Store linked user
    expires_at = (
        datetime.utcnow() + timedelta(days=duration_days) if duration_days else None
    )
    await store_linked_user(
        telegram_id=str(telegram_user_id),
        jellyseerr_user_id=str(jellyseerr_user.get("id")),
        jellyfin_user_id=str(jellyfin_user_id),
        username=username,
        expires_at=expires_at.isoformat() if expires_at else None,
        guild_id=None,
        role_name=role_name_to_assign,
    )

    # 5. DM Credentials
    try:
        dm_message = (
            f"## Welcome to the Media Server! 🎉\n\n"
            f"An account has been created for you. Here are your login details:\n\n"
            f"**Username:** `{username}`\n"
            f"**Temporary Password:** `{temp_password}`\n\n"
            f"Please change your password after logging in.\n\n"
            f"🔗 Jellyfin: {jellyfin_url}\n"
            f"🔗 Jellyseerr: {jellyseerr_url}\n\n"
        )
        if duration_days:
            dm_message += f"**Note:** This is a temporary account that will expire in {duration_days} days."

        await app_client.send_message(
            chat_id=telegram_user_id, text=dm_message, parse_mode=ParseMode.MARKDOWN
        )
        await reply_message.edit(
            f"✅ Successfully created account for `{username}` and sent them a DM."
        )
    except Exception as e:
        logger.warning(f"Failed to DM user {telegram_user_id}: {e}")
        await reply_message.edit(
            f"✅ Account for {username} created, but I could not DM them.\nPassword: `{temp_password}`"
        )


@app.on_message(filters.command("invite", prefixes="/"))
async def invite_cmd(client: Client, message: Message):
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.reply("❌ You are not authorized to use this command.")
        return
    if not message.reply_to_message:
        await message.reply(
            "Please reply to a user's message to invite them.", parse_mode=None
        )
        return
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    target_username = target_user.username or f"tg_user_{target_id}"
    sent_message = await message.reply(
        f"Processing permanent invite for {html.escape(target_username)}..."
    )
    await _create_user(client, sent_message, target_id, target_username, None, None)


@app.on_message(filters.command("trial", prefixes="/"))
async def trial_cmd(client: Client, message: Message):
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.reply("❌ You are not authorized to use this command.")
        return
    if not message.reply_to_message:
        await message.reply(
            "Please reply to a user's message to give them a trial.", parse_mode=None
        )
        return
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    target_username = target_user.username or f"tg_user_{target_id}"
    sent_message = await message.reply(
        f"Processing 7-day trial for {html.escape(target_username)}..."
    )
    await _create_user(client, sent_message, target_id, target_username, 7, "Trial")


@app.on_message(filters.command("vip", prefixes="/"))
async def vip_cmd(client: Client, message: Message):
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.reply("❌ You are not authorized to use this command.")
        return
    if not message.reply_to_message:
        await message.reply(
            "Please reply to a user's message to give them VIP.", parse_mode=None
        )
        return
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    target_username = target_user.username or f"tg_user_{target_id}"
    sent_message = await message.reply(
        f"Processing 30-day VIP invite for {html.escape(target_username)}..."
    )
    await _create_user(client, sent_message, target_id, target_username, 30, "VIP")


@app.on_message(filters.command("listusers", prefixes="/") & filters.private)
async def list_users_cmd(client: Client, message: Message):
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.reply("❌ You are not authorized to use this command.")
        return

    sent_message = await message.reply("Fetching users from Jellyfin API...")

    try:
        users_url = f"{settings.JELLYFIN_URL}/Users"
        response = await http_client.get(
            users_url, headers=jellyfin_headers, timeout=10
        )
        response.raise_for_status()
        jellyfin_users = response.json()

    except httpx.RequestError as e:
        await sent_message.edit(
            f"❌ An error occurred while fetching users from Jellyfin: {e}"
        )
        return

    if not jellyfin_users:
        await sent_message.edit("No users found on the Jellyfin server.")
        return

    reply_text = "<b>Jellyfin Server User List:</b>\n\n"
    for user in jellyfin_users:
        username = user.get("Name", "Unknown")
        is_admin = user.get("Policy", {}).get("IsAdministrator", False)
        admin_tag = " (Admin)" if is_admin else ""

        reply_text += f"• <code>{html.escape(username)}</code>{admin_tag}\n"

    await sent_message.edit(reply_text, parse_mode=ParseMode.HTML)


@app.on_message(filters.command("deleteuser", prefixes="/") & filters.private)
async def delete_user_cmd(client: Client, message: Message):
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.reply("❌ You are not authorized to use this command.")
        return

    try:
        username_to_delete = message.text.split(maxsplit=1)[1]
    except IndexError:
        await message.reply("Usage: `/deleteuser <username>`", parse_mode=None)
        return

    sent_message = await message.reply(
        f"Finding user '{username_to_delete}' in services..."
    )

    user_data = await get_user_by_username(username_to_delete)

    jellyfin_user_id = None
    jellyseerr_user_id = None

    if user_data:
        telegram_id, jellyseerr_user_id, jellyfin_user_id = user_data
    else:
        await sent_message.edit(
            f"User '{html.escape(username_to_delete)}' not in bot DB. Trying to find on Jellyfin..."
        )
        try:
            users_url = f"{settings.JELLYFIN_URL}/Users"
            response = await http_client.get(
                users_url, headers=jellyfin_headers, timeout=10
            )
            response.raise_for_status()
            jellyfin_users = response.json()

            found_user = next(
                (
                    u
                    for u in jellyfin_users
                    if u.get("Name").lower() == username_to_delete.lower()
                ),
                None,
            )

            if not found_user:
                await sent_message.edit(
                    f"❌ User '{html.escape(username_to_delete)}' not found on Jellyfin either."
                )
                return

            jellyfin_user_id = found_user.get("Id")

            await sent_message.edit(
                f"Found Jellyfin ID ({jellyfin_user_id}). Now finding Jellyseerr user..."
            )

            seerr_users_url = f"{settings.JELLYSEERR_URL}/api/v1/user?take=1000"
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

            if found_seerr_user:
                jellyseerr_user_id = found_seerr_user.get("id")
                logger.info(f"Found corresponding Jellyseerr ID: {jellyseerr_user_id}")
            else:
                logger.warning(
                    f"User {jellyfin_user_id} exists on Jellyfin but not on Jellyseerr."
                )

        except httpx.RequestError as e:
            await sent_message.edit(
                f"❌ Error finding user on Jellyfin/Jellyseerr: {e}"
            )
            return

    await sent_message.edit(
        f"Deleting user '{username_to_delete}' (JF ID: {jellyfin_user_id}, JS ID: {jellyseerr_user_id}) from all services..."
    )

    try:
        if jellyfin_user_id:
            jf_del_url = f"{settings.JELLYFIN_URL}/Users/{jellyfin_user_id}"
            jf_res = await http_client.delete(
                jf_del_url, headers=jellyfin_headers, timeout=10
            )
            jf_res.raise_for_status()
            logger.info(f"Deleted Jellyfin user: {jellyfin_user_id}")

        if jellyseerr_user_id:
            js_del_url = f"{settings.JELLYSEERR_URL}/api/v1/user/{jellyseerr_user_id}"
            js_res = await http_client.delete(
                js_del_url, headers=jellyseerr_headers, timeout=10
            )
            if js_res.status_code != 404:
                js_res.raise_for_status()
            logger.info(f"Deleted Jellyseerr user: {jellyseerr_user_id}")
        else:
            logger.warning(
                f"No Jellyseerr ID found for {username_to_delete}, skipping Jellyseerr deletion."
            )

        if user_data:
            await delete_linked_user(user_data[0])
            logger.info(f"Deleted user from bot DB: {user_data[0]}")

        await sent_message.edit(
            f"✅ Successfully deleted user '{username_to_delete}' from Jellyfin and bot database."
        )

    except httpx.RequestError as e:
        await sent_message.edit(f"❌ An error occurred during API deletion: {e}")
    except Exception as e:
        await sent_message.edit(f"❌ An unexpected error occurred: {e}")
