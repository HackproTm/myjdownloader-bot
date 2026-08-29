"""MyJDownloader service for managing downloads."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable, Optional

import myjdapi

from config import (
  DOWNLOADS_PATH,
  MYJD_DEVICE_NAME,
  MYJD_EMAIL,
  MYJD_PASSWORD,
  POLL_INTERVAL,
)
from data import DownloadJob
from utils.file_utils import newest_file, search_in_tree
from utils.formatters import describe_option_label

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


class JDownloaderManager:
  """Manages interactions with MyJDownloader API."""

  def __init__(self) -> None:
    """Initialize the manager."""
    self._jd: Optional[myjdapi.Myjdapi] = None
    self._device = None
    self._lock = asyncio.Lock()

  # ── Connection ────────────────────────────────────────────────────────────

  async def ensure_connected(self,
                             max_retries: int = 10,
                             retry_delay: int = 15) -> None:
    """
    Ensure connection to MyJDownloader is established.

    Args:
      max_retries: Maximum number of retry attempts
      retry_delay: Delay between retries in seconds

    Raises:
      RuntimeError: If connection cannot be established
    """
    async with self._lock:
      if self._device is not None:
        return
      for attempt in range(1, max_retries + 1):
        try:
          await self._run(self._connect_sync)
          logger.info("Connected to MyJDownloader device: %s",
                      MYJD_DEVICE_NAME)
          return
        except Exception as exc:
          logger.warning("Attempt %d/%d failed: %s", attempt, max_retries, exc)
          if attempt < max_retries:
            await asyncio.sleep(retry_delay)
      raise RuntimeError(
        f"Could not connect to MyJDownloader after {max_retries} attempts.")

  async def reconnect(self) -> None:
    """Reconnect to MyJDownloader."""
    logger.info("Reconnecting to MyJDownloader...")
    async with self._lock:
      self._jd = None
      self._device = None
    await self.ensure_connected()

  def _connect_sync(self) -> None:
    """Synchronously connect to MyJDownloader."""
    jd = myjdapi.Myjdapi()
    jd.set_app_key("telegram-jd-bot")
    jd.connect(MYJD_EMAIL, MYJD_PASSWORD)
    jd.update_devices()
    self._jd = jd
    self._device = jd.get_device(MYJD_DEVICE_NAME)

  # ── Helpers ───────────────────────────────────────────────────────────────

  async def _run(self, fn, *args):
    """Run a synchronous function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)

  # ── Collect & select ──────────────────────────────────────────────────────

  async def collect_link(self, url: str, package_name: Optional[str]) -> dict:
    """
    Add a URL to the LinkGrabber (without starting the download yet) and
    report the selectable options (files/resolutions/formats) it offers.

    Args:
      url: URL to add
      package_name: Requested package name, or None to let JDownloader name
        it automatically from site metadata (e.g. the real video title)

    Returns:
      Dict with "package_uuid", "package_name" (as resolved by JDownloader),
      and "options" (list of dicts with "link_uuid", "variant_id", "label")

    Raises:
      RuntimeError: If the link could not be added (offline, unsupported, etc.)
    """
    await self.ensure_connected()

    before = await self._run(self._query_linkgrabber_packages)
    before_uuids = {pkg["uuid"] for pkg in before}

    await self._run(self._add_link_sync, url, package_name)
    await self._wait_until_collected()

    after = await self._run(self._query_linkgrabber_packages)
    new_pkgs = [pkg for pkg in after if pkg["uuid"] not in before_uuids]
    if not new_pkgs:
      raise RuntimeError(
        "The link could not be added (offline, unsupported, or duplicate).")

    pkg = new_pkgs[0]
    links = await self._run(self._query_linkgrabber_links_for_package,
                            pkg["uuid"])
    options = await self._build_options(links)

    return {
      "package_uuid": pkg["uuid"],
      "package_name": pkg["name"],
      "options": options,
    }

  def _add_link_sync(self, url: str, package_name: Optional[str]) -> None:
    """Synchronously add a link to the LinkGrabber (not started yet)."""
    self._device.linkgrabber.add_links([{
      "autostart":
      False,
      "links":
      url,
      "packageName":
      package_name,
      "destinationFolder":
      DOWNLOADS_PATH,
      "overwritePackagizerRules":
      bool(package_name),
    }])

  async def _wait_until_collected(self, max_wait: float = 15.0) -> None:
    """Wait for the LinkGrabber to finish resolving the added link."""
    await asyncio.sleep(1.5)  # Give JD a moment to start collecting.
    elapsed = 0.0
    while elapsed < max_wait:
      collecting = await self._run(self._is_collecting_sync)
      if not collecting:
        return
      await asyncio.sleep(1)
      elapsed += 1

  def _is_collecting_sync(self) -> bool:
    """Synchronously check if the LinkGrabber is still resolving links."""
    return bool(self._device.linkgrabber.is_collecting())

  def _query_linkgrabber_links_for_package(self, package_uuid: int) -> list:
    """Query links of a specific LinkGrabber package, including variants."""
    return (self._device.linkgrabber.query_links(
      [{
        "packageUUIDs": [package_uuid],
        "name": True,
        "url": True,
        "variant": True,
        "variants": True,
      }]) or [])

  async def _build_options(self, links: list) -> list:
    """Build the list of selectable options (link + variant) for a package."""
    options = []
    for link in links:
      variants = []
      if link.get("variants"):
        variants = await self._run(self._get_variants_sync, link["uuid"])

      link_name = link.get("name", "file")
      if len(variants) > 1:
        for variant in variants:
          variant_name = variant.get("name", variant.get("id", "variant"))
          options.append({
            "link_uuid":
            link["uuid"],
            "variant_id":
            variant.get("id"),
            "label":
            describe_option_label(link_name, variant_name),
          })
      else:
        options.append({
          "link_uuid": link["uuid"],
          "variant_id": None,
          "label": describe_option_label(link_name),
        })
    return options

  def _get_variants_sync(self, link_uuid: int) -> list:
    """Synchronously get the available variants of a link."""
    return self._device.linkgrabber.get_variants([link_uuid]) or []

  async def finalize_selection(
    self,
    package_uuid: int,
    chosen_link_uuid: Optional[int],
    variant_id: Optional[str],
    final_name: str,
  ) -> None:
    """
    Keep only the chosen link in a LinkGrabber package, apply its variant,
    rename the package, and move it to the download queue.

    Args:
      package_uuid: LinkGrabber package UUID
      chosen_link_uuid: UUID of the link to keep (None keeps everything)
      variant_id: Variant ID to select on the chosen link, if any
      final_name: Name to assign to the package before downloading
    """
    await self.ensure_connected()

    if chosen_link_uuid is not None:
      all_links = await self._run(self._query_linkgrabber_links_for_package,
                                  package_uuid)
      other_ids = [
        link["uuid"] for link in all_links if link["uuid"] != chosen_link_uuid
      ]
      if other_ids:
        await self._run(self._remove_linkgrabber_links_sync, other_ids)

      if variant_id:
        await self._run(self._set_variant_sync, chosen_link_uuid, variant_id)

    await self._run(self._rename_package_sync, package_uuid, final_name)
    await self._run(self._move_to_downloadlist_sync, package_uuid)

  def _remove_linkgrabber_links_sync(self, link_ids: list) -> None:
    """Synchronously remove links (not the whole package) from the LinkGrabber."""
    self._device.linkgrabber.remove_links(link_ids, [])

  def _set_variant_sync(self, link_uuid: int, variant_id: str) -> None:
    """Synchronously select a variant for a link (not wrapped by myjdapi)."""
    self._device.action("/linkgrabberv2/setVariant", [variant_id, [link_uuid]])

  def _rename_package_sync(self, package_uuid: int, name: str) -> None:
    """Synchronously rename a LinkGrabber package."""
    self._device.linkgrabber.rename_package(package_uuid, name)

  def _move_to_downloadlist_sync(self, package_uuid: int) -> None:
    """Synchronously move a package from LinkGrabber to the download queue."""
    self._device.linkgrabber.move_to_downloadlist([], [package_uuid])

  # ── Monitoring ────────────────────────────────────────────────────────────

  async def monitor_job(
    self,
    job: DownloadJob,
    on_progress: Optional[Callable[[DownloadJob], Awaitable[None]]] = None,
  ) -> str:
    """
    Monitor a download job until completion.

    Args:
      job: DownloadJob to monitor
      on_progress: Optional callback for progress updates

    Returns:
      Absolute path of the downloaded file

    Raises:
      RuntimeError: If download fails
    """
    await asyncio.sleep(4)  # Allow JD to process the link.

    # Phase 1 - move from LinkGrabber to download queue
    await self._phase_move_to_queue(job)

    # Phase 2 - poll until completion
    return await self._phase_wait_completion(job, on_progress)

  async def _phase_move_to_queue(self,
                                 job: DownloadJob,
                                 max_attempts: int = 20) -> None:
    """Move package from LinkGrabber to download queue."""
    for attempt in range(max_attempts):
      try:
        # Already in downloads (autostart may have moved it)?
        dl_pkgs = await self._run(self._query_download_packages)
        match = _find_by_name(dl_pkgs, job.package_name)
        if match:
          job.package_uuid = match["uuid"]
          logger.info(
            "Package '%s' is already in download queue.",
            job.package_name,
          )
          return

        # Still in LinkGrabber?
        lg_pkgs = await self._run(self._query_linkgrabber_packages)
        match = _find_by_name(lg_pkgs, job.package_name)
        if match:
          job.package_uuid = match["uuid"]
          await self._run(
            self._device.linkgrabber.move_to_downloadlist,
            [],
            [job.package_uuid],
          )
          logger.info("Package '%s' moved to download queue.",
                      job.package_name)
          return

      except Exception as exc:
        logger.warning("Phase 1 error (attempt %d): %s", attempt + 1, exc)
        try:
          await self.reconnect()
        except Exception:
          pass

      await asyncio.sleep(3)

    raise RuntimeError(
      f"Package '{job.package_name}' did not appear in JDownloader after 60 seconds."
    )

  async def _phase_wait_completion(
    self,
    job: DownloadJob,
    on_progress: Optional[Callable[[DownloadJob], Awaitable[None]]],
  ) -> str:
    """Poll until download is complete."""
    last_reported_pct = -1.0

    while True:
      try:
        dl_pkgs = await self._run(self._query_download_packages)
        match = _find_by_uuid_or_name(dl_pkgs, job.package_uuid,
                                      job.package_name)

        if match:
          job.package_uuid = match["uuid"]
          job.bytes_total = match.get("bytesTotal", 0)
          job.bytes_loaded = match.get("bytesLoaded", 0)
          job.status = match.get("status", "")

          # Report progress every ~10%
          if on_progress and job.bytes_total > 0:
            pct = job.bytes_loaded / job.bytes_total * 100
            if pct - last_reported_pct >= 10:
              last_reported_pct = pct
              try:
                await on_progress(job)
              except Exception:
                pass

          if match.get("finished") or job.status in (
              "Finished",
              "Extraction OK",
          ):
            return await self._locate_file(job)

          if "Error" in job.status or "Failed" in job.status:
            raise RuntimeError(f"Download failed: {job.status}")

      except RuntimeError:
        raise
      except Exception as exc:
        logger.warning("Error while monitoring download: %s", exc)
        await asyncio.sleep(5)
        try:
          await self.reconnect()
        except Exception:
          pass

      await asyncio.sleep(POLL_INTERVAL)

  # ── Locate file ───────────────────────────────────────────────────────────

  async def _locate_file(self, job: DownloadJob) -> str:
    """Locate the downloaded file on disk."""
    # Try to resolve actual file name via package links.
    if job.package_uuid:
      try:
        links = await self._run(self._query_download_links, job.package_uuid)
        for link in links:
          name = link.get("name", "")
          if name:
            path = search_in_tree(DOWNLOADS_PATH, name)
            if path:
              return path
      except Exception as exc:
        logger.warning("Could not query package links: %s", exc)

    # Fallback: most recently modified file in download directory.
    path = newest_file(DOWNLOADS_PATH)
    if path:
      return path

    raise RuntimeError("Download completed but file was not found on disk.")

  # ── Sync queries ──────────────────────────────────────────────────────────

  def _query_linkgrabber_packages(self) -> list:
    """Query packages in LinkGrabber."""
    return (self._device.linkgrabber.query_packages([{
      "name": True,
      "uuid": True
    }]) or [])

  def _query_download_packages(self) -> list:
    """Query packages in download queue."""
    return (self._device.downloads.query_packages([{
      "name": True,
      "uuid": True,
      "status": True,
      "finished": True,
      "bytesTotal": True,
      "bytesLoaded": True,
    }]) or [])

  def _query_download_links(self, package_uuid: int) -> list:
    """Query links in a package."""
    return (self._device.downloads.query_links([{
      "packageUUIDs": [package_uuid],
      "name": True,
      "finished": True
    }]) or [])

  # ── Queue management ─────────────────────────────────────────────────────

  async def list_queue(self) -> list:
    """
    List packages that are queued (LinkGrabber) or actively downloading.

    Finished downloads are excluded since they've already been delivered.

    Returns:
      List of dicts with uuid, name, url, status, bytes_total, bytes_loaded
    """
    await self.ensure_connected()

    lg_pkgs = await self._run(self._query_linkgrabber_packages)
    lg_links = await self._run(self._query_linkgrabber_links)
    dl_pkgs = await self._run(self._query_download_packages)
    dl_links = await self._run(self._query_all_download_links)

    entries = []
    for pkg in lg_pkgs:
      entries.append({
        "uuid": pkg["uuid"],
        "name": pkg["name"],
        "url": _first_link_url(lg_links, pkg["uuid"]),
        "status": "Queued",
        "bytes_total": 0,
        "bytes_loaded": 0,
      })
    for pkg in dl_pkgs:
      if pkg.get("finished"):
        continue
      entries.append({
        "uuid": pkg["uuid"],
        "name": pkg["name"],
        "url": _first_link_url(dl_links, pkg["uuid"]),
        "status": pkg.get("status", ""),
        "bytes_total": pkg.get("bytesTotal", 0),
        "bytes_loaded": pkg.get("bytesLoaded", 0),
      })
    return entries

  def _query_linkgrabber_links(self) -> list:
    """Query links in LinkGrabber (with URL)."""
    return (self._device.linkgrabber.query_links([{
      "url": True,
      "packageUUIDs": [],
    }]) or [])

  def _query_all_download_links(self) -> list:
    """Query all links in the download list (with URL)."""
    return (self._device.downloads.query_links([{
      "url": True,
      "packageUUIDs": [],
    }]) or [])

  async def remove_from_queue(self, package_name: str) -> bool:
    """
    Remove a package by name from LinkGrabber or Downloads.

    When removed from Downloads, the local files are deleted too.

    Args:
      package_name: Name of the package to remove

    Returns:
      True if a matching package was found and removed, False otherwise
    """
    await self.ensure_connected()

    lg_pkgs = await self._run(self._query_linkgrabber_packages)
    match = _find_by_name(lg_pkgs, package_name)
    if match:
      await self._run(self._remove_from_linkgrabber_sync, match["uuid"])
      return True

    dl_pkgs = await self._run(self._query_download_packages)
    match = _find_by_name(dl_pkgs, package_name)
    if match:
      await self._run(self._remove_from_downloads_sync, match["uuid"])
      return True

    return False

  def _remove_from_linkgrabber_sync(self, package_uuid: int) -> None:
    """Synchronously remove a package from the LinkGrabber list."""
    self._device.linkgrabber.remove_links([], [package_uuid])

  def _remove_from_downloads_sync(self, package_uuid: int) -> None:
    """Synchronously remove a package from Downloads and delete its files on disk."""
    self._device.downloads.cleanup(
      "DELETE_ALL",
      "REMOVE_LINKS_AND_DELETE_FILES",
      "SELECTED",
      [],
      [package_uuid],
    )

  # ── Accounts ──────────────────────────────────────────────────────────────

  async def list_accounts(self) -> list:
    """List configured premium accounts."""
    await self.ensure_connected()
    return await self._run(self._list_accounts_sync)

  def _list_accounts_sync(self) -> list:
    """Synchronously list premium accounts."""
    return self._device.accounts.list_accounts() or []

  async def add_account(self, hoster: str, username: str,
                        password: str) -> None:
    """Add a premium account for a hoster plugin (e.g. "instagram.com")."""
    await self.ensure_connected()
    await self._run(self._add_account_sync, hoster, username, password)

  def _add_account_sync(self, hoster: str, username: str,
                        password: str) -> None:
    """Synchronously add a premium account."""
    self._device.accounts.add_account(hoster, username, password)

  async def remove_account(self, account_id: int) -> None:
    """Remove a premium account by its UUID."""
    await self.ensure_connected()
    await self._run(self._remove_account_sync, account_id)

  def _remove_account_sync(self, account_id: int) -> None:
    """Synchronously remove a premium account."""
    self._device.accounts.remove_accounts([account_id])


# ── Utilities ──────────────────────────────────────────────────────────────────


def _find_by_name(packages: list, name: str) -> Optional[dict]:
  """Find a package by name."""
  return next((p for p in packages if p.get("name") == name), None)


def _find_by_uuid_or_name(packages: list, uuid: Optional[int],
                          name: str) -> Optional[dict]:
  """Find a package by UUID or name."""
  if uuid is not None:
    match = next((p for p in packages if p.get("uuid") == uuid), None)
    if match:
      return match
  return _find_by_name(packages, name)


def _first_link_url(links: list, package_uuid: int) -> str:
  """Find the URL of the first link belonging to a package."""
  for link in links:
    if link.get("packageUUID") == package_uuid:
      return link.get("url", "")
  return ""


# Shared global instance used by handlers.
manager = JDownloaderManager()
