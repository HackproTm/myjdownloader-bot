"""Tests for utils.validators."""

from unittest.mock import MagicMock

from utils.validators import extract_urls, is_authorized, is_valid_url


class TestExtractUrls:

  def test_single_http_url(self):
    assert extract_urls("get http://example.com/file.zip now") == [
      "http://example.com/file.zip"
    ]

  def test_single_https_url(self):
    assert extract_urls("https://example.com/a.zip") == [
      "https://example.com/a.zip"
    ]

  def test_no_url_present(self):
    assert extract_urls("no links here") == []

  def test_multiple_urls(self):
    text = "http://a.com/1.zip and http://b.com/2.zip"
    assert extract_urls(text) == ["http://a.com/1.zip", "http://b.com/2.zip"]

  def test_case_insensitive_scheme(self):
    assert extract_urls("HTTP://EXAMPLE.COM/file") == [
      "HTTP://EXAMPLE.COM/file"
    ]


class TestIsAuthorized:

  def test_allows_all_when_no_restriction(self, monkeypatch):
    import config

    monkeypatch.setattr(config, "ALLOWED_CHAT_IDS", set())
    update = MagicMock()
    update.effective_chat.id = 999
    assert is_authorized(update) is True

  def test_allows_chat_in_allowlist(self, monkeypatch):
    import config

    monkeypatch.setattr(config, "ALLOWED_CHAT_IDS", {123, 456})
    update = MagicMock()
    update.effective_chat.id = 123
    assert is_authorized(update) is True

  def test_denies_chat_not_in_allowlist(self, monkeypatch):
    import config

    monkeypatch.setattr(config, "ALLOWED_CHAT_IDS", {123})
    update = MagicMock()
    update.effective_chat.id = 999
    assert is_authorized(update) is False


class TestIsValidUrl:

  def test_accepts_http_url(self):
    assert is_valid_url("http://example.com/file.zip") is True

  def test_accepts_https_url(self):
    assert is_valid_url("https://example.com/file.zip") is True

  def test_accepts_url_with_surrounding_whitespace(self):
    assert is_valid_url("  https://example.com/file.zip  ") is True

  def test_rejects_plain_text(self):
    assert is_valid_url("not a url") is False

  def test_rejects_text_with_extra_words_after_url(self):
    assert is_valid_url("https://example.com/file.zip please") is False
