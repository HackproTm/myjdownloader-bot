"""Validation utilities."""

import re
from typing import List

from telegram import Update

# Regex pattern for URL validation
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def is_authorized(update: Update) -> bool:
  """
  Check if the user is authorized to use the bot.

  Args:
    update: Telegram update object

  Returns:
    True if authorized, False otherwise
  """
  # Import here to avoid circular dependency with config
  from config import ALLOWED_CHAT_IDS

  if not ALLOWED_CHAT_IDS:
    return True
  return update.effective_chat.id in ALLOWED_CHAT_IDS  # type: ignore[operator]


def extract_urls(text: str) -> List[str]:
  """
  Extract URLs from text.

  Args:
    text: Text to search for URLs

  Returns:
    List of URLs found
  """
  return _URL_PATTERN.findall(text)
