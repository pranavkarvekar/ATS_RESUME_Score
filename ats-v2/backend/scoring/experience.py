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
        
    # Exceeds or meets target
    if total_months >= target_months:
        return max_score
        
    # Proportional scoring: (Candidate Exp / Target Exp) * Max Score
    # Example: target is 24, candidate has 12 -> 50% score
    # Target is 12, candidate has 0 -> 0% score
    ratio = total_months / target_months
    return round(max_score * ratio, 2)
