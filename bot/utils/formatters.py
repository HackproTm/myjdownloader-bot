"""Formatting utilities for messages and data."""


def format_size(size_bytes: int) -> str:
  """
  Convert bytes to human-readable format.

  Args:
    size_bytes: Size in bytes

  Returns:
    Formatted size string (e.g., "1.5 MB")
  """
  for unit in ("B", "KB", "MB", "GB", "TB"):
    if size_bytes < 1024:
      return f"{size_bytes:.1f} {unit}"
    size_bytes //= 1024
  return f"{size_bytes:.1f} PB"


def progress_bar(pct: float, width: int = 12) -> str:
  """
  Create a visual progress bar.

  Args:
    pct: Percentage (0-100)
    width: Width of the bar

  Returns:
    ASCII progress bar string
  """
  filled = round(pct / 100 * width)
  return "█" * filled + "░" * (width - filled)
