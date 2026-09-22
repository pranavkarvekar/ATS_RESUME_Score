# -*- coding: utf-8 -*-
"""
Health check endpoint — always public, no auth required.
Used by monitoring tools, Docker HEALTHCHECK, and frontend status indicator.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models.schemas import HealthResponse
from config import GROQ_API_KEY, GROQ_MODEL, DEFAULT_SKILL_WEIGHT, DEFAULT_EXPERIENCE_WEIGHT, DEFAULT_CONTEXT_WEIGHT, API_KEY

log = logging.getLogger("ats.health")
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Operations"],
    summary="Health check",
)
async def health_check() -> HealthResponse:
    """
    Returns system health status including:
    - LLM model configured
    - API key presence
    - Database connectivity (placeholder until Phase 5)
    - Current scoring config version
    """
    return HealthResponse(
        status="ok",
        model=GROQ_MODEL,
        api_key_configured=bool(GROQ_API_KEY),
        database_connected=True,  # TODO: real DB check in Phase 5
        scoring_config_version="v1.0",
        default_weights={
            "skill": DEFAULT_SKILL_WEIGHT,
            "experience": DEFAULT_EXPERIENCE_WEIGHT,
            "context": DEFAULT_CONTEXT_WEIGHT,
        },
    )


@router.get(
    "/api/config",
    tags=["Operations"],
    summary="Frontend configuration (public)",
    include_in_schema=False,
)
async def get_frontend_config() -> JSONResponse:
    """
    Returns runtime configuration for the frontend.
    Public endpoint — served from same origin as frontend.
    Allows the frontend to pick up the correct API key at runtime.
    """
    return JSONResponse({"api_key": API_KEY})
