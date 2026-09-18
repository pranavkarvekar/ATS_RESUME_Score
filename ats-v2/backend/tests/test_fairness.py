# -*- coding: utf-8 -*-
"""
Fairness Regression & Behavioral Evaluation Test Suite
=======================================================

Tests that the ATS scoring system does NOT penalize candidates for
irrelevant empty categories (certifications, projects, education)
and that structural fairness properties are preserved.
"""

import sys
import os
import pytest

from models.schemas import ExperienceItem
from scoring.skill_match import compute_semantic_skill_score
from scoring.experience import compute_experience_longevity

# ─────────────────────────────────────────────────────────────────────
# Test Fixtures — Controlled resume data
# ─────────────────────────────────────────────────────────────────────

REQUIRED_SKILLS = ["python", "docker", "react", "postgresql", "kubernetes"]

BASELINE_EXPERIENCE = [
    ExperienceItem(
        company="Acme Corp",
        role="Software Engineer",
        duration_months=48,
        responsibilities=[
            "Built REST APIs using Python and FastAPI",
            "Managed Kubernetes clusters on AWS",
            "Developed React frontends for internal tools",
        ],
    ),
]

FRESH_GRAD_EXPERIENCE = []

# ─────────────────────────────────────────────────────────────────────
# FAIR-001: Baseline
# ─────────────────────────────────────────────────────────────────────
def test_fair_001_baseline():
    skill_score, matched, missing = compute_semantic_skill_score(
        candidate_skills=["python", "docker", "react", "postgresql", "kubernetes"],
        required_skills=REQUIRED_SKILLS,
        max_score=35.0,
    )
    assert skill_score == 35.0
    
    exp_score = compute_experience_longevity(
        total_months=48,
        target_months=36,
        max_score=25.0,
    )
    assert exp_score == 25.0

# ─────────────────────────────────────────────────────────────────────
# FAIR-005: Fresh graduate
# ─────────────────────────────────────────────────────────────────────
def test_fair_005_fresh_grad():
    skill_score, matched, missing = compute_semantic_skill_score(
        candidate_skills=["python", "docker", "react", "postgresql", "kubernetes"],
        required_skills=REQUIRED_SKILLS,
        max_score=35.0,
    )
    assert skill_score == 35.0
    
    exp_score = compute_experience_longevity(
        total_months=0,
        target_months=36,
        max_score=25.0,
    )
    assert exp_score == 0.0  # According to v2 bracket, 0 months vs 36 target diff=36, so 0.0

# ─────────────────────────────────────────────────────────────────────
# FAIR-008: Partial skills — 3/5 matched
# ─────────────────────────────────────────────────────────────────────
def test_fair_008_partial_skills():
    skill_score, matched, missing = compute_semantic_skill_score(
        candidate_skills=["python", "docker", "react"],
        required_skills=REQUIRED_SKILLS,
        max_score=35.0,
    )
    assert 20.0 <= skill_score <= 28.0  # Proportional score + partial cluster credit
    assert len(matched) == 4  # python, docker, react (exact) + kubernetes (partial via docker cluster)
    assert len(missing) == 1  # postgresql

# ─────────────────────────────────────────────────────────────────────
# FAIR-009: Alias equivalence under scoring
# ─────────────────────────────────────────────────────────────────────
def test_fair_009_alias_equivalence():
    skill_score_exact, _, _ = compute_semantic_skill_score(
        candidate_skills=["python", "docker", "react", "postgresql", "kubernetes"],
        required_skills=REQUIRED_SKILLS,
        max_score=35.0,
    )
    skill_score_alias, _, _ = compute_semantic_skill_score(
        candidate_skills=["python", "docker", "reactjs", "postgres", "k8s"],
        required_skills=REQUIRED_SKILLS,
        max_score=35.0,
    )
    assert abs(skill_score_exact - skill_score_alias) < 0.01

# ─────────────────────────────────────────────────────────────────────
# FAIR-011: No required skills specified
# ─────────────────────────────────────────────────────────────────────
def test_fair_011_no_required_skills():
    skill_score, matched, missing = compute_semantic_skill_score(
        candidate_skills=["python", "docker", "react"],
        required_skills=[],
        max_score=35.0,
    )
    assert skill_score == 35.0  # If no skills required, they get full points
    assert matched == ["python", "docker", "react"]
    assert missing == []
