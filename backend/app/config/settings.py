"""
Application settings — loads environment variables.
Never exposes secrets in API responses or logs.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level above backend/)
_project_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_project_root / ".env")

# Telegram API credentials (required)
TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION: str = os.getenv("TELEGRAM_SESSION", "telegram_session")

# The .session file is stored in the project root alongside the .env
SESSION_FILE_PATH: str = str(_project_root / TELEGRAM_SESSION)

# Database
DATABASE_PATH: str = str(Path(__file__).resolve().parent.parent.parent / "socialscope.db")

# Server
BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

# Frontend origin for CORS
FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173")
