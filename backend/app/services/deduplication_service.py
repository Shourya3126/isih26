"""
Deduplication service.

Primary dedup:   platform + channel_id + message_id
Secondary dedup: text content hash for forwarded/copied duplicate content.
"""

import hashlib
from typing import Set


class DeduplicationService:
    """Tracks seen events during a single collection run."""

    def __init__(self):
        self._seen_ids: Set[str] = set()      # "platform_channelId_msgId"
        self._seen_hashes: Set[str] = set()    # sha256 of normalized text
        self.duplicates_removed: int = 0

    def _make_primary_key(self, platform: str, channel_id: str, message_id: int) -> str:
        return f"{platform}_{channel_id}_{message_id}"

    def _make_text_hash(self, text: str) -> str:
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def is_duplicate(self, platform: str, channel_id: str, message_id: int, text: str) -> bool:
        """
        Check whether a message is a duplicate.

        Returns True if the message should be skipped.
        """
        # Primary dedup: exact platform+channel+message
        pk = self._make_primary_key(platform, channel_id, message_id)
        if pk in self._seen_ids:
            self.duplicates_removed += 1
            return True

        # Secondary dedup: content hash (catches forwarded/copied text)
        if text and text.strip():
            th = self._make_text_hash(text)
            if th in self._seen_hashes:
                self.duplicates_removed += 1
                return True
            self._seen_hashes.add(th)

        self._seen_ids.add(pk)
        return False
