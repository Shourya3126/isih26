"""
Async SQLite database manager.
Creates tables on startup, provides CRUD for jobs and social events.
"""

import aiosqlite
import json
from pathlib import Path
from app.config.settings import DATABASE_PATH


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Create tables if they don't exist."""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS collection_jobs (
                job_id          TEXT PRIMARY KEY,
                platform        TEXT NOT NULL DEFAULT 'telegram',
                status          TEXT NOT NULL DEFAULT 'queued',
                topic           TEXT,
                keywords_json   TEXT DEFAULT '[]',
                hashtags_json   TEXT DEFAULT '[]',
                handles_json    TEXT DEFAULT '[]',
                lookback_hours  INTEGER DEFAULT 24,
                target_items    INTEGER DEFAULT 100,
                progress        INTEGER DEFAULT 0,
                channels_checked INTEGER DEFAULT 0,
                channels_total  INTEGER DEFAULT 0,
                messages_scanned INTEGER DEFAULT 0,
                relevant_items  INTEGER DEFAULT 0,
                duplicates_removed INTEGER DEFAULT 0,
                final_items     INTEGER DEFAULT 0,
                current_channel TEXT DEFAULT '',
                error_message   TEXT DEFAULT '',
                channel_errors_json TEXT DEFAULT '[]',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS social_events (
                event_id            TEXT PRIMARY KEY,
                job_id              TEXT NOT NULL,
                platform            TEXT NOT NULL DEFAULT 'telegram',
                event_type          TEXT NOT NULL DEFAULT 'post',
                channel_id          TEXT,
                channel_username    TEXT,
                channel_title       TEXT,
                message_id          INTEGER,
                author_id           TEXT,
                author_username     TEXT,
                author_display_name TEXT,
                content_text        TEXT,
                timestamp           TEXT,
                views               INTEGER DEFAULT 0,
                replies             INTEGER DEFAULT 0,
                forwards            INTEGER DEFAULT 0,
                relevance_score     REAL DEFAULT 0.0,
                matched_keywords_json TEXT DEFAULT '[]',
                matched_hashtags_json TEXT DEFAULT '[]',
                raw_metadata_json   TEXT DEFAULT '{}',
                collected_at        TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES collection_jobs(job_id),
                UNIQUE(platform, channel_id, message_id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_job ON social_events(job_id);
            CREATE INDEX IF NOT EXISTS idx_events_platform ON social_events(platform);
            CREATE INDEX IF NOT EXISTS idx_events_channel ON social_events(channel_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON collection_jobs(status);
        """)
        await db.commit()
    finally:
        await db.close()


# ── Job CRUD ──────────────────────────────────────────────────────────

async def create_job(job: dict) -> dict:
    """Insert a new collection job."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO collection_jobs
               (job_id, platform, status, topic, keywords_json, hashtags_json,
                handles_json, lookback_hours, target_items, channels_total,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job["job_id"], job["platform"], job["status"], job["topic"],
                json.dumps(job.get("keywords", [])),
                json.dumps(job.get("hashtags", [])),
                json.dumps(job.get("handles", [])),
                job["lookback_hours"], job["target_items"],
                job.get("channels_total", 0),
                job["created_at"], job["updated_at"],
            ),
        )
        await db.commit()
        return job
    finally:
        await db.close()


async def update_job(job_id: str, updates: dict):
    """Update fields on an existing job."""
    db = await get_db()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            if key.endswith("_json") or key == "channel_errors_json":
                values.append(json.dumps(value) if isinstance(value, (list, dict)) else value)
            else:
                values.append(value)
            set_clauses.append(f"{key} = ?")
        values.append(job_id)
        query = f"UPDATE collection_jobs SET {', '.join(set_clauses)} WHERE job_id = ?"
        await db.execute(query, values)
        await db.commit()
    finally:
        await db.close()


async def get_job(job_id: str) -> dict | None:
    """Fetch a job by ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM collection_jobs WHERE job_id = ?", (job_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        result = dict(row)
        # Parse JSON fields
        for field in ("keywords_json", "hashtags_json", "handles_json", "channel_errors_json"):
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return result
    finally:
        await db.close()


# ── Social Event CRUD ─────────────────────────────────────────────────

async def insert_event(event: dict) -> bool:
    """Insert a social event. Returns False if duplicate."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT OR IGNORE INTO social_events
               (event_id, job_id, platform, event_type,
                channel_id, channel_username, channel_title, message_id,
                author_id, author_username, author_display_name,
                content_text, timestamp, views, replies, forwards,
                relevance_score, matched_keywords_json, matched_hashtags_json,
                raw_metadata_json, collected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event["event_id"], event["job_id"], event["platform"],
                event["event_type"], event.get("channel_id"),
                event.get("channel_username"), event.get("channel_title"),
                event.get("message_id"), event.get("author_id"),
                event.get("author_username"), event.get("author_display_name"),
                event.get("content_text"), event.get("timestamp"),
                event.get("views", 0), event.get("replies", 0),
                event.get("forwards", 0), event.get("relevance_score", 0.0),
                json.dumps(event.get("matched_keywords", [])),
                json.dumps(event.get("matched_hashtags", [])),
                json.dumps(event.get("raw_metadata", {})),
                event["collected_at"],
            ),
        )
        await db.commit()
        return db.total_changes > 0
    finally:
        await db.close()


async def get_events_by_job(job_id: str) -> list[dict]:
    """Fetch all social events for a given job."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM social_events WHERE job_id = ? ORDER BY relevance_score DESC",
            (job_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            item = dict(row)
            for field in ("matched_keywords_json", "matched_hashtags_json", "raw_metadata_json"):
                if item.get(field):
                    try:
                        item[field] = json.loads(item[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            results.append(item)
        return results
    finally:
        await db.close()


async def get_all_events(limit: int = 200) -> list[dict]:
    """Fetch all collected social events across all jobs, newest first."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM social_events ORDER BY collected_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            item = dict(row)
            for field in ("matched_keywords_json", "matched_hashtags_json", "raw_metadata_json"):
                if item.get(field):
                    try:
                        item[field] = json.loads(item[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            results.append(item)
        return results
    finally:
        await db.close()

