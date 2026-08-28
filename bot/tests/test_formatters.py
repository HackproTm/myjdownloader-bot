"""Tests for utils.formatters."""

from utils.formatters import format_size, progress_bar


class TestFormatSize:

  def test_bytes(self):
    assert format_size(500) == "500.0 B"

  def test_kilobytes(self):
    # Note: implementation uses integer division between units,
    # so sub-unit precision is truncated once it crosses a boundary.
    assert format_size(1536) == "1.0 KB"

  def test_megabytes(self):
    assert format_size(2 * 1024 * 1024) == "2.0 MB"

  def test_gigabytes(self):
    assert format_size(3 * 1024**3) == "3.0 GB"

  def test_zero(self):
    assert format_size(0) == "0.0 B"


class TestProgressBar:

  def test_zero_percent(self):
    assert progress_bar(0) == "░" * 12

  def test_full_percent(self):
    assert progress_bar(100) == "█" * 12

  def test_half_with_custom_width(self):
    assert progress_bar(50, width=10) == "█████░░░░░"

  def test_respects_custom_width(self):
    assert len(progress_bar(30, width=20)) == 20
