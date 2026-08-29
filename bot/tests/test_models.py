"""Tests for data.models."""

from shared.data.models import DownloadJob


class TestDownloadJob:

  def test_default_values(self):
    job = DownloadJob(url="http://x.com/a.zip", package_name="a.zip")

    assert job.url == "http://x.com/a.zip"
    assert job.package_name == "a.zip"
    assert job.package_uuid is None
    assert job.bytes_total == 0
    assert job.bytes_loaded == 0
    assert job.status == "pending"

  def test_custom_values(self):
    job = DownloadJob(
      url="http://x.com/a.zip",
      package_name="a.zip",
      package_uuid=42,
      bytes_total=100,
      bytes_loaded=50,
      status="Downloading",
    )

    assert job.package_uuid == 42
    assert job.bytes_total == 100
    assert job.bytes_loaded == 50
    assert job.status == "Downloading"
