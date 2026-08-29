"""Detect the source platform of a URL for package naming."""

from typing import Optional
from urllib.parse import urlparse

_PLATFORMS = {
  "youtube.com": "YouTube",
  "youtu.be": "YouTube",
  "instagram.com": "Instagram",
  "twitter.com": "X",
  "x.com": "X",
  "facebook.com": "Facebook",
  "fb.watch": "Facebook",
  "tiktok.com": "TikTok",
  "vimeo.com": "Vimeo",
  "twitch.tv": "Twitch",
  "reddit.com": "Reddit",
  "soundcloud.com": "SoundCloud",
}


def detect_platform(url: str) -> Optional[str]:
  """
  Detect the source platform of a URL from its domain.

  Args:
    url: URL to inspect

  Returns:
    A human-friendly platform name (e.g. "YouTube"), or None if unknown.
  """
  try:
    host = urlparse(url).netloc.lower()
  except ValueError:
    return None

  host = host.split("@")[-1]  # strip userinfo
  host = host.split(":")[0]  # strip port
  if host.startswith("www."):
    host = host[len("www."):]

  return _PLATFORMS.get(host)
