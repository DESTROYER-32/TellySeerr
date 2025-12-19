from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from bot import app


@app.on_message(filters.command("start", prefixes="/") & filters.private)
async def start_cmd(client: Client, message: Message):
    await message.reply(
        "👋 Welcome to the JellyRequest Bot!\n\n"
        "You can use me to request media for your Jellyfin server.\n"
        "To get started, you must link your account using the `/link` command.\n\n"
        "Type `/help` to see all available commands.",
        parse_mode=None,
    )


HELP_TEXT = """
**JellyRequest Bot Help**

**User Commands:**
• `/help`: Shows this help message.
• `/link <username> <password>`: Link your Telegram account to your Jellyfin/Jellyseerr account.
• `/unlink`: Remove the link between your accounts.
• `/request <name>`: Search for a movie or TV show to request.
• `/discover`: Browse popular and trending media.
• `/requests`: View the status of your past requests.
• `/watch`: See your personal watch statistics from Jellyfin.

**Direct Link Support:**
You can also send TMDB links directly to request media:
• Send TMDB links like: `https://themoviedb.org/movie/550-fight-club`
• Send TMDB TV links like: `https://tmdb.org/tv/1399-breaking-bad`

**Admin Commands:**
• `/invite` (reply to a user): Create a permanent account for the user.
• `/trial` (reply to a user): Create a 7-day trial account for the user.
• `/vip` (reply to a user): Create a 30-day trial account for the user.
• `/listusers`: List all users registered in the bot's database.
• `/deleteuser <username>`: Delete a user from Jellyfin, Jellyseerr, and the bot.
"""


@app.on_message(filters.command("help", prefixes="/"))
async def help_cmd(client: Client, message: Message):
    await message.reply(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)
