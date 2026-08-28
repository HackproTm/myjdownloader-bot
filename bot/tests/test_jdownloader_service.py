"""Tests for services.jdownloader."""

from unittest.mock import AsyncMock, MagicMock

from data import DownloadJob
from services.jdownloader import (
  JDownloaderManager,
  _find_by_name,
  _find_by_uuid_or_name,
  _first_link_url,
)


class TestFindByName:

  def test_returns_matching_package(self):
    packages = [{"name": "a", "uuid": 1}, {"name": "b", "uuid": 2}]
    assert _find_by_name(packages, "b") == {"name": "b", "uuid": 2}

  def test_returns_none_when_not_found(self):
    assert _find_by_name([{"name": "a"}], "z") is None


class TestFindByUuidOrName:

  def test_matches_by_uuid_first(self):
    packages = [{"name": "a", "uuid": 1}, {"name": "b", "uuid": 2}]
    assert _find_by_uuid_or_name(packages, 2, "a") == {"name": "b", "uuid": 2}

  def test_falls_back_to_name_when_uuid_missing(self):
    packages = [{"name": "a", "uuid": 1}]
    assert _find_by_uuid_or_name(packages, None, "a") == {
      "name": "a",
      "uuid": 1
    }

  def test_falls_back_to_name_when_uuid_not_found(self):
    packages = [{"name": "a", "uuid": 1}]
    assert _find_by_uuid_or_name(packages, 999, "a") == {
      "name": "a",
      "uuid": 1
    }

  def test_returns_none_when_nothing_matches(self):
    packages = [{"name": "a", "uuid": 1}]
    assert _find_by_uuid_or_name(packages, 999, "z") is None


class TestAddDownload:

  async def test_returns_download_job(self, monkeypatch):
    manager = JDownloaderManager()
    monkeypatch.setattr(manager, "ensure_connected", AsyncMock())
    monkeypatch.setattr(manager, "_run", AsyncMock())

    job = await manager.add_download("http://x.com/f.zip", "f.zip")

    assert isinstance(job, DownloadJob)
    assert job.url == "http://x.com/f.zip"
    assert job.package_name == "f.zip"
    manager.ensure_connected.assert_awaited_once()
    manager._run.assert_awaited_once()


class TestListAccounts:

  async def test_returns_accounts(self, monkeypatch):
    manager = JDownloaderManager()
    monkeypatch.setattr(manager, "ensure_connected", AsyncMock())
    monkeypatch.setattr(
      manager, "_run", AsyncMock(return_value=[{
        "hostname": "instagram.com"
      }]))

    accounts = await manager.list_accounts()

    assert accounts == [{"hostname": "instagram.com"}]
    manager.ensure_connected.assert_awaited_once()

  def test_sync_returns_device_accounts_list(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()
    manager._device.accounts.list_accounts.return_value = [{"hostname": "x"}]

    assert manager._list_accounts_sync() == [{"hostname": "x"}]


class TestAddAccount:

  async def test_calls_run_with_sync_helper(self, monkeypatch):
    manager = JDownloaderManager()
    monkeypatch.setattr(manager, "ensure_connected", AsyncMock())
    monkeypatch.setattr(manager, "_run", AsyncMock())

    await manager.add_account("instagram.com", "user", "pass")

    manager.ensure_connected.assert_awaited_once()
    manager._run.assert_awaited_once_with(manager._add_account_sync,
                                          "instagram.com", "user", "pass")

  def test_sync_calls_device_accounts_add_account(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()

    manager._add_account_sync("instagram.com", "user", "pass")

    manager._device.accounts.add_account.assert_called_once_with(
      "instagram.com", "user", "pass")


class TestRemoveAccount:

  async def test_calls_run_with_sync_helper(self, monkeypatch):
    manager = JDownloaderManager()
    monkeypatch.setattr(manager, "ensure_connected", AsyncMock())
    monkeypatch.setattr(manager, "_run", AsyncMock())

    await manager.remove_account(42)

    manager.ensure_connected.assert_awaited_once()
    manager._run.assert_awaited_once_with(manager._remove_account_sync, 42)

  def test_sync_calls_device_accounts_remove_accounts(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()

    manager._remove_account_sync(42)

    manager._device.accounts.remove_accounts.assert_called_once_with([42])


class TestConnectSync:

  def test_connects_and_stores_device(self, monkeypatch):
    manager = JDownloaderManager()
    mock_jd_instance = MagicMock()
    mock_jd_class = MagicMock(return_value=mock_jd_instance)
    monkeypatch.setattr("services.jdownloader.myjdapi.Myjdapi", mock_jd_class)

    manager._connect_sync()

    mock_jd_instance.set_app_key.assert_called_once_with("telegram-jd-bot")
    mock_jd_instance.connect.assert_called_once()
    mock_jd_instance.update_devices.assert_called_once()
    assert manager._jd is mock_jd_instance
    mock_jd_instance.get_device.assert_called_once()


class TestQueryHelpers:

  def test_query_linkgrabber_packages_calls_device(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()
    manager._device.linkgrabber.query_packages.return_value = [{"name": "a"}]

    result = manager._query_linkgrabber_packages()

    assert result == [{"name": "a"}]
    manager._device.linkgrabber.query_packages.assert_called_once()

  def test_query_linkgrabber_packages_handles_none(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()
    manager._device.linkgrabber.query_packages.return_value = None

    assert manager._query_linkgrabber_packages() == []

  def test_query_download_packages_calls_device(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()
    manager._device.downloads.query_packages.return_value = [{"name": "a"}]

    result = manager._query_download_packages()

    assert result == [{"name": "a"}]

  def test_query_download_links_calls_device(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()
    manager._device.downloads.query_links.return_value = [{"name": "f.zip"}]

    result = manager._query_download_links(42)

    assert result == [{"name": "f.zip"}]


class TestFirstLinkUrl:

  def test_returns_url_of_matching_package(self):
    links = [{
      "packageUUID": 1,
      "url": "http://a"
    }, {
      "packageUUID": 2,
      "url": "http://b"
    }]

    assert _first_link_url(links, 2) == "http://b"

  def test_returns_empty_string_when_no_match(self):
    assert _first_link_url([{"packageUUID": 1, "url": "http://a"}], 99) == ""


class TestListQueue:

  async def test_combines_linkgrabber_and_active_downloads(self, monkeypatch):
    manager = JDownloaderManager()
    monkeypatch.setattr(manager, "ensure_connected", AsyncMock())

    async def fake_run(fn, *args):
      return fn(*args)

    monkeypatch.setattr(manager, "_run", fake_run)
    monkeypatch.setattr(
      manager,
      "_query_linkgrabber_packages",
      lambda: [{
        "uuid": 1,
        "name": "queued.zip"
      }],
    )
    monkeypatch.setattr(
      manager,
      "_query_linkgrabber_links",
      lambda: [{
        "packageUUID": 1,
        "url": "http://x.com/queued.zip"
      }],
    )
    monkeypatch.setattr(
      manager,
      "_query_download_packages",
      lambda: [
        {
          "uuid": 2,
          "name": "downloading.zip",
          "status": "Downloading",
          "finished": False,
          "bytesTotal": 100,
          "bytesLoaded": 50,
        },
        {
          "uuid": 3,
          "name": "done.zip",
          "status": "Finished",
          "finished": True,
          "bytesTotal": 100,
          "bytesLoaded": 100,
        },
      ],
    )
    monkeypatch.setattr(
      manager,
      "_query_all_download_links",
      lambda: [{
        "packageUUID": 2,
        "url": "http://x.com/downloading.zip"
      }],
    )

    entries = await manager.list_queue()

    names = [e["name"] for e in entries]
    assert "queued.zip" in names
    assert "downloading.zip" in names
    assert "done.zip" not in names  # finished downloads are excluded


class TestRemoveFromQueue:

  async def test_removes_from_linkgrabber_when_found(self, monkeypatch):
    manager = JDownloaderManager()
    monkeypatch.setattr(manager, "ensure_connected", AsyncMock())
    run_mock = AsyncMock(side_effect=lambda fn, *args: fn(*args))
    monkeypatch.setattr(manager, "_run", run_mock)
    monkeypatch.setattr(manager, "_query_linkgrabber_packages",
                        lambda: [{
                          "uuid": 1,
                          "name": "f.zip"
                        }])
    monkeypatch.setattr(manager, "_remove_from_linkgrabber_sync", MagicMock())

    removed = await manager.remove_from_queue("f.zip")

    assert removed is True
    manager._remove_from_linkgrabber_sync.assert_called_once_with(1)

  async def test_removes_from_downloads_when_not_in_linkgrabber(
      self, monkeypatch):
    manager = JDownloaderManager()
    monkeypatch.setattr(manager, "ensure_connected", AsyncMock())
    run_mock = AsyncMock(side_effect=lambda fn, *args: fn(*args))
    monkeypatch.setattr(manager, "_run", run_mock)
    monkeypatch.setattr(manager, "_query_linkgrabber_packages", lambda: [])
    monkeypatch.setattr(manager, "_query_download_packages",
                        lambda: [{
                          "uuid": 2,
                          "name": "f.zip"
                        }])
    monkeypatch.setattr(manager, "_remove_from_downloads_sync", MagicMock())

    removed = await manager.remove_from_queue("f.zip")

    assert removed is True
    manager._remove_from_downloads_sync.assert_called_once_with(2)

  async def test_returns_false_when_not_found(self, monkeypatch):
    manager = JDownloaderManager()
    monkeypatch.setattr(manager, "ensure_connected", AsyncMock())
    run_mock = AsyncMock(side_effect=lambda fn, *args: fn(*args))
    monkeypatch.setattr(manager, "_run", run_mock)
    monkeypatch.setattr(manager, "_query_linkgrabber_packages", lambda: [])
    monkeypatch.setattr(manager, "_query_download_packages", lambda: [])

    assert await manager.remove_from_queue("missing.zip") is False

  def test_sync_removes_from_linkgrabber(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()

    manager._remove_from_linkgrabber_sync(1)

    manager._device.linkgrabber.remove_links.assert_called_once_with([], [1])

  def test_sync_removes_from_downloads_with_cleanup(self):
    manager = JDownloaderManager()
    manager._device = MagicMock()

    manager._remove_from_downloads_sync(2)

    manager._device.downloads.cleanup.assert_called_once_with(
      "DELETE_ALL", "REMOVE_LINKS_AND_DELETE_FILES", "SELECTED", [], [2])
