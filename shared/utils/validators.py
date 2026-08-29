"""URL validation utilities shared by the bot and the Mini App API."""

import re
from typing import List

# Regex pattern for URL validation
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def extract_urls(text: str) -> List[str]:
  """
  Extract URLs from text.

  Args:
    text: Text to search for URLs

  Returns:
    List of URLs found
  """
  return _URL_PATTERN.findall(text)


def is_valid_url(text: str) -> bool:
  """
  Check whether text is (only) a single valid URL.

  Args:
    text: Text to validate

  Returns:
    True if text is a well-formed http(s) URL
  """
  return bool(_URL_PATTERN.fullmatch(text.strip()))
