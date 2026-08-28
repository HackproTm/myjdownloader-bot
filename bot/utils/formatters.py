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


def _truncate(text: str, width: int) -> str:
  """Truncate text to a max width, adding an ellipsis if needed."""
  return text if len(text) <= width else text[:width - 1] + "…"


def format_queue_list(entries: list) -> str:
  """
  Format queue entries as a monospace table with download percentage.

  Args:
    entries: List of dicts with "name", "url", "bytes_total", "bytes_loaded"

  Returns:
    Markdown code block with a NAME / % / URL table
  """
  if not entries:
    return "📭 The queue is empty."

  header = f"{'NAME':<24}{'%':>5}  URL"
  rows = [header, "-" * len(header)]
  for entry in entries:
    pct = 0.0
    if entry["bytes_total"]:
      pct = entry["bytes_loaded"] / entry["bytes_total"] * 100
    name = _truncate(entry["name"], 24)
    url = _truncate(entry["url"] or "-", 40)
    rows.append(f"{name:<24}{pct:>4.0f}%  {url}")

  return "```\n" + "\n".join(rows) + "\n```"


def format_status_list(entries: list) -> str:
  """
  Format queue entries as a monospace table with status text.

  Args:
    entries: List of dicts with "name", "url", "status"

  Returns:
    Markdown code block with a NAME / STATUS / URL table
  """
  if not entries:
    return "📭 No downloads in progress."

  header = f"{'NAME':<24}{'STATUS':<16}URL"
  rows = [header, "-" * len(header)]
  for entry in entries:
    name = _truncate(entry["name"], 24)
    status = _truncate(entry["status"] or "Queued", 16)
    url = _truncate(entry["url"] or "-", 30)
    rows.append(f"{name:<24}{status:<16}{url}")

  return "```\n" + "\n".join(rows) + "\n```"
