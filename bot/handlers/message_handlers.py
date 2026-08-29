"""Telegram message handlers and commands."""

import logging
import os
import time
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import MAX_FILE_SIZE_BYTES
from data import DownloadJob, history
from services import manager
from utils import (
  detect_platform,
  extract_urls,
  format_queue_list,
  format_size,
  format_status_list,
  is_authorized,
  is_valid_url,
  progress_bar,
)

logger = logging.getLogger(__name__)


# ─── Commands ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update,
                    context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /start command."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized /start attempt", chat_id)
    return
  logger.info("Chat %s: /start", chat_id)

  await update.message.reply_text(  # type: ignore[union-attr]
    "👋 *JDownloader Bot*\n\n"
    "Send me a URL and I will download it with JDownloader\\.\n\n"
    "*Accepted formats:*\n"
    "• `https://example\\.com/file\\.zip`\n"
    "• `https://example\\.com/file\\.zip my_file\\.zip`\n\n"
    "When the download finishes, I will send the file back here\\.\n\n"
    "*Queue management:*\n"
    "• `/queue <url> [name] [force]` — add a download \\(or just `/queue` to be asked for it\\)\n"
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
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized /accounts attempt", chat_id)
    return
  logger.info("Chat %s: /accounts", chat_id)

  try:
    accounts = await manager.list_accounts()
  except Exception as exc:
    logger.error("Error listing accounts: %s", exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not list accounts:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  logger.info("Chat %s: found %d configured account(s)", chat_id,
              len(accounts))

  if not accounts:
    await update.message.reply_text(  # type: ignore[union-attr]
      "No premium accounts configured.\n"
      "Use `/addaccount <hoster> <username> <password>` to add one.",
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
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized /addaccount attempt", chat_id)
    return

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
  logger.info("Chat %s: /addaccount hoster=%s username=%s", chat_id, hoster,
              username)  # never log the password

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

  logger.info("Chat %s: account added for %s (%s)", chat_id, hoster, username)
  await context.bot.send_message(
    chat_id=chat_id,
    text=f"✅ Account added for *{hoster}* (`{username}`).",
    parse_mode=ParseMode.MARKDOWN,
  )


async def cmd_remove_account(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /removeaccount <uuid> command."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized /removeaccount attempt", chat_id)
    return

  args = context.args  # type: ignore[assignment]
  if len(args) != 1 or not args[0].lstrip("-").isdigit():
    await update.message.reply_text(  # type: ignore[union-attr]
      "Usage: `/removeaccount <uuid>`\nUse `/accounts` to see the UUIDs.",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  account_id = int(args[0])
  logger.info("Chat %s: /removeaccount account_id=%s", chat_id, account_id)

  try:
    await manager.remove_account(account_id)
  except Exception as exc:
    logger.error("Error removing account: %s", exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not remove account:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  logger.info("Chat %s: account %s removed", chat_id, account_id)
  await update.message.reply_text(  # type: ignore[union-attr]
    f"🗑️ Account `{account_id}` removed.",
    parse_mode=ParseMode.MARKDOWN)


async def cmd_queue(update: Update,
                    context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /queue <url> [name] [force] command."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized /queue attempt", chat_id)
    return

  args = list(context.args or [])  # type: ignore[arg-type]
  force = bool(args) and args[-1].lower() == "force"
  if force:
    args = args[:-1]

  if not args:
    context.chat_data[  # type: ignore[union-attr]
      "awaiting_queue_url"] = True
    logger.info("Chat %s: /queue with no args, asking for the URL", chat_id)
    await update.message.reply_text(  # type: ignore[union-attr]
      "🔗 Send me the URL you want to queue.")
    return

  url = args[0]
  if not is_valid_url(url):
    await update.message.reply_text(  # type: ignore[union-attr]
      f"⚠️ `{url}` doesn't look like a valid URL.",
      parse_mode=ParseMode.MARKDOWN)
    return

  package_name = args[1] if len(args) > 1 else None
  await _start_queue(update, context, url, package_name, force)


async def _start_queue(
  update: Update,
  context: ContextTypes.DEFAULT_TYPE,
  url: str,
  package_name: Optional[str],
  force: bool = False,
) -> None:
  """Check for duplicates (unless forced), record history, and start the download."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  dedup_name = package_name or _default_package_name(url)
  logger.info("Chat %s: queueing url=%s name=%s force=%s", chat_id, url,
              dedup_name, force)

  if not force:
    existing = history.find_duplicate(url, dedup_name)
    if existing:
      logger.info("Chat %s: duplicate detected (matched_by=%s)", chat_id,
                  existing["matched_by"])
      matched = "URL" if existing["matched_by"] == "url" else "file name"
      await update.message.reply_text(  # type: ignore[union-attr]
        f"⚠️ This {matched} was already queued on {existing['added_at']} "
        f"as `{existing['package_name']}`.\n"
        f"Resend with `force` at the end to download it again:\n"
        f"`/queue {url} {dedup_name} force`",
        parse_mode=ParseMode.MARKDOWN,
      )
      return

  history.record(url, dedup_name)
  await _run_download(update, context, url, package_name)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /list command - show the queue with download percentage."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized /list attempt", chat_id)
    return

  try:
    entries = await manager.list_queue()
  except Exception as exc:
    logger.error("Error listing queue: %s", exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not list the queue:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  logger.info("Chat %s: /list -> %d queue entries", chat_id, len(entries))
  await update.message.reply_text(  # type: ignore[union-attr]
    format_queue_list(entries),
    parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update,
                     context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /status command - show the queue with status text."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized /status attempt", chat_id)
    return

  try:
    entries = await manager.list_queue()
  except Exception as exc:
    logger.error("Error fetching status: %s", exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not fetch the status:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  logger.info("Chat %s: /status -> %d queue entries", chat_id, len(entries))
  await update.message.reply_text(  # type: ignore[union-attr]
    format_status_list(entries),
    parse_mode=ParseMode.MARKDOWN)


async def cmd_remove(update: Update,
                     context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle /remove <name> command - remove a download and its local file."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized /remove attempt", chat_id)
    return

  args = context.args  # type: ignore[assignment]
  if not args:
    await update.message.reply_text(  # type: ignore[union-attr]
      "Usage: `/remove <name>`",
      parse_mode=ParseMode.MARKDOWN)
    return

  name = " ".join(args)
  logger.info("Chat %s: /remove name=%s", chat_id, name)

  try:
    removed = await manager.remove_from_queue(name)
  except Exception as exc:
    logger.error("Error removing '%s' from queue: %s", name, exc)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"❌ Could not remove `{name}`:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN)
    return

  if not removed:
    logger.info("Chat %s: no queue entry found for '%s'", chat_id, name)
    await update.message.reply_text(  # type: ignore[union-attr]
      f"⚠️ No queue entry found matching `{name}`.",
      parse_mode=ParseMode.MARKDOWN)
    return

  logger.info("Chat %s: removed '%s' from the queue", chat_id, name)
  await update.message.reply_text(  # type: ignore[union-attr]
    f"🗑️ Removed `{name}` from the queue and JDownloader.",
    parse_mode=ParseMode.MARKDOWN)


# ─── Message Handler ──────────────────────────────────────────────────────────


async def handle_message(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle incoming messages with URLs."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized message rejected", chat_id)
    await update.message.reply_text("⛔ You are not allowed to use this bot."
                                    )  # type: ignore[union-attr]
    return

  text = (update.message.text or "").strip()  # type: ignore[union-attr]

  # Reply to an interactive /queue conversation, if one is in progress.
  if context.chat_data.get(  # type: ignore[union-attr]
      "awaiting_queue_url"):
    await _handle_queue_url_reply(update, context, text)
    return
  if context.chat_data.get(  # type: ignore[union-attr]
      "awaiting_queue_name"):
    await _handle_queue_name_reply(update, context, text)
    return

  urls = extract_urls(text)

  if not urls:
    await update.message.reply_text(  # type: ignore[union-attr]
      "I couldn't find a URL in your message. Please send a download link.")
    return

  url = urls[0]
  # Remaining text after removing the URL is treated as the requested package name.
  remainder = text.replace(url, "").strip()
  requested_name = remainder or None
  logger.info("Chat %s: received URL %s (requested_name=%s)", chat_id, url,
              requested_name)

  await _run_download(update, context, url, requested_name)


async def _handle_queue_url_reply(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE,
                                  text: str) -> None:
  """Handle the URL reply of an interactive /queue conversation."""
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_valid_url(text):
    await update.message.reply_text(  # type: ignore[union-attr]
      "⚠️ That doesn't look like a valid URL. "
      "Please send a link starting with http:// or https://.")
    return  # Keep waiting for a valid URL.

  context.chat_data["awaiting_queue_url"] = False  # type: ignore[union-attr]
  context.chat_data["queue_pending_url"] = text  # type: ignore[union-attr]
  context.chat_data["awaiting_queue_name"] = True  # type: ignore[union-attr]
  logger.info("Chat %s: got URL for interactive /queue: %s", chat_id, text)

  await update.message.reply_text(  # type: ignore[union-attr]
    "🏷️ Now send me a file name, or `-` to use the default name.",
    parse_mode=ParseMode.MARKDOWN,
  )


async def _handle_queue_name_reply(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE,
                                   text: str) -> None:
  """Handle the file name reply of an interactive /queue conversation."""
  context.chat_data["awaiting_queue_name"] = False  # type: ignore[union-attr]
  url = context.chat_data.pop(  # type: ignore[union-attr]
    "queue_pending_url", None)
  if url is None:
    await update.message.reply_text(  # type: ignore[union-attr]
      "⚠️ Something went wrong, please start again with /queue.")
    return

  package_name = None if text in ("-", "") else text
  await _start_queue(update, context, url, package_name)


def _default_package_name(url: str) -> str:
  """Generate a default package name from URL."""
  name = url.rstrip("/").split("/")[-1].split("?")[0]
  return name if name else f"download_{int(time.time())}"


# ─── Selection Callback ────────────────────────────────────────────────────────


async def on_select_option(update: Update,
                           context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle inline-keyboard taps when a link offers multiple files/resolutions."""
  query = update.callback_query
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  if not is_authorized(update):
    logger.warning("Chat %s: unauthorized selection attempt", chat_id)
    await query.answer("Not authorized.", show_alert=True)
    return
  await query.answer()

  _, package_uuid_str, idx_str = query.data.split(":", 2)
  pending_all = context.chat_data.setdefault(  # type: ignore[union-attr]
    "pending_downloads", {})
  pending = pending_all.pop(package_uuid_str, None)
  if pending is None:
    await query.edit_message_text("⚠️ This selection has expired.")
    return

  option = pending["options"][int(idx_str)]
  package_uuid = int(package_uuid_str)
  final_name = pending["final_name"]
  url = pending["url"]
  logger.info("Chat %s: selected '%s' for %s", chat_id, option["label"],
              final_name)

  await query.edit_message_text(
    f"⏳ *Starting download...*\n`{final_name}`",
    parse_mode=ParseMode.MARKDOWN,
  )

  try:
    await manager.finalize_selection(package_uuid, option["link_uuid"],
                                     option["variant_id"], final_name)
  except Exception as exc:
    logger.error("Error finalizing selection: %s", exc)
    await query.edit_message_text(f"❌ Could not start download:\n`{exc}`",
                                  parse_mode=ParseMode.MARKDOWN)
    return

  job = DownloadJob(url=url,
                    package_name=final_name,
                    package_uuid=package_uuid)
  await _monitor_and_deliver(query.message, chat_id, context, job)


# ─── Download Flow ────────────────────────────────────────────────────────────


async def _run_download(
  update: Update,
  context: ContextTypes.DEFAULT_TYPE,
  url: str,
  requested_name: Optional[str] = None,
) -> None:
  """
  Add a URL to JDownloader and either start the download right away, or ask
  the user to pick a file/resolution when the link offers more than one.
  """
  chat_id = update.effective_chat.id  # type: ignore[union-attr]
  logger.info("Chat %s: collecting url=%s requested_name=%s", chat_id, url,
              requested_name)

  status_msg = await update.message.reply_text(  # type: ignore[union-attr]
    f"🔎 *Looking up...*\n`{url}`",
    parse_mode=ParseMode.MARKDOWN,
  )

  try:
    collected = await manager.collect_link(url, requested_name)
  except Exception as exc:
    logger.error("Error collecting link: %s", exc)
    await status_msg.edit_text(
      f"❌ Could not add the link:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  package_uuid = collected["package_uuid"]
  options = collected["options"]
  base_name = requested_name or collected[
    "package_name"] or _default_package_name(url)
  platform = detect_platform(url)
  final_name = f"{platform} - {base_name}" if platform else base_name

  if len(options) <= 1:
    chosen = options[0] if options else {"link_uuid": None, "variant_id": None}
    try:
      await manager.finalize_selection(package_uuid, chosen["link_uuid"],
                                       chosen["variant_id"], final_name)
    except Exception as exc:
      logger.error("Error finalizing download: %s", exc)
      await status_msg.edit_text(
        f"❌ Could not start download:\n`{exc}`",
        parse_mode=ParseMode.MARKDOWN,
      )
      return

    job = DownloadJob(url=url,
                      package_name=final_name,
                      package_uuid=package_uuid)
    await _monitor_and_deliver(status_msg, chat_id, context, job)
    return

  # Multiple files/resolutions available: let the user pick one.
  context.chat_data.setdefault(  # type: ignore[union-attr]
    "pending_downloads", {})[str(package_uuid)] = {
      "url": url,
      "final_name": final_name,
      "options": options,
    }
  keyboard = [[
    InlineKeyboardButton(opt["label"][:60],
                         callback_data=f"dlopt:{package_uuid}:{i}")
  ] for i, opt in enumerate(options)]
  logger.info("Chat %s: %d option(s) available for %s, asking user", chat_id,
              len(options), final_name)
  await status_msg.edit_text(
    f"📋 *Multiple files available for* `{final_name}`\nChoose one:",
    parse_mode=ParseMode.MARKDOWN,
    reply_markup=InlineKeyboardMarkup(keyboard),
  )


async def _monitor_and_deliver(
  status_msg,
  chat_id: int,
  context: ContextTypes.DEFAULT_TYPE,
  job: DownloadJob,
) -> None:
  """Monitor a queued download and deliver the resulting file to the chat."""
  await status_msg.edit_text(
    f"📥 *Downloading:* `{job.package_name}`\n_Waiting for progress data..._",
    parse_mode=ParseMode.MARKDOWN,
  )

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

  try:
    file_path = await manager.monitor_job(job, on_progress=on_progress)
  except Exception as exc:
    logger.error("Download failed: %s", exc)
    await status_msg.edit_text(
      f"❌ Download failed:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN,
    )
    return

  file_size = os.path.getsize(file_path)
  filename = os.path.basename(file_path)
  logger.info("Chat %s: download finished file=%s size=%d bytes", chat_id,
              filename, file_size)

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
    logger.info("Chat %s: file '%s' sent successfully", chat_id, filename)
  except Exception as exc:
    logger.error("Error sending file: %s", exc)
    await status_msg.edit_text(
      f"✅ Download completed but failed to send the file:\n`{exc}`",
      parse_mode=ParseMode.MARKDOWN,
    )
