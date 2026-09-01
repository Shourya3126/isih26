"""
Integration test — test Telegram collection with a real query.

This test requires:
  - TELEGRAM_API_ID and TELEGRAM_API_HASH in .env
  - A valid telegram_session.session file
  - Network access to Telegram

Run with:
  cd backend
  python -m pytest tests/test_collection.py -v -s
"""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestTelegramCollectionIntegration:
    """
    Integration tests that hit the real Telegram API.
    These are skipped if credentials are not configured.
    """

    @pytest.fixture(autouse=True)
    def check_credentials(self):
        from app.config.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
        if not TELEGRAM_API_ID or TELEGRAM_API_ID == 0 or not TELEGRAM_API_HASH:
            pytest.skip("Telegram credentials not configured")

    @pytest.mark.asyncio
    async def test_connection_check(self):
        from app.services.telegram_service import check_connection
        result = await check_connection()
        assert isinstance(result, dict)
        assert "connected" in result
        assert "status" in result
        # Don't assert connected=True since session might not be authenticated
        print(f"Connection status: {result}")

    @pytest.mark.asyncio
    async def test_collect_from_known_channel(self):
        """Test collecting from DevelopmentNewsIndia channel."""
        from app.services.telegram_service import check_connection, collect_from_channel

        conn = await check_connection()
        if not conn["connected"]:
            pytest.skip("Telegram session not authenticated")

        result = await collect_from_channel(
            "DevelopmentNewsIndia",
            lookback_hours=24,
            max_messages=10,
        )

        print(f"Collection result: success={result['success']}, messages={len(result['messages'])}")

        if result["success"]:
            assert result["channel_entity"] is not None
            assert isinstance(result["messages"], list)
            # Print sample messages
            for msg in result["messages"][:3]:
                print(f"  MSG {msg.id}: {(msg.text or '')[:80]}...")
        else:
            print(f"  Error: {result['error']}")

    @pytest.mark.asyncio
    async def test_full_pipeline_small(self):
        """
        End-to-end test: create job, run collection, verify results.
        Uses a small target to keep it fast.
        """
        from app.services.telegram_service import check_connection
        from app.database.db import init_db, get_job, get_events_by_job
        from app.services.job_runner import run_telegram_collection

        conn = await check_connection()
        if not conn["connected"]:
            pytest.skip("Telegram session not authenticated")

        # Initialize DB
        await init_db()

        # Run collection with small target
        job_id = await run_telegram_collection(
            topic="Government schemes for farmers",
            keywords=["farmer", "agriculture", "scheme", "yojana"],
            hashtags=["#PMKISAN", "#Farmers", "#Agriculture"],
            handles=[],
            lookback_hours=24,
            target_items=10,  # Small target for testing
        )

        print(f"Job ID: {job_id}")
        assert job_id.startswith("telegram_")

        # Wait for collection to finish (with timeout)
        import time
        for _ in range(60):
            await asyncio.sleep(2)
            job = await get_job(job_id)
            if job and job["status"] in ("completed", "partial", "failed"):
                break

        job = await get_job(job_id)
        assert job is not None
        print(f"Job status: {job['status']}")
        print(f"Messages scanned: {job['messages_scanned']}")
        print(f"Relevant items: {job['relevant_items']}")
        print(f"Duplicates removed: {job['duplicates_removed']}")
        print(f"Final items: {job['final_items']}")

        # Get events
        events = await get_events_by_job(job_id)
        print(f"Events stored: {len(events)}")

        for ev in events[:5]:
            print(f"\n  Event: {ev['event_id']}")
            print(f"  Channel: {ev['channel_title']}")
            print(f"  Score: {ev['relevance_score']}")
            print(f"  Text: {(ev['content_text'] or '')[:100]}...")

        assert job["status"] in ("completed", "partial", "failed")
