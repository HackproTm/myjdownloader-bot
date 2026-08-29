"""Queue management endpoints for the Mini App.

Mirrors the bot's /queue, /list, /status, /remove commands.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import require_telegram_user
from shared.data import history
from shared.services.jdownloader import manager
from shared.utils import detect_platform

router = APIRouter(dependencies=[Depends(require_telegram_user)])


class QueueRequest(BaseModel):
  """Request body for POST /api/queue."""

  url: str
  name: Optional[str] = None
  force: bool = False


class SelectOptionRequest(BaseModel):
  """Request body for POST /api/queue/{package_uuid}/select."""

  link_uuid: Optional[int] = None
  variant_id: Optional[str] = None
  final_name: str


def _default_package_name(url: str) -> str:
  """Generate a default package name from a URL."""
  name = url.rstrip("/").split("/")[-1].split("?")[0]
  return name or "download"


@router.get("")
async def get_queue() -> list:
  """List packages currently queued (LinkGrabber) or actively downloading."""
  return await manager.list_queue()


@router.post("")
async def add_to_queue(payload: QueueRequest) -> dict:
  """
  Add a URL to the queue.

  Mirrors the Telegram bot's /queue command: checks for duplicates (unless
  forced) and, when the link offers more than one file/resolution, returns
  the list of options instead of queuing right away.
  """
  dedup_name = payload.name or _default_package_name(payload.url)

  if not payload.force:
    existing = history.find_duplicate(payload.url, dedup_name)
    if existing:
      return {"status": "duplicate", "existing": existing}

  try:
    collected = await manager.collect_link(payload.url, payload.name)
  except Exception as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc

  history.record(payload.url, dedup_name)

  platform = detect_platform(payload.url)
  base_name = payload.name or collected["package_name"] or dedup_name
  final_name = f"{platform} - {base_name}" if platform else base_name

  if len(collected["options"]) > 1:
    return {
      "status": "choose_option",
      "package_uuid": collected["package_uuid"],
      "final_name": final_name,
      "options": collected["options"],
    }

  chosen = collected["options"][0] if collected["options"] else {
    "link_uuid": None,
    "variant_id": None,
  }
  await manager.finalize_selection(collected["package_uuid"],
                                   chosen["link_uuid"], chosen["variant_id"],
                                   final_name)
  return {
    "status": "queued",
    "package_uuid": collected["package_uuid"],
    "final_name": final_name,
  }


@router.post("/{package_uuid}/select")
async def select_option(package_uuid: int,
                        payload: SelectOptionRequest) -> dict:
  """Finalize a file/resolution selection for a package with multiple options."""
  try:
    await manager.finalize_selection(package_uuid, payload.link_uuid,
                                     payload.variant_id, payload.final_name)
  except Exception as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
  return {
    "status": "queued",
    "package_uuid": package_uuid,
    "final_name": payload.final_name,
  }


@router.delete("/{name}")
async def remove_from_queue(name: str) -> dict:
  """Remove a download from the queue/JDownloader, deleting its local file if any."""
  removed = await manager.remove_from_queue(name)
  if not removed:
    raise HTTPException(status_code=404, detail="No queue entry found.")
  return {"status": "removed"}
