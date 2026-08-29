"""Tests for handlers.message_handlers."""

from unittest.mock import AsyncMock, MagicMock

from handlers.message_handlers import (
  _default_package_name,
  cmd_accounts,
  cmd_add_account,
  cmd_help,
  cmd_list,
  cmd_queue,
  cmd_remove,
  cmd_remove_account,
  cmd_start,
  cmd_status,
  handle_message,
  on_select_option,
)


class TestDefaultPackageName:

  def test_extracts_filename_from_url(self):
    assert _default_package_name("http://x.com/dir/file.zip") == "file.zip"

  def test_strips_query_string(self):
    assert _default_package_name(
      "http://x.com/file.zip?token=abc") == "file.zip"

  def test_falls_back_to_timestamp_name(self):
    name = _default_package_name("")
    assert name.startswith("download_")


class TestCmdStart:

  async def test_sends_welcome_message_when_authorized(self, mock_update,
                                                       mock_context,
                                                       monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)

    await cmd_start(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()

  async def test_does_nothing_when_unauthorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)

    await cmd_start(mock_update, mock_context)

    mock_update.message.reply_text.assert_not_awaited()


class TestCmdHelp:

  async def test_delegates_to_cmd_start(self, mock_update, mock_context,
                                        monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)

    await cmd_help(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()


class TestCmdAccounts:

  async def test_lists_accounts_when_authorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr(
      "handlers.message_handlers.manager.list_accounts",
      AsyncMock(return_value=[{
        "uuid": 1,
        "hostname": "instagram.com",
        "userName": "user",
        "valid": True,
        "enabled": True,
      }]),
    )

    await cmd_accounts(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()
    message = mock_update.message.reply_text.call_args.args[0]
    assert "instagram.com" in message

  async def test_reports_no_accounts_configured(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.manager.list_accounts",
                        AsyncMock(return_value=[]))

    await cmd_accounts(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()

  async def test_does_nothing_when_unauthorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)

    await cmd_accounts(mock_update, mock_context)

    mock_update.message.reply_text.assert_not_awaited()


class TestCmdAddAccount:

  async def test_adds_account_and_deletes_message(self, mock_update,
                                                  mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.manager.add_account",
                        AsyncMock())
    mock_update.message.delete = AsyncMock()
    mock_context.bot.send_message = AsyncMock()
    mock_context.args = ["instagram.com", "user", "pass"]

    await cmd_add_account(mock_update, mock_context)

    mock_update.message.delete.assert_awaited_once()
    mock_context.bot.send_message.assert_awaited_once()

  async def test_reports_usage_when_args_missing(self, mock_update,
                                                 mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    mock_update.message.delete = AsyncMock()
    mock_context.bot.send_message = AsyncMock()
    mock_context.args = ["instagram.com"]

    await cmd_add_account(mock_update, mock_context)

    mock_context.bot.send_message.assert_awaited_once()
    assert "Usage" in mock_context.bot.send_message.call_args.kwargs["text"]

  async def test_does_nothing_when_unauthorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)
    mock_update.message.delete = AsyncMock()

    await cmd_add_account(mock_update, mock_context)

    mock_update.message.delete.assert_not_awaited()


class TestCmdRemoveAccount:

  async def test_removes_account_when_uuid_valid(self, mock_update,
                                                 mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.manager.remove_account",
                        AsyncMock())
    mock_context.args = ["42"]

    await cmd_remove_account(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()

  async def test_reports_usage_when_uuid_invalid(self, mock_update,
                                                 mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    mock_context.args = ["not-a-number"]

    await cmd_remove_account(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()
    assert "Usage" in mock_update.message.reply_text.call_args.args[0]

  async def test_does_nothing_when_unauthorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)

    await cmd_remove_account(mock_update, mock_context)

    mock_update.message.reply_text.assert_not_awaited()


class TestCmdQueue:

  async def test_queues_new_url(self, mock_update, mock_context, monkeypatch,
                                tmp_path):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.history.find_duplicate",
                        lambda url, name: None)
    monkeypatch.setattr("handlers.message_handlers.history.record",
                        MagicMock())
    run_download_mock = AsyncMock()
    monkeypatch.setattr("handlers.message_handlers._run_download",
                        run_download_mock)
    mock_context.args = ["http://x.com/f.zip", "f.zip"]

    await cmd_queue(mock_update, mock_context)

    run_download_mock.assert_awaited_once()
    call_args = run_download_mock.call_args.args
    assert call_args[2] == "http://x.com/f.zip"
    assert call_args[3] == "f.zip"

  async def test_warns_when_duplicate_found(self, mock_update, mock_context,
                                            monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr(
      "handlers.message_handlers.history.find_duplicate",
      lambda url, name: {
        "matched_by": "url",
        "added_at": "2026-01-01 00:00:00",
        "package_name": "f.zip",
      },
    )
    run_download_mock = AsyncMock()
    monkeypatch.setattr("handlers.message_handlers._run_download",
                        run_download_mock)
    mock_context.args = ["http://x.com/f.zip", "f.zip"]

    await cmd_queue(mock_update, mock_context)

    run_download_mock.assert_not_awaited()
    mock_update.message.reply_text.assert_awaited_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "already queued" in args[0]

  async def test_force_bypasses_duplicate_check(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    find_duplicate_mock = MagicMock()
    monkeypatch.setattr("handlers.message_handlers.history.find_duplicate",
                        find_duplicate_mock)
    monkeypatch.setattr("handlers.message_handlers.history.record",
                        MagicMock())
    run_download_mock = AsyncMock()
    monkeypatch.setattr("handlers.message_handlers._run_download",
                        run_download_mock)
    mock_context.args = ["http://x.com/f.zip", "f.zip", "force"]

    await cmd_queue(mock_update, mock_context)

    find_duplicate_mock.assert_not_called()
    run_download_mock.assert_awaited_once()

  async def test_reports_usage_when_no_args(self, mock_update, mock_context,
                                            monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    mock_context.args = []

    await cmd_queue(mock_update, mock_context)

    args, _ = mock_update.message.reply_text.call_args
    assert "Usage" in args[0]

  async def test_does_nothing_when_unauthorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)

    await cmd_queue(mock_update, mock_context)

    mock_update.message.reply_text.assert_not_awaited()


class TestCmdList:

  async def test_replies_with_formatted_queue(self, mock_update, mock_context,
                                              monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.manager.list_queue",
                        AsyncMock(return_value=[]))

    await cmd_list(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()

  async def test_does_nothing_when_unauthorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)

    await cmd_list(mock_update, mock_context)

    mock_update.message.reply_text.assert_not_awaited()


class TestCmdStatus:

  async def test_replies_with_formatted_status(self, mock_update, mock_context,
                                               monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.manager.list_queue",
                        AsyncMock(return_value=[]))

    await cmd_status(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()

  async def test_does_nothing_when_unauthorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)

    await cmd_status(mock_update, mock_context)

    mock_update.message.reply_text.assert_not_awaited()


class TestCmdRemove:

  async def test_removes_when_found(self, mock_update, mock_context,
                                    monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.manager.remove_from_queue",
                        AsyncMock(return_value=True))
    mock_context.args = ["f.zip"]

    await cmd_remove(mock_update, mock_context)

    args, _ = mock_update.message.reply_text.call_args
    assert "Removed" in args[0]

  async def test_reports_when_not_found(self, mock_update, mock_context,
                                        monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.manager.remove_from_queue",
                        AsyncMock(return_value=False))
    mock_context.args = ["missing.zip"]

    await cmd_remove(mock_update, mock_context)

    args, _ = mock_update.message.reply_text.call_args
    assert "No queue entry found" in args[0]

  async def test_reports_usage_when_no_args(self, mock_update, mock_context,
                                            monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    mock_context.args = []

    await cmd_remove(mock_update, mock_context)

    args, _ = mock_update.message.reply_text.call_args
    assert "Usage" in args[0]

  async def test_does_nothing_when_unauthorized(self, mock_update,
                                                mock_context, monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)

    await cmd_remove(mock_update, mock_context)

    mock_update.message.reply_text.assert_not_awaited()


class TestHandleMessage:

  async def test_rejects_unauthorized_user(self, mock_update, mock_context,
                                           monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)
    mock_update.message.text = "http://x.com/f.zip"

    await handle_message(mock_update, mock_context)

    args, _ = mock_update.message.reply_text.call_args
    assert "not allowed" in args[0]

  async def test_replies_when_no_url_found(self, mock_update, mock_context,
                                           monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    mock_update.message.text = "hello there"

    await handle_message(mock_update, mock_context)

    args, _ = mock_update.message.reply_text.call_args
    assert "couldn't find a URL" in args[0]

  async def test_valid_url_triggers_download(self, mock_update, mock_context,
                                             monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    run_download_mock = AsyncMock()
    monkeypatch.setattr("handlers.message_handlers._run_download",
                        run_download_mock)
    mock_update.message.text = "http://x.com/f.zip custom_name.zip"

    await handle_message(mock_update, mock_context)

    run_download_mock.assert_awaited_once()
    call_args = run_download_mock.call_args.args
    assert call_args[2] == "http://x.com/f.zip"
    assert call_args[3] == "custom_name.zip"


class TestRunDownloadFlow:

  async def test_successful_download_sends_file(self, mock_update,
                                                mock_context, monkeypatch,
                                                tmp_path):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)

    file_path = tmp_path / "result.zip"
    file_path.write_bytes(b"x" * 1024)

    status_msg = MagicMock()
    status_msg.edit_text = AsyncMock()
    status_msg.delete = AsyncMock()
    mock_update.message.reply_text = AsyncMock(return_value=status_msg)
    mock_update.message.text = "http://x.com/f.zip"

    monkeypatch.setattr(
      "handlers.message_handlers.manager.collect_link",
      AsyncMock(
        return_value={
          "package_uuid": 1,
          "package_name": "f.zip",
          "options": [{
            "link_uuid": 10,
            "variant_id": None,
            "label": "f.zip"
          }],
        }),
    )
    monkeypatch.setattr("handlers.message_handlers.manager.finalize_selection",
                        AsyncMock())
    monkeypatch.setattr(
      "handlers.message_handlers.manager.monitor_job",
      AsyncMock(return_value=str(file_path)),
    )

    await handle_message(mock_update, mock_context)

    mock_context.bot.send_document.assert_awaited_once()
    status_msg.delete.assert_awaited_once()

  async def test_collect_failure_reports_error(self, mock_update, mock_context,
                                               monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)

    status_msg = MagicMock()
    status_msg.edit_text = AsyncMock()
    mock_update.message.reply_text = AsyncMock(return_value=status_msg)
    mock_update.message.text = "http://x.com/f.zip"

    monkeypatch.setattr(
      "handlers.message_handlers.manager.collect_link",
      AsyncMock(side_effect=RuntimeError("boom")),
    )

    await handle_message(mock_update, mock_context)

    status_msg.edit_text.assert_awaited_once()
    args, _ = status_msg.edit_text.call_args
    assert "Could not add the link" in args[0]

  async def test_oversized_file_is_not_sent(self, mock_update, mock_context,
                                            monkeypatch, tmp_path):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    monkeypatch.setattr("handlers.message_handlers.MAX_FILE_SIZE_BYTES", 10)

    file_path = tmp_path / "big.zip"
    file_path.write_bytes(b"x" * 1024)

    status_msg = MagicMock()
    status_msg.edit_text = AsyncMock()
    mock_update.message.reply_text = AsyncMock(return_value=status_msg)
    mock_update.message.text = "http://x.com/big.zip"

    monkeypatch.setattr(
      "handlers.message_handlers.manager.collect_link",
      AsyncMock(
        return_value={
          "package_uuid": 1,
          "package_name": "big.zip",
          "options": [{
            "link_uuid": 10,
            "variant_id": None,
            "label": "big.zip"
          }],
        }),
    )
    monkeypatch.setattr("handlers.message_handlers.manager.finalize_selection",
                        AsyncMock())
    monkeypatch.setattr(
      "handlers.message_handlers.manager.monitor_job",
      AsyncMock(return_value=str(file_path)),
    )

    await handle_message(mock_update, mock_context)

    mock_context.bot.send_document.assert_not_awaited()
    args, _ = status_msg.edit_text.call_args_list[-1]
    assert "exceeds" in args[0]

  async def test_multiple_options_asks_user_to_choose(self, mock_update,
                                                      mock_context,
                                                      monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)

    status_msg = MagicMock()
    status_msg.edit_text = AsyncMock()
    mock_update.message.reply_text = AsyncMock(return_value=status_msg)
    mock_update.message.text = "https://www.youtube.com/watch?v=abc"
    mock_context.chat_data = {}

    monkeypatch.setattr(
      "handlers.message_handlers.manager.collect_link",
      AsyncMock(
        return_value={
          "package_uuid":
          1,
          "package_name":
          "cool video",
          "options": [
            {
              "link_uuid": 10,
              "variant_id": "1080p",
              "label": "video — 1080p"
            },
            {
              "link_uuid": 10,
              "variant_id": "720p",
              "label": "video — 720p"
            },
          ],
        }),
    )

    await handle_message(mock_update, mock_context)

    status_msg.edit_text.assert_awaited_once()
    _, kwargs = status_msg.edit_text.call_args
    assert "reply_markup" in kwargs
    assert "1" in mock_context.chat_data["pending_downloads"]
    assert mock_context.chat_data["pending_downloads"]["1"][
      "final_name"] == "YouTube - cool video"


class TestOnSelectOption:

  def _make_callback_update(self, data: str):
    """Build a MagicMock update with a callback_query for the given data."""
    update = MagicMock()
    update.effective_chat.id = 12345
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.message = MagicMock()
    update.callback_query.message.edit_text = AsyncMock()
    return update

  async def test_starts_download_for_selected_option(self, mock_context,
                                                     monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    finalize_mock = AsyncMock()
    monkeypatch.setattr("handlers.message_handlers.manager.finalize_selection",
                        finalize_mock)
    monkeypatch.setattr(
      "handlers.message_handlers.manager.monitor_job",
      AsyncMock(side_effect=RuntimeError("stop after finalize")),
    )
    update = self._make_callback_update("dlopt:1:0")
    mock_context.chat_data = {
      "pending_downloads": {
        "1": {
          "url":
          "https://youtube.com/watch?v=abc",
          "final_name":
          "YouTube - cool video",
          "options": [{
            "link_uuid": 10,
            "variant_id": "1080p",
            "label": "video — 1080p"
          }],
        }
      }
    }

    await on_select_option(update, mock_context)

    update.callback_query.answer.assert_awaited_once()
    finalize_mock.assert_awaited_once_with(1, 10, "1080p",
                                           "YouTube - cool video")
    assert "1" not in mock_context.chat_data["pending_downloads"]

  async def test_expired_selection_is_reported(self, mock_context,
                                               monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: True)
    update = self._make_callback_update("dlopt:999:0")
    mock_context.chat_data = {"pending_downloads": {}}

    await on_select_option(update, mock_context)

    update.callback_query.edit_message_text.assert_awaited_once()
    args, _ = update.callback_query.edit_message_text.call_args
    assert "expired" in args[0]

  async def test_does_nothing_when_unauthorized(self, mock_context,
                                                monkeypatch):
    monkeypatch.setattr("handlers.message_handlers.is_authorized",
                        lambda update: False)
    update = self._make_callback_update("dlopt:1:0")
    mock_context.chat_data = {"pending_downloads": {}}

    await on_select_option(update, mock_context)

    update.callback_query.answer.assert_awaited_once_with("Not authorized.",
                                                          show_alert=True)
