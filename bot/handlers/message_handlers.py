"""Telegram message handlers and commands."""

import logging
import os
import time
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import MAX_FILE_SIZE_BYTES
from data import DownloadJob, history
from services import manager
from utils import (
  extract_urls,
  format_queue_list,
  format_size,
  format_status_list,
  is_authorized,
  progress_bar,
  validators,
)

logger = logging.getLogger(__name__)


# ─── Commands ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update,
                    context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /start command."""
  if not is_authorized(update):
    return

  await update.message.reply_text(  # type: ignore[union-attr]
    "👋 *JDownloader Bot*\n\n"
    "Send me a URL and I will download it with JDownloader\\.\n\n"
    "*Accepted formats:*\n"
    "• `https://example\\.com/file\\.zip`\n"
    "• `https://example\\.com/file\\.zip my_file\\.zip`\n\n"
    "When the download finishes, I will send the file back here\\.\n\n"
    "*Queue management:*\n"
    "• `/queue <url> [name] [force]` — add a download to the queue\n"
    "• `/list` — queue with download percentage\n"
    "• `/status` — queue with status text\n"
    "• `/remove <name>` — remove a download and delete its local file\n\n"
    "*Premium accounts:*\n"
    "• `/accounts` — list configured accounts\n"
    "• `/addaccount <hoster> <username> <password>` — add one\n"
    "• `/removeaccount <uuid>` — remove one",
    parse_mode=ParseMode.MARKDOWN_V2,
  )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /help command."""
  await cmd_start(update, context)


async def cmd_accounts(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /accounts command - list configured premium accounts."""
  if not is_authorized(update):
    return

  try:
    accounts = await manager.list_accounts()
  except Exception as exc:
    logger.error("Error listing accounts: %s", exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not list accounts:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  if not accounts:
    await update.message.reply_text(  # type: ignore[union-attr]
      "No premium accounts configured.\nUse `/addaccount <hoster> <username> <password>` to add one.",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  lines = ["🔑 *Premium accounts:*"]
  for acc in accounts:
    status = "✅" if acc.get("valid") else "⚠️"
    disabled = "" if acc.get("enabled", True) else " _(disabled)_"
    lines.append(f"{status} `{acc.get('uuid')}` — *{acc.get('hostname', '?')}*"
                 f" — `{acc.get('userName', '?')}`{disabled}")
  lines.append("\nUse `/removeaccount <uuid>` to remove one.")

  await update.message.reply_text(  # type: ignore[union-attr]
    "\n".join(lines),
    parse_mode=ParseMode.MARKDOWN)


async def cmd_add_account(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /addaccount <hoster> <username> <password> command."""
  if not is_authorized(update):
    return

  chat_id = update.effective_chat.id  # type: ignore[union-attr]

  # Delete the command message right away so the password doesn't linger in chat history.
  try:
    await update.message.delete()  # type: ignore[union-attr]
  except Exception:
    pass

  if len(context.args) != 3:  # type: ignore[arg-type]
    await context.bot.send_message(
      chat_id=chat_id,
      text="Usage: `/addaccount <hoster> <username> <password>`\n"
      "Example: `/addaccount instagram.com myuser mypass`",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  hoster, username, password = context.args  # type: ignore[misc]

  try:
    await manager.add_account(hoster, username, password)
  except Exception as exc:
    logger.error("Error adding account: %s", exc)
    await context.bot.send_message(
      chat_id=chat_id,
      text=f"❌ Could not add account:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  await context.bot.send_message(
    chat_id=chat_id,
    text=f"✅ Account added for *{hoster}* (`{username}`).",
    parse_mode=ParseMode.MARKDOWN,
  )


async def cmd_remove_account(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /removeaccount <uuid> command."""
  if not is_authorized(update):
    return

  args = context.args  # type: ignore[assignment]
  if len(args) != 1 or not args[0].lstrip("-").isdigit():
    await update.message.reply_text(  # type: ignore[union-attr]
      "Usage: `/removeaccount <uuid>`\nUse `/accounts` to see the UUIDs.",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  account_id = int(args[0])

  try:
    await manager.remove_account(account_id)
  except Exception as exc:
    logger.error("Error removing account: %s", exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not remove account:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  await update.message.reply_text(  # type: ignore[union-attr]
    f"🗑️ Account `{account_id}` removed.",
    parse_mode=ParseMode.MARKDOWN)


async def cmd_queue(update: Update,
                    context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /queue <url> [name] [force] command."""
  if not is_authorized(update):
    return

  args = list(context.args or [])  # type: ignore[arg-type]
  force = bool(args) and args[-1].lower() == "force"
  if force:
    args = args[:-1]

  if not args:
    await update.message.reply_text(  # type: ignore[union-attr]
      "Usage: `/queue <url> [name] [force]`",
      parse_mode=ParseMode.MARKDOWN)
    return

  url = args[0]
  package_name = args[1] if len(args) > 1 else _default_package_name(url)

  if not force:
    existing = history.find_duplicate(url, package_name)
    if existing:
      matched = "URL" if existing["matched_by"] == "url" else "file name"
      await update.message.reply_text(  # type: ignore[union-attr]
        f"⚠️ This {matched} was already queued on {existing['added_at']} "
        f"as `{existing['package_name']}`.\n"
        f"Resend with `force` at the end to download it again:\n"
        f"`/queue {url} {package_name} force`",
        parse_mode=ParseMode.MARKDOWN,
      )
      return

  history.record(url, package_name)
  await _run_download(update, context, url, package_name)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /list command - show the queue with download percentage."""
  if not is_authorized(update):
    return

  try:
    entries = await manager.list_queue()
  except Exception as exc:
    logger.error("Error listing queue: %s", exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not list the queue:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  await update.message.reply_text(  # type: ignore[union-attr]
    format_queue_list(entries),
    parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update,
                     context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /status command - show the queue with status text."""
  if not is_authorized(update):
    return

  try:
    entries = await manager.list_queue()
  except Exception as exc:
    logger.error("Error fetching status: %s", exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not fetch the status:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  await update.message.reply_text(  # type: ignore[union-attr]
    format_status_list(entries),
    parse_mode=ParseMode.MARKDOWN)


async def cmd_remove(update: Update,
                     context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /remove <name> command - remove a download and its local file."""
  if not is_authorized(update):
    return

  args = context.args  # type: ignore[assignment]
  if not args:
    await update.message.reply_text(  # type: ignore[union-attr]
      "Usage: `/remove <name>`",
      parse_mode=ParseMode.MARKDOWN)
    return

  name = " ".join(args)

  try:
    removed = await manager.remove_from_queue(name)
  except Exception as exc:
    logger.error("Error removing '%s' from queue: %s", name, exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not remove `{name}`:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  if not removed:
    await update.message.reply_text(  # type: ignore[union-attr]
      f"⚠️ No queue entry found matching `{name}`.",
      parse_mode=ParseMode.MARKDOWN)
    return

  await update.message.reply_text(  # type: ignore[union-attr]
    f"🗑️ Removed `{name}` from the queue and JDownloader.",
    parse_mode=ParseMode.MARKDOWN)


# ─── Message Handler ──────────────────────────────────────────────────────────


async def handle_message(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle incoming messages with URLs."""
  if not is_authorized(update):
    await update.message.reply_text("⛔ You are not allowed to use this bot."
                                    )  # type: ignore[union-attr]
    return

  text = (update.message.text or "").strip()  # type: ignore[union-attr]
  urls = extract_urls(text)

  if not urls:
    await update.message.reply_text(  # type: ignore[union-attr]
      "I couldn't find a URL in your message. Please send a download link.")
    return

  url = urls[0]
  # Remaining text after removing the URL is treated as package name.
  remainder = text.replace(url, "").strip()
  package_name = remainder if remainder else _default_package_name(url)

  await _run_download(update, context, url, package_name)


def _default_package_name(url: str) -> str:
  """Generate a default package name from URL."""
  name = url.rstrip("/").split("/")[-1].split("?")[0]
  return name if name else f"download_{int(time.time())}"


# ─── Download Flow ────────────────────────────────────────────────────────────


async def _run_download(
  update: Update,
  context: ContextTypes.DEFAULT_TYPE,
  url: str,
  package_name: str,
) -> None:
  """Execute the download workflow."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]

  status_msg = await update.message.reply_text(  # type: ignore[union-attr]
    f"⏳ *Starting download...*\n`{url}`",
    parse_mode=ParseMode.MARKDOWN,
  )

  # 1. Add link to JDownloader
  try:
    job = await manager.add_download(url, package_name)
  except Exception as exc:
    logger.error("Error adding download: %s", exc)
    await status_msg.edit_text(
      f"❌ Could not start download:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  await status_msg.edit_text(
    f"📥 *Downloading:* `{package_name}`\n_Waiting for progress data..._",
    parse_mode=ParseMode.MARKDOWN,
  )

  # 2. Progress callback -> updates status message
  async def on_progress(job: DownloadJob) -> None:
    """Update progress message."""
    if job.bytes_total == 0:
      return
    pct = job.bytes_loaded / job.bytes_total * 100
    bar = progress_bar(pct)
    try:
      await status_msg.edit_text(
        f"📥 *Downloading:* `{job.package_name}`\n"
        f"{bar} *{pct:.0f}%*\n"
        f"`{format_size(job.bytes_loaded)}` / `{format_size(job.bytes_total)}`\n"
        f"_{job.status}_",
        parse_mode=ParseMode.MARKDOWN,
      )
    except Exception:
      pass  # Message might be unchanged (flood control, etc.).

  # 3. Wait until completion
  try:
    file_path = await manager.monitor_job(job, on_progress=on_progress)
  except Exception as exc:
    logger.error("Download failed: %s", exc)
    await status_msg.edit_text(
      f"❌ Download failed:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  # 4. Send file or notify if too large
  file_size = os.path.getsize(file_path)
  filename = os.path.basename(file_path)

  if file_size > MAX_FILE_SIZE_BYTES:
    await status_msg.edit_text(
      f"✅ *Download completed:* `{filename}`\n"
      f"⚠️ File size is *{format_size(file_size)}* and exceeds "
      f"Telegram's 50 MB bot limit. You can access it on the server.",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  await status_msg.edit_text(
    f"✅ *Download completed:* `{filename}`\nSending...",
    parse_mode=ParseMode.MARKDOWN,
  )

  try:
    with open(file_path, "rb") as fh:
      await context.bot.send_document(
        chat_id=chat_id,
        document=fh,
        filename=filename,
        caption=f"✅ `{filename}` — {format_size(file_size)}",
        parse_mode=ParseMode.MARKDOWN,
      )
    await status_msg.delete()
  except Exception as exc:
    logger.error("Error sending file: %s", exc)
    await status_msg.edit_text(
      f"✅ Download completed but failed to send the file:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN,
    )
