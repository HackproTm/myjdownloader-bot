"""Service layer for business logic shared by the bot and the Mini App API."""

from .jdownloader import JDownloaderManager, manager

__all__ = ["JDownloaderManager", "manager"]
