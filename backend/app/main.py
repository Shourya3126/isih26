"""
SocialScope Backend — FastAPI Application Entry Point.

Serves the Telegram collection API. CORS configured for the Vite frontend.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import FRONTEND_ORIGIN
from app.database.db import init_db
from app.api.collection import router as collection_router

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("socialscope")


# ── Lifespan ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="SocialScope Backend",
    description="Multi-Platform Social Intelligence — Telegram Collection API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(collection_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "socialscope-backend"}
