# -*- coding: utf-8 -*-
"""
ATS Resume Analyzer v2 — Application Entry Point

FastAPI app factory with:
- Lifespan hook (startup/shutdown)
- CORS middleware
- Rate limiting
- API key auth (middleware)
- Router registration
- Frontend static file serving
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import CORS_ORIGINS, FRONTEND_DIR
from security.auth import verify_api_key
from security.rate_limiter import limiter
from routers import health, analyze, history, feedback, analytics, compare
from db.database import create_tables, close_engine

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("ats.server")


# ─────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan hook.
    - Startup: initialize DB, seed scoring config
    - Shutdown: close DB connections
    """
    log.info("=" * 60)
    log.info("  ATS Resume Analyzer v2 -- Starting Up")
    log.info("=" * 60)

    # Initialize database and create tables
    await create_tables()
    log.info("Database: initialized and tables verified")
    log.info("Scoring weights: 35/25/40 (Skill/Exp/Context)")
    log.info("CORS origins: %s", CORS_ORIGINS)

    yield  # App is running

    log.info("ATS Resume Analyzer v2 — Shutting Down")
    await close_engine()


# ─────────────────────────────────────────────
# App Factory
# ─────────────────────────────────────────────
app = FastAPI(
    title="ATS Resume Analyzer v2",
    description=(
        "Intelligent resume screening system with hybrid scoring: "
        "rule-based deterministic scoring + LLM-based contextual scoring. "
        "Dynamic weight configuration (default 35/25/40)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────

# CORS — restricted to configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# API key authentication (runs on every request)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Validate API key on protected endpoints."""
    try:
        await verify_api_key(request)
    except Exception as exc:
        # Re-raise HTTPException as JSON response
        from fastapi.exceptions import HTTPException as FastAPIHTTPException
        if isinstance(exc, FastAPIHTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )
        raise
    return await call_next(request)


# ─────────────────────────────────────────────
# Register Routers
# ─────────────────────────────────────────────
app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(history.router)
app.include_router(feedback.router)
app.include_router(analytics.router)
app.include_router(compare.router)


# ─────────────────────────────────────────────
# Frontend Serving
# ─────────────────────────────────────────────

# Serve frontend static files (CSS, JS)
_css_dir = FRONTEND_DIR / "css"
_js_dir = FRONTEND_DIR / "js"
_pages_dir = FRONTEND_DIR / "pages"

log.info("Frontend directory resolved to: %s (index.html exists: %s)", FRONTEND_DIR, (FRONTEND_DIR / "index.html").exists())

if _css_dir.exists():
    app.mount("/css", StaticFiles(directory=str(_css_dir)), name="css")
if _js_dir.exists():
    app.mount("/js", StaticFiles(directory=str(_js_dir)), name="js")
if _pages_dir.exists():
    app.mount("/pages", StaticFiles(directory=str(_pages_dir)), name="pages")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the main frontend HTML page."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        status_code=200,
        content={
            "message": "ATS Resume Analyzer v2 API",
            "docs": "/docs",
            "health": "/health",
            "frontend": "Not found — create frontend/index.html",
        },
    )


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
