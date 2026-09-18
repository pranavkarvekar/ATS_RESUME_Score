# -*- coding: utf-8 -*-
"""
ATS Resume Analyzer v2 — Pydantic Data Models

All API request/response schemas and internal data structures.
These models validate every piece of data flowing through the system:
- LLM output validation (untrusted source)
- API request validation
- API response shapes
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# Word-to-number map for LLM duration coercion
# ─────────────────────────────────────────────
_WORD_TO_NUM: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12,
}


# ═════════════════════════════════════════════
# Resume Parsing Models (LLM output shapes)
# ═════════════════════════════════════════════

class ExperienceItem(BaseModel):
    """
    A single work experience entry extracted from a resume.
    Strict validation: extra fields are forbidden to catch LLM hallucinations.
    """
    model_config = ConfigDict(extra="forbid")

    company: str = ""
    role: str = ""
    duration_months: int = Field(default=0, ge=0, le=600)
    responsibilities: list[str] = Field(default_factory=list)

    @field_validator("duration_months", mode="before")
    @classmethod
    def _coerce_duration(cls, value: Any) -> int:
        """
        Handle LLM returning duration as various string formats:
        '6 months' → 6, '1 year' → 12, 'three' → 3, '2.5 years' → 30
        """
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if not isinstance(value, str):
            return 0

        text = value.strip().lower()

        # Word form: "three", "six"
        if text in _WORD_TO_NUM:
            return _WORD_TO_NUM[text]

        # "N year(s)" → N × 12
        year_match = re.match(r"(\d+(?:\.\d+)?)\s*year", text)
        if year_match:
            return int(float(year_match.group(1)) * 12)

        # "N month(s)" → N
        month_match = re.match(r"(\d+)\s*month", text)
        if month_match:
            return int(month_match.group(1))

        # Plain number string: "6", "24"
        digit_match = re.match(r"^(\d+)$", text)
        if digit_match:
            return int(digit_match.group(1))

        return 0

    @field_validator("responsibilities", mode="before")
    @classmethod
    def _coerce_responsibilities(cls, value: Any) -> list[str]:
        """Accept None or plain string in place of a list."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return value


class ProjectItem(BaseModel):
    """
    A project entry extracted from a resume (NEW in v2).
    Captures project name, technologies used, and description.
    """
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    description: str = ""

    @field_validator("tech_stack", mode="before")
    @classmethod
    def _coerce_tech_stack(cls, value: Any) -> list[str]:
        """Accept comma-separated string or None."""
        if value is None:
            return []
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        return value


class ParsedResume(BaseModel):
    """
    Structured resume data extracted by the LLM parser.
    Strict validation with coercion for common LLM output quirks.
    """
    model_config = ConfigDict(extra="forbid")

    name: str = "Unknown"
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def _coerce_skills(cls, value: Any) -> list[str]:
        """If LLM returns skills as comma-separated string, split it."""
        if value is None:
            return []
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        return value

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, value: Any) -> str:
        """Strip whitespace, fall back to 'Unknown' for blank/non-string."""
        if not isinstance(value, str) or not value.strip():
            return "Unknown"
        return value.strip()

    @model_validator(mode="after")
    def _deduplicate_skills(self) -> "ParsedResume":
        """Remove duplicate skills case-insensitively, preserve insertion order."""
        seen: set[str] = set()
        unique: list[str] = []
        for skill in self.skills:
            key = skill.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(skill.strip())
        self.skills = unique
        return self


# ═════════════════════════════════════════════
# Internal Parse Result (between parser and scorer)
# ═════════════════════════════════════════════

@dataclass
class ParseResult:
    """
    Internal container passed from the parsing stage to the scoring stage.
    Not exposed to the API — used only within the analysis pipeline.
    """
    resume: ParsedResume
    llm_attempts: int = 0
    used_fallback: bool = False
    field_confidence: dict[str, str] = dc_field(default_factory=dict)
    verified_skills: list[str] = dc_field(default_factory=list)
    unverified_skills: list[str] = dc_field(default_factory=list)
    unverified_fields: list[str] = dc_field(default_factory=list)


# ═════════════════════════════════════════════
# API Response Models
# ═════════════════════════════════════════════

class AnalysisResult(BaseModel):
    """
    Full API response for POST /api/v1/analyze.
    Contains scores, parsed resume, metadata, and verification info.
    """
    # Identity
    id: UUID | None = None
    candidate_name: str = "Unknown"

    # Parsed resume data
    parsed_resume: ParsedResume = Field(default_factory=ParsedResume)

    # Scores (dynamic weights — see PRD Section 4.2)
    total_score: float = Field(default=0.0, ge=0.0, le=100.0)
    semantic_skill_match: float = Field(default=0.0, ge=0.0)
    experience_longevity: float = Field(default=0.0, ge=0.0)
    context_alignment: float = Field(default=0.0, ge=0.0)
    context_justification: str = ""

    # Scoring config
    scoring_config_version: str = "v1.0"
    skill_weight: int = 35
    experience_weight: int = 25
    context_weight: int = 40

    # Skills breakdown
    total_experience_months: int = 0
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)

    # Extraction metadata
    extraction_tier_used: int = 1
    processing_time_ms: int = 0
    calibration_applied: bool = False

    # Parse pipeline metadata
    llm_parse_attempts: int = 0
    used_regex_fallback: bool = False
    difficult_layout_detected: bool = False
    manual_review_recommended: bool = False

    # Verification metadata
    field_confidence: dict[str, str] = Field(default_factory=dict)
    verified_skills: list[str] = Field(default_factory=list)
    unverified_skills: list[str] = Field(default_factory=list)
    unverified_fields: list[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime | None = None

    # Debug / Raw Data
    extracted_text: str | None = None


# ═════════════════════════════════════════════
# Feedback Models
# ═════════════════════════════════════════════

class FeedbackRequest(BaseModel):
    """Request body for POST /api/v1/feedback."""
    analysis_id: UUID
    feedback_type: str = Field(
        ...,
        pattern=r"^(accurate|too_high|too_low|inaccurate)$",
        description="One of: accurate, too_high, too_low, inaccurate",
    )
    reason: str = Field(default="", max_length=1000)


class FeedbackResponse(BaseModel):
    """Response for POST /api/v1/feedback."""
    id: UUID
    analysis_id: UUID
    feedback_type: str
    message: str = "Feedback recorded successfully"
    created_at: datetime


# ═════════════════════════════════════════════
# History & Analytics Models
# ═════════════════════════════════════════════

class HistoryItem(BaseModel):
    """Single item in the history list."""
    id: UUID
    candidate_name: str
    total_score: float
    extraction_tier_used: int
    scoring_config_version: str
    processing_time_ms: int
    created_at: datetime


class HistoryResponse(BaseModel):
    """Response for GET /api/v1/history."""
    items: list[HistoryItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 20


class AnalyticsSummary(BaseModel):
    """Response for GET /api/v1/analytics/summary."""
    total_analyses: int = 0
    avg_score: float = 0.0
    score_distribution: dict[str, int] = Field(
        default_factory=lambda: {"0-39": 0, "40-69": 0, "70-89": 0, "90-100": 0}
    )
    tier_distribution: dict[str, int] = Field(
        default_factory=lambda: {"tier_1": 0, "tier_2": 0, "tier_3": 0}
    )
    top_missing_skills: list[dict[str, Any]] = Field(default_factory=list)
    feedback_breakdown: dict[str, int] = Field(
        default_factory=lambda: {
            "accurate": 0, "too_high": 0, "too_low": 0, "inaccurate": 0
        }
    )
    llm_success_rate: float = 0.0


# ═════════════════════════════════════════════
# Health Check
# ═════════════════════════════════════════════

class HealthResponse(BaseModel):
    """Response for GET /health."""
    status: str = "ok"
    model: str = ""
    api_key_configured: bool = False
    database_connected: bool = False
    scoring_config_version: str = ""
    default_weights: dict[str, int] = Field(default_factory=dict)
