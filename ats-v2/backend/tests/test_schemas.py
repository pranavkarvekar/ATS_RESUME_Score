# -*- coding: utf-8 -*-
"""
Schema validation tests for all Pydantic models.

Tests validators, coercion logic, and edge cases.
No external dependencies — pure unit tests.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# Add backend to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.schemas import (
    ExperienceItem,
    ProjectItem,
    ParsedResume,
    AnalysisResult,
    FeedbackRequest,
)


# ═════════════════════════════════════════════
# ExperienceItem Validators
# ═════════════════════════════════════════════

class TestExperienceItem:
    """Tests for ExperienceItem duration coercion and validation."""

    def test_int_duration(self):
        """Integer duration should pass through unchanged."""
        item = ExperienceItem(duration_months=12)
        assert item.duration_months == 12

    def test_string_months(self):
        """'6 months' should coerce to 6."""
        item = ExperienceItem(duration_months="6 months")
        assert item.duration_months == 6

    def test_string_years(self):
        """'2 years' should coerce to 24."""
        item = ExperienceItem(duration_months="2 years")
        assert item.duration_months == 24

    def test_string_year_singular(self):
        """'1 year' should coerce to 12."""
        item = ExperienceItem(duration_months="1 year")
        assert item.duration_months == 12

    def test_fractional_years(self):
        """'1.5 years' should coerce to 18."""
        item = ExperienceItem(duration_months="1.5 years")
        assert item.duration_months == 18

    def test_word_number(self):
        """'three' should coerce to 3."""
        item = ExperienceItem(duration_months="three")
        assert item.duration_months == 3

    def test_word_twelve(self):
        """'twelve' should coerce to 12."""
        item = ExperienceItem(duration_months="twelve")
        assert item.duration_months == 12

    def test_plain_digit_string(self):
        """'24' should coerce to 24."""
        item = ExperienceItem(duration_months="24")
        assert item.duration_months == 24

    def test_float_duration(self):
        """Float 6.5 should coerce to 6."""
        item = ExperienceItem(duration_months=6.5)
        assert item.duration_months == 6

    def test_none_defaults_to_zero(self):
        """None should not crash — defaults to 0."""
        item = ExperienceItem(duration_months=None)
        assert item.duration_months == 0

    def test_gibberish_defaults_to_zero(self):
        """Unrecognized string should default to 0."""
        item = ExperienceItem(duration_months="a long time")
        assert item.duration_months == 0

    def test_max_600_months(self):
        """Duration must not exceed 600 (50 years)."""
        with pytest.raises(ValidationError):
            ExperienceItem(duration_months=601)

    def test_negative_rejected(self):
        """Negative duration must be rejected."""
        with pytest.raises(ValidationError):
            ExperienceItem(duration_months=-1)

    def test_responsibilities_from_none(self):
        """None responsibilities should coerce to empty list."""
        item = ExperienceItem(responsibilities=None)
        assert item.responsibilities == []

    def test_responsibilities_from_string(self):
        """String responsibility should coerce to single-item list."""
        item = ExperienceItem(responsibilities="Built REST APIs")
        assert item.responsibilities == ["Built REST APIs"]

    def test_extra_fields_rejected(self):
        """Extra fields should be rejected (extra='forbid')."""
        with pytest.raises(ValidationError):
            ExperienceItem(company="Acme", hallucinated_field="bad")


# ═════════════════════════════════════════════
# ProjectItem Validators
# ═════════════════════════════════════════════

class TestProjectItem:
    """Tests for ProjectItem tech_stack coercion."""

    def test_tech_stack_from_list(self):
        """List tech_stack should pass through."""
        item = ProjectItem(name="ATS", tech_stack=["Python", "FastAPI"])
        assert item.tech_stack == ["Python", "FastAPI"]

    def test_tech_stack_from_string(self):
        """Comma-separated string should split into list."""
        item = ProjectItem(name="ATS", tech_stack="Python, FastAPI, Docker")
        assert item.tech_stack == ["Python", "FastAPI", "Docker"]

    def test_tech_stack_from_none(self):
        """None should coerce to empty list."""
        item = ProjectItem(name="ATS", tech_stack=None)
        assert item.tech_stack == []

    def test_extra_fields_rejected(self):
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            ProjectItem(name="ATS", fake_field="bad")


# ═════════════════════════════════════════════
# ParsedResume Validators
# ═════════════════════════════════════════════

class TestParsedResume:
    """Tests for ParsedResume coercion and deduplication."""

    def test_skills_from_comma_string(self):
        """Comma-separated skill string should split into list."""
        resume = ParsedResume(skills="Python, Docker, React")
        assert resume.skills == ["Python", "Docker", "React"]

    def test_skills_deduplication(self):
        """Duplicate skills (case-insensitive) should be removed."""
        resume = ParsedResume(skills=["Python", "python", "PYTHON", "Docker"])
        assert len(resume.skills) == 2
        assert resume.skills[0] == "Python"  # First occurrence preserved
        assert resume.skills[1] == "Docker"

    def test_name_strip_whitespace(self):
        """Name should be stripped of whitespace."""
        resume = ParsedResume(name="  Rahul Sharma  ")
        assert resume.name == "Rahul Sharma"

    def test_name_empty_defaults(self):
        """Empty/blank name should default to 'Unknown'."""
        resume = ParsedResume(name="")
        assert resume.name == "Unknown"

    def test_name_none_defaults(self):
        """None name should default to 'Unknown'."""
        resume = ParsedResume(name=None)
        assert resume.name == "Unknown"

    def test_name_non_string_defaults(self):
        """Non-string name should default to 'Unknown'."""
        resume = ParsedResume(name=123)
        assert resume.name == "Unknown"

    def test_skills_none_to_empty(self):
        """None skills should coerce to empty list."""
        resume = ParsedResume(skills=None)
        assert resume.skills == []

    def test_full_resume_parses(self):
        """A complete resume with all fields should parse correctly."""
        resume = ParsedResume(
            name="Rahul Sharma",
            skills=["Python", "FastAPI", "Docker"],
            experience=[
                ExperienceItem(
                    company="Acme Corp",
                    role="Backend Developer",
                    duration_months=24,
                    responsibilities=["Built APIs", "Managed DB"],
                )
            ],
            education=["B.Tech CSE, SPPU 2025"],
            projects=[
                ProjectItem(
                    name="ATS Analyzer",
                    tech_stack=["Python", "FastAPI"],
                    description="Resume scoring system",
                )
            ],
            certifications=["AWS Cloud Practitioner"],
        )
        assert resume.name == "Rahul Sharma"
        assert len(resume.skills) == 3
        assert len(resume.experience) == 1
        assert resume.experience[0].duration_months == 24
        assert len(resume.projects) == 1
        assert resume.projects[0].name == "ATS Analyzer"
        assert len(resume.certifications) == 1

    def test_extra_fields_rejected(self):
        """Extra fields should be rejected by ParsedResume."""
        with pytest.raises(ValidationError):
            ParsedResume(name="Test", hallucinated_summary="I am great")


# ═════════════════════════════════════════════
# FeedbackRequest Validation
# ═════════════════════════════════════════════

class TestFeedbackRequest:
    """Tests for FeedbackRequest validation."""

    def test_valid_types(self):
        """All valid feedback types should be accepted."""
        for fb_type in ["accurate", "too_high", "too_low", "inaccurate"]:
            req = FeedbackRequest(
                analysis_id="00000000-0000-0000-0000-000000000001",
                feedback_type=fb_type,
            )
            assert req.feedback_type == fb_type

    def test_invalid_type_rejected(self):
        """Invalid feedback type should be rejected."""
        with pytest.raises(ValidationError):
            FeedbackRequest(
                analysis_id="00000000-0000-0000-0000-000000000001",
                feedback_type="wrong",
            )

    def test_reason_max_length(self):
        """Reason exceeding 1000 chars should be rejected."""
        with pytest.raises(ValidationError):
            FeedbackRequest(
                analysis_id="00000000-0000-0000-0000-000000000001",
                feedback_type="accurate",
                reason="x" * 1001,
            )

    def test_reason_optional(self):
        """Reason should be optional (default empty)."""
        req = FeedbackRequest(
            analysis_id="00000000-0000-0000-0000-000000000001",
            feedback_type="accurate",
        )
        assert req.reason == ""
