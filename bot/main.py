"""Bot entry point."""

import logging

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# load_dotenv must run BEFORE importing config (which reads os.environ)
load_dotenv()

from config import TELEGRAM_TOKEN  # noqa: E402
from handlers import cmd_help, cmd_start, handle_message  # noqa: E402
from utils.logger import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
  """Start the Telegram bot."""
  app = Application.builder().token(TELEGRAM_TOKEN).build()

  # Register command and message handlers
  app.add_handler(CommandHandler("start", cmd_start))
  app.add_handler(CommandHandler("help", cmd_help))
  app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

  logger.info("Bot started — waiting for Telegram messages...")
  app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
  main()
