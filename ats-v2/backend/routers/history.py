# -*- coding: utf-8 -*-
"""
History endpoints — list past analyses and get detail by ID.

Queries the SQLite database for stored analysis records.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from models.schemas import AnalysisResult, HistoryItem, HistoryResponse
from db.database import get_session
from db import crud

log = logging.getLogger("ats.history")
router = APIRouter(prefix="/api/v1", tags=["History"])


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="List past analyses",
)
async def list_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    name: str = Query(default="", description="Filter by candidate name"),
    min_score: float = Query(default=0.0, ge=0.0, le=100.0, description="Min score filter"),
    max_score: float = Query(default=100.0, ge=0.0, le=100.0, description="Max score filter"),
) -> HistoryResponse:
    """Returns paginated list of past analyses from the database."""
    log.info("History request: page=%d limit=%d name=%s", page, limit, name)

    async with get_session() as session:
        records, total = await crud.list_analyses(
            session,
            page=page,
            limit=limit,
            name_filter=name,
            min_score=min_score,
            max_score=max_score,
        )

    items = [
        HistoryItem(
            id=UUID(r.id),
            candidate_name=r.candidate_name,
            total_score=r.total_score,
            extraction_tier_used=r.extraction_tier_used,
            scoring_config_version=r.scoring_config_version,
            processing_time_ms=r.processing_time_ms,
            created_at=r.created_at,
        )
        for r in records
    ]

    return HistoryResponse(items=items, total=total, page=page, limit=limit)


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResult,
    summary="Get analysis detail by ID",
)
async def get_analysis_detail(analysis_id: UUID) -> AnalysisResult:
    """Returns full analysis detail for a specific analysis UUID."""
    log.info("Detail request: id=%s", analysis_id)

    async with get_session() as session:
        record = await crud.get_analysis(session, str(analysis_id))

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found.",
        )

    return crud.record_to_analysis_result(record)
