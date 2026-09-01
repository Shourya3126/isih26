"""
Job runner — orchestrates the full Telegram collection pipeline
as an async background task.

Architecture:
  asyncio.create_task() for now, designed so Celery can replace it
  without rewriting the collector logic.

Pipeline:
  Create Job → For each channel →
    Collect → Filter → Deduplicate → Normalize → Store →
  Update Job Status
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.config.telegram_sources import TELEGRAM_CHANNELS
from app.services.telegram_service import collect_from_channel
from app.services.relevance_service import compute_relevance
from app.services.normalization_service import normalize_telegram_message
from app.services.deduplication_service import DeduplicationService
from app.database.db import create_job, update_job, insert_event

logger = logging.getLogger("socialscope.job_runner")


def _generate_job_id() -> str:
    """Generate a unique job ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    import random
    suffix = random.randint(100, 999)
    return f"telegram_{ts}_{suffix}"


async def run_telegram_collection(
    topic: str,
    keywords: list[str],
    hashtags: list[str],
    handles: list[str],
    lookback_hours: int,
    target_items: int,
) -> str:
    """
    Entry point — creates a job and launches the collection pipeline
    as a background task. Returns the job_id immediately.
    """
    job_id = _generate_job_id()
    now = datetime.now(timezone.utc).isoformat()

    job = {
        "job_id": job_id,
        "platform": "telegram",
        "status": "queued",
        "topic": topic,
        "keywords": keywords,
        "hashtags": hashtags,
        "handles": handles,
        "lookback_hours": lookback_hours,
        "target_items": target_items,
        "channels_total": len(TELEGRAM_CHANNELS),
        "created_at": now,
        "updated_at": now,
    }

    await create_job(job)

    # Launch as background task (Celery-replaceable seam)
    # Note: topic words are extracted and scored separately inside
    # relevance_service with lower weight — no need to mix them into keywords
    asyncio.create_task(_execute_collection(job_id, topic, keywords, hashtags, handles, lookback_hours, target_items))

    return job_id


async def _execute_collection(
    job_id: str,
    topic: str,
    keywords: list[str],
    hashtags: list[str],
    handles: list[str],
    lookback_hours: int,
    target_items: int,
):
    """
    The actual collection pipeline. Runs as a background task.
    """
    now_str = lambda: datetime.now(timezone.utc).isoformat()
    dedup = DeduplicationService()

    channels_checked = 0
    messages_scanned = 0
    relevant_items = 0
    final_items = 0
    channel_errors = []

    try:
        # Mark as running
        await update_job(job_id, {
            "status": "running",
            "updated_at": now_str(),
        })

        # Distribute items across channels: allow each channel up to
        # (target / num_channels * 2) items so all channels contribute
        num_channels = len(TELEGRAM_CHANNELS)
        per_channel_cap = max(10, (target_items // num_channels) * 2)

        for ch_username in TELEGRAM_CHANNELS:
            # Check if we've hit the overall target
            if final_items >= target_items:
                logger.info("Job %s: reached target of %d items, stopping", job_id, target_items)
                break

            # Update current channel
            channels_checked += 1
            progress = int((channels_checked / num_channels) * 100)
            await update_job(job_id, {
                "current_channel": ch_username,
                "channels_checked": channels_checked,
                "progress": min(progress, 95),  # reserve 100 for completion
                "updated_at": now_str(),
            })

            # ── Stage: Collect ──
            logger.info("Job %s: collecting from %s", job_id, ch_username)
            result = await collect_from_channel(
                ch_username,
                lookback_hours=lookback_hours,
                max_messages=min(500, target_items * 5),  # fetch enough to filter
            )

            if not result["success"]:
                logger.warning("Job %s: channel %s failed: %s", job_id, ch_username, result["error"])
                channel_errors.append({"channel": ch_username, "error": result["error"]})
                await update_job(job_id, {
                    "channel_errors_json": channel_errors,
                    "messages_scanned": messages_scanned,
                    "updated_at": now_str(),
                })
                continue

            channel_entity = result["channel_entity"]
            channel_messages = result["messages"]
            channel_items_added = 0

            for message in channel_messages:
                if final_items >= target_items:
                    break
                if channel_items_added >= per_channel_cap:
                    break  # Move to next channel

                messages_scanned += 1

                # ── Stage 1: Text extraction ──
                text = message.text or ""
                if not text.strip():
                    continue  # Skip empty messages

                # ── Stage: Deduplicate ──
                channel_id = str(channel_entity.id)
                if dedup.is_duplicate("telegram", channel_id, message.id, text):
                    continue

                # ── Stages 2–5: Relevance filtering ──
                rel = compute_relevance(
                    message_text=text,
                    topic=topic,
                    keywords=keywords,
                    hashtags=hashtags,
                    handles=handles,
                )

                if not rel["above_threshold"]:
                    continue

                relevant_items += 1

                # ── Stage: Normalize ──
                event = normalize_telegram_message(
                    message=message,
                    channel_entity=channel_entity,
                    relevance_result=rel,
                    job_id=job_id,
                )

                # ── Stage: Store ──
                inserted = await insert_event(event)
                if inserted:
                    final_items += 1
                    channel_items_added += 1

                # Periodic progress update (every 10 items)
                if final_items % 10 == 0:
                    await update_job(job_id, {
                        "messages_scanned": messages_scanned,
                        "relevant_items": relevant_items,
                        "duplicates_removed": dedup.duplicates_removed,
                        "final_items": final_items,
                        "updated_at": now_str(),
                    })

            # Small delay between channels to be polite to Telegram API
            await asyncio.sleep(1)

        # ── Determine final status ──
        status = "completed"
        if channel_errors and final_items > 0:
            status = "partial"
        elif channel_errors and final_items == 0:
            status = "failed"

        await update_job(job_id, {
            "status": status,
            "progress": 100,
            "channels_checked": channels_checked,
            "messages_scanned": messages_scanned,
            "relevant_items": relevant_items,
            "duplicates_removed": dedup.duplicates_removed,
            "final_items": final_items,
            "current_channel": "",
            "channel_errors_json": channel_errors,
            "error_message": f"{len(channel_errors)} channel(s) failed" if channel_errors else "",
            "updated_at": now_str(),
        })

        logger.info(
            "Job %s: %s — scanned %d msgs, %d relevant, %d deduped, %d final",
            job_id, status, messages_scanned, relevant_items,
            dedup.duplicates_removed, final_items,
        )

    except Exception as e:
        logger.error("Job %s: unhandled error: %s", job_id, e, exc_info=True)
        await update_job(job_id, {
            "status": "failed",
            "error_message": f"Unhandled error: {type(e).__name__}: {e}",
            "messages_scanned": messages_scanned,
            "relevant_items": relevant_items,
            "duplicates_removed": dedup.duplicates_removed,
            "final_items": final_items,
            "updated_at": now_str(),
        })
