# -*- coding: utf-8 -*-
"""
Feedback endpoint — POST /api/v1/feedback

Stores recruiter feedback in the database.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from models.schemas import FeedbackRequest, FeedbackResponse
from db.database import get_session
from db import crud

log = logging.getLogger("ats.feedback")
router = APIRouter(prefix="/api/v1", tags=["Feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Submit recruiter feedback on an analysis",
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    Records recruiter feedback about a specific analysis in the database.

    Feedback types:
    - accurate: The score matched the recruiter's assessment
    - too_high: The score was higher than expected
    - too_low: The score was lower than expected
    - inaccurate: The score was significantly wrong
    """
    log.info(
        "Feedback received: analysis=%s type=%s reason=%s",
        request.analysis_id,
        request.feedback_type,
        request.reason[:100] if request.reason else "",
    )

    # Verify the analysis exists
    async with get_session() as session:
        analysis = await crud.get_analysis(session, str(request.analysis_id))
        if analysis is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {request.analysis_id} not found.",
            )

        fb = await crud.create_feedback(
            session=session,
            analysis_id=str(request.analysis_id),
            feedback_type=request.feedback_type,
            reason=request.reason or "",
        )

    return FeedbackResponse(
        id=uuid.UUID(fb.id),
        analysis_id=request.analysis_id,
        feedback_type=request.feedback_type,
        message="Feedback recorded successfully.",
        created_at=fb.created_at,
    )
