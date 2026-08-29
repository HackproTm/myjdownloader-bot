"""Telegram Mini App authentication (initData validation).

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from api.config import ALLOWED_CHAT_IDS, TELEGRAM_TOKEN

_MAX_AUTH_AGE_SECONDS = 24 * 60 * 60


def _compute_hash(data_check_string: str, bot_token: str) -> str:
  """Compute the expected HMAC-SHA256 hash for a Mini App data-check-string."""
  secret_key = hmac.new(b"WebAppData", bot_token.encode(),
                        hashlib.sha256).digest()
  return hmac.new(secret_key, data_check_string.encode(),
                  hashlib.sha256).hexdigest()


def validate_init_data(init_data: str) -> dict:
  """
  Validate a Telegram Mini App `initData` string and return its parsed fields.

  Args:
    init_data: The raw `initData` string sent by the Mini App frontend
      (`Telegram.WebApp.initData`)

  Returns:
    The parsed fields, with "user" decoded from JSON into a dict.

  Raises:
    ValueError: If the signature is missing, invalid, or expired.
  """
  pairs = dict(parse_qsl(init_data, keep_blank_values=True))
  received_hash = pairs.pop("hash", None)
  if not received_hash:
    raise ValueError("Missing hash in initData.")

  data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
  expected_hash = _compute_hash(data_check_string, TELEGRAM_TOKEN)

  if not hmac.compare_digest(expected_hash, received_hash):
    raise ValueError("Invalid initData signature.")

  auth_date = int(pairs.get("auth_date", "0"))
  if time.time() - auth_date > _MAX_AUTH_AGE_SECONDS:
    raise ValueError("initData has expired, reopen the Mini App.")

  if "user" in pairs:
    pairs["user"] = json.loads(pairs["user"])
  return pairs


async def require_telegram_user(x_telegram_init_data: str = Header(
  ..., alias="X-Telegram-Init-Data")) -> dict:
  """FastAPI dependency: validate initData and enforce the chat allow-list."""
  try:
    data = validate_init_data(x_telegram_init_data)
  except ValueError as exc:
    raise HTTPException(status_code=401, detail=str(exc)) from exc

  user = data.get("user") or {}
  chat_id = user.get("id")
  if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
    raise HTTPException(status_code=403, detail="Not authorized.")

  return data
