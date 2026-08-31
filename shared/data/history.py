"""Persistent history of URLs/file names ever queued for download."""

import json
import os
import time
from typing import Optional

from shared.config import DOWNLOADS_PATH

# Stored under a hidden subfolder so it's never picked up as a downloaded file.
_HISTORY_FILE = os.path.join(DOWNLOADS_PATH, ".bot_data", "history.json")


def _load() -> list:
  """Load all recorded history entries."""
  if not os.path.exists(_HISTORY_FILE):
    return []
  try:
    with open(_HISTORY_FILE, "r", encoding="utf-8") as fh:
      return json.load(fh)
  except (json.JSONDecodeError, OSError):
    return []


def _save(records: list) -> None:
  """Persist history entries to disk."""
  os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)
  with open(_HISTORY_FILE, "w", encoding="utf-8") as fh:
    json.dump(records, fh, indent=2)


def find_duplicate(url: str, package_name: str) -> Optional[dict]:
  """
  Find a previous record matching the given URL or package name.

  Args:
    url: URL to check
    package_name: Package/file name to check

  Returns:
    The matching record (plus a "matched_by" key set to "url" or "name"),
    or None if nothing matches.
  """
  for entry in _load():
    if entry["url"] == url:
      return {**entry, "matched_by": "url"}
    if entry["package_name"] == package_name:
      return {**entry, "matched_by": "name"}
  return None


def record(url: str, package_name: str) -> None:
  """Persist a newly queued download in the history."""
  entries = _load()
  entries.append({
    "url": url,
    "package_name": package_name,
    "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
  })
  _save(entries)


def update_file_path(url: str, package_name: str, file_path: str) -> None:
  """
  Attach the resulting local file path to the most recent matching entry.

  This lets a later duplicate /queue request offer to resend the file
  instead of downloading it again.

  Args:
    url: URL of the completed download
    package_name: Package/file name of the completed download
    file_path: Absolute path of the downloaded file on disk
  """
  entries = _load()
  for entry in reversed(entries):
    if entry["url"] == url or entry["package_name"] == package_name:
      entry["file_path"] = file_path
      break
  _save(entries)


def find_by_package_name(package_name: str) -> Optional[dict]:
  """
  Find the most recent history entry with the given package name.

  Args:
    package_name: Package/file name to look up

  Returns:
    The matching record, or None if nothing matches.
  """
  for entry in reversed(_load()):
    if entry["package_name"] == package_name:
      return entry
  return None
