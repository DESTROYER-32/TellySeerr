import httpx
from config import settings

http_client = httpx.AsyncClient(timeout=15.0)

jellyseerr_headers = {
    "X-Api-Key": settings.JELLYSEERR_API_KEY,
    "Content-Type": "application/json",
}

jellyfin_headers = {
    "X-Emby-Token": settings.JELLYFIN_API_KEY,
    "Content-Type": "application/json",
}


async def close_http_client():
    """To be called on bot shutdown."""
    await http_client.aclose()
