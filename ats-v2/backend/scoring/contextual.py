# -*- coding: utf-8 -*-
"""
Contextual AI Fit Scoring.

Uses LLM (Groq) to assess how well the candidate's actual responsibilities 
and projects align with the Job Description.
"""

from __future__ import annotations

import json
import logging
from typing import Tuple

from openai import AsyncOpenAI

import config
from models.schemas import ParsedResume

log = logging.getLogger("ats.scoring.contextual")

_CONTEXT_SYSTEM_PROMPT = """You are an expert technical recruiter AI.
Evaluate the alignment between the candidate's past work experience/projects and the provided Job Description.

Score on a scale of 10 to 40. 
- 40 = Perfect contextual alignment, they have done exactly what the JD asks for.
- 10 = Very poor alignment, almost no relevant contextual experience.

Return ONLY valid JSON matching this schema:
{
    "score": 35,
    "justification": "A brief 2-sentence explanation of why they got this score."
}
"""

_CONTEXT_USER_TEMPLATE = """
--- JOB DESCRIPTION ---
{job_description}

--- CANDIDATE EXPERIENCE & PROJECTS ---
{candidate_context}

Evaluate the alignment and return the JSON.
"""

async def compute_contextual_fit_score(
    parsed_resume: ParsedResume, 
    job_description: str,
    max_score: float = 40.0
) -> Tuple[float, str]:
    """
    Contextual fit is now calculated during the initial LLM parsing step
    to save an extra network round-trip. This function returns a placeholder.
    """
    return 0.0, "Contextual score calculated during parsing."
