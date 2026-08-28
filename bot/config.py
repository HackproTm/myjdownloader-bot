import os
import socket
from typing import Optional
import logging

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

# Get MyJDownloader credentials from environment variables (required)
try:
  MYJD_EMAIL: str = _get_required_secret("MYJD_EMAIL",
                                         "MyJDownloader account email")
  MYJD_PASSWORD: str = _get_required_secret("MYJD_PASSWORD",
                                            "MyJDownloader account password")
  logger.info(
    f"MyJD credentials configured: email={_sanitize_for_logging(MYJD_EMAIL)}")
except ValueError as e:
  logger.error(str(e))
  raise

MYJD_DEVICE_NAME: str = os.environ.get("MYJD_DEVICE_NAME",
                                       socket.gethostname()).strip()
logger.info(f"MyJDownloader device name: {MYJD_DEVICE_NAME}")

# Get download settings from environment variables (optional)
DOWNLOADS_PATH: str = os.environ.get("DOWNLOADS_PATH", "/downloads").strip()
POLL_INTERVAL: int = int(os.environ.get("POLL_INTERVAL", "10"))
MAX_FILE_SIZE_BYTES: int = int(os.environ.get("MAX_FILE_SIZE_MB",
                                              "50")) * 1024 * 1024

logger.info("Configuration loaded successfully.")
