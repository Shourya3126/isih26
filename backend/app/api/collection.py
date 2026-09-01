"""
Collection API endpoints.

POST /api/collection/telegram/start   — Start a new Telegram collection job
GET  /api/collection/telegram/status  — Check Telegram connection status
GET  /api/collection/{job_id}         — Get job progress/status
GET  /api/collection/{job_id}/results — Get collected items for a job
"""

from fastapi import APIRouter, HTTPException, Query
from app.schemas.collection import (
    CollectionStartRequest,
    CollectionStartResponse,
    JobStatusResponse,
    JobResultsResponse,
    SocialEventResponse,
    TelegramStatusResponse,
    ChannelError,
)
from app.services.job_runner import run_telegram_collection
from app.services.telegram_service import check_connection
from app.database.db import get_job, get_events_by_job, get_all_events

router = APIRouter(prefix="/api/collection", tags=["collection"])


@router.post("/telegram/start", response_model=CollectionStartResponse)
async def start_telegram_collection(req: CollectionStartRequest):
    """
    Launch a Telegram collection pipeline.
    Returns immediately with a job_id; collection runs in the background.
    """
    # Verify Telegram is connected before starting
    conn = await check_connection()
    if not conn["connected"]:
        raise HTTPException(
            status_code=503,
            detail=f"Telegram is not connected: {conn['message']}",
        )

    job_id = await run_telegram_collection(
        topic=req.topic,
        keywords=req.keywords,
        hashtags=req.hashtags,
        handles=req.handles,
        lookback_hours=req.lookback_hours,
        target_items=req.target_items,
    )

    return CollectionStartResponse(
        job_id=job_id,
        platform="telegram",
        status="queued",
        message="Collection job created and started",
    )


@router.get("/telegram/status", response_model=TelegramStatusResponse)
async def telegram_connection_status():
    """Check whether the Telegram session is authenticated."""
    result = await check_connection()
    return TelegramStatusResponse(**result)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the current status and progress of a collection job."""
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Parse channel errors
    raw_errors = job.get("channel_errors_json", [])
    if isinstance(raw_errors, str):
        import json
        try:
            raw_errors = json.loads(raw_errors)
        except Exception:
            raw_errors = []

    channel_errors = []
    for err in (raw_errors or []):
        if isinstance(err, dict):
            channel_errors.append(ChannelError(
                channel=err.get("channel", "unknown"),
                error=err.get("error", "unknown error"),
            ))

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        platform=job.get("platform", "telegram"),
        progress=job.get("progress", 0),
        channels_checked=job.get("channels_checked", 0),
        channels_total=job.get("channels_total", 0),
        messages_scanned=job.get("messages_scanned", 0),
        relevant_items=job.get("relevant_items", 0),
        duplicates_removed=job.get("duplicates_removed", 0),
        final_items=job.get("final_items", 0),
        target_items=job.get("target_items", 100),
        current_channel=job.get("current_channel", ""),
        topic=job.get("topic", ""),
        lookback_hours=job.get("lookback_hours", 24),
        error_message=job.get("error_message", ""),
        channel_errors=channel_errors,
        created_at=job.get("created_at", ""),
        updated_at=job.get("updated_at", ""),
    )


@router.get("/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(job_id: str):
    """Get the collected items for a completed (or partial) job."""
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    events = await get_events_by_job(job_id)

    items = []
    for ev in events:
        items.append(SocialEventResponse(
            event_id=ev["event_id"],
            platform=ev.get("platform", "telegram"),
            event_type=ev.get("event_type", "post"),
            channel_id=ev.get("channel_id"),
            channel_username=ev.get("channel_username"),
            channel_title=ev.get("channel_title"),
            message_id=ev.get("message_id"),
            author_id=ev.get("author_id"),
            author_username=ev.get("author_username"),
            author_display_name=ev.get("author_display_name"),
            content_text=ev.get("content_text"),
            timestamp=ev.get("timestamp"),
            views=ev.get("views", 0),
            replies=ev.get("replies", 0),
            forwards=ev.get("forwards", 0),
            relevance_score=ev.get("relevance_score", 0.0),
            matched_keywords=ev.get("matched_keywords_json", []),
            matched_hashtags=ev.get("matched_hashtags_json", []),
        ))

    return JobResultsResponse(
        job_id=job_id,
        platform="telegram",
        status=job["status"],
        query={
            "topic": job.get("topic", ""),
            "lookback_hours": job.get("lookback_hours", 24),
        },
        statistics={
            "channels_checked": job.get("channels_checked", 0),
            "messages_scanned": job.get("messages_scanned", 0),
            "relevant_messages": job.get("relevant_items", 0),
            "duplicates_removed": job.get("duplicates_removed", 0),
            "final_items": job.get("final_items", 0),
        },
        items=items,
    )


@router.get("/events/all")
async def list_all_events(limit: int = Query(default=200, le=1000)):
    """Get all collected events across all jobs. Used by Evidence Vault."""
    events = await get_all_events(limit=limit)

    items = []
    for ev in events:
        items.append(SocialEventResponse(
            event_id=ev["event_id"],
            platform=ev.get("platform", "telegram"),
            event_type=ev.get("event_type", "post"),
            channel_id=ev.get("channel_id"),
            channel_username=ev.get("channel_username"),
            channel_title=ev.get("channel_title"),
            message_id=ev.get("message_id"),
            author_id=ev.get("author_id"),
            author_username=ev.get("author_username"),
            author_display_name=ev.get("author_display_name"),
            content_text=ev.get("content_text"),
            timestamp=ev.get("timestamp"),
            views=ev.get("views", 0),
            replies=ev.get("replies", 0),
            forwards=ev.get("forwards", 0),
            relevance_score=ev.get("relevance_score", 0.0),
            matched_keywords=ev.get("matched_keywords_json", []),
            matched_hashtags=ev.get("matched_hashtags_json", []),
        ))

    return {"total": len(items), "items": items}
