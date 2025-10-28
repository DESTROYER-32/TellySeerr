import aiosqlite
import os
import logging
from config import settings

DB_PATH = settings.DB_PATH
logger = logging.getLogger(__name__)


async def init_db():
    """Initializes the SQLite database asynchronously."""

    logger.info(f"Attempting to initialize database at: {DB_PATH}")
    db_dir = os.path.dirname(DB_PATH)

    if db_dir and not os.path.exists(db_dir):
        logger.info(f"Creating directory: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
    elif not db_dir:
        logger.info("Database path is in the root directory. No directory to create.")

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            logger.info("Database connection successful. Creating tables...")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS linked_users (
                    telegram_id TEXT PRIMARY KEY,
                    jellyseerr_user_id TEXT,
                    jellyfin_user_id TEXT,
                    username TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    guild_id TEXT,
                    role_name TEXT
                )
            """)

            await db.commit()
            logger.info("Database tables created/verified successfully.")

    except Exception as e:
        logger.error(f"CRITICAL: Failed to initialize database: {e}")


async def delete_linked_user(telegram_id: str):
    """Deletes a linked user from the database by their ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM linked_users WHERE telegram_id=?", (str(telegram_id),)
        )
        await db.commit()


async def store_linked_user(
    telegram_id,
    jellyseerr_user_id,
    jellyfin_user_id,
    username=None,
    expires_at=None,
    guild_id=None,
    role_name=None,
):
    """Stores or updates a linked user in the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO linked_users (telegram_id, jellyseerr_user_id, jellyfin_user_id, username, expires_at, guild_id, role_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                jellyseerr_user_id=excluded.jellyseerr_user_id,
                jellyfin_user_id=excluded.jellyfin_user_id,
                username=excluded.username,
                expires_at=excluded.expires_at,
                guild_id=excluded.guild_id,
                role_name=excluded.role_name
        """,
            (
                str(telegram_id),
                jellyseerr_user_id,
                jellyfin_user_id,
                username,
                expires_at,
                guild_id,
                role_name,
            ),
        )
        await db.commit()


async def get_linked_user(telegram_id: str):
    """Retrieves a linked user's details by their ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT jellyseerr_user_id, jellyfin_user_id, username, expires_at
            FROM linked_users WHERE telegram_id=?
        """,
            (str(telegram_id),),
        ) as cursor:
            return await cursor.fetchone()


async def get_all_expiring_users():
    """Retrieves all IDs for users with an expiration date."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT telegram_id, jellyseerr_user_id, jellyfin_user_id, expires_at FROM linked_users WHERE expires_at IS NOT NULL"
        ) as cursor:
            return await cursor.fetchall()


async def get_all_linked_users():
    """Retrieves all users from the bot's database for /listusers."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT telegram_id, username, role_name, expires_at FROM linked_users ORDER BY created_at"
        ) as cursor:
            return await cursor.fetchall()


async def get_user_by_username(username: str):
    """Retrieves a user's IDs by their Jellyfin/Jellyseerr username."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT telegram_id, jellyseerr_user_id, jellyfin_user_id FROM linked_users WHERE username = ?",
            (username,),
        ) as cursor:
            return await cursor.fetchone()
