"""Shared pytest fixtures and test environment setup for the API."""

import os
import sys
from pathlib import Path

# Make the repo-root "shared" and "api" packages importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Required secrets must exist BEFORE api.config is imported by any module under test.
os.environ.setdefault("TELEGRAM_TOKEN", "test-telegram-token")
os.environ.setdefault("MYJD_EMAIL", "test@example.com")
os.environ.setdefault("MYJD_PASSWORD", "test-password")
os.environ.setdefault("MYJD_DEVICE_NAME", "test-device")
os.environ.setdefault("DOWNLOADS_PATH", "/tmp/downloads")
