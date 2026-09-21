# -*- coding: utf-8 -*-
"""
Experience Longevity Scoring.

Implements the bracket system to calculate score based on months of experience.
"""

def compute_experience_longevity(
    total_months: int, 
    target_months: int = 36, 
    max_score: float = 25.0
) -> float:
    """
    Bracket system logic from PRD Section 4.2.2.
    - FRESHER MODE (target_months <= 0): everyone gets full score — experience irrelevant
    - Matches or exceeds target: 100% of max_score
    - Within 1 year (12 months) of target: 80%
    - Within 2 years (24 months) of target: 50%
    - Anything less: 0%
    """
    # FRESHER MODE: role requires 0 experience (explicit 0 or auto-detected via JD keywords)
    # giving everyone full 25/25 is the FAIR approach — experience dimension does not apply
    if target_months <= 0:
        return max_score
        
    diff = target_months - total_months
    
    if diff <= 0:
        return max_score
    elif diff <= 12:
        return round(max_score * 0.8, 2)
    elif diff <= 24:
        return round(max_score * 0.5, 2)
    else:
        return 0.0
