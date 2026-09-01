"""
Pydantic request/response models for the collection API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class CollectionStartRequest(BaseModel):
    """Request body for POST /api/collection/telegram/start"""
    topic: str = Field(..., description="The topic or phrase to search for")
    keywords: list[str] = Field(default_factory=list, description="Keywords to match in message text")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags to match (with or without #)")
    handles: list[str] = Field(default_factory=list, description="Account handles to match")
    lookback_hours: int = Field(default=24, ge=1, le=720, description="Hours to look back")
    target_items: int = Field(default=100, ge=1, le=10000, description="Max items to collect")


class CollectionStartResponse(BaseModel):
    """Response for POST /api/collection/telegram/start"""
    job_id: str
    platform: str = "telegram"
    status: str = "queued"
    message: str = "Collection job created and started"


class ChannelError(BaseModel):
    """Info about a channel that failed during collection."""
    channel: str
    error: str


class JobStatusResponse(BaseModel):
    """Response for GET /api/collection/{job_id}"""
    job_id: str
    status: str
    platform: str = "telegram"
    progress: int = 0
    channels_checked: int = 0
    channels_total: int = 0
    messages_scanned: int = 0
    relevant_items: int = 0
    duplicates_removed: int = 0
    final_items: int = 0
    target_items: int = 100
    current_channel: str = ""
    topic: str = ""
    lookback_hours: int = 24
    error_message: str = ""
    channel_errors: list[ChannelError] = []
    created_at: str = ""
    updated_at: str = ""


class SocialEventResponse(BaseModel):
    """A single collected social event for API response."""
    event_id: str
    platform: str = "telegram"
    event_type: str = "post"

    channel_id: Optional[str] = None
    channel_username: Optional[str] = None
    channel_title: Optional[str] = None
    message_id: Optional[int] = None

    author_id: Optional[str] = None
    author_username: Optional[str] = None
    author_display_name: Optional[str] = None

    content_text: Optional[str] = None
    timestamp: Optional[str] = None
    views: int = 0
    replies: int = 0
    forwards: int = 0

    relevance_score: float = 0.0
    matched_keywords: list[str] = []
    matched_hashtags: list[str] = []


class JobResultsResponse(BaseModel):
    """Response for GET /api/collection/{job_id}/results"""
    job_id: str
    platform: str = "telegram"
    status: str

    query: dict = {}
    statistics: dict = {}
    items: list[SocialEventResponse] = []


class TelegramStatusResponse(BaseModel):
    """Response for GET /api/collection/telegram/status"""
    connected: bool
    status: str  # "connected", "disconnected", "invalid_credentials"
    message: str = ""
