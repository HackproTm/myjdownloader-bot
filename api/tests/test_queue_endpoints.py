"""Tests for api.routers.queue (auth wiring + basic endpoint behavior)."""

import hashlib
import hmac
import time
from unittest.mock import AsyncMock
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

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


class TestAuthWiring:

  def test_missing_header_is_rejected(self):
    response = client.get("/api/queue")
    assert response.status_code == 422

  def test_invalid_init_data_is_rejected(self):
    response = client.get("/api/queue",
                          headers={"X-Telegram-Init-Data": "bogus"})
    assert response.status_code == 401


class TestGetQueue:

  def test_returns_manager_data(self, monkeypatch):
    monkeypatch.setattr("api.routers.queue.manager.list_queue",
                        AsyncMock(return_value=[{
                          "uuid": 1,
                          "name": "f.zip"
                        }]))
    init_data = build_init_data(auth_date=str(int(time.time())))

    response = client.get("/api/queue",
                          headers={"X-Telegram-Init-Data": init_data})

    assert response.status_code == 200
    assert response.json() == [{"uuid": 1, "name": "f.zip"}]


class TestAddToQueue:

  def test_returns_duplicate_status(self, monkeypatch):
    monkeypatch.setattr(
      "api.routers.queue.history.find_duplicate",
      lambda url, name: {
        "matched_by": "url",
        "added_at": "2026-01-01",
        "package_name": "f.zip",
      },
    )
    init_data = build_init_data(auth_date=str(int(time.time())))

    response = client.post(
      "/api/queue",
      headers={"X-Telegram-Init-Data": init_data},
      json={"url": "http://x.com/f.zip"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "duplicate"

  def test_queues_when_single_option(self, monkeypatch):
    monkeypatch.setattr("api.routers.queue.history.find_duplicate",
                        lambda url, name: None)
    monkeypatch.setattr("api.routers.queue.history.record", lambda *a: None)
    monkeypatch.setattr(
      "api.routers.queue.manager.collect_link",
      AsyncMock(
        return_value={
          "package_uuid": 1,
          "package_name": "f.zip",
          "options": [{
            "link_uuid": 10,
            "variant_id": None,
            "label": "f.zip"
          }],
        }),
    )
    monkeypatch.setattr("api.routers.queue.manager.finalize_selection",
                        AsyncMock())
    init_data = build_init_data(auth_date=str(int(time.time())))

    response = client.post(
      "/api/queue",
      headers={"X-Telegram-Init-Data": init_data},
      json={"url": "http://x.com/f.zip"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


class TestRemoveFromQueue:

  def test_returns_404_when_not_found(self, monkeypatch):
    monkeypatch.setattr("api.routers.queue.manager.remove_from_queue",
                        AsyncMock(return_value=False))
    init_data = build_init_data(auth_date=str(int(time.time())))

    response = client.delete("/api/queue/missing.zip",
                             headers={"X-Telegram-Init-Data": init_data})

    assert response.status_code == 404
