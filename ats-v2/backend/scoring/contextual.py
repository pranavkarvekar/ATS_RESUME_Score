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
    Calls Groq to get a contextual fit score based on responsibilities and projects.
    """
    if not config.GROQ_API_KEY:
        log.warning("No GROQ_API_KEY. Defaulting contextual score to 10.0")
        return 10.0, "API key missing. Defaulting to base score."
        
    if not job_description.strip():
        return 10.0, "No job description provided."

    # Build candidate context
    context_lines = []
    for exp in parsed_resume.experience:
        context_lines.append(f"Role: {exp.role} at {exp.company}")
        for resp in exp.responsibilities[:5]: # limit to prevent token bloat
            context_lines.append(f"- {resp}")
            
    for proj in parsed_resume.projects:
        context_lines.append(f"Project: {proj.name}")
        context_lines.append(f"- {proj.description}")
        
    candidate_context = "\n".join(context_lines)
    
    if not candidate_context.strip():
        return 10.0, "Candidate has no experience or projects listed."
        
    client = AsyncOpenAI(
        api_key=config.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    
    # Truncate JD to prevent token bloat
    jd = job_description[:config.MAX_JD_CHARS_FOR_CONTEXT]
    
    messages = [
        {"role": "system", "content": _CONTEXT_SYSTEM_PROMPT},
        {"role": "user", "content": _CONTEXT_USER_TEMPLATE.format(
            job_description=jd,
            candidate_context=candidate_context
        )},
    ]
    
    try:
        response = await client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
        )
        
        raw_output = response.choices[0].message.content or ""
        
        # Sanitize JSON
        from parsing import json_sanitizer
        json_str = json_sanitizer.sanitize_json_string(raw_output)
        
        data = json.loads(json_str)
        score = float(data.get("score", 10.0))
        just = data.get("justification", "Contextual alignment calculated.")
        
        # Clamp score between 10 and max_score
        score = max(10.0, min(score, max_score))
        
        return round(score, 2), just
        
    except Exception as e:
        log.error("Contextual scoring failed: %s", str(e))
        return 10.0, "Error calculating contextual score. Defaulting to base."
