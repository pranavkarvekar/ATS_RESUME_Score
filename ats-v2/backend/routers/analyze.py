# -*- coding: utf-8 -*-
"""
Resume analysis endpoint — POST /api/v1/analyze

Full pipeline: validate → extract → cache check → parse → verify → score → store → return.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from models.schemas import AnalysisResult, ParsedResume
from security.file_validator import validate_file
from security.sanitizer import sanitize_text
from extraction import pipeline
from parsing import llm_parser, verifier
from scoring import aggregator
from db.database import get_session
from db import crud

log = logging.getLogger("ats.analyze")
router = APIRouter(prefix="/api/v1", tags=["Analysis"])


@router.post(
    "/analyze",
    response_model=AnalysisResult,
    summary="Analyze a resume against a job description",
    status_code=status.HTTP_200_OK,
)
async def analyze_resume(
    resume: UploadFile = File(..., description="PDF or DOCX resume file"),
    job_description: str = Form(..., description="Job description text"),
    required_skills: str = Form(default="", description="Comma-separated required skills"),
    experience_target_months: int = Form(default=36, description="Target experience in months"),
) -> AnalysisResult:
    """
    Full analysis pipeline:
    1. Validate file (type, size, magic bytes)
    2. Extract text (3-tier pipeline)
    3. Check resume cache (SHA-256 hash)
    4. Parse with LLM (3 retries + regex fallback)
    5. Verify parsed data against raw text
    6. Score (skill match + experience + contextual)
    7. Store result in database
    8. Return AnalysisResult
    """
    start_time = time.time()

    # ── Input validation ──────────────────────
    if not job_description.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job description cannot be empty.",
        )

    content_type = resume.content_type or ""
    if content_type not in (
        "application/pdf",
        "application/octet-stream",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}. Upload a PDF or DOCX.",
        )

    file_bytes = await resume.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    # Parse required skills list
    skills_list = [s.strip() for s in required_skills.split(",") if s.strip()]

    # 1. Validate file (type, size, magic bytes)
    is_valid, error_msg, detected_type = validate_file(file_bytes, resume.filename or "")
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg,
        )

    # 2. Compute resume hash for cache
    resume_hash = crud.compute_resume_hash(file_bytes)

    # 3. Check cache
    cache_hit = False
    async with get_session() as session:
        cached = await crud.get_cached_resume(session, resume_hash)

    if cached:
        # Cache hit — skip extraction + parsing
        cache_hit = True
        parsed_resume = ParsedResume.model_validate(cached.parsed_resume_json)
        tier_used = f"tier{cached.extraction_tier_used}_cached"
        tier_num = cached.extraction_tier_used
        parse_attempts = cached.llm_parse_attempts
        used_fallback = cached.used_regex_fallback
        extracted_text = "[cached — extraction skipped]"
        clean_text = ""
        log.info("Cache HIT for %s — skipping extraction + parsing", resume_hash[:12])
    else:
        # Cache miss — full pipeline
        # 3a. Extract text
        try:
            extracted_text, tier_used = await pipeline.extract_resume_text(file_bytes, detected_type)
        except Exception as e:
            log.error("Extraction failed: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to extract text from document: {str(e)}"
            )

        # 3b. Sanitize text
        clean_text = sanitize_text(extracted_text)

        # 4. Parse with LLM
        try:
            parsed_resume, parse_attempts, used_fallback = await llm_parser.parse_resume_with_groq(clean_text)
        except Exception as e:
            log.error("LLM Parsing failed unexpectedly: %s — using regex fallback", str(e))
            from parsing import regex_fallback
            fallback_data = regex_fallback.fallback_parse(clean_text)
            parsed_resume = ParsedResume(**fallback_data)
            parse_attempts = 0
            used_fallback = True

        # Convert tier string to int
        tier_map = {"tier1_fitz": 1, "tier2_plumber": 2, "tier3_ocr": 3, "docx": 4, "failed": 0}
        tier_num = tier_map.get(tier_used, 0)

        # Store in cache
        async with get_session() as session:
            await crud.cache_resume(session, resume_hash, parsed_resume, tier_num, parse_attempts, used_fallback)

    # 5. Verify parsed data
    verified_skills, unverified_skills = verifier.verify_parsed_data(
        parsed_resume, clean_text if clean_text else ""
    )

    # 6. Scoring Engine
    (
        total_score,
        skill_score,
        exp_score,
        ctx_score,
        matched_skills,
        missing_skills,
        justification
    ) = await aggregator.calculate_total_score(
        parsed_resume=parsed_resume,
        job_description=job_description,
        required_skills=skills_list,
        target_months=experience_target_months,
        skill_weight=35,
        experience_weight=25,
        context_weight=40
    )

    total_candidate_months = sum(exp.duration_months for exp in parsed_resume.experience)
    processing_time_ms = int((time.time() - start_time) * 1000)

    log.info(
        "Analyze complete: file=%s size=%d, score=%.1f, tier=%d, cached=%s, time=%dms",
        resume.filename, len(file_bytes), total_score, tier_num, cache_hit, processing_time_ms
    )

    # Build result
    result = AnalysisResult(
        id=uuid.uuid4(),
        candidate_name=parsed_resume.name,
        parsed_resume=parsed_resume,
        total_score=total_score,
        semantic_skill_match=skill_score,
        experience_longevity=exp_score,
        context_alignment=ctx_score,
        context_justification=justification,
        scoring_config_version="v1.0",
        skill_weight=35,
        experience_weight=25,
        context_weight=40,
        total_experience_months=total_candidate_months,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        extraction_tier_used=tier_num,
        processing_time_ms=processing_time_ms,
        llm_parse_attempts=parse_attempts,
        used_regex_fallback=used_fallback,
        difficult_layout_detected=False,
        manual_review_recommended=used_fallback,
        field_confidence={},
        verified_skills=verified_skills,
        unverified_skills=unverified_skills,
        unverified_fields=[],
        created_at=datetime.now(timezone.utc),
        calibration_applied=cache_hit,
    )

    # 7. Store in database
    async with get_session() as session:
        scoring_config = await crud.get_or_create_scoring_config(session)
        await crud.create_analysis(
            session=session,
            result=result,
            job_description=job_description,
            required_skills_csv=required_skills,
            experience_target_months=experience_target_months,
            resume_hash=resume_hash,
            scoring_config=scoring_config,
        )

    return result
