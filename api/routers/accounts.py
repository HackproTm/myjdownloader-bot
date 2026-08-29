"""Premium account management endpoints for the Mini App.

Mirrors the bot's /accounts, /addaccount, /removeaccount commands.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import require_telegram_user
from shared.services.jdownloader import manager

router = APIRouter(dependencies=[Depends(require_telegram_user)])


class AccountRequest(BaseModel):
  """Request body for POST /api/accounts."""

  hoster: str
  username: str
  password: str


@router.get("")
async def list_accounts() -> list:
  """List configured premium accounts."""
  return await manager.list_accounts()


@router.post("")
async def add_account(payload: AccountRequest) -> dict:
  """Add a premium account for a hoster plugin (e.g. "instagram.com")."""
  try:
    await manager.add_account(payload.hoster, payload.username,
                              payload.password)
  except Exception as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
  return {"status": "added"}


@router.delete("/{account_id}")
async def remove_account(account_id: int) -> dict:
  """Remove a premium account by its UUID."""
  try:
    await manager.remove_account(account_id)
  except Exception as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
  return {"status": "removed"}
