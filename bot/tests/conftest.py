"""Shared pytest fixtures and test environment setup."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make the "bot" package directory importable (config, data, services, etc.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Required secrets must exist BEFORE config.py is imported by any module under test.
import os  # noqa: E402

os.environ.setdefault("TELEGRAM_TOKEN", "test-telegram-token")
os.environ.setdefault("MYJD_EMAIL", "test@example.com")
os.environ.setdefault("MYJD_PASSWORD", "test-password")
os.environ.setdefault("MYJD_DEVICE_NAME", "test-device")
os.environ.setdefault("DOWNLOADS_PATH", "/tmp/downloads")


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
