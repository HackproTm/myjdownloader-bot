"""Shared pytest fixtures and test environment setup."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make the "bot" package directory importable (config, data, services, etc.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Make the repo-root "shared" package importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Required secrets must exist BEFORE config.py is imported by any module under test.
# Force-set (not setdefault) so tests are deterministic even if the shell already
# has these exported (e.g. from manually running the bot/API against a real .env).
import os  # noqa: E402

os.environ["TELEGRAM_TOKEN"] = "test-telegram-token"
os.environ["JD_EMAIL"] = "test@example.com"
os.environ["JD_PASSWORD"] = "test-password"
os.environ["JD_DEVICENAME"] = "test-device"
os.environ["DOWNLOADS_PATH"] = "/tmp/downloads"
os.environ["ALLOWED_CHAT_IDS"] = ""


@pytest.fixture
def mock_update():
  """Create a mock Telegram Update with an async-capable message."""
  update = MagicMock()
  update.effective_chat.id = 12345
  update.message.text = ""
  update.message.reply_text = AsyncMock()
  # Mirrors real PTB behavior where effective_message resolves to .message.
  update.effective_message = update.message
  return update


@pytest.fixture
def mock_context():
  """Create a mock Telegram context with an async-capable bot."""
  context = MagicMock()
  context.bot.send_document = AsyncMock()
  context.chat_data = {}
  return context
