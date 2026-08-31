"""Shared pytest fixtures and test environment setup for the API."""

import os
import sys
from pathlib import Path

# Make the repo-root "shared" and "api" packages importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Required secrets must exist BEFORE api.config is imported by any module under test.
# Force-set (not setdefault) so tests are deterministic even if the shell already
# has these exported (e.g. from manually running the bot/API against a real .env).
os.environ["TELEGRAM_TOKEN"] = "test-telegram-token"
os.environ["JD_EMAIL"] = "test@example.com"
os.environ["JD_PASSWORD"] = "test-password"
os.environ["JD_DEVICENAME"] = "test-device"
os.environ["DOWNLOADS_PATH"] = "/tmp/downloads"
os.environ["ALLOWED_CHAT_IDS"] = ""
