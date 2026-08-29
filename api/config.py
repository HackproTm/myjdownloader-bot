"""API-specific configuration (Telegram Mini App auth and CORS)."""

import os

from shared.config import _get_required_secret

TELEGRAM_TOKEN: str = _get_required_secret(
  "TELEGRAM_TOKEN", "Telegram Bot Token (used to validate Mini App requests)")

# Reuse the same chat allow-list as the bot, if configured.
_allowed_raw = os.environ.get("ALLOWED_CHAT_IDS", "").strip()
ALLOWED_CHAT_IDS: set[int] = (
  {int(x)
   for x in _allowed_raw.split(",") if x.strip()} if _allowed_raw else set())

# Comma-separated list of origins allowed to call this API (the Mini App's own
# origin). Empty means no CORS middleware is added (same-origin only).
CORS_ORIGINS: list[str] = [
  origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",")
  if origin.strip()
]
