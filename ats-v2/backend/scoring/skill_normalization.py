# -*- coding: utf-8 -*-
"""
Skill Normalization.

Cleans and standardizes skill strings before alias/cluster matching.
Removes special characters, standardizes casing, and drops version numbers.
"""

import re
import logging

log = logging.getLogger("ats.scoring.normalization")

def normalize_string(skill: str) -> str:
    """
    Standardizes a skill string for comparison.
    - Lowercases
    - Strips leading/trailing spaces
    - Removes common version numbers (e.g. "Python 3.x" -> "python")
    - Removes certain special characters, retaining some (e.g. C#, C++)
    """
    if not skill:
        return ""
        
    s = skill.lower().strip()
    
    # Special cases that shouldn't be stripped of symbols
    if s in ("c#", "c++", ".net", "k8s", "html5", "w3c"):
        return s
        
    # Remove version numbers (e.g. "html5" -> "html", "react 18" -> "react")
    s = re.sub(r'[\s\-]*[vV]?\d+(\.\d+)*[xX]?', '', s)
    
    # Remove special characters that are often used as separators
    s = re.sub(r'[^\w\s\+#\.]', ' ', s)
    
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s)
    
    return s.strip()
