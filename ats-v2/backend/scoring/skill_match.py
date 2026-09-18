# -*- coding: utf-8 -*-
"""
Semantic Skill Matching — Phase 8 Enhanced.

4-tier similarity pipeline (ordered by confidence):
  Tier 1: Exact canonical match            → 1.0
  Tier 2: Alias / cluster match            → 0.7–0.9
  Tier 3: Embedding cosine similarity      → 0.0–1.0 (if available)
  Tier 4: No match fallback                → 0.0

The MATCH_THRESHOLD determines what counts as a "matched" skill.
Skills above the threshold are added to matched_skills; below → missing_skills.
"""

from __future__ import annotations

import logging
from typing import Tuple

from . import skill_normalization
from . import skill_aliases
from . import skill_clusters
from . import embeddings as emb

log = logging.getLogger("ats.scoring.skill_match")

# A skill pair with cosine similarity >= this is counted as "matched"
EMBEDDING_MATCH_THRESHOLD = 0.72
# Partial credit weight for embedding matches (below exact-match but above cluster)
EMBEDDING_PARTIAL_WEIGHT = 0.8


def get_semantic_similarity(candidate_skill: str, required_skill: str) -> float:
    """
    4-tier pipeline that returns a similarity score [0.0, 1.0].

    1. Exact canonical match      → 1.0
    2. Shared cluster             → 0.75
    3. Embedding cosine >= 0.72  → cosine score (0.72 – 1.0)
    4. No match                   → 0.0
    """
    c_norm = skill_normalization.normalize_string(candidate_skill)
    r_norm = skill_normalization.normalize_string(required_skill)

    c_canon = skill_aliases.get_canonical(c_norm)
    r_canon = skill_aliases.get_canonical(r_norm)

    # Tier 1 — exact canonical match
    if c_canon == r_canon:
        return 1.0

    # Tier 2 — shared cluster
    c_clusters = set(skill_clusters.get_clusters(c_canon))
    r_clusters = set(skill_clusters.get_clusters(r_canon))
    if c_clusters and r_clusters and c_clusters.intersection(r_clusters):
        return 0.75

    # Tier 3 — embedding cosine similarity (if model available)
    if emb.is_available():
        sim = emb.get_skill_similarity(candidate_skill, required_skill)
        if sim >= EMBEDDING_MATCH_THRESHOLD:
            return sim

    return 0.0


def compute_semantic_skill_score(
    candidate_skills: list[str],
    required_skills: list[str],
    max_score: float = 35.0,
) -> Tuple[float, list[str], list[str]]:
    """
    Computes proportional skill score using the 4-tier pipeline.

    When the embedding model is loaded, uses batch_similarity for efficiency
    (one encode call for all skills instead of N×M individual calls).

    Returns:
        (score, matched_skills, missing_skills)
    """
    if not required_skills:
        return max_score, list(candidate_skills), []

    matched: list[str] = []
    missing: list[str] = []
    total_similarity = 0.0

    # Use batch embeddings when available for performance
    if emb.is_available() and candidate_skills:
        sim_matrix = emb.batch_similarity(candidate_skills, required_skills)
    else:
        sim_matrix = None

    for req_idx, req_skill in enumerate(required_skills):
        r_norm = skill_normalization.normalize_string(req_skill)
        r_canon = skill_aliases.get_canonical(r_norm)
        r_clusters = set(skill_clusters.get_clusters(r_canon))

        best_sim = 0.0

        for cand_idx, cand_skill in enumerate(candidate_skills):
            c_norm = skill_normalization.normalize_string(cand_skill)
            c_canon = skill_aliases.get_canonical(c_norm)

            # Tier 1 — exact
            if c_canon == r_canon:
                best_sim = 1.0
                break

            # Tier 2 — cluster
            c_clusters = set(skill_clusters.get_clusters(c_canon))
            if c_clusters and r_clusters and c_clusters.intersection(r_clusters):
                best_sim = max(best_sim, 0.75)
                continue

            # Tier 3 — embedding (from pre-computed matrix, note axes are swapped)
            if sim_matrix is not None:
                # matrix is [candidate_idx][required_idx]
                emb_sim = sim_matrix[cand_idx][req_idx]
                if emb_sim >= EMBEDDING_MATCH_THRESHOLD:
                    best_sim = max(best_sim, emb_sim)

        total_similarity += best_sim

        # Count as matched if similarity is meaningful
        if best_sim >= 0.5:
            matched.append(req_skill)
        else:
            missing.append(req_skill)

    ratio = total_similarity / len(required_skills)
    score = ratio * max_score
    return round(score, 2), matched, missing
