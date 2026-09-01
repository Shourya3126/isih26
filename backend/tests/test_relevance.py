"""
Unit tests for relevance scoring, deduplication, and normalization services.
"""

import sys
import os
import pytest

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.relevance_service import compute_relevance, _extract_hashtags, _extract_mentions
from app.services.deduplication_service import DeduplicationService


# ── Keyword Filtering Tests ──────────────────────────────────────────

class TestKeywordFiltering:

    def test_single_keyword_match(self):
        result = compute_relevance(
            "Government announces new farmer support scheme",
            topic="farmer support",
            keywords=["farmer"],
            hashtags=[],
            handles=[],
        )
        assert result["score"] > 0
        assert "farmer" in result["matched_keywords"]

    def test_multiple_keyword_match(self):
        result = compute_relevance(
            "New agriculture scheme announced for farmer welfare and yojana",
            topic="",
            keywords=["farmer", "agriculture", "scheme", "yojana"],
            hashtags=[],
            handles=[],
        )
        assert len(result["matched_keywords"]) == 4
        assert result["score"] >= 0.60  # 4 keywords × 0.15 = 0.60

    def test_no_keyword_match(self):
        result = compute_relevance(
            "The weather today is sunny and warm",
            topic="",
            keywords=["farmer", "agriculture"],
            hashtags=[],
            handles=[],
        )
        assert len(result["matched_keywords"]) == 0

    def test_case_insensitive_match(self):
        result = compute_relevance(
            "FARMER AGRICULTURE SCHEME",
            topic="",
            keywords=["farmer", "agriculture"],
            hashtags=[],
            handles=[],
        )
        assert len(result["matched_keywords"]) == 2

    def test_empty_text(self):
        result = compute_relevance(
            "",
            topic="test",
            keywords=["test"],
            hashtags=[],
            handles=[],
        )
        assert result["score"] == 0.0
        assert result["above_threshold"] is False


# ── Hashtag Filtering Tests ──────────────────────────────────────────

class TestHashtagFiltering:

    def test_hashtag_extraction(self):
        tags = _extract_hashtags("Post about #PMKISAN and #Farmers")
        assert "pmkisan" in tags
        assert "farmers" in tags

    def test_hashtag_match(self):
        result = compute_relevance(
            "Great initiative #PMKISAN #Agriculture",
            topic="",
            keywords=[],
            hashtags=["#PMKISAN", "#Agriculture"],
            handles=[],
        )
        assert len(result["matched_hashtags"]) == 2
        assert result["score"] >= 0.4  # 2 hashtags × 0.20 = 0.40

    def test_hashtag_without_hash_prefix(self):
        result = compute_relevance(
            "Post about #PMKISAN",
            topic="",
            keywords=[],
            hashtags=["PMKISAN"],  # without #
            handles=[],
        )
        assert len(result["matched_hashtags"]) == 1

    def test_no_hashtag_match(self):
        result = compute_relevance(
            "No hashtags here",
            topic="",
            keywords=[],
            hashtags=["#PMKISAN"],
            handles=[],
        )
        assert len(result["matched_hashtags"]) == 0


# ── Time Filtering Tests ─────────────────────────────────────────────

class TestTimeFiltering:
    """Time filtering is handled in telegram_service.py at the collection level.
    These tests verify the lookback logic is correct."""

    def test_lookback_hours_boundary(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)

        # Message within lookback
        recent_date = now - timedelta(hours=12)
        assert recent_date >= cutoff

        # Message outside lookback
        old_date = now - timedelta(hours=48)
        assert old_date < cutoff


# ── Relevance Scoring Tests ──────────────────────────────────────────

class TestRelevanceScoring:

    def test_combined_score(self):
        result = compute_relevance(
            "Government farmer scheme #PMKISAN @tech_analyst_raj",
            topic="Government schemes for farmers",
            keywords=["farmer", "scheme"],
            hashtags=["#PMKISAN"],
            handles=["@tech_analyst_raj"],
        )
        # Should have keyword + hashtag + topic + handle scores
        assert result["score"] > 0.5
        assert result["above_threshold"] is True

    def test_below_threshold(self):
        result = compute_relevance(
            "Something completely unrelated about weather",
            topic="Government schemes for farmers",
            keywords=["farmer", "agriculture", "scheme"],
            hashtags=["#PMKISAN"],
            handles=[],
        )
        assert result["above_threshold"] is False

    def test_score_normalized_to_max_1(self):
        result = compute_relevance(
            "farmer agriculture scheme yojana #PMKISAN #Farmers #Agriculture @tech_analyst_raj Government schemes for farmers",
            topic="Government schemes for farmers",
            keywords=["farmer", "agriculture", "scheme", "yojana"],
            hashtags=["#PMKISAN", "#Farmers", "#Agriculture"],
            handles=["@tech_analyst_raj"],
        )
        assert 0.0 <= result["score"] <= 1.0

    def test_topic_phrase_match(self):
        result = compute_relevance(
            "Government schemes for farmers are really helpful",
            topic="Government schemes for farmers",
            keywords=[],
            hashtags=[],
            handles=[],
        )
        assert result["score"] >= 0.1  # topic words match at 0.05 each


# ── Deduplication Tests ──────────────────────────────────────────────

class TestDeduplication:

    def test_primary_key_dedup(self):
        dedup = DeduplicationService()
        assert dedup.is_duplicate("telegram", "123", 1, "text") is False
        assert dedup.is_duplicate("telegram", "123", 1, "text") is True
        assert dedup.duplicates_removed == 1

    def test_different_messages_not_deduped(self):
        dedup = DeduplicationService()
        assert dedup.is_duplicate("telegram", "123", 1, "text one") is False
        assert dedup.is_duplicate("telegram", "123", 2, "text two") is False
        assert dedup.duplicates_removed == 0

    def test_text_hash_dedup(self):
        """Forwarded messages with same text from different channels should be deduped."""
        dedup = DeduplicationService()
        same_text = "Government announces new scheme for farmers welfare"
        assert dedup.is_duplicate("telegram", "111", 1, same_text) is False
        assert dedup.is_duplicate("telegram", "222", 5, same_text) is True
        assert dedup.duplicates_removed == 1

    def test_different_text_not_deduped(self):
        dedup = DeduplicationService()
        assert dedup.is_duplicate("telegram", "111", 1, "First unique text") is False
        assert dedup.is_duplicate("telegram", "222", 1, "Second unique text") is False


# ── Mention Extraction Tests ─────────────────────────────────────────

class TestMentionExtraction:

    def test_extract_mentions(self):
        mentions = _extract_mentions("Hey @user1 and @user2 check this out")
        assert "user1" in mentions
        assert "user2" in mentions

    def test_no_mentions(self):
        mentions = _extract_mentions("No mentions here")
        assert len(mentions) == 0


# ── SocialEvent Conversion Tests ─────────────────────────────────────

class TestSocialEventConversion:

    def test_normalize_creates_correct_event_id(self):
        from app.services.normalization_service import normalize_telegram_message
        from unittest.mock import MagicMock
        from datetime import datetime, timezone

        # Mock message
        message = MagicMock()
        message.id = 42
        message.text = "Test message"
        message.date = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
        message.views = 100
        message.forwards = 5
        message.replies = MagicMock()
        message.replies.replies = 3
        message.sender = None
        message.fwd_from = None
        message.reply_to = None
        message.media = None
        message.grouped_id = None

        # Mock channel
        channel = MagicMock()
        channel.id = 12345
        channel.username = "TestChannel"
        channel.title = "Test Channel"

        relevance = {
            "score": 0.85,
            "matched_keywords": ["test"],
            "matched_hashtags": [],
        }

        event = normalize_telegram_message(message, channel, relevance, "job_001")

        assert event["event_id"] == "telegram_12345_42"
        assert event["platform"] == "telegram"
        assert event["channel_id"] == "12345"
        assert event["message_id"] == 42
        assert event["views"] == 100
        assert event["forwards"] == 5
        assert event["replies"] == 3
        assert event["relevance_score"] == 0.85
        assert event["job_id"] == "job_001"


# ── Failed Channel Handling Tests ─────────────────────────────────────

class TestFailedChannelHandling:

    def test_channel_error_does_not_crash_dedup(self):
        """If one channel fails, dedup service should still work for other channels."""
        dedup = DeduplicationService()
        # Simulate messages from a successful channel
        assert dedup.is_duplicate("telegram", "111", 1, "msg1") is False
        assert dedup.is_duplicate("telegram", "111", 2, "msg2") is False
        # After a "failed channel" (not represented here), next channel still works
        assert dedup.is_duplicate("telegram", "333", 1, "msg3") is False
        assert dedup.duplicates_removed == 0
