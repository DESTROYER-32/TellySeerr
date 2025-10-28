from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config(BaseSettings):
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_BOT_TOKEN: str

    JELLYSEERR_URL: str
    JELLYSEERR_API_KEY: str

    JELLYFIN_URL: str
    JELLYFIN_API_KEY: str

    # Path to the database (defaults to the root folder)
    DB_PATH: str = "jellyseerr_bot.db"

    # Admin User IDs
    ADMIN_USER_IDS: list[int]


settings = Config()
