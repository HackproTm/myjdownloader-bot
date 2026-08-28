"""Tests for utils.file_utils."""

import time

from utils.file_utils import newest_file, search_in_tree


class TestSearchInTree:

  def test_finds_file_in_nested_directory(self, tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    target = sub / "file.txt"
    target.write_text("data")

    assert search_in_tree(str(tmp_path), "file.txt") == str(target)

  def test_returns_none_when_missing(self, tmp_path):
    assert search_in_tree(str(tmp_path), "missing.txt") is None

  def test_skips_hidden_directories(self, tmp_path):
    hidden = tmp_path / ".bot_data"
    hidden.mkdir()
    (hidden / "history.json").write_text("{}")

    assert search_in_tree(str(tmp_path), "history.json") is None


class TestNewestFile:

  def test_returns_most_recently_modified_file(self, tmp_path):
    old = tmp_path / "old.txt"
    old.write_text("old")
    time.sleep(0.01)
    new = tmp_path / "new.txt"
    new.write_text("new")

    assert newest_file(str(tmp_path)) == str(new)

  def test_skips_temporary_extensions(self, tmp_path):
    (tmp_path / "download.part").write_text("partial")
    (tmp_path / "download.crdownload").write_text("partial")

    assert newest_file(str(tmp_path)) is None

  def test_returns_none_for_empty_directory(self, tmp_path):
    assert newest_file(str(tmp_path)) is None

  def test_ignores_hidden_directories_and_files(self, tmp_path):
    (tmp_path / "real.txt").write_text("data")
    hidden_dir = tmp_path / ".bot_data"
    hidden_dir.mkdir()
    time.sleep(0.01)
    (hidden_dir / "history.json").write_text("{}")
    (tmp_path / ".hidden_file").write_text("x")

    assert newest_file(str(tmp_path)) == str(tmp_path / "real.txt")
