"""
Normalization service — converts raw Telethon messages into
canonical SocialEvent dictionaries.
"""

from datetime import datetime, timezone


def normalize_telegram_message(
    message,
    channel_entity,
    relevance_result: dict,
    job_id: str,
) -> dict:
    """
    Convert a Telethon Message + channel entity into a canonical SocialEvent dict.

    Args:
        message:          telethon.tl.types.Message
        channel_entity:   telethon.tl.types.Channel
        relevance_result: dict from relevance_service.compute_relevance()
        job_id:           the parent collection job ID

    Returns:
        dict matching the SocialEvent storage schema
    """
    channel_id = str(channel_entity.id)
    channel_username = getattr(channel_entity, "username", "") or ""
    channel_title = getattr(channel_entity, "title", "") or channel_username

    msg_id = message.id
    event_id = f"telegram_{channel_id}_{msg_id}"

    # Author info — for channel posts the "author" is the channel itself
    # unless there is a from_id (e.g. discussion group replies)
    author_id = ""
    author_username = ""
    author_display_name = ""

    if message.sender:
        author_id = str(getattr(message.sender, "id", ""))
        author_username = getattr(message.sender, "username", "") or ""
        first = getattr(message.sender, "first_name", "") or ""
        last = getattr(message.sender, "last_name", "") or ""
        author_display_name = f"{first} {last}".strip() or author_username
    else:
        # Channel post — attribute to the channel
        author_id = channel_id
        author_username = channel_username
        author_display_name = channel_title

    # Engagement
    views = message.views or 0
    forwards = message.forwards or 0
    replies_count = 0
    if message.replies:
        replies_count = message.replies.replies or 0

    # Timestamp
    msg_timestamp = message.date
    if msg_timestamp and msg_timestamp.tzinfo is None:
        msg_timestamp = msg_timestamp.replace(tzinfo=timezone.utc)

    # Content
    content_text = message.text or ""

    # Build raw metadata for audit / future use
    raw_metadata = {
        "forward_from": None,
        "reply_to_msg_id": None,
        "media_type": None,
        "grouped_id": getattr(message, "grouped_id", None),
    }

    if message.fwd_from:
        fwd = message.fwd_from
        raw_metadata["forward_from"] = {
            "from_id": str(getattr(fwd, "from_id", "")),
            "channel_post": getattr(fwd, "channel_post", None),
        }

    if message.reply_to:
        raw_metadata["reply_to_msg_id"] = getattr(message.reply_to, "reply_to_msg_id", None)

    if message.media:
        raw_metadata["media_type"] = type(message.media).__name__

    return {
        "event_id": event_id,
        "job_id": job_id,
        "platform": "telegram",
        "event_type": "post",
        "channel_id": channel_id,
        "channel_username": channel_username,
        "channel_title": channel_title,
        "message_id": msg_id,
        "author_id": author_id,
        "author_username": author_username,
        "author_display_name": author_display_name,
        "content_text": content_text,
        "timestamp": msg_timestamp.isoformat() if msg_timestamp else "",
        "views": views,
        "replies": replies_count,
        "forwards": forwards,
        "relevance_score": relevance_result.get("score", 0.0),
        "matched_keywords": relevance_result.get("matched_keywords", []),
        "matched_hashtags": relevance_result.get("matched_hashtags", []),
        "raw_metadata": raw_metadata,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
