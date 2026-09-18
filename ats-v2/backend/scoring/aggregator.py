# -*- coding: utf-8 -*-
"""
Scoring Aggregator.

Combines skill match, experience longevity, and contextual fit scores.
"""

from __future__ import annotations

import logging
from typing import Tuple

from models.schemas import ParsedResume
from . import skill_match
from . import experience
from . import contextual

log = logging.getLogger("ats.scoring.aggregator")

async def calculate_total_score(
    parsed_resume: ParsedResume,
    job_description: str,
    required_skills: list[str],
    target_months: int,
    skill_weight: int = 35,
    experience_weight: int = 25,
    context_weight: int = 40
) -> Tuple[float, float, float, float, list[str], list[str], str]:
    """
    Orchestrates the 3 scoring components and aggregates the results.
    
    Returns:
        (total_score, skill_score, exp_score, ctx_score, matched_skills, missing_skills, justification)
    """
    log.info("Calculating total score")
    
    # 1. Semantic Skill Match
    skill_score, matched_skills, missing_skills = skill_match.compute_semantic_skill_score(
        candidate_skills=parsed_resume.skills,
        required_skills=required_skills,
        max_score=float(skill_weight)
    )
    
    # 2. Experience Longevity
    # First, calculate total months of experience from the parsed resume
    total_candidate_months = sum(exp.duration_months for exp in parsed_resume.experience)
    
    exp_score = experience.compute_experience_longevity(
        total_months=total_candidate_months,
        target_months=target_months,
        max_score=float(experience_weight)
    )
    
    # 3. Contextual AI Fit
    ctx_score, justification = await contextual.compute_contextual_fit_score(
        parsed_resume=parsed_resume,
        job_description=job_description,
        max_score=float(context_weight)
    )
    
    # Aggregate and clamp
    total_score = skill_score + exp_score + ctx_score
    total_score = max(0.0, min(total_score, 100.0))
    
    log.info("Score computed: Total=%.2f, Skills=%.2f, Exp=%.2f, Ctx=%.2f", 
             total_score, skill_score, exp_score, ctx_score)
             
    return round(total_score, 2), skill_score, exp_score, ctx_score, matched_skills, missing_skills, justification
