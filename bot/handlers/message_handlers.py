"""Telegram message handlers and commands."""

import logging
import os
import time
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import MAX_FILE_SIZE_BYTES
from data import DownloadJob
from services import manager
from utils import extract_urls, format_size, is_authorized, progress_bar, validators

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
    "When the download finishes, I will send the file back here\\.",
    parse_mode=ParseMode.MARKDOWN_V2,
  )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /help command."""
  await cmd_start(update, context)


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
