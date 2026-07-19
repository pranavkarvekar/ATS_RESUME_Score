# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   ATS Resume Analyzer — Enterprise FastAPI Backend               ║
║   Model: llama-3.3-70b-versatile (Groq LPU)                     ║
║   Architecture: Multi-Tier Extraction + Hybrid Scoring Matrix    ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import textwrap
import time
from contextlib import asynccontextmanager
from typing import Any


import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel, Field, ValidationError, model_validator

# ─────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────
load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("ats.server")

# ─────────────────────────────────────────────
# Environment Configuration
# ─────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")

# Hybrid scoring configuration
EXPERIENCE_TARGET_MONTHS: int = int(os.getenv("EXPERIENCE_TARGET_MONTHS", "36"))
OCR_CHAR_THRESHOLD: int = int(os.getenv("OCR_CHAR_THRESHOLD", "150"))

MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024


# ─────────────────────────────────────────────
# Pydantic Data Models
# ─────────────────────────────────────────────
class ExperienceItem(BaseModel):
    company: str = Field(default="", description="Name of the employer organisation.")
    role: str = Field(default="", description="Job title / designation held.")
    duration_months: int = Field(
        default=0,
        ge=0,
        description="Approximate tenure expressed in whole months.",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="Key responsibility or achievement bullet points.",
    )


class ParsedResume(BaseModel):
    name: str = Field(default="Unknown", description="Candidate's full name.")
    skills: list[str] = Field(default_factory=list, description="Technical & soft skill tokens.")
    experience: list[ExperienceItem] = Field(
        default_factory=list,
        description="Ordered professional history blocks.",
    )
    education: list[str] = Field(
        default_factory=list,
        description="Degree / institution strings.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_skills(cls, values: Any) -> Any:
        """Normalise skills — accept comma-string or list from LLM output."""
        skills = values.get("skills")
        if isinstance(skills, str):
            values["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
        return values


class AnalysisResult(BaseModel):
    candidate_name: str
    parsed_resume: ParsedResume
    total_score: float = Field(ge=0, le=100)
    # ── New weight split: 40 / 35 / 25 ──────────────────────────────
    semantic_skill_match: float = Field(ge=0, le=40,
        description="Fuzzy + semantic skill alignment score (0–40 pts).")
    experience_longevity: float = Field(ge=0, le=35,
        description="Bracket-based experience score protecting students (0–35 pts).")
    context_alignment: float = Field(ge=0, le=25,
        description="LLM-assessed contextual fit score (0–25 pts).")
    context_justification: str
    total_experience_months: int
    matched_skills: list[str]
    missing_skills: list[str]
    extraction_tier_used: int
    processing_time_ms: int
    calibration_applied: bool = Field(default=False,
        description="True if the +10% floor calibration was applied for a high-skill low-exp profile.")


# ─────────────────────────────────────────────
# Application Lifecycle
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 ATS Resume Analyzer starting — model: %s", GROQ_MODEL)
    if not GROQ_API_KEY:
        log.warning("⚠️  GROQ_API_KEY is not set — LLM parsing will fail at runtime.")
    yield
    log.info("🛑 ATS Resume Analyzer shutting down.")


# ─────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────
app = FastAPI(
    title="ATS Resume Analyzer",
    description="Enterprise-grade, low-latency hybrid-scoring Applicant Tracking System.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Tier 1 — PyMuPDF Fast Character Streaming
# ─────────────────────────────────────────────
def _extract_tier1_fitz(file_bytes: bytes) -> str:
    """Extract text using PyMuPDF (fitz) — fast, in-memory streaming."""
    try:
        # pyrefly: ignore [missing-import]
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()
        return "\n".join(pages)
    except ImportError:
        log.warning("PyMuPDF (fitz) not installed — skipping Tier 1.")
        return ""
    except Exception as exc:
        log.error("Tier 1 extraction failed: %s", exc)
        return ""


# ─────────────────────────────────────────────
# Tier 2 — pdfplumber Structural Parser
# ─────────────────────────────────────────────
def _extract_tier2_pdfplumber(file_bytes: bytes) -> str:
    """
    Extract text with pdfplumber — handles multi-column layouts and
    serialises detected tables as pipe-delimited rows for downstream NLP.
    """
    try:
        import pdfplumber

        chunks: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                # Raw text preserving reading order
                raw = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                chunks.append(raw)

                # Serialise any detected tables
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        safe_row = [cell or "" for cell in row]
                        chunks.append(" | ".join(safe_row))

        return "\n".join(chunks)
    except ImportError:
        log.warning("pdfplumber not installed — skipping Tier 2.")
        return ""
    except Exception as exc:
        log.error("Tier 2 extraction failed: %s", exc)
        return ""


# ─────────────────────────────────────────────
# Tier 3 — OCR Hard Fallback
# ─────────────────────────────────────────────
def _extract_tier3_ocr(file_bytes: bytes) -> str:
    """
    Rasterise pages via pdf2image and extract tokens via pytesseract.
    Invoked only when Tiers 1 & 2 yield < OCR_CHAR_THRESHOLD characters.
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        # Tesseract binary path — required on Windows
        pytesseract.pytesseract.tesseract_cmd = r"D:\OCR_Setup\tesseract.exe"

        # Poppler bin path — required on Windows (not auto-detected from PATH)
        poppler_path = r"C:\poppler\poppler-24.08.0\Library\bin"
        images = convert_from_bytes(file_bytes, dpi=300, fmt="png", poppler_path=poppler_path)
        pages: list[str] = []
        for img in images:
            pages.append(pytesseract.image_to_string(img, lang="eng"))
        return "\n".join(pages)
    except ImportError as exc:
        log.error("OCR dependencies missing (%s) — Tier 3 unavailable.", exc)
        return ""
    except Exception as exc:
        log.error("Tier 3 OCR extraction failed: %s", exc)
        return ""


# ─────────────────────────────────────────────
# Multi-Tier Defensible Extractor
# ─────────────────────────────────────────────
async def extract_text_pipeline(file_bytes: bytes) -> tuple[str, int]:
    """
    Orchestrate the three-tier extraction pipeline asynchronously.

    Returns:
        (extracted_text, tier_used)  — tier_used ∈ {1, 2, 3}
    """
    loop = asyncio.get_running_loop()

    # Tier 1 — PyMuPDF (non-blocking via executor)
    tier1_text: str = await loop.run_in_executor(None, _extract_tier1_fitz, file_bytes)
    log.info("Tier 1 — extracted %d chars via PyMuPDF.", len(tier1_text))

    if len(tier1_text.strip()) >= OCR_CHAR_THRESHOLD:
        return tier1_text.strip(), 1

    # Tier 2 — pdfplumber augmentation
    tier2_text: str = await loop.run_in_executor(None, _extract_tier2_pdfplumber, file_bytes)
    log.info("Tier 2 — extracted %d chars via pdfplumber.", len(tier2_text))

    combined: str = (tier1_text + "\n" + tier2_text).strip()
    if len(combined) >= OCR_CHAR_THRESHOLD:
        return combined, 2

    # Tier 3 — OCR fallback (CPU-intensive; off-thread)
    log.warning("Both native tiers yielded < %d chars — engaging OCR fallback.", OCR_CHAR_THRESHOLD)
    tier3_text: str = await loop.run_in_executor(None, _extract_tier3_ocr, file_bytes)
    log.info("Tier 3 — extracted %d chars via OCR.", len(tier3_text))

    final: str = (combined + "\n" + tier3_text).strip()
    return final, 3


# ─────────────────────────────────────────────
# Groq LLM Parsing Engine
# ─────────────────────────────────────────────
_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a precise resume parsing assistant.
    Extract the following information from the raw resume text and return ONLY a valid JSON object
    with this exact schema — no markdown fences, no commentary:

    {
      "name": "string",
      "skills": ["string", ...],
      "experience": [
        {
          "company": "string",
          "role": "string",
          "duration_months": integer,
          "responsibilities": ["string", ...]
        }
      ],
      "education": ["string", ...]
    }

    Rules:
    - duration_months must be an integer (estimate if only years are given; 1 year = 12 months).
    - skills must be individual tokens (e.g., "Python", "Docker", "REST APIs").
    - responsibilities should be concise bullet strings without leading dashes.
    - If a field cannot be determined, use its default (empty string / empty list / 0).
    """
).strip()


async def parse_resume_with_groq(raw_text: str) -> ParsedResume:
    """
    Send raw resume text to Groq LPU and parse the structured JSON response
    into a validated ParsedResume Pydantic model.
    """
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY environment variable is not configured.",
        )

    client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        timeout=60.0,
        max_retries=2,
    )

    truncated_text = raw_text[:12_000]  # Stay within context window safely

    try:
        log.info("Sending resume to Groq — model: %s", GROQ_MODEL)
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Parse this resume:\n\n{truncated_text}",
                },
            ],
        )

        raw_json: str = response.choices[0].message.content or "{}"
        log.info("Groq response received — %d chars.", len(raw_json))

        try:
            parsed = ParsedResume.model_validate_json(raw_json)
        except ValidationError as ve:
            log.error("Pydantic validation failed — attempting fallback: %s", ve)
            # Attempt lenient parse with raw dict
            data = json.loads(raw_json)
            parsed = ParsedResume.model_validate(data)

        return parsed

    except APITimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Groq API request timed out. Please retry.",
        )
    except APIConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq API connection error: {exc}",
        )
    except APIStatusError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=f"Groq API returned status {exc.status_code}: {exc.message}",
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"LLM returned invalid JSON: {exc}",
        )


# ─────────────────────────────────────────────
# Contextual Justification via Groq
# ─────────────────────────────────────────────
async def _contextual_fit_score(
    responsibilities: list[str],
    job_description: str,
) -> tuple[float, str]:
    """
    Ask the Groq LLM to compute a contextual fit score (0–100) comparing
    the candidate's responsibilities against the job description.
    Returns (normalised_score_0_to_30, justification_text).
    """
    if not GROQ_API_KEY or not responsibilities or not job_description.strip():
        return 0.0, "Contextual analysis unavailable (missing inputs or API key)."

    client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        timeout=45.0,
        max_retries=1,
    )

    bullet_block = "\n".join(f"- {r}" for r in responsibilities[:50])
    prompt = textwrap.dedent(
        f"""
        Job Description:
        {job_description[:3000]}

        Candidate Responsibilities:
        {bullet_block}

        Return ONLY a JSON object with two keys:
        {{
          "score": <integer 0-100>,
          "justification": "<one concise paragraph explaining the fit>"
        }}
        """
    ).strip()

    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.2,
            max_tokens=512,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert technical recruiter. "
                        "Evaluate how well candidate experience matches the job description."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

        raw = response.choices[0].message.content or '{"score":0,"justification":""}'
        data = json.loads(raw)
        raw_score = float(data.get("score", 0))
        justification = str(data.get("justification", ""))
        # Scale 0–100 LLM score to 0–25 pts, apply 40% floor (10 pts)
        floor_pts = 25 * 0.40  # = 10.0
        normalised = round(max((raw_score / 100) * 25, floor_pts), 2)
        return normalised, justification

    except Exception as exc:
        log.error("Contextual scoring failed: %s", exc)
        # Return floor on failure rather than zero — prevents catastrophic drops
        return round(25 * 0.40, 2), f"Contextual analysis could not be completed: {exc}"


# ─────────────────────────────────────────────
# Token Normalisation (aggressive regex clean)
# ─────────────────────────────────────────────
def normalize_string(text: str) -> str:
    """
    Aggressively normalise a skill/token string so that surface-form
    variations ("React-JS", "React.js", "reactjs") resolve to an
    identical comparison token.

    Steps:
      1. Lower-case the entire string.
      2. Strip all characters that are NOT [a-z0-9] (removes punctuation,
         spaces, dashes, dots, slashes, underscores, etc.).
    """
    if not isinstance(text, str):
        return ""
    lowered = text.lower()
    return re.sub(r"[^a-z0-9]", "", lowered)


# ─────────────────────────────────────────────
# Semantic Cluster Map
# ─────────────────────────────────────────────
# Each entry maps a canonical concept label to a set of normalised
# surface-form tokens that are semantically equivalent to it.
_SEMANTIC_CLUSTERS: dict[str, frozenset[str]] = {
    "machinelearning": frozenset({
        "machinelearning", "ml", "ai", "artificialintelligence",
        "generativeai", "genai", "llm", "llms", "deeplearning", "dl",
        "nlp", "naturallanguageprocessing", "computervision", "cv",
        "neuralnetwork", "transformers", "pytorch", "tensorflow", "keras",
        "sklearn", "scikitlearn",
    }),
    "backenddev": frozenset({
        "backend", "backenddev", "backendevelopment", "serverside",
        "fastapi", "django", "flask", "expressjs", "nodejs", "springboot",
        "restapi", "restapis", "graphql", "grpc", "microservices",
        "python", "java", "golang", "go", "rust", "ruby",
    }),
    "frontend": frozenset({
        "frontend", "frontenddev", "ui", "ux",
        "reactjs", "react", "vuejs", "vue", "angular", "nextjs", "nuxtjs",
        "javascript", "js", "typescript", "ts", "html", "css", "sass",
        "tailwind", "webpack", "vite",
    }),
    "clouddevops": frozenset({
        "cloud", "devops", "aws", "gcp", "azure", "googlecloud",
        "docker", "kubernetes", "k8s", "terraform", "ansible",
        "cicd", "githubactions", "jenkins", "helm", "linux",
        "serverless", "lambda", "ec2", "s3",
    }),
    "database": frozenset({
        "database", "db", "sql", "nosql", "postgresql", "postgres",
        "mysql", "mariadb", "sqlite", "mongodb", "cassandra",
        "redis", "elasticsearch", "dynamodb", "bigquery",
    }),
    "datascienceanalytics": frozenset({
        "datascience", "dataanalysis", "dataanalytics", "dataengineer",
        "pandas", "numpy", "spark", "hadoop", "etl", "dbt", "airflow",
        "powerbi", "tableau", "excel", "jupyter",
    }),
    "security": frozenset({
        "security", "cybersecurity", "appsecurity", "owasp",
        "penetrationtesting", "pentest", "soc", "siem", "encryption",
        "tls", "ssl", "oauth", "jwt", "iam",
    }),
    "mobiledevelopment": frozenset({
        "mobile", "ios", "android", "reactnative", "flutter", "swift",
        "kotlin", "xamarin", "capacitor",
    }),
}

# Build reverse index: normalised_token -> canonical_cluster_label
_TOKEN_TO_CLUSTER: dict[str, str] = {}
for _cluster, _tokens in _SEMANTIC_CLUSTERS.items():
    for _tok in _tokens:
        _TOKEN_TO_CLUSTER[_tok] = _cluster


def _get_cluster(token: str) -> str | None:
    """Return the semantic cluster label for a normalised token, or None."""
    return _TOKEN_TO_CLUSTER.get(normalize_string(token))


# ─────────────────────────────────────────────
# Semantic Similarity Proxy
# ─────────────────────────────────────────────
def get_semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Compute a conceptual alignment score in [0.0, 1.0] between two skill
    tokens without requiring a vector model.

    Matching tiers (best wins):
      1.0 — Exact normalised token match           ("PostgreSQL" == "postgres")
      0.9 — Same semantic cluster                  ("FastAPI" ≈ "Backend Dev")
      0.0 — No structural or conceptual link
    """
    if not text_a or not text_b:
        return 0.0

    norm_a = normalize_string(text_a)
    norm_b = normalize_string(text_b)

    if not norm_a or not norm_b:
        return 0.0

    # Tier 1: exact normalised match
    if norm_a == norm_b:
        return 1.0

    # Tier 1b: substring containment (handles abbreviations / partials)
    if norm_a in norm_b or norm_b in norm_a:
        return 0.95

    # Tier 2: semantic cluster alignment
    cluster_a = _get_cluster(norm_a)
    cluster_b = _get_cluster(norm_b)
    if cluster_a and cluster_b and cluster_a == cluster_b:
        return 0.9

    return 0.0


# ─────────────────────────────────────────────
# Scoring Component 1: Semantic Skill Match (40 pts)
# ─────────────────────────────────────────────
def compute_semantic_skill_score(
    resume_skills: list[str],
    required_skills: list[str],
    job_description: str,
) -> tuple[float, list[str], list[str]]:
    """
    Pure Proportional Semantic Skill Match — 40% weight (0–40 pts).

    Scoring is a strict linear scale with zero artificial floor:
      - 10 / 10 required skills matched  →  40.0 pts  (100%)
      - 1  / 10 required skills matched  →   4.0 pts  ( 10%)
      - 0  / 10 required skills matched  →   0.0 pts  (  0%)

    Fuzzy matching is retained via semantic cluster alignment and
    JD token containment fallback. Only the floor is removed.

    Returns: (score_0_to_40, matched_skills, missing_skills)
    """
    MAX_PTS: float = 40.0
    MATCH_THRESHOLD: float = 0.9

    # No required skills specified — no skill dimension to score.
    if not required_skills:
        return 0.0, [], []

    jd_norm_tokens: set[str] = set(normalize_string(job_description).split())
    matched: list[str] = []
    missing: list[str] = []
    total_similarity: float = 0.0

    valid_required = [s for s in required_skills if s.strip()]
    if not valid_required:
        return 0.0, [], []

    for req_skill in valid_required:
        best_sim: float = 0.0

        # Primary: compare against every parsed resume skill
        for res_skill in resume_skills:
            sim = get_semantic_similarity(req_skill, res_skill)
            if sim > best_sim:
                best_sim = sim
            if best_sim >= 1.0:  # perfect match — short-circuit inner loop
                break

        # Fallback: containment check against raw JD token set
        if best_sim < MATCH_THRESHOLD:
            req_norm = normalize_string(req_skill)
            if req_norm and req_norm in jd_norm_tokens:
                best_sim = max(best_sim, 0.95)

        total_similarity += best_sim
        if best_sim >= MATCH_THRESHOLD:
            matched.append(req_skill)
        else:
            missing.append(req_skill)

    # Pure proportional score — no floor, no bonus, no conditional branching.
    # Floating-point safety: clamp similarity ratio to [0.0, 1.0] before scaling.
    raw_ratio: float = min(max(total_similarity / len(valid_required), 0.0), 1.0)
    final_score: float = round(raw_ratio * MAX_PTS, 2)

    log.info(
        "Semantic skill score: %.2f/40 (ratio=%.4f, matched=%d/%d)",
        final_score, raw_ratio, len(matched), len(valid_required),
    )
    return final_score, matched, missing


# ─────────────────────────────────────────────
# Scoring Component 2: Experience Longevity Bracket (35 pts)
# ─────────────────────────────────────────────
def compute_experience_longevity(
    experience: list[ExperienceItem],
    resume_skills: list[str],
) -> tuple[float, int]:
    """
    Student-Protective Bounded Experience Matrix — 35% weight (0–35 pts).

    Bracket table (percentage of 35-pt maximum):
      0 months + skills/projects listed  = 60%  baseline floor
      1 – 11 months (internships)         = 75%
      12 – 35 months                      = 90%
      36+ months                          = 100%

    Returns: (score_0_to_35, total_months)
    """
    MAX_PTS: float = 35.0

    total_months: int = sum(
        max(item.duration_months, 0) for item in experience
    )
    has_skills_or_projects: bool = bool(resume_skills) or any(
        item.responsibilities for item in experience
    )

    if total_months == 0:
        bracket_pct = 0.60 if has_skills_or_projects else 0.40
    elif total_months <= 11:
        bracket_pct = 0.75
    elif total_months <= 35:
        bracket_pct = 0.90
    else:
        bracket_pct = 1.00

    score = round(bracket_pct * MAX_PTS, 2)
    log.info(
        "Experience longevity: %d months -> bracket %.0f%% -> %.2f/35",
        total_months, bracket_pct * 100, score,
    )
    return score, total_months


# ─────────────────────────────────────────────
# Input Validation Helpers
# ─────────────────────────────────────────────
def _validate_file(file: UploadFile) -> None:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Only PDF files are accepted.",
        )


def _parse_skills_input(skills_raw: str) -> list[str]:
    return [s.strip() for s in skills_raw.split(",") if s.strip()]


# ─────────────────────────────────────────────
# REST Endpoints
# ─────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Health check endpoint.")
async def health_check() -> JSONResponse:
    return JSONResponse(
        content={
            "status": "ok",
            "model": GROQ_MODEL,
            "experience_target_months": EXPERIENCE_TARGET_MONTHS,
            "api_key_configured": bool(GROQ_API_KEY),
        }
    )


@app.post(
    "/api/v1/analyze",
    response_model=AnalysisResult,
    tags=["ATS"],
    summary="Analyze a resume PDF against a job description.",
    status_code=status.HTTP_200_OK,
)
async def analyze_resume(
    resume: UploadFile = File(..., description="Candidate resume in PDF format."),
    job_description: str = Form(..., description="Full job description text."),
    required_skills: str = Form(
        default="",
        description="Comma-separated list of required skills (e.g. 'Python, Docker, SQL').",
    ),
    experience_target_months: int = Form(
        default=0,
        description="Override the global experience target in months (0 = use server default).",
    ),
) -> AnalysisResult:
    start_ts = time.monotonic()

    # ── Validate inputs ──────────────────────────────────────────────
    _validate_file(resume)

    if not job_description.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="job_description must not be empty.",
        )

    file_bytes = await resume.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded resume file is empty.",
        )
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_MB} MB.",
        )

    skills_list = _parse_skills_input(required_skills)
    target_months = experience_target_months if experience_target_months > 0 else EXPERIENCE_TARGET_MONTHS

    log.info(
        "▶ Analyze request — file: %s | skills: %s | target_months: %d",
        resume.filename,
        skills_list,
        target_months,
    )

    # ── Multi-Tier Extraction ────────────────────────────────────────
    try:
        raw_text, tier_used = await extract_text_pipeline(file_bytes)
    except Exception as exc:
        log.exception("Fatal extraction error.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF extraction failed: {exc}",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any text from the uploaded PDF across all extraction tiers.",
        )

    # ── Groq LLM Parsing ────────────────────────────────────────────
    parsed_resume = await parse_resume_with_groq(raw_text)

    # ── Collect all responsibilities ─────────────────────────────────
    all_responsibilities: list[str] = []
    for exp in parsed_resume.experience:
        all_responsibilities.extend(exp.responsibilities)

    # ── Component Scoring ────────────────────────────────────────────
    # Each component is independently computed and fully auditable.
    # No post-hoc penalties, bonuses, or conditional overrides are applied.

    # Component 1 — Semantic Skill Match (0–40 pts): pure proportional linear scale
    semantic_skill_score, matched_skills, missing_skills = compute_semantic_skill_score(
        parsed_resume.skills,
        skills_list,
        job_description,
    )

    # Component 2 — Experience Longevity (0–35 pts): bracket-protected (student-safe)
    exp_longevity_score, total_months = compute_experience_longevity(
        parsed_resume.experience,
        parsed_resume.skills,
    )

    # Component 3 — Contextual Alignment (0–25 pts): LLM semantic fit score
    ctx_alignment_score, context_justification = await _contextual_fit_score(
        all_responsibilities,
        job_description,
    )

    # ── Transparent Aggregation ──────────────────────────────────────
    # Total = sum of three independent components, clamped to [0.0, 100.0].
    # No bonuses, no penalties, no floors applied at this layer.
    calibration_applied: bool = False  # retained for schema compatibility
    raw_total: float = semantic_skill_score + exp_longevity_score + ctx_alignment_score
    total_score: float = round(min(max(raw_total, 0.0), 100.0), 2)

    elapsed_ms = int((time.monotonic() - start_ts) * 1000)
    log.info(
        "Analysis complete: score=%.1f/100 | semantic=%.1f/40 | exp=%.1f/35 | ctx=%.1f/25 | tier=%d | %dms",
        total_score, semantic_skill_score, exp_longevity_score,
        ctx_alignment_score, tier_used, elapsed_ms,
    )

    return AnalysisResult(
        candidate_name=parsed_resume.name,
        parsed_resume=parsed_resume,
        total_score=total_score,
        semantic_skill_match=semantic_skill_score,
        experience_longevity=exp_longevity_score,
        context_alignment=ctx_alignment_score,
        context_justification=context_justification,
        total_experience_months=total_months,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        extraction_tier_used=tier_used,
        processing_time_ms=elapsed_ms,
        calibration_applied=calibration_applied,
    )


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
        log_level="info",
    )
