# -*- coding: utf-8 -*-
"""
API Key authentication middleware.

Simple header-based API key validation. API key is configured via .env.
The /health endpoint is always public (no auth required).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader

from config import API_KEY

log = logging.getLogger("ats.auth")

# Header name for the API key
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Paths that do NOT require authentication
PUBLIC_PATHS: set[str] = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
    "/favicon.ico",
    "/api/config",
}


async def verify_api_key(request: Request) -> None:
    """
    Middleware-style dependency that validates the API key header.

    Skips validation for:
    - Public paths (health, docs, frontend assets)
    - Static file requests
    - OPTIONS preflight requests (CORS)

    Raises HTTPException 401 if key is missing or invalid.
    """
    path = request.url.path

    # Skip auth for public paths
    if path in PUBLIC_PATHS:
        return

    # Skip auth for frontend static files (CSS, JS, pages, images)
    if path.startswith(("/static", "/pages", "/css", "/js")):
        return

    # Skip auth for CORS preflight
    if request.method == "OPTIONS":
        return

    # Extract and validate key
    api_key = request.headers.get("X-API-Key", "")

    if not api_key:
        log.warning("Missing API key for %s %s", request.method, path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include 'X-API-Key' header.",
        )

    if api_key != API_KEY:
        log.warning("Invalid API key for %s %s", request.method, path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
