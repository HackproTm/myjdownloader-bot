"""Tests for utils.platform."""

from utils.platform import detect_platform


class TestDetectPlatform:

  def test_detects_youtube(self):
    assert detect_platform("https://www.youtube.com/watch?v=abc") == "YouTube"

  def test_detects_youtube_short_domain(self):
    assert detect_platform("https://youtu.be/abc") == "YouTube"

  def test_detects_instagram(self):
    assert detect_platform("https://instagram.com/p/abc") == "Instagram"

  def test_detects_x(self):
    assert detect_platform("https://x.com/user/status/1") == "X"

  def test_detects_facebook(self):
    assert detect_platform("https://www.facebook.com/watch/?v=1") == "Facebook"

  def test_returns_none_for_unknown_domain(self):
    assert detect_platform("https://example.com/file.zip") is None

  def test_returns_none_for_invalid_url(self):
    assert detect_platform("not a url") is None
