# -*- coding: utf-8 -*-
"""
Embedding Engine — Phase 8.

Provides semantic skill similarity using sentence-transformers
(all-MiniLM-L6-v2, ~90MB, runs fully locally via CPU).

The model is lazy-loaded once on first use and cached for the
lifetime of the process.  Falls back gracefully to 0.0 if
the library is not installed or the model fails to load.

Similarity scale:
  >= 0.85  -> very high (treat as exact-ish match)
  >= 0.70  -> high      (clear semantic overlap)
  >= 0.55  -> moderate  (same domain, different tools)
  <  0.55  -> low       (no meaningful match)
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

log = logging.getLogger("ats.scoring.embeddings")

# ── Model state ──────────────────────────────────────────────
_model = None
_model_lock = threading.Lock()
_model_available: Optional[bool] = None   # None = not checked yet
MODEL_NAME = "all-MiniLM-L6-v2"


def _load_model():
    """Lazy-loads the sentence-transformers model (thread-safe)."""
    global _model, _model_available

    with _model_lock:
        if _model_available is not None:
            return _model  # Already attempted

        try:
            from sentence_transformers import SentenceTransformer
            log.info("Loading embedding model: %s ...", MODEL_NAME)
            _model = SentenceTransformer(MODEL_NAME)
            _model_available = True
            log.info("Embedding model loaded — semantic similarity enabled.")
        except ImportError:
            log.warning("sentence-transformers not installed. Semantic similarity disabled.")
            _model_available = False
        except Exception as exc:
            log.error("Failed to load embedding model: %s", exc)
            _model_available = False

    return _model


def is_available() -> bool:
    """Returns True if the embedding model is loaded and ready."""
    if _model_available is None:
        _load_model()
    return bool(_model_available)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Pure-Python cosine similarity (no numpy required)."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = sum(a * a for a in vec_a) ** 0.5
    mag_b = sum(b * b for b in vec_b) ** 0.5
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def get_skill_similarity(skill_a: str, skill_b: str) -> float:
    """
    Returns cosine similarity [0.0, 1.0] between two skill strings
    using the embedding model.  Falls back to 0.0 if unavailable.
    """
    model = _load_model()
    if model is None:
        return 0.0

    try:
        vecs = model.encode([skill_a, skill_b], normalize_embeddings=True)
        sim = float(sum(a * b for a, b in zip(vecs[0], vecs[1])))
        return max(0.0, min(1.0, sim))
    except Exception as exc:
        log.warning("Embedding similarity failed: %s", exc)
        return 0.0


def batch_similarity(skills_a: list[str], skills_b: list[str]) -> list[list[float]]:
    """
    Returns a len(skills_a) x len(skills_b) similarity matrix.
    Falls back to all-zeros if model unavailable.
    """
    model = _load_model()
    if model is None or not skills_a or not skills_b:
        return [[0.0] * len(skills_b) for _ in skills_a]

    try:
        all_skills = skills_a + skills_b
        vecs = model.encode(all_skills, normalize_embeddings=True)
        vecs_a = vecs[:len(skills_a)]
        vecs_b = vecs[len(skills_a):]

        matrix = []
        for va in vecs_a:
            row = []
            for vb in vecs_b:
                sim = float(sum(a * b for a, b in zip(va, vb)))
                row.append(max(0.0, min(1.0, sim)))
            matrix.append(row)
        return matrix
    except Exception as exc:
        log.warning("Batch embedding similarity failed: %s", exc)
        return [[0.0] * len(skills_b) for _ in skills_a]
