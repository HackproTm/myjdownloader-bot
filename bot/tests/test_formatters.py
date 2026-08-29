"""Tests for utils.formatters."""

from shared.utils.formatters import (
  describe_option_label,
  format_queue_list,
  format_size,
  format_status_list,
  progress_bar,
)


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


class TestFormatQueueList:

  def test_returns_empty_message_when_no_entries(self):
    assert format_queue_list([]) == "📭 The queue is empty."

  def test_includes_name_url_and_percentage(self):
    entries = [{
      "name": "file.zip",
      "url": "http://x.com/file.zip",
      "bytes_total": 200,
      "bytes_loaded": 100,
    }]

    result = format_queue_list(entries)

    assert "file.zip" in result
    assert "http://x.com/file.zip" in result
    assert "50%" in result

  def test_handles_zero_bytes_total(self):
    entries = [{
      "name": "file.zip",
      "url": "",
      "bytes_total": 0,
      "bytes_loaded": 0,
    }]

    result = format_queue_list(entries)

    assert "0%" in result
    assert "-" in result


class TestFormatStatusList:

  def test_returns_empty_message_when_no_entries(self):
    assert format_status_list([]) == "📭 No downloads in progress."

  def test_includes_name_status_and_url(self):
    entries = [{
      "name": "file.zip",
      "url": "http://x.com/file.zip",
      "status": "Downloading",
    }]

    result = format_status_list(entries)

    assert "file.zip" in result
    assert "Downloading" in result
    assert "http://x.com/file.zip" in result

  def test_full_percent(self):
    assert progress_bar(100) == "█" * 12

  def test_half_with_custom_width(self):
    assert progress_bar(50, width=10) == "█████░░░░░"

  def test_respects_custom_width(self):
    assert len(progress_bar(30, width=20)) == 20


class TestDescribeOptionLabel:

  def test_video_extension_gets_video_icon(self):
    assert describe_option_label("clip.mp4") == "🎬 clip.mp4"

  def test_audio_extension_gets_audio_icon(self):
    assert describe_option_label("song.m4a") == "🎵 song.m4a"

  def test_image_extension_gets_image_icon(self):
    assert describe_option_label("thumb.jpg") == "🖼 thumb.jpg"

  def test_subtitle_extension_gets_subtitle_icon(self):
    assert describe_option_label("movie.en.srt") == "📝 movie.en.srt"

  def test_unknown_extension_gets_generic_icon(self):
    assert describe_option_label("archive.zip") == "📄 archive.zip"

  def test_appends_variant_name_when_given(self):
    assert describe_option_label(
      "clip.mp4", "1080p60 (mp4)") == "🎬 clip.mp4 — 1080p60 (mp4)"
