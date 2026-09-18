# -*- coding: utf-8 -*-
"""
ATS Resume Analyzer v2 — Centralized Configuration

Single source of truth for all environment variables, constants,
and application settings. No other file should call os.getenv().
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Bootstrap — load .env file
# ─────────────────────────────────────────────
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH, override=True)


# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parent
FRONTEND_DIR: Path = BASE_DIR.parent / "frontend"


# ─────────────────────────────────────────────
# LLM Configuration
# ─────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")


# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ats_data.db")


# ─────────────────────────────────────────────
# Security
# ─────────────────────────────────────────────
API_KEY: str = os.getenv("API_KEY", "dev-api-key-change-in-production")
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
    if origin.strip()
]


# ─────────────────────────────────────────────
# Rate Limiting
# ─────────────────────────────────────────────
RATE_LIMIT: str = os.getenv("RATE_LIMIT", "30/minute")


# ─────────────────────────────────────────────
# File Upload Limits
# ─────────────────────────────────────────────
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_PAGE_COUNT: int = 10


# ─────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────
OCR_CHAR_THRESHOLD: int = int(os.getenv("OCR_CHAR_THRESHOLD", "150"))
TWO_COLUMN_THRESHOLD: float = 0.15  # 15% more content → prefer Tier 2


# ─────────────────────────────────────────────
# Scoring Defaults (seed values for first ScoringConfig)
# ─────────────────────────────────────────────
DEFAULT_SKILL_WEIGHT: int = int(os.getenv("DEFAULT_SKILL_WEIGHT", "35"))
DEFAULT_EXPERIENCE_WEIGHT: int = int(os.getenv("DEFAULT_EXPERIENCE_WEIGHT", "25"))
DEFAULT_CONTEXT_WEIGHT: int = int(os.getenv("DEFAULT_CONTEXT_WEIGHT", "40"))
EXPERIENCE_TARGET_MONTHS: int = int(os.getenv("EXPERIENCE_TARGET_MONTHS", "36"))


# ─────────────────────────────────────────────
# System Paths (Tesseract / Poppler)
# ─────────────────────────────────────────────
TESSERACT_CMD: str | None = os.getenv("TESSERACT_CMD")
POPPLER_PATH: str | None = os.getenv("POPPLER_PATH")


# ─────────────────────────────────────────────
# LLM Parsing
# ─────────────────────────────────────────────
LLM_MAX_ATTEMPTS: int = 3
LLM_TEMP_FIRST: float = 0.1
LLM_TEMP_RETRY: float = 0.0
MAX_RESPONSIBILITIES_FOR_CONTEXT: int = 50
MAX_JD_CHARS_FOR_CONTEXT: int = 3000


# ─────────────────────────────────────────────
# Embedding (Phase 8)
# ─────────────────────────────────────────────
ONNX_MODEL_PATH: Path = BASE_DIR / "assets" / "all-MiniLM-L6-v2.onnx"
EMBEDDING_SIMILARITY_THRESHOLD: float = 0.75


# ─────────────────────────────────────────────
# Resume Cache
# ─────────────────────────────────────────────
RESUME_CACHE_TTL_DAYS: int = 30
