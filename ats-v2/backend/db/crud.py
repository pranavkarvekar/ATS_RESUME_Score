# -*- coding: utf-8 -*-
"""
CRUD Operations.

All database read/write operations for analyses, feedback, scoring config, and cache.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import AnalysisRecord, RecruiterFeedback, ResumeCache, ScoringConfig
from models.schemas import AnalysisResult, ParsedResume
import config

log = logging.getLogger("ats.db.crud")


# ─────────────────────────────────────────────
# Scoring Config
# ─────────────────────────────────────────────

async def get_or_create_scoring_config(session: AsyncSession) -> ScoringConfig:
    """Finds the active scoring config or creates the default one."""
    stmt = select(ScoringConfig).where(ScoringConfig.is_active == True).limit(1)
    result = await session.execute(stmt)
    cfg = result.scalar_one_or_none()

    if cfg is None:
        cfg = ScoringConfig(
            id=str(uuid.uuid4()),
            version="v1.0",
            skill_weight=config.DEFAULT_SKILL_WEIGHT,
            experience_weight=config.DEFAULT_EXPERIENCE_WEIGHT,
            context_weight=config.DEFAULT_CONTEXT_WEIGHT,
            model_name=config.GROQ_MODEL,
            is_active=True,
        )
        session.add(cfg)
        await session.flush()
        log.info("Created default ScoringConfig v1.0")

    return cfg


# ─────────────────────────────────────────────
# Analysis Records
# ─────────────────────────────────────────────

async def create_analysis(
    session: AsyncSession,
    result: AnalysisResult,
    job_description: str,
    required_skills_csv: str,
    experience_target_months: int,
    resume_hash: str | None,
    scoring_config: ScoringConfig,
) -> AnalysisRecord:
    """Stores an AnalysisResult in the database."""
    record = AnalysisRecord(
        id=str(result.id),
        candidate_name=result.candidate_name,
        parsed_resume_json=result.parsed_resume.model_dump(),
        total_score=result.total_score,
        semantic_skill_match=result.semantic_skill_match,
        experience_longevity=result.experience_longevity,
        context_alignment=result.context_alignment,
        context_justification=result.context_justification,
        total_experience_months=result.total_experience_months,
        matched_skills=result.matched_skills,
        missing_skills=result.missing_skills,
        extraction_tier_used=result.extraction_tier_used,
        processing_time_ms=result.processing_time_ms,
        llm_parse_attempts=result.llm_parse_attempts,
        used_regex_fallback=result.used_regex_fallback,
        manual_review_recommended=result.manual_review_recommended,
        verified_skills=result.verified_skills,
        unverified_skills=result.unverified_skills,
        job_description=job_description,
        required_skills_csv=required_skills_csv,
        experience_target_months=experience_target_months,
        resume_hash=resume_hash,
        scoring_config_id=scoring_config.id,
        scoring_config_version=scoring_config.version,
        created_at=result.created_at or datetime.now(timezone.utc),
    )
    session.add(record)
    await session.flush()
    log.info("Stored analysis %s for %s (score=%.1f)", record.id, record.candidate_name, record.total_score)
    return record


async def get_analysis(session: AsyncSession, analysis_id: str) -> AnalysisRecord | None:
    """Retrieves a single analysis by UUID."""
    stmt = select(AnalysisRecord).where(AnalysisRecord.id == analysis_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_analyses(
    session: AsyncSession,
    page: int = 1,
    limit: int = 20,
    name_filter: str = "",
    min_score: float = 0.0,
    max_score: float = 100.0,
) -> tuple[list[AnalysisRecord], int]:
    """Returns paginated, filterable list of analyses."""
    base = select(AnalysisRecord)

    if name_filter:
        base = base.where(AnalysisRecord.candidate_name.ilike(f"%{name_filter}%"))
    base = base.where(AnalysisRecord.total_score >= min_score)
    base = base.where(AnalysisRecord.total_score <= max_score)

    # Count total
    count_stmt = select(func.count()).select_from(base.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * limit
    data_stmt = base.order_by(desc(AnalysisRecord.created_at)).offset(offset).limit(limit)
    data_result = await session.execute(data_stmt)
    records = list(data_result.scalars().all())

    return records, total


def record_to_analysis_result(record: AnalysisRecord) -> AnalysisResult:
    """Converts a DB AnalysisRecord back to an API AnalysisResult."""
    return AnalysisResult(
        id=uuid.UUID(record.id),
        candidate_name=record.candidate_name,
        parsed_resume=ParsedResume.model_validate(record.parsed_resume_json),
        total_score=record.total_score,
        semantic_skill_match=record.semantic_skill_match,
        experience_longevity=record.experience_longevity,
        context_alignment=record.context_alignment,
        context_justification=record.context_justification,
        scoring_config_version=record.scoring_config_version,
        skill_weight=35,
        experience_weight=25,
        context_weight=40,
        total_experience_months=record.total_experience_months,
        matched_skills=record.matched_skills,
        missing_skills=record.missing_skills,
        extraction_tier_used=record.extraction_tier_used,
        processing_time_ms=record.processing_time_ms,
        llm_parse_attempts=record.llm_parse_attempts,
        used_regex_fallback=record.used_regex_fallback,
        difficult_layout_detected=False,
        manual_review_recommended=record.manual_review_recommended,
        field_confidence={},
        verified_skills=record.verified_skills,
        unverified_skills=record.unverified_skills,
        unverified_fields=[],
        created_at=record.created_at,
    )


# ─────────────────────────────────────────────
# Feedback
# ─────────────────────────────────────────────

async def create_feedback(
    session: AsyncSession,
    analysis_id: str,
    feedback_type: str,
    reason: str,
) -> RecruiterFeedback:
    """Stores recruiter feedback."""
    # Verify analysis exists
    analysis = await get_analysis(session, analysis_id)
    
    fb = RecruiterFeedback(
        id=str(uuid.uuid4()),
        analysis_id=analysis_id,
        scoring_config_id=analysis.scoring_config_id if analysis else None,
        feedback_type=feedback_type,
        reason=reason,
    )
    session.add(fb)
    await session.flush()
    log.info("Stored feedback %s for analysis %s", fb.id, analysis_id)
    return fb


# ─────────────────────────────────────────────
# Resume Cache
# ─────────────────────────────────────────────

def compute_resume_hash(file_bytes: bytes) -> str:
    """Returns SHA-256 hex digest of file content."""
    return hashlib.sha256(file_bytes).hexdigest()


async def get_cached_resume(session: AsyncSession, resume_hash: str) -> ResumeCache | None:
    """Looks up a cached parsed resume by hash."""
    stmt = select(ResumeCache).where(
        ResumeCache.resume_hash == resume_hash,
        (ResumeCache.expires_at == None) | (ResumeCache.expires_at > datetime.now(timezone.utc)),
    )
    result = await session.execute(stmt)
    cached = result.scalar_one_or_none()
    if cached:
        log.info("Cache HIT for resume hash %s...", resume_hash[:12])
    return cached


async def cache_resume(
    session: AsyncSession,
    resume_hash: str,
    parsed_resume: ParsedResume,
    extraction_tier: int,
    parse_attempts: int,
    used_fallback: bool,
) -> ResumeCache:
    """Stores a parsed resume in the cache."""
    ttl_days = config.RESUME_CACHE_TTL_DAYS
    entry = ResumeCache(
        id=str(uuid.uuid4()),
        resume_hash=resume_hash,
        parsed_resume_json=parsed_resume.model_dump(),
        extraction_tier_used=extraction_tier,
        llm_parse_attempts=parse_attempts,
        used_regex_fallback=used_fallback,
        expires_at=datetime.now(timezone.utc) + timedelta(days=ttl_days),
    )
    session.add(entry)
    await session.flush()
    log.info("Cached resume %s... (TTL=%d days)", resume_hash[:12], ttl_days)
    return entry


# ─────────────────────────────────────────────
# Analytics Helpers
# ─────────────────────────────────────────────

async def get_analytics_data(session: AsyncSession) -> dict:
    """Gathers analytics summary data from the database."""
    # Total analyses
    total_result = await session.execute(select(func.count(AnalysisRecord.id)))
    total_analyses = total_result.scalar() or 0

    # Average score
    avg_result = await session.execute(select(func.avg(AnalysisRecord.total_score)))
    avg_score = round(avg_result.scalar() or 0.0, 1)

    # Score distribution
    score_dist = {"0-39": 0, "40-69": 0, "70-89": 0, "90-100": 0}
    all_scores_result = await session.execute(select(AnalysisRecord.total_score))
    for (score,) in all_scores_result:
        if score < 40:
            score_dist["0-39"] += 1
        elif score < 70:
            score_dist["40-69"] += 1
        elif score < 90:
            score_dist["70-89"] += 1
        else:
            score_dist["90-100"] += 1

    # Tier distribution
    tier_dist = {"tier_1": 0, "tier_2": 0, "tier_3": 0}
    tier_result = await session.execute(select(AnalysisRecord.extraction_tier_used))
    for (tier,) in tier_result:
        key = f"tier_{tier}"
        if key in tier_dist:
            tier_dist[key] += 1

    # Feedback breakdown
    fb_breakdown = {"accurate": 0, "too_high": 0, "too_low": 0, "inaccurate": 0}
    fb_result = await session.execute(select(RecruiterFeedback.feedback_type))
    for (ft,) in fb_result:
        if ft in fb_breakdown:
            fb_breakdown[ft] += 1

    # LLM success rate
    fallback_result = await session.execute(
        select(func.count(AnalysisRecord.id)).where(AnalysisRecord.used_regex_fallback == True)
    )
    fallback_count = fallback_result.scalar() or 0
    llm_success = round((1 - (fallback_count / max(total_analyses, 1))) * 100, 1)

    # Top missing skills — aggregated across all analyses
    missing_counts: dict = {}
    missing_result = await session.execute(select(AnalysisRecord.missing_skills))
    for (skills_list,) in missing_result:
        if isinstance(skills_list, list):
            for skill in skills_list:
                if skill:
                    key = skill.strip().lower()
                    missing_counts[key] = missing_counts.get(key, 0) + 1
    top_missing = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_missing_skills = [{"skill": s.title(), "count": c} for s, c in top_missing]

    # Score trend — daily averages (last 30 days)
    trend_result = await session.execute(
        select(AnalysisRecord.created_at, AnalysisRecord.total_score)
        .order_by(AnalysisRecord.created_at)
    )
    daily_scores: dict = {}
    for (created_at, score) in trend_result:
        day = created_at.strftime("%Y-%m-%d") if hasattr(created_at, "strftime") else str(created_at)[:10]
        daily_scores.setdefault(day, []).append(score)
    score_trend = [
        {"date": day, "avg_score": round(sum(vals) / len(vals), 1)}
        for day, vals in sorted(daily_scores.items())
    ][-30:]

    return {
        "total_analyses": total_analyses,
        "avg_score": avg_score,
        "score_distribution": score_dist,
        "tier_distribution": tier_dist,
        "top_missing_skills": top_missing_skills,
        "feedback_breakdown": fb_breakdown,
        "llm_success_rate": llm_success,
        "score_trend": score_trend,
    }
