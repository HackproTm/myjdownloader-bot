"""Service layer re-exported from the shared package."""

from shared.services.jdownloader import JDownloaderManager, manager

__all__ = ["JDownloaderManager", "manager"]
