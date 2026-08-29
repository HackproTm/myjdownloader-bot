"""Tests for api.auth (Telegram Mini App initData validation)."""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from api.auth import validate_init_data

# Matches the TELEGRAM_TOKEN env var set by conftest.py.
_BOT_TOKEN = "test-telegram-token"


def build_init_data(**fields) -> str:
  """Build a validly-signed initData string for tests."""
  data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
  secret_key = hmac.new(b"WebAppData", _BOT_TOKEN.encode(),
                        hashlib.sha256).digest()
  computed_hash = hmac.new(secret_key, data_check_string.encode(),
                           hashlib.sha256).hexdigest()
  fields["hash"] = computed_hash
  return urlencode(fields)


class TestValidateInitData:

  def test_accepts_correctly_signed_data(self):
    init_data = build_init_data(
      auth_date=str(int(time.time())),
      user=json.dumps({
        "id": 12345,
        "first_name": "Test"
      }),
    )

    result = validate_init_data(init_data)

    assert result["user"]["id"] == 12345

  def test_rejects_invalid_hash(self):
    init_data = build_init_data(auth_date=str(int(time.time())))
    tampered = init_data[:-4] + "0000"

    with pytest.raises(ValueError, match="Invalid initData signature"):
      validate_init_data(tampered)

  def test_rejects_missing_hash(self):
    with pytest.raises(ValueError, match="Missing hash"):
      validate_init_data("auth_date=123")

  def test_rejects_expired_auth_date(self):
    old_timestamp = str(int(time.time()) - 100000)
    init_data = build_init_data(auth_date=old_timestamp)

    with pytest.raises(ValueError, match="expired"):
      validate_init_data(init_data)
