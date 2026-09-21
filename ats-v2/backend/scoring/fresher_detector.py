# -*- coding: utf-8 -*-
"""
Fresher Role Detector.

Determines if a job description targets freshers / entry-level candidates
by scanning for known keyword patterns.

Two triggers activate fresher mode:
1. experience_target_months == 0  (recruiter explicitly set it)
2. JD text contains fresher/entry-level signals (auto-detected here)

When fresher mode is active -> experience_longevity = max_score (25/25)
because experience is irrelevant for roles that require none.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger("ats.scoring.fresher_detector")

# ---------------------------------------------
# Keyword patterns that signal a fresher role
# ---------------------------------------------
_FRESHER_PATTERNS: list[str] = [
    # Direct fresher mentions
    r"\bfreshers?\b",
    r"\bfreshers?\s+(?:can\s+apply|welcome|preferred|only|encouraged)\b",
    r"\bopen\s+to\s+freshers?\b",

    # Entry / Junior level signals
    r"\bentry[\s\-]level\b",
    r"\bjunior[\s\-]level\b",
    r"\btrainee[s]?\b",

    # Experience: 0 years / 0-1 years
    r"\b0\s*[\-\u2013]\s*1\s+year[s]?\b",
    r"\b0\s+year[s]?\s*(?:of\s+)?experience\b",
    r"\bno\s+(?:prior\s+)?(?:work\s+)?experience\s+(?:required|needed|necessary)\b",
    r"\bwithout\s+experience\b",

    # Graduate / Intern signals
    r"\brecent\s+graduate[s]?\b",
    r"\bnew\s+graduate[s]?\b",
    r"\bfresh\s+graduate[s]?\b",
    r"\bcampus\s+hire[s]?\b",
    r"\bcollege\s+hire[s]?\b",

    # Internship / Apprenticeship
    r"\binternship\b",
    r"\bapprentice[s]?\b",
]

# Pre-compile for performance (called on every /analyze request)
_COMPILED_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _FRESHER_PATTERNS
]


def detect_fresher_role(job_description: str) -> tuple[bool, str]:
    """
    Scans the job description for fresher / entry-level signals.

    Args:
        job_description: Raw JD text from the recruiter.

    Returns:
        (is_fresher, reason) where reason is the matched keyword for transparency.
    """
    if not job_description or not job_description.strip():
        return False, ""

    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(job_description)
        if match:
            matched_text = match.group(0).strip()
            log.info("Fresher role detected via pattern '%s' -> matched: '%s'", pattern.pattern, matched_text)
            return True, matched_text

    return False, ""


def resolve_experience_target(
    experience_target_months: int,
    job_description: str,
) -> tuple[int, bool, str]:
    """
    Central function to resolve the effective experience target for scoring.

    Two ways fresher mode activates:
      1. Recruiter explicitly set experience_target_months = 0
      2. JD text auto-detected as a fresher role

    Args:
        experience_target_months: Value sent by the client (form field).
        job_description: JD text to scan for fresher keywords.

    Returns:
        (effective_target_months, fresher_mode_active, detection_reason)
    """
    # Trigger 1: Explicit 0 from client
    if experience_target_months == 0:
        log.info("Fresher mode ACTIVE -- recruiter explicitly set experience target to 0")
        return 0, True, "experience_target_months explicitly set to 0"

    # Trigger 2: Auto-detect from JD text
    is_fresher, reason = detect_fresher_role(job_description)
    if is_fresher:
        log.info("Fresher mode ACTIVE -- auto-detected from JD: '%s'", reason)
        return 0, True, f"JD keyword detected: '{reason}'"

    # Normal role -- use the value as-is
    return experience_target_months, False, ""
