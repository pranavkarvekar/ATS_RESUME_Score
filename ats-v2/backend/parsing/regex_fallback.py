# -*- coding: utf-8 -*-
"""
Regex Fallback Parser.

Provides a deterministic fallback parsing method if the LLM completely fails 
after all retries, ensuring the system never crashes on a bad parse.
"""

import re
import logging
from typing import Any

log = logging.getLogger("ats.parsing.regex")

def fallback_parse(text: str) -> dict[str, Any]:
    """
    Crude but deterministic regex extraction for absolute fallback.
    Returns a dict matching the ParsedResume schema.
    """
    log.warning("Initiating regex fallback parser")
    
    parsed = {
        "name": "Unknown",
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
    }
    
    # Very crude name extraction (first line with letters)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines:
        for line in lines[:5]:
            if re.search(r'[A-Za-z]', line) and len(line.split()) <= 4:
                parsed["name"] = line
                break
                
    # Crude skills extraction (look for common keywords and take the next few lines)
    text_lower = text.lower()
    skills_match = re.search(r'(skills|technologies|tech stack)\b:?(.*?)(?:\n\n|\Z)', text_lower, re.DOTALL)
    if skills_match:
        raw_skills = skills_match.group(2)
        # Split by comma or newline
        skills = [s.strip() for s in re.split(r'[,\n]', raw_skills) if len(s.strip()) > 1 and len(s.strip()) < 30]
        parsed["skills"] = list(set(skills))
        
    # We leave experience, education, projects empty in fallback as they are too complex
    # for reliable generic regex extraction without NLP.
    
    return parsed
