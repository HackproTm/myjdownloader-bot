"""Bot entry point."""

import logging

from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import (
  Application,
  CallbackQueryHandler,
  CommandHandler,
  MessageHandler,
  filters,
)

# load_dotenv must run BEFORE importing config (which reads os.environ)
load_dotenv()

from config import TELEGRAM_TOKEN  # noqa: E402
from handlers import (  # noqa: E402
  cmd_accounts, cmd_add_account, cmd_help, cmd_list, cmd_queue, cmd_remove,
  cmd_remove_account, cmd_start, cmd_status, handle_message, on_select_option,
)
from utils.logger import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_COMMANDS = [
  BotCommand("start", "Show help and usage"),
  BotCommand("help", "Show help and usage"),
  BotCommand("queue", "Add a download to the queue"),
  BotCommand("list", "Show the queue with download percentage"),
  BotCommand("status", "Show the queue with status text"),
  BotCommand("remove", "Remove a download and delete its local file"),
  BotCommand("accounts", "List configured premium accounts"),
  BotCommand("addaccount", "Add a premium account"),
  BotCommand("removeaccount", "Remove a premium account"),
]


async def _post_init(app: Application) -> None:
  """Register the command menu shown by Telegram clients."""
  await app.bot.set_my_commands(_COMMANDS)
  logger.info("Command menu registered with Telegram (%d commands)",
              len(_COMMANDS))


def main() -> None:
  """Start the Telegram bot."""
  # concurrent_updates lets /list, /status, etc. respond while a download is in progress.
  app = Application.builder().token(TELEGRAM_TOKEN).concurrent_updates(
    True).post_init(_post_init).build()

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
  app.add_handler(CallbackQueryHandler(on_select_option, pattern=r"^dlopt:"))
  app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

  logger.info("Bot started — waiting for Telegram messages...")
  app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
  main()
