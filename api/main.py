"""Mini App API entry point.

Run from the repo root with: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import logging

from dotenv import load_dotenv

# load_dotenv must run BEFORE importing api.config (which reads os.environ)
load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from api.config import CORS_ORIGINS  # noqa: E402
from api.routers import accounts, queue  # noqa: E402

logging.basicConfig(
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MyJDownloader Mini App API")

if CORS_ORIGINS:
  app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
  )

app.include_router(queue.router, prefix="/api/queue", tags=["queue"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])


@app.get("/api/health")
async def health() -> dict:
  """Liveness check (no auth required)."""
  return {"status": "ok"}
