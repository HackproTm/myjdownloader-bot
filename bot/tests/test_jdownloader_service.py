"""Tests for services.jdownloader."""

from unittest.mock import AsyncMock, MagicMock

from data import DownloadJob
from services.jdownloader import JDownloaderManager, _find_by_name, _find_by_uuid_or_name


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
