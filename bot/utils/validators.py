"""Validation utilities."""

from telegram import Update


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
