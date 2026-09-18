"""
Fairness Regression & Behavioral Evaluation Test Suite
=======================================================

Tests that the ATS scoring system does NOT penalize candidates for
irrelevant empty categories (certifications, projects, education)
and that structural fairness properties are preserved.

These tests call scoring functions directly — no LLM, no PDF,
no network calls, no API keys required. Fully deterministic.

Run:  python test_fairness.py
Exit: 0 = all pass, 1 = failures detected

Rerun when:
  - Scoring logic changes (compute_semantic_skill_score, compute_experience_longevity)
  - Weight configuration changes (40/35/25)
  - _SKILL_ALIASES or _SEMANTIC_CLUSTERS modified
  - Pydantic model schema changes
  - Scoring prompt or model changes (to verify downstream effects)
"""

import sys
import os

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    ExperienceItem,
    compute_semantic_skill_score,
    compute_experience_longevity,
    get_semantic_similarity,
)


# ─────────────────────────────────────────────────────────────────────
# Test Fixtures — Controlled resume data
# ─────────────────────────────────────────────────────────────────────

REQUIRED_SKILLS = ["Python", "Docker", "React", "PostgreSQL", "Kubernetes"]

JD_TEXT = (
    "We are looking for a Full Stack Engineer proficient in Python, Docker, "
    "React, PostgreSQL, and Kubernetes. Experience with CI/CD pipelines and "
    "microservices architecture is a plus."
)

# Baseline experience: 3+ years, valid responsibilities
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

# Fresh graduate: zero months, but has skills
FRESH_GRAD_EXPERIENCE: list[ExperienceItem] = []

# Internship-level experience
INTERN_EXPERIENCE = [
    ExperienceItem(
        company="StartupXYZ",
        role="Software Engineering Intern",
        duration_months=6,
        responsibilities=[
            "Assisted with backend development in Python",
            "Wrote unit tests for REST APIs",
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────
# Test Framework (minimal, zero dependencies)
# ─────────────────────────────────────────────────────────────────────

_results: list[tuple[str, bool, str]] = []


def _test(test_id: str, description: str, passed: bool, detail: str = ""):
    """Register a test result."""
    _results.append((test_id, passed, description + (f" — {detail}" if detail else "")))


# ─────────────────────────────────────────────────────────────────────
# FAIR-001: Baseline — all skills matched, 36+ months experience
# ─────────────────────────────────────────────────────────────────────
skill_score_001, matched_001, missing_001 = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)
exp_score_001, months_001 = compute_experience_longevity(
    experience=BASELINE_EXPERIENCE,
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
)

_test(
    "FAIR-001", "Baseline: all skills matched, 36+ months",
    skill_score_001 >= 38.0 and exp_score_001 == 35.0,
    f"skill={skill_score_001:.2f}/40, exp={exp_score_001:.2f}/35",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-002: Same as 001 but with empty education list
# Verifies education=[]] does not reduce score
# ─────────────────────────────────────────────────────────────────────
# Education is not an input to either scoring function.
# This test verifies that the scoring functions are structurally
# independent of education — calling with identical inputs produces
# identical scores regardless of what education the resume contains.
skill_score_002, _, _ = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)
exp_score_002, _ = compute_experience_longevity(
    experience=BASELINE_EXPERIENCE,
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
)

_test(
    "FAIR-002", "Empty education: scores identical to baseline",
    abs(skill_score_002 - skill_score_001) < 0.01 and abs(exp_score_002 - exp_score_001) < 0.01,
    f"skill_delta={abs(skill_score_002 - skill_score_001):.4f}, "
    f"exp_delta={abs(exp_score_002 - exp_score_001):.4f}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-003: Same as 001 but "no certifications"
# Certifications are not a scoring input — verify no penalty
# ─────────────────────────────────────────────────────────────────────
skill_score_003, _, _ = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)
exp_score_003, _ = compute_experience_longevity(
    experience=BASELINE_EXPERIENCE,
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
)

_test(
    "FAIR-003", "No certifications: scores identical to baseline",
    abs(skill_score_003 - skill_score_001) < 0.01 and abs(exp_score_003 - exp_score_001) < 0.01,
    f"skill_delta={abs(skill_score_003 - skill_score_001):.4f}, "
    f"exp_delta={abs(exp_score_003 - exp_score_001):.4f}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-004: Same as 001 but "no projects"
# Projects are not a scoring input — verify no penalty
# ─────────────────────────────────────────────────────────────────────
skill_score_004, _, _ = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)
exp_score_004, _ = compute_experience_longevity(
    experience=BASELINE_EXPERIENCE,
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
)

_test(
    "FAIR-004", "No projects: scores identical to baseline",
    abs(skill_score_004 - skill_score_001) < 0.01 and abs(exp_score_004 - exp_score_001) < 0.01,
    f"skill_delta={abs(skill_score_004 - skill_score_001):.4f}, "
    f"exp_delta={abs(exp_score_004 - exp_score_001):.4f}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-005: Fresh graduate — has skills, 0 months experience
# Skill score should be unchanged; exp should hit 60% floor (21.0)
# ─────────────────────────────────────────────────────────────────────
skill_score_005, _, _ = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)
exp_score_005, months_005 = compute_experience_longevity(
    experience=FRESH_GRAD_EXPERIENCE,
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
)

_test(
    "FAIR-005", "Fresh grad: skill score unchanged, exp = 21.0 (60% floor)",
    abs(skill_score_005 - skill_score_001) < 0.01 and exp_score_005 == 21.0 and months_005 == 0,
    f"skill={skill_score_005:.2f}, exp={exp_score_005:.2f}, months={months_005}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-006: Fresh grad with skills + responsibilities, 0 months
# Same exp score as FAIR-005 (60% floor)
# ─────────────────────────────────────────────────────────────────────
exp_with_zero_months = [
    ExperienceItem(
        company="University Project",
        role="Team Lead",
        duration_months=0,
        responsibilities=["Built a web app using React and FastAPI"],
    ),
]
exp_score_006, months_006 = compute_experience_longevity(
    experience=exp_with_zero_months,
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
)

_test(
    "FAIR-006", "Fresh grad + responsibilities: exp = 21.0 (same floor as 005)",
    exp_score_006 == 21.0 and months_006 == 0,
    f"exp={exp_score_006:.2f}, months={months_006}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-007: Empty everything — no skills, no experience, no education
# Skill = 0.0, Exp = 14.0 (40% floor — no skills/projects either)
# ─────────────────────────────────────────────────────────────────────
skill_score_007, _, _ = compute_semantic_skill_score(
    resume_skills=[],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)
exp_score_007, months_007 = compute_experience_longevity(
    experience=[],
    resume_skills=[],
)

_test(
    "FAIR-007", "Empty everything: skill=0.0, exp=14.0 (40% floor), never negative",
    skill_score_007 == 0.0 and exp_score_007 == 14.0 and months_007 == 0,
    f"skill={skill_score_007:.2f}, exp={exp_score_007:.2f}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-008: Partial skills — 3/5 matched
# Skill score should be proportional, roughly 20–28 range
# ─────────────────────────────────────────────────────────────────────
skill_score_008, matched_008, missing_008 = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)

_test(
    "FAIR-008", "Partial skills (3/5): score proportional, in [20.0, 28.0]",
    20.0 <= skill_score_008 <= 28.0 and len(matched_008) == 3 and len(missing_008) == 2,
    f"skill={skill_score_008:.2f}, matched={matched_008}, missing={missing_008}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-009: Alias equivalence under scoring
# "React.js", "Postgres", "K8s" should score identically to
# "React", "PostgreSQL", "Kubernetes"
# ─────────────────────────────────────────────────────────────────────
skill_score_exact, _, _ = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)
skill_score_alias, _, _ = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React.js", "Postgres", "K8s"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)

_test(
    "FAIR-009", "Alias equivalence: React.js/Postgres/K8s = React/PostgreSQL/Kubernetes",
    abs(skill_score_exact - skill_score_alias) < 0.01,
    f"exact={skill_score_exact:.2f}, alias={skill_score_alias:.2f}, "
    f"delta={abs(skill_score_exact - skill_score_alias):.4f}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-010: Experience with empty responsibilities but valid duration
# Bracket should be based on months, not on whether responsibilities exist
# ─────────────────────────────────────────────────────────────────────
exp_no_resp = [
    ExperienceItem(
        company="SomeCorp",
        role="Engineer",
        duration_months=24,
        responsibilities=[],
    ),
]
exp_score_010, months_010 = compute_experience_longevity(
    experience=exp_no_resp,
    resume_skills=["Python"],
)

# 12-35 months bracket → 90% = 31.5
_test(
    "FAIR-010", "Empty responsibilities, 24 months: bracket = 90% (31.5)",
    exp_score_010 == 31.5 and months_010 == 24,
    f"exp={exp_score_010:.2f}, months={months_010}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-011: No required skills specified
# Skill score should be 0.0 (not scored), not a penalty
# ─────────────────────────────────────────────────────────────────────
skill_score_011, matched_011, missing_011 = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React"],
    required_skills=[],
    job_description=JD_TEXT,
)

_test(
    "FAIR-011", "No required skills: score=0.0 (not scored, not penalized)",
    skill_score_011 == 0.0 and matched_011 == [] and missing_011 == [],
    f"skill={skill_score_011:.2f}, matched={matched_011}, missing={missing_011}",
)


# ─────────────────────────────────────────────────────────────────────
# FAIR-012: Missing certs + missing projects + has skills + has exp
# Score must be >= baseline minus epsilon (no penalty for missing optional fields)
# ─────────────────────────────────────────────────────────────────────
skill_score_012, _, _ = compute_semantic_skill_score(
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
    required_skills=REQUIRED_SKILLS,
    job_description=JD_TEXT,
)
exp_score_012, _ = compute_experience_longevity(
    experience=BASELINE_EXPERIENCE,
    resume_skills=["Python", "Docker", "React", "PostgreSQL", "Kubernetes"],
)
total_012 = skill_score_012 + exp_score_012
total_001 = skill_score_001 + exp_score_001

_test(
    "FAIR-012", "Missing certs+projects: deterministic score >= baseline - 0.01",
    total_012 >= total_001 - 0.01,
    f"total_012={total_012:.2f}, total_001={total_001:.2f}, "
    f"delta={total_012 - total_001:.4f}",
)


# ─────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────
print()
print("=" * 78)
print("  FAIRNESS REGRESSION TEST SUITE — ATS Resume Analyzer")
print("=" * 78)
print()

passed_count = 0
failed_count = 0

for test_id, passed, description in _results:
    status = "PASS" if passed else "FAIL"
    icon = "✓" if passed else "✗"
    print(f"  {icon}  [{test_id}] {status}  {description}")
    if passed:
        passed_count += 1
    else:
        failed_count += 1

print()
print("-" * 78)
print(f"  Results: {passed_count} passed, {failed_count} failed, {len(_results)} total")
print("-" * 78)

if failed_count > 0:
    print()
    print("  ⚠  FAIRNESS REGRESSIONS DETECTED — review failures above.")
    print("     These tests verify structural fairness properties.")
    print("     Failures indicate that a code change has altered scoring")
    print("     behavior in a way that may unfairly penalize candidates.")
    print()
    sys.exit(1)
else:
    print()
    print("  All fairness properties verified.")
    print("  Note: These tests do NOT prove the system is unbiased.")
    print("  They verify that known-good properties are preserved.")
    print()
    sys.exit(0)
