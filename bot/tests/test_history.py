"""Tests for data.history."""

import shared.data.history as history


def _use_temp_history(tmp_path, monkeypatch):
  """Point the history module at a temporary file for test isolation."""
  monkeypatch.setattr(history, "_HISTORY_FILE", str(tmp_path / "history.json"))


class TestFindDuplicate:

  def test_returns_none_when_no_history(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)

    assert history.find_duplicate("http://x.com/f.zip", "f.zip") is None

  def test_matches_by_url(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)
    history.record("http://x.com/f.zip", "f.zip")

    match = history.find_duplicate("http://x.com/f.zip", "other_name.zip")

    assert match["matched_by"] == "url"

  def test_matches_by_package_name(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)
    history.record("http://x.com/f.zip", "f.zip")

    match = history.find_duplicate("http://other.com/g.zip", "f.zip")

    assert match["matched_by"] == "name"


class TestRecord:

  def test_persists_entry_to_disk(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)

    history.record("http://x.com/f.zip", "f.zip")

    entries = history._load()
    assert len(entries) == 1
    assert entries[0]["url"] == "http://x.com/f.zip"
    assert entries[0]["package_name"] == "f.zip"


class TestUpdateFilePath:

  def test_attaches_file_path_to_matching_entry(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)
    history.record("http://x.com/f.zip", "f.zip")

    history.update_file_path("http://x.com/f.zip", "f.zip", "/downloads/f.zip")

    match = history.find_duplicate("http://x.com/f.zip", "f.zip")
    assert match["file_path"] == "/downloads/f.zip"

  def test_matches_by_package_name_too(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)
    history.record("http://x.com/f.zip", "f.zip")

    history.update_file_path("http://other.com/g.zip", "f.zip",
                             "/downloads/f.zip")

    match = history.find_duplicate("http://x.com/f.zip", "f.zip")
    assert match["file_path"] == "/downloads/f.zip"

  def test_does_nothing_when_no_match(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)
    history.record("http://x.com/f.zip", "f.zip")

    history.update_file_path("http://none.com/x", "unrelated", "/downloads/x")

    match = history.find_duplicate("http://x.com/f.zip", "f.zip")
    assert "file_path" not in match


class TestFindByPackageName:

  def test_returns_none_when_no_match(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)

    assert history.find_by_package_name("missing.zip") is None

  def test_returns_matching_entry(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)
    history.record("http://x.com/f.zip", "f.zip")

    entry = history.find_by_package_name("f.zip")

    assert entry["url"] == "http://x.com/f.zip"

  def test_returns_most_recent_match(self, tmp_path, monkeypatch):
    _use_temp_history(tmp_path, monkeypatch)
    history.record("http://old.com/f.zip", "f.zip")
    history.record("http://new.com/f.zip", "f.zip")

    entry = history.find_by_package_name("f.zip")

    assert entry["url"] == "http://new.com/f.zip"
