# -*- coding: utf-8 -*-
"""
Analytics endpoints — aggregate statistics from the database.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from models.schemas import AnalyticsSummary
from db.database import get_session
from db import crud

log = logging.getLogger("ats.analytics")
router = APIRouter(prefix="/api/v1", tags=["Analytics"])


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummary,
    summary="Get aggregate analytics",
)
async def get_analytics_summary() -> AnalyticsSummary:
    """
    Returns aggregate statistics across all analyses:
    - Total analyses count
    - Average score
    - Score distribution histogram
    - Extraction tier distribution
    - Feedback breakdown
    - LLM parse success rate
    """
    log.info("Analytics summary requested")

    async with get_session() as session:
        data = await crud.get_analytics_data(session)

    return AnalyticsSummary(**data)
