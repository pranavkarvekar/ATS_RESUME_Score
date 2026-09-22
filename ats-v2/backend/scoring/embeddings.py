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
import numpy as np
from typing import Optional

log = logging.getLogger("ats.scoring.embeddings")

_session = None
_tokenizer = None
_model_lock = threading.Lock()
_model_available: Optional[bool] = None

MODEL_NAME = "all-MiniLM-L6-v2"
_embed_cache: dict[str, np.ndarray] = {}

def _load_model():
    global _session, _tokenizer, _model_available

    with _model_lock:
        if _model_available is not None:
            return _session, _tokenizer

        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
            import config
            
            log.info("Loading ONNX embedding model and tokenizer...")
            
            if not config.ONNX_MODEL_PATH.exists():
                log.warning("ONNX model not found at %s", config.ONNX_MODEL_PATH)
                raise FileNotFoundError()
                
            _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            # Use CPUExecutionProvider for standard CPU environments
            _session = ort.InferenceSession(str(config.ONNX_MODEL_PATH), providers=["CPUExecutionProvider"])
            
            _model_available = True
            log.info("ONNX Embedding model loaded successfully.")
        except ImportError:
            log.warning("onnxruntime or transformers not installed. Semantic similarity disabled.")
            _model_available = False
        except Exception as exc:
            log.error("Failed to load ONNX embedding model: %s", exc)
            _model_available = False

    return _session, _tokenizer

def is_available() -> bool:
    if _model_available is None:
        _load_model()
    return bool(_model_available)

def _mean_pooling(model_output, attention_mask):
    token_embeddings = model_output
    input_mask_expanded = np.expand_dims(attention_mask, -1)
    input_mask_expanded = np.broadcast_to(input_mask_expanded, token_embeddings.shape)
    
    sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
    sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
    
    return sum_embeddings / sum_mask

def _encode(sentences: list[str]) -> np.ndarray:
    """Encodes sentences using ONNX, utilizing memory cache."""
    session, tokenizer = _load_model()
    if not session or not tokenizer:
        return np.zeros((len(sentences), 384))
    
    uncached = [s for s in sentences if s not in _embed_cache]
    
    if uncached:
        encoded_input = tokenizer(uncached, padding=True, truncation=True, return_tensors='np')
        
        ort_inputs = {
            session.get_inputs()[0].name: encoded_input['input_ids'],
            session.get_inputs()[1].name: encoded_input['attention_mask'],
        }
        
        input_names = [i.name for i in session.get_inputs()]
        if 'token_type_ids' in input_names and 'token_type_ids' in encoded_input:
            ort_inputs['token_type_ids'] = encoded_input['token_type_ids']
            
        ort_outs = session.run(None, ort_inputs)
        sentence_embeddings = _mean_pooling(ort_outs[0], encoded_input['attention_mask'])
        
        norms = np.linalg.norm(sentence_embeddings, axis=1, keepdims=True)
        sentence_embeddings = np.divide(sentence_embeddings, norms, out=np.zeros_like(sentence_embeddings), where=norms!=0)
        
        for i, sentence in enumerate(uncached):
            _embed_cache[sentence] = sentence_embeddings[i]
            
    return np.array([_embed_cache[s] for s in sentences])

def get_skill_similarity(skill_a: str, skill_b: str) -> float:
    if not is_available():
        return 0.0
    try:
        vecs = _encode([skill_a, skill_b])
        sim = float(np.dot(vecs[0], vecs[1]))
        return max(0.0, min(1.0, sim))
    except Exception as exc:
        log.warning("Embedding similarity failed: %s", exc)
        return 0.0

def batch_similarity(skills_a: list[str], skills_b: list[str]) -> list[list[float]]:
    if not is_available() or not skills_a or not skills_b:
        return [[0.0] * len(skills_b) for _ in skills_a]

    try:
        vecs_a = _encode(skills_a)
        vecs_b = _encode(skills_b)
        
        sim_matrix = np.dot(vecs_a, vecs_b.T)
        return np.clip(sim_matrix, 0.0, 1.0).tolist()
    except Exception as exc:
        log.warning("Batch embedding similarity failed: %s", exc)
        return [[0.0] * len(skills_b) for _ in skills_a]
