# -*- coding: utf-8 -*-
"""
SQLAlchemy ORM Models.

Defines the database schema for:
- ScoringConfig: Weight configuration versioning
- AnalysisRecord: Stored analysis results
- RecruiterFeedback: Recruiter feedback on analyses
- ResumeCache: SHA-256 keyed parsed resume cache
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, 
    String, Text, JSON, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class ScoringConfig(Base):
    """Stores scoring weight configurations for versioning."""
    __tablename__ = "scoring_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version = Column(String(20), nullable=False, unique=True)
    skill_weight = Column(Integer, nullable=False, default=35)
    experience_weight = Column(Integer, nullable=False, default=25)
    context_weight = Column(Integer, nullable=False, default=40)
    model_name = Column(String(100), nullable=False, default="llama-3.3-70b-versatile")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    analyses = relationship("AnalysisRecord", back_populates="scoring_config")
    feedbacks = relationship("RecruiterFeedback", back_populates="scoring_config")


class AnalysisRecord(Base):
    """Stores a complete analysis result."""
    __tablename__ = "analysis_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_name = Column(String(200), nullable=False, default="Unknown")
    
    # Parsed resume as JSON blob
    parsed_resume_json = Column(JSON, nullable=False)
    
    # Scores
    total_score = Column(Float, nullable=False, default=0.0)
    semantic_skill_match = Column(Float, nullable=False, default=0.0)
    experience_longevity = Column(Float, nullable=False, default=0.0)
    context_alignment = Column(Float, nullable=False, default=0.0)
    context_justification = Column(Text, nullable=False, default="")
    
    # Skills breakdown
    total_experience_months = Column(Integer, nullable=False, default=0)
    matched_skills = Column(JSON, nullable=False, default=list)
    missing_skills = Column(JSON, nullable=False, default=list)
    
    # Extraction metadata
    extraction_tier_used = Column(Integer, nullable=False, default=1)
    processing_time_ms = Column(Integer, nullable=False, default=0)
    
    # Parse metadata
    llm_parse_attempts = Column(Integer, nullable=False, default=0)
    used_regex_fallback = Column(Boolean, nullable=False, default=False)
    manual_review_recommended = Column(Boolean, nullable=False, default=False)
    
    # Verification
    verified_skills = Column(JSON, nullable=False, default=list)
    unverified_skills = Column(JSON, nullable=False, default=list)
    
    # Job description (stored for re-scoring)
    job_description = Column(Text, nullable=False, default="")
    required_skills_csv = Column(Text, nullable=False, default="")
    experience_target_months = Column(Integer, nullable=False, default=36)
    
    # Resume hash for dedup
    resume_hash = Column(String(64), nullable=True, index=True)
    
    # Scoring config FK
    scoring_config_id = Column(String(36), ForeignKey("scoring_configs.id"), nullable=True)
    scoring_config_version = Column(String(20), nullable=False, default="v1.0")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    scoring_config = relationship("ScoringConfig", back_populates="analyses")
    feedbacks = relationship("RecruiterFeedback", back_populates="analysis")


class RecruiterFeedback(Base):
    """Stores recruiter feedback on a specific analysis."""
    __tablename__ = "recruiter_feedbacks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String(36), ForeignKey("analysis_records.id"), nullable=False)
    scoring_config_id = Column(String(36), ForeignKey("scoring_configs.id"), nullable=True)
    feedback_type = Column(String(20), nullable=False)  # accurate, too_high, too_low, inaccurate
    reason = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis = relationship("AnalysisRecord", back_populates="feedbacks")
    scoring_config = relationship("ScoringConfig", back_populates="feedbacks")


class ResumeCache(Base):
    """Caches parsed resume data keyed by SHA-256 hash of file content."""
    __tablename__ = "resume_cache"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_hash = Column(String(64), nullable=False, unique=True, index=True)
    parsed_resume_json = Column(JSON, nullable=False)
    extraction_tier_used = Column(Integer, nullable=False, default=1)
    llm_parse_attempts = Column(Integer, nullable=False, default=0)
    used_regex_fallback = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)
