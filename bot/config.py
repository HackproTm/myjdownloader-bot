"""Bot-specific configuration (Telegram token and chat allow-list)."""

import logging
import os

from shared.config import (  # noqa: F401
  DOWNLOADS_PATH, JD_DEVICENAME, JD_EMAIL, JD_PASSWORD, MAX_FILE_SIZE_BYTES,
  POLL_INTERVAL, _get_required_secret, _sanitize_for_logging,
)

logger = logging.getLogger(__name__)

# Get Telegram Bot Token from environment variables (required)
try:
  TELEGRAM_TOKEN: str = _get_required_secret("TELEGRAM_TOKEN",
                                             "Telegram Bot Token")
  logger.info(
    f"Telegram Bot Token configured: {_sanitize_for_logging(TELEGRAM_TOKEN)}")
except ValueError as e:
  logger.error(str(e))
  raise

# Get allowed chat IDs from environment variables (optional)
_allowed_raw = os.environ.get("ALLOWED_CHAT_IDS", "").strip()
ALLOWED_CHAT_IDS: set[int] = (
  {int(x)
   for x in _allowed_raw.split(",") if x.strip()} if _allowed_raw else set())

logger.info("Bot configuration loaded successfully.")
