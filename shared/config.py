"""Shared configuration: MyJDownloader connectivity and download settings.

Used by both the Telegram bot (bot/config.py re-exports these) and the
Mini App API.
"""

import logging
import os
import socket
from typing import Optional

logger = logging.getLogger(__name__)


def _get_required_secret(key: str, description: str) -> str:
  """
  Retrieves a required secret from environment variables.

  Args:
    key: Name of the environment variable
    description: Human-readable description of the secret (does NOT include the value)

  Returns:
    The value of the secret

  Raises:
    ValueError: If the variable is not configured
  """
  value = os.environ.get(key)
  if not value or not value.strip():
    raise ValueError(
      f"Required environment variable not configured: {key} ({description}). "
      "Please configure it before running the application.")
  return value.strip()


def _sanitize_for_logging(value: Optional[str], prefix_len: int = 4) -> str:
  """Masks a value for safe logging (shows only the first few characters)."""
  if not value:
    return "[NOT_CONFIGURED]"
  return f"{value[:prefix_len]}{'*' * (len(value) - prefix_len)}"


# Get MyJDownloader credentials from environment variables (required)
try:
  JD_EMAIL: str = _get_required_secret("JD_EMAIL",
                                       "MyJDownloader account email")
  JD_PASSWORD: str = _get_required_secret("JD_PASSWORD",
                                          "MyJDownloader account password")
  logger.info(
    f"MyJD credentials configured: email={_sanitize_for_logging(JD_EMAIL)}")
except ValueError as e:
  logger.error(str(e))
  raise

JD_DEVICENAME: str = os.environ.get("JD_DEVICENAME",
                                    socket.gethostname()).strip()
logger.info(f"MyJDownloader device name: {JD_DEVICENAME}")

# Get download settings from environment variables (optional)
DOWNLOADS_PATH: str = os.environ.get("DOWNLOADS_PATH", "/downloads").strip()
POLL_INTERVAL: int = int(os.environ.get("POLL_INTERVAL", "10"))
MAX_FILE_SIZE_BYTES: int = int(os.environ.get("MAX_FILE_SIZE_MB",
                                              "50")) * 1024 * 1024

logger.info("Shared configuration loaded successfully.")
