"""Bot entry point."""

import logging

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# load_dotenv must run BEFORE importing config (which reads os.environ)
load_dotenv()

from config import TELEGRAM_TOKEN  # noqa: E402
from handlers import (  # noqa: E402
  cmd_accounts, cmd_add_account, cmd_help, cmd_list, cmd_queue, cmd_remove,
  cmd_remove_account, cmd_start, cmd_status, handle_message,
)
from utils.logger import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
  """Start the Telegram bot."""
  app = Application.builder().token(TELEGRAM_TOKEN).build()

  # Register command and message handlers
  app.add_handler(CommandHandler("start", cmd_start))
  app.add_handler(CommandHandler("help", cmd_help))
  app.add_handler(CommandHandler("queue", cmd_queue))
  app.add_handler(CommandHandler("list", cmd_list))
  app.add_handler(CommandHandler("status", cmd_status))
  app.add_handler(CommandHandler("remove", cmd_remove))
  app.add_handler(CommandHandler("accounts", cmd_accounts))
  app.add_handler(CommandHandler("addaccount", cmd_add_account))
  app.add_handler(CommandHandler("removeaccount", cmd_remove_account))
  app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

  logger.info("Bot started — waiting for Telegram messages...")
  app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
  main()
