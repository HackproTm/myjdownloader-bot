"""Logger configuration."""

import logging


def configure_logging() -> None:
  """Configure logging for the application."""
  logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
  )
  # Suppress verbose logs from external libraries
  logging.getLogger("httpx").setLevel(logging.WARNING)
  logging.getLogger("httpcore").setLevel(logging.WARNING)
