import asyncio
import httpx
import logging
from datetime import datetime
from pyrogram import Client

from config import settings

from bot.services.database import get_all_expiring_users, delete_linked_user

from bot.services.http_clients import http_client, jellyfin_headers, jellyseerr_headers

logger = logging.getLogger(__name__)


async def check_expired_users_task(app: Client):
    """
    A background task that runs once daily to check for and DELETE expired users.
    """
    while not app.is_connected:
        await asyncio.sleep(1)

    logger.info("Starting daily check for expired users...")

    while True:
        now = datetime.utcnow()
        jellyfin_url = settings.JELLYFIN_URL
        jellyseerr_url = settings.JELLYSEERR_URL

        expiring_users = await get_all_expiring_users()
        logger.info(f"Checking {len(expiring_users)} users for expiration.")

        for user_row in expiring_users:
            try:
                telegram_id, jellyseerr_user_id, jellyfin_user_id, expires_at_str = (
                    user_row
                )
            except ValueError:
                logger.error(f"Error unpacking user row: {user_row}")
                continue

            if not expires_at_str:
                continue

            try:
                expires_at = datetime.fromisoformat(expires_at_str)
            except ValueError:
                logger.error(
                    f"Invalid expires_at format for user {telegram_id}: {expires_at_str}"
                )
                continue

            if now >= expires_at:
                logger.info(f"User {telegram_id} has expired. Deleting...")
                try:
                    jf_del_url = f"{jellyfin_url}/Users/{jellyfin_user_id}"
                    jf_res = await http_client.delete(
                        jf_del_url, headers=jellyfin_headers, timeout=10
                    )
                    jf_res.raise_for_status()
                    logger.info(f"Deleted Jellyfin user: {jellyfin_user_id}")

                    js_del_url = f"{jellyseerr_url}/api/v1/user/{jellyseerr_user_id}"
                    js_res = await http_client.delete(
                        js_del_url, headers=jellyseerr_headers, timeout=10
                    )
                    if js_res.status_code != 404:
                        js_res.raise_for_status()
                    logger.info(f"Deleted Jellyseerr user: {jellyseerr_user_id}")

                    try:
                        await app.send_message(
                            chat_id=int(telegram_id),
                            text="Your temporary access to the media server has expired and your account has been deleted.",
                        )
                        logger.info(f"Notified user {telegram_id} of expiration.")
                    except Exception as e:
                        logger.warning(
                            f"Could not DM user {telegram_id} about expiration: {e}"
                        )

                    # --- 4. Cleanup DB ---
                    await delete_linked_user(telegram_id)
                    logger.info(
                        f"Unlinked expired user from bot database: {telegram_id}"
                    )

                except httpx.RequestError as e:
                    logger.error(
                        f"Failed to delete expired user {telegram_id} via API: {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"An unexpected error occurred while processing expiration for user {telegram_id}: {e}"
                    )

        # Wait for 24 hours
        await asyncio.sleep(60 * 60 * 24)
