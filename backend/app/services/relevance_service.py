"""
Relevance scoring service — multi-stage deterministic filtering.

Scoring model (additive per-match, not proportional):
  Each keyword match   = +0.15  (user-specified terms)
  Each hashtag match   = +0.20  (high-signal, explicitly targeted)
  Each handle match    = +0.10
  Topic phrase bonus   = +0.10  (if full topic phrase appears verbatim)
  Each topic-only word = +0.05  (auto-extracted, lower weight)

Score capped at 1.0. Threshold configurable via telegram_sources.py.

This means a post matching "farmer" + "#Agriculture" scores:
  0.15 (keyword) + 0.20 (hashtag) = 0.35 (35%)
While a post matching only "government" scores:
  0.05 (topic word) = 0.05 (5%)
"""

import re
import unicodedata
from app.config.telegram_sources import RELEVANCE_THRESHOLD


def _normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip accents."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_hashtags(text: str) -> list[str]:
    """Extract #hashtags from text, returned lowercase without the # prefix."""
    return [tag.lower() for tag in re.findall(r"#(\w+)", text)]


def _extract_mentions(text: str) -> list[str]:
    """Extract @mentions from text, returned lowercase without the @ prefix."""
    return [m.lower() for m in re.findall(r"@(\w+)", text)]


def compute_relevance(
    message_text: str,
    topic: str,
    keywords: list[str],
    hashtags: list[str],
    handles: list[str],
) -> dict:
    """
    Compute a relevance score for a message using additive per-match scoring.

    Each matched keyword/hashtag/handle adds a fixed amount (not proportional).
    This ensures a post matching "farmer" + "#Agriculture" always scores higher
    than a post matching just "government".

    Returns:
        {
            "score": float (0.0 – 1.0),
            "matched_keywords": [...],
            "matched_hashtags": [...],
            "matched_handles": [...],
            "above_threshold": bool
        }
    """
    if not message_text or not message_text.strip():
        return {
            "score": 0.0,
            "matched_keywords": [],
            "matched_hashtags": [],
            "matched_handles": [],
            "above_threshold": False,
        }

    normalized = _normalize_text(message_text)
    raw_score = 0.0
    matched_keywords = []
    matched_hashtags = []
    matched_handles = []

    # Identify which words are topic-only (auto-extracted, lower weight)
    stop_words = {
        "the", "and", "for", "with", "from", "this", "that", "are",
        "was", "were", "has", "have", "had", "not", "but", "its",
        "can", "will", "about", "into", "over", "such",
    }
    topic_words_set = set()
    if topic:
        topic_words_set = {
            w.lower() for w in topic.split()
            if len(w) > 2 and w.lower() not in stop_words
        }

    user_kw_set = set()
    for kw in keywords:
        kw_norm = _normalize_text(kw)
        if kw_norm:
            user_kw_set.add(kw_norm)

    # Topic-only words = in topic but NOT in user keywords
    topic_only_words = topic_words_set - user_kw_set

    # ── User keyword matches: +0.15 each ──
    for kw in user_kw_set:
        if kw in normalized:
            matched_keywords.append(kw)
            raw_score += 0.15

    # ── Hashtag matches: +0.20 each (highest signal) ──
    if hashtags:
        msg_tags = _extract_hashtags(message_text)
        norm_hashtags = [h.lstrip("#").lower() for h in hashtags if h.strip()]
        for tag in norm_hashtags:
            if tag in msg_tags:
                matched_hashtags.append(f"#{tag}")
                raw_score += 0.20

    # ── Topic-only word matches: +0.05 each (low weight) ──
    if topic_only_words:
        for tw in topic_only_words:
            if tw in normalized:
                raw_score += 0.05

    # ── Handle matches: +0.10 each ──
    if handles:
        msg_mentions = _extract_mentions(message_text)
        norm_handles = [h.lstrip("@").lower() for h in handles if h.strip()]
        for handle in norm_handles:
            if handle in msg_mentions:
                matched_handles.append(f"@{handle}")
                raw_score += 0.10

    # ── Exact topic phrase bonus: +0.10 ──
    if topic:
        norm_topic = _normalize_text(topic)
        if len(norm_topic) > 5 and norm_topic in normalized:
            raw_score += 0.10

    # Cap at 1.0
    score = min(1.0, max(0.0, raw_score))

    return {
        "score": round(score, 4),
        "matched_keywords": matched_keywords,
        "matched_hashtags": matched_hashtags,
        "matched_handles": matched_handles,
        "above_threshold": score >= RELEVANCE_THRESHOLD,
    }
