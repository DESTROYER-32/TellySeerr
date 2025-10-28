import asyncio
import logging

from pyrogram import Client
from pyrogram.types import BotCommand
from pyrogram.types import BotCommandScopeChat
from config import settings
from bot import app
from bot.services import database
from bot.services.http_clients import close_http_client
from bot.handlers import load_all_handlers
from tasks import check_expired_users_task

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


USER_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("help", "Show this help message"),
    BotCommand("request", "Request a movie/show. Usage: /request <name>"),
    BotCommand("discover", "Discover popular and trending media"),
    BotCommand("requests", "View your pending media requests"),
    BotCommand("watch", "See your personal watch statistics"),
    BotCommand("link", "Link your Jellyfin account. Usage: /link <user> <pass>"),
    BotCommand("unlink", "Unlink your Jellyfin account"),
]

ADMIN_COMMANDS = USER_COMMANDS + [
    BotCommand("invite", "Reply to a user to create a permanent account"),
    BotCommand("trial", "Reply to a user to create a 7-day trial"),
    BotCommand("vip", "Reply to a user to create a 30-day VIP account"),
    BotCommand("deleteuser", "Delete a user. Usage: /deleteuser <username>"),
    BotCommand("listusers", "List all users on the Jellyfin server"),
]


@app.on_start()
async def start_services(client: Client):
    """Async tasks to run *after* Pyrogram connects."""
    logger.info("Running startup services...")

    try:
        await client.set_bot_commands(USER_COMMANDS)
        logger.info("Default user commands set successfully.")

        for admin_id in settings.ADMIN_USER_IDS:
            try:
                await client.set_bot_commands(
                    ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id)
                )
            except Exception as e:
                logger.error(f"Failed to set commands for admin {admin_id}: {e}")
        logger.info(f"Admin commands set for {len(settings.ADMIN_USER_IDS)} admins.")

    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    await database.init_db()

    asyncio.create_task(check_expired_users_task(client))
    logger.info("Background task created. Bot is ready!")


@app.on_stop()
async def stop_services(client: Client):
    """Async tasks to run *before* Pyrogram disconnects."""
    logger.info("Running shutdown services...")
    await close_http_client()
    logger.info("HTTP client closed.")


if __name__ == "__main__":
    logger.info("Starting bot configuration...")

    app.api_id = settings.TELEGRAM_API_ID
    app.api_hash = settings.TELEGRAM_API_HASH
    app.bot_token = settings.TELEGRAM_BOT_TOKEN

    logger.info("Loading handlers...")
    load_all_handlers(app)
    logger.info("Handlers loaded.")

    logger.info("Bot configured. Starting Pyrogram's app.run()...")
    app.run()

    logger.info("Bot has stopped.")
