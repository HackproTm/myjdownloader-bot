"""File system utilities."""

import os
from typing import Optional


def search_in_tree(root: str, filename: str) -> Optional[str]:
  """
  Search for a file in a directory tree.

  Args:
    root: Root directory to search
    filename: Filename to search for

  Returns:
    Full path to the file, or None if not found
  """
  for dirpath, dirnames, files in os.walk(root):
    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
    if filename in files:
      return os.path.join(dirpath, filename)
  return None


def newest_file(root: str) -> Optional[str]:
  """
  Find the most recently modified file in a directory tree.

  Skips temporary files (.part, .tmp, .crdownload, .download).

  Args:
    root: Root directory to search

  Returns:
    Path to the newest file, or None if not found
  """
  skip_extensions = {".part", ".tmp", ".crdownload", ".download"}
  newest_path, newest_mtime = None, 0.0

  for dirpath, dirnames, files in os.walk(root):
    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
    for filename in files:
      if filename.startswith(".") or any(
          filename.endswith(ext) for ext in skip_extensions):
        continue
      path = os.path.join(dirpath, filename)
      mtime = os.path.getmtime(path)
      if mtime > newest_mtime:
        newest_mtime, newest_path = mtime, path

  return newest_path
