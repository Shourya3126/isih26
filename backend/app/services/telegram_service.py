"""
Telegram service — manages the Telethon client singleton.
Reuses the existing .session file. Never exposes credentials.
"""

import logging
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    ChannelInvalidError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from app.config.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, SESSION_FILE_PATH

logger = logging.getLogger("socialscope.telegram")

# ── Singleton client ──────────────────────────────────────────────────

_client: TelegramClient | None = None


def _get_client() -> TelegramClient:
    """Return the Telethon client (lazy-initialized, reuses session file)."""
    global _client
    if _client is None:
        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
        _client = TelegramClient(
            SESSION_FILE_PATH,
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH,
        )
    return _client


async def ensure_connected() -> TelegramClient:
    """Connect the client if not already connected. Returns the client."""
    client = _get_client()
    if not client.is_connected():
        await client.connect()
    return client


async def check_connection() -> dict:
    """
    Verify the Telegram session is authenticated.
    Returns {"connected": bool, "status": str, "message": str}
    Never exposes credentials.
    """
    try:
        client = await ensure_connected()
        if not await client.is_user_authorized():
            return {
                "connected": False,
                "status": "disconnected",
                "message": "Telegram session is not authorized. Run the authentication flow first.",
            }
        me = await client.get_me()
        return {
            "connected": True,
            "status": "connected",
            "message": f"Authenticated as {me.first_name} (@{me.username or 'N/A'})",
        }
    except Exception as e:
        logger.error("Telegram connection check failed: %s", e)
        return {
            "connected": False,
            "status": "disconnected",
            "message": f"Connection failed: {type(e).__name__}",
        }


async def collect_from_channel(
    channel_username: str,
    lookback_hours: int,
    max_messages: int = 500,
) -> dict:
    """
    Retrieve recent messages from a single Telegram channel.

    Args:
        channel_username:  the @username of the channel (without @)
        lookback_hours:    only consider messages newer than now - lookback_hours
        max_messages:      hard limit on messages to fetch from this channel

    Returns:
        {
            "success": bool,
            "channel_entity": ...,  # Telethon channel object
            "messages": [...],      # list of Telethon Message objects
            "error": str | None
        }
    """
    try:
        client = await ensure_connected()

        # Resolve channel
        try:
            channel = await client.get_entity(channel_username)
        except (ChannelPrivateError, ChannelInvalidError) as e:
            return {
                "success": False,
                "channel_entity": None,
                "messages": [],
                "error": f"Channel inaccessible: {e}",
            }
        except (UsernameInvalidError, UsernameNotOccupiedError) as e:
            return {
                "success": False,
                "channel_entity": None,
                "messages": [],
                "error": f"Invalid channel username '{channel_username}': {e}",
            }

        # Time boundary
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        messages = []
        async for message in client.iter_messages(channel, limit=max_messages):
            # Time filter — stop if we've gone past the lookback window
            msg_date = message.date
            if msg_date and msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            if msg_date and msg_date < cutoff:
                break

            messages.append(message)

        return {
            "success": True,
            "channel_entity": channel,
            "messages": messages,
            "error": None,
        }

    except FloodWaitError as e:
        logger.warning("FloodWaitError on channel %s: wait %ds", channel_username, e.seconds)
        return {
            "success": False,
            "channel_entity": None,
            "messages": [],
            "error": f"Rate limited (FloodWait {e.seconds}s). Try again later.",
        }
    except Exception as e:
        logger.error("Error collecting from %s: %s", channel_username, e, exc_info=True)
        return {
            "success": False,
            "channel_entity": None,
            "messages": [],
            "error": f"{type(e).__name__}: {e}",
        }
