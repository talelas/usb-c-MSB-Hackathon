"""AI-MINDS FastAPI application.

Start with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import load_graphs, router
from app.db.postgres import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    log.info("Starting AI-MINDS backend …")

    # 1 – Ensure Postgres tables exist
    try:
        init_db()
        log.info("PostgreSQL tables initialized")
    except Exception:
        log.exception("PostgreSQL init failed — DB may be unavailable")

    # 2 – Load or build graphs
    load_graphs()

    yield  # ← app is running

    log.info("Shutting down AI-MINDS backend")


app = FastAPI(
    title="AI-MINDS",
    description="Retrieval-Augmented Generation backend with graph-augmented search",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes under /api
app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"service": "AI-MINDS", "docs": "/docs"}
