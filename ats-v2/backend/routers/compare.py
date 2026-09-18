# -*- coding: utf-8 -*-
"""
Compare endpoint — GET /api/v1/compare?a={id}&b={id}

Returns two full AnalysisResult objects side-by-side for frontend comparison.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from models.schemas import AnalysisResult
from db.database import get_session
from db import crud

log = logging.getLogger("ats.compare")
router = APIRouter(prefix="/api/v1", tags=["Compare"])


class CompareResponse(BaseModel):
    """Response containing two analysis results for comparison."""
    analysis_a: AnalysisResult
    analysis_b: AnalysisResult


@router.get(
    "/compare",
    response_model=CompareResponse,
    summary="Compare two analyses side-by-side",
)
async def compare_analyses(
    a: UUID = Query(..., description="First analysis UUID"),
    b: UUID = Query(..., description="Second analysis UUID"),
) -> CompareResponse:
    """
    Returns two full analysis results for side-by-side comparison.
    Both must exist in the database.
    """
    log.info("Compare request: a=%s b=%s", a, b)

    async with get_session() as session:
        record_a = await crud.get_analysis(session, str(a))
        record_b = await crud.get_analysis(session, str(b))

    if record_a is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis A ({a}) not found.",
        )
    if record_b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis B ({b}) not found.",
        )

    return CompareResponse(
        analysis_a=crud.record_to_analysis_result(record_a),
        analysis_b=crud.record_to_analysis_result(record_b),
    )
