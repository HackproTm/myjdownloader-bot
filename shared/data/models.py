"""Data models for download jobs."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DownloadJob:
  """Represents a download job being processed by MyJDownloader."""

  url: str
  package_name: str
  package_uuid: Optional[int] = None
  bytes_total: int = 0
  bytes_loaded: int = 0
  status: str = "pending"
