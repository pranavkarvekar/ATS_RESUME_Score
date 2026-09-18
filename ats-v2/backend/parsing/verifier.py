# -*- coding: utf-8 -*-
"""
Data Verifier.

Cross-references LLM parsed fields against the raw extracted text
to prevent hallucinations (e.g. LLM inventing a skill that isn't in the text).
"""

from __future__ import annotations

import logging
from typing import Tuple

from models.schemas import ParsedResume

log = logging.getLogger("ats.parsing.verifier")

def verify_parsed_data(
    parsed: ParsedResume, raw_text: str
) -> Tuple[list[str], list[str]]:
    """
    Checks skills against the raw text.
    
    Returns:
        (verified_skills, unverified_skills)
    """
    text_lower = raw_text.lower()
    
    verified_skills = []
    unverified_skills = []
    
    # We only verify skills for now to ensure we don't penalize based on LLM hallucinations
    for skill in parsed.skills:
        # Simple exact substring match (lowered)
        if skill.lower() in text_lower:
            verified_skills.append(skill)
        else:
            log.warning("Skill '%s' not found in raw text (potential hallucination)", skill)
            unverified_skills.append(skill)
            
    # We can expand this to verify companies, degrees, etc.
    return verified_skills, unverified_skills
