"""Tests for config.py helper functions and environment-driven settings."""

import importlib

import pytest

import config


class TestSanitizeForLogging:

  def test_masks_value_keeping_prefix(self):
    assert config._sanitize_for_logging("secretvalue") == "secr" + "*" * 7

  def test_returns_placeholder_for_none(self):
    assert config._sanitize_for_logging(None) == "[NOT_CONFIGURED]"

  def test_respects_custom_prefix_length(self):
    assert config._sanitize_for_logging("abcdefgh",
                                        prefix_len=2) == "ab" + "*" * 6


class TestGetRequiredSecret:

  def test_returns_stripped_value(self, monkeypatch):
    monkeypatch.setenv("SOME_SECRET", "  value123  ")
    assert config._get_required_secret("SOME_SECRET", "desc") == "value123"

  def test_raises_when_missing(self, monkeypatch):
    monkeypatch.delenv("SOME_SECRET", raising=False)
    with pytest.raises(ValueError, match="SOME_SECRET"):
      config._get_required_secret("SOME_SECRET", "desc")

  def test_raises_when_blank(self, monkeypatch):
    monkeypatch.setenv("SOME_SECRET", "   ")
    with pytest.raises(ValueError):
      config._get_required_secret("SOME_SECRET", "desc")


class TestDeviceNameFallback:

  def test_falls_back_to_hostname_when_not_configured(self, monkeypatch):
    monkeypatch.delenv("JD_DEVICENAME", raising=False)
    monkeypatch.setattr("socket.gethostname", lambda: "resolved-hostname")

    import shared.config as shared_config

    importlib.reload(shared_config)
    importlib.reload(config)
    try:
      assert config.JD_DEVICENAME == "resolved-hostname"
    finally:
      monkeypatch.undo()
      importlib.reload(shared_config)
      importlib.reload(config)
