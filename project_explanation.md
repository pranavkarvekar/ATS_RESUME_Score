# 📘 ATS Resume Analyzer — Complete Deep Dive Explanation

> **Goal of this document:** After reading this, you will fully understand every part of this project — how the code works, what each function does, why each decision was made, and how the scores are calculated. No prior knowledge assumed.

---

## 🗺️ The Big Picture (What This Project Does)

Imagine you apply for a job. The company receives hundreds of resumes. They use an **ATS (Applicant Tracking System)** — software that reads your resume and gives it a score. If your score is high, a human reads your resume. If low, you're filtered out automatically.

This project **builds that ATS system**. It:
1. Takes your **PDF resume** as input
2. Reads text from it
3. Sends that text to an **AI (LLM)** to extract structured data
4. Compares your resume against a **job description**
5. Produces a **score out of 100** with 3 sub-scores

---

## 🏗️ Architecture Overview

```
User uploads PDF + Job Description
          │
          ▼
┌─────────────────────────┐
│  Step 1: PDF Extraction │  ← 3 Tier system (PyMuPDF → pdfplumber → OCR)
└─────────────────────────┘
          │
          ▼
┌─────────────────────────┐
│  Step 2: LLM Parsing    │  ← Groq AI reads raw text, returns JSON
└─────────────────────────┘
          │
          ▼
┌─────────────────────────┐
│  Step 3: Scoring        │  ← 3 independent scores calculated
│  • Semantic Skills (40) │
│  • Experience (35)      │
│  • Context Alignment(25)│
└─────────────────────────┘
          │
          ▼
      Final Score /100
```

---

## 📦 Part 1 — Imports and Setup (Lines 1–56)

### What are imports?
Think of imports like loading tools from a toolbox before starting work.

```python
import asyncio      # Lets multiple things happen at the same time (like cooking 2 dishes together)
import io           # Handles bytes/memory (like a RAM buffer)
import json         # Converts Python dict ↔ JSON text
import logging      # Prints status messages to the terminal
import os           # Reads from the .env file / environment
import re           # Regular expressions — pattern matching in text
import textwrap     # Cleans up multi-line strings (removes extra indentation)
import time         # Measures how long things take
```

```python
import uvicorn                  # Web server that actually listens for HTTP requests
from dotenv import load_dotenv  # Reads the .env file and loads API keys into memory
from fastapi import FastAPI ...  # The web framework — creates endpoints like /api/v1/analyze
from fastapi.middleware.cors ... # Allows browser JS to call the backend (cross-origin)
from openai import AsyncOpenAI  # Client that talks to Groq's AI (Groq uses OpenAI's API format)
from pydantic import BaseModel  # Data validation library — ensures data has correct types/shapes
```

### Environment Variables (`.env` file)
```python
load_dotenv(override=True)      # Load the .env file into memory
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")   # Your secret key to call Groq AI
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # Which AI model to use
EXPERIENCE_TARGET_MONTHS = int(os.getenv("EXPERIENCE_TARGET_MONTHS", "36"))  # Default = 36 months
OCR_CHAR_THRESHOLD = int(os.getenv("OCR_CHAR_THRESHOLD", "150"))  # Less than 150 chars = bad extraction
```

> **Simple analogy:** The `.env` file is like a post-it note stuck on your computer that says "here are your passwords". `load_dotenv()` reads that note and remembers the values.

---

## 🧱 Part 2 — Pydantic Data Models (Lines 62–116)

### What is Pydantic?

Pydantic is a library that **validates data**. Imagine you're filling a form — if you type letters in the "age" field, Pydantic rejects it and says "age must be a number". It ensures your data has the right shape before you use it.

### Why do we need it here?

The AI (LLM) returns a JSON string. JSON is just text. Pydantic converts that raw text into proper Python objects with the correct types, and throws an error if something is wrong or missing.

---

### Model 1: `ExperienceItem` (One job in your work history)

```python
class ExperienceItem(BaseModel):
    company:          str       # "Google", "Infosys", etc.
    role:             str       # "Software Engineer", "Intern"
    duration_months:  int       # How many months you worked there (>= 0)
    responsibilities: list[str] # ["Built REST APIs", "Managed database", ...]
```

**What `BaseModel` does:** When you write `class ExperienceItem(BaseModel)`, Pydantic automatically:
- Checks that `company` is a string (not a number)
- Checks that `duration_months` is an integer ≥ 0 (because of `ge=0`)
- If the AI gives `duration_months: "six"`, Pydantic tries to convert it, and if it can't, throws a `ValidationError`

**Example — What the AI gives:**
```json
{
  "company": "Ascent Cyber Solutions",
  "role": "Software Development Intern",
  "duration_months": 3,
  "responsibilities": ["Built ATM parser", "Created analytics dashboard"]
}
```
Pydantic reads this → creates an `ExperienceItem` Python object you can use safely.

---

### Model 2: `ParsedResume` (The whole resume)

```python
class ParsedResume(BaseModel):
    name:       str             # "Rahul Sharma"
    skills:     list[str]       # ["Python", "Django", "MongoDB", ...]
    experience: list[ExperienceItem]  # List of jobs
    education:  list[str]       # ["B.Tech IT, PICT Pune"]

    @model_validator(mode="before")
    @classmethod
    def _coerce_skills(cls, values):
        # If LLM returns skills as a comma string instead of a list, fix it
        skills = values.get("skills")
        if isinstance(skills, str):
            values["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
        return values
```

**The `@model_validator` — Why it exists:**

The AI sometimes returns:
```json
{"skills": "Python, Django, MongoDB"}    ← a string (WRONG format)
```
But we need:
```json
{"skills": ["Python", "Django", "MongoDB"]}    ← a list (CORRECT format)
```

The `_coerce_skills` validator runs **before** Pydantic validates the data. It sees the string, splits it by commas, and converts it to a list. This is called **data coercion** (forcing data into the right shape).

---

### Model 3: `AnalysisResult` (The final output returned to user)

```python
class AnalysisResult(BaseModel):
    candidate_name:         str           # "Rahul Sharma"
    parsed_resume:          ParsedResume  # The full structured resume (nested model)
    total_score:            float         # 0–100, the final ATS score
    semantic_skill_match:   float         # 0–40 pts
    experience_longevity:   float         # 0–35 pts
    context_alignment:      float         # 0–25 pts
    context_justification:  str           # AI's written explanation of the context score
    total_experience_months: int          # e.g., 3
    matched_skills:         list[str]     # Skills found in both resume and JD
    missing_skills:         list[str]     # Skills in JD but not in resume
    extraction_tier_used:   int           # Which tier (1, 2, or 3) extracted the PDF
    processing_time_ms:     int           # How many milliseconds the whole thing took
    calibration_applied:    bool          # Was the +10 bonus applied?
```

> **Key concept — Nested Models:** Notice `parsed_resume: ParsedResume`. You can put one Pydantic model inside another. When FastAPI sends this as JSON to the browser, it automatically converts everything — including the nested `ParsedResume` and all `ExperienceItem` objects inside it — into a clean JSON response.

---

## 🚀 Part 3 — FastAPI Application Setup (Lines 119–147)

### The Lifespan (startup/shutdown hooks)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("ATS Resume Analyzer starting")    # Runs when server starts
    if not GROQ_API_KEY:
        log.warning("GROQ_API_KEY is not set")  # Warn if API key missing
    yield                                        # Server runs here (between start and stop)
    log.info("ATS Resume Analyzer shutting down")  # Runs when server stops
```

Think of `yield` like pressing play on a tape recorder. Everything before `yield` is startup. Everything after is cleanup.

### Creating the App

```python
app = FastAPI(
    title="ATS Resume Analyzer",
    version="1.0.0",
    lifespan=lifespan,
)
```

This creates the web server object. When you visit `http://localhost:8000/docs`, FastAPI auto-generates a beautiful UI to test your API — that's one of its best features.

### CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Any website can call this API
    allow_methods=["*"],     # GET, POST, PUT, DELETE — all allowed
    allow_headers=["*"],     # All headers allowed
)
```

**Why CORS?** Your browser has a security rule: "A webpage from `file:///index.html` cannot call an API at `http://localhost:8000` unless the API explicitly says it's okay." CORS middleware tells the browser "yes, it's okay, let anyone call us." In production you'd lock this down to specific domains.

---

## 📄 Part 4 — Three-Tier PDF Extraction (Lines 150–264)

This is one of the most important and clever parts of the system. PDFs are notoriously difficult to extract text from because they come in many formats.

### Why 3 tiers?

| PDF Type | Problem | Solution |
|---|---|---|
| Normal text PDF | Easy | Tier 1 — fast |
| Multi-column / table PDF | Layout is complex | Tier 2 — structural |
| Scanned image PDF | No text at all, just a photo | Tier 3 — OCR reads pixels |

---

### Tier 1 — PyMuPDF (`_extract_tier1_fitz`) Lines 153–168

```python
def _extract_tier1_fitz(file_bytes: bytes) -> str:
    import fitz           # PyMuPDF library
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))   # Extract text from each page
    doc.close()
    return "\n".join(pages)
```

**How it works:**
- PyMuPDF (called `fitz`) reads the PDF bytes directly from memory (not from disk)
- It opens each page like a book page and extracts all characters
- Very fast — a 10-page resume takes ~5ms
- Works perfectly for 90% of PDFs

**Analogy:** Like using Ctrl+A, Ctrl+C on a normal text-based PDF.

---

### Tier 2 — pdfplumber (`_extract_tier2_pdfplumber`) Lines 175–203

```python
def _extract_tier2_pdfplumber(file_bytes: bytes) -> str:
    import pdfplumber
    chunks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            raw = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            chunks.append(raw)

            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    safe_row = [cell or "" for cell in row]
                    chunks.append(" | ".join(safe_row))   # Table rows as pipe-separated text
    return "\n".join(chunks)
```

**How it works:**
- `x_tolerance=3, y_tolerance=3` means "if two text items are within 3 pixels of each other horizontally/vertically, treat them as the same line/word." This handles multi-column layouts.
- **Table detection:** pdfplumber can find HTML-like tables in PDFs and extract them row-by-row. Each row is joined with `|` so the AI can parse it as structured data.

**Analogy:** Like a smarter version of Ctrl+A that understands table structure.

---

### Tier 3 — OCR (`_extract_tier3_ocr`) Lines 209–228

```python
def _extract_tier3_ocr(file_bytes: bytes) -> str:
    from pdf2image import convert_from_bytes
    import pytesseract

    images = convert_from_bytes(file_bytes, dpi=300, fmt="png")  # Convert PDF pages to images
    pages = []
    for img in images:
        pages.append(pytesseract.image_to_string(img, lang="eng"))  # OCR on each image
    return "\n".join(pages)
```

**How it works:**
- `pdf2image` converts each PDF page into a PNG image (at 300 DPI for high quality)
- `pytesseract` is a Python wrapper for **Tesseract**, Google's open-source OCR engine
- Tesseract looks at the image pixel-by-pixel and recognizes characters (like how you read text in a photo)
- This is the slowest method (~500ms–2s per page) so it's only used as a last resort

**Analogy:** Like taking a photo of a handwritten note and using Google Lens to read it.

---

### The Pipeline Orchestrator (`extract_text_pipeline`) Lines 234–264

```python
async def extract_text_pipeline(file_bytes: bytes) -> tuple[str, int]:
    loop = asyncio.get_running_loop()

    # Try Tier 1
    tier1_text = await loop.run_in_executor(None, _extract_tier1_fitz, file_bytes)
    if len(tier1_text.strip()) >= OCR_CHAR_THRESHOLD:   # e.g., >= 150 chars
        return tier1_text.strip(), 1      # ✅ Good enough — stop here

    # Try Tier 2
    tier2_text = await loop.run_in_executor(None, _extract_tier2_pdfplumber, file_bytes)
    combined = (tier1_text + "\n" + tier2_text).strip()
    if len(combined) >= OCR_CHAR_THRESHOLD:
        return combined, 2               # ✅ Good enough — stop here

    # Last resort: Tier 3
    tier3_text = await loop.run_in_executor(None, _extract_tier3_ocr, file_bytes)
    final = (combined + "\n" + tier3_text).strip()
    return final, 3
```

**Key concept — `asyncio` and `run_in_executor`:**

FastAPI is `async` — it can handle many requests at the same time. But PDF extraction is CPU-heavy (blocking). If you run it directly, it freezes the server for everyone while one person's PDF is being read.

`loop.run_in_executor(None, func, arg)` says: *"Run this function in a separate thread, so the main async server stays responsive."* It's like sending a task to a worker while you continue taking new orders.

---

## 🤖 Part 5 — How the LLM Works (Lines 270–367)

This is the heart of the system. Let's understand it completely.

### What is an LLM?

**LLM = Large Language Model.** It's a massive AI (like ChatGPT) trained on billions of text documents. It has learned patterns of human language — so it can read text and understand it the way a human does.

In this project, the LLM used is **LLaMA 3.3 70B** — an open-source AI with 70 billion parameters (like 70 billion adjustable knobs), running on **Groq's LPU** (Language Processing Unit — hardware that runs AI extremely fast, ~10x faster than regular GPUs).

### How does the LLM parse a resume?

You give it raw resume text (messy, unstructured). It returns clean, structured JSON.

```
INPUT:
"Rahul Sharma | Python Developer
Experience: Software Intern at Ascent, Jun 2024 – Sep 2024
Skills: Python, Django, MongoDB, FastAPI
Education: B.Tech IT, PICT Pune"

OUTPUT (from LLM):
{
  "name": "Rahul Sharma",
  "skills": ["Python", "Django", "MongoDB", "FastAPI"],
  "experience": [
    {
      "company": "Ascent Cyber Solutions",
      "role": "Software Development Intern",
      "duration_months": 3,
      "responsibilities": ["Built web-based ATM parser", "Created analytics dashboard"]
    }
  ],
  "education": ["B.Tech IT, PICT Pune"]
}
```

### The System Prompt (Lines 270–296)

```python
_SYSTEM_PROMPT = """
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
```

**Why is the system prompt important?**

The LLM is very powerful but needs clear instructions. The system prompt acts like a job briefing — it tells the AI exactly what role it's playing ("You are a resume parser"), what format to return, and what rules to follow.

- `"no markdown fences"` = Don't wrap JSON in ` ```json ``` ` blocks, just raw JSON
- `"duration_months must be an integer"` = If resume says "1 year", convert to `12`
- `"If a field cannot be determined, use its default"` = Never leave things null/undefined

**`temperature=0.1`** — This controls how creative/random the AI is. `0.0` = very deterministic (same input → same output always). `1.0` = very creative/random. We use `0.1` because we want consistent, predictable JSON parsing, not creative writing.

---

### The `parse_resume_with_groq` function (Lines 299–367)

```python
async def parse_resume_with_groq(raw_text: str) -> ParsedResume:
    client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",  # Groq uses OpenAI's API format
        timeout=60.0,
        max_retries=2,
    )

    truncated_text = raw_text[:12_000]  # Keep only first 12,000 characters

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=2048,
        response_format={"type": "json_object"},   # Force JSON output
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},   # Instructions
            {"role": "user",   "content": f"Parse this resume:\n\n{truncated_text}"},  # Input
        ],
    )

    raw_json = response.choices[0].message.content   # The AI's response text
    parsed = ParsedResume.model_validate_json(raw_json)   # Pydantic validates the JSON
    return parsed
```

**Step by step:**

1. **Create client** — `AsyncOpenAI` is a Python library that sends HTTP requests to Groq's API. Even though it's called `openai`, we point it to Groq's URL because Groq made their API compatible with OpenAI's format (clever!).

2. **Truncate text** — `raw_text[:12_000]` keeps only the first 12,000 characters. LLMs have a "context window" — a limit on how much text they can process at once. 12,000 characters ≈ ~5 pages of resume, which is more than enough.

3. **`messages` list** — LLMs work in a conversation format:
   - `"role": "system"` = Instructions given to the AI before the conversation
   - `"role": "user"` = The actual input being processed

4. **`response_format={"type": "json_object"}`** — This is a special Groq/OpenAI feature that forces the model to always return valid JSON. Without this, the AI might sometimes return text like "Here is the JSON:" followed by the JSON — which would break parsing.

5. **`ParsedResume.model_validate_json(raw_json)`** — After getting the JSON string from the AI, Pydantic parses it and validates every field. If `duration_months` comes back as a string, Pydantic will try to coerce it to int.

**Error handling:**
- `APITimeoutError` → 504 Gateway Timeout (Groq took too long)
- `APIConnectionError` → 502 Bad Gateway (network issue)
- `APIStatusError` → passes through Groq's error code (like 429 rate limit)
- `json.JSONDecodeError` → 422 Unprocessable Entity (AI returned invalid JSON)

---

## 🧮 Part 6 — The Three Scoring Systems

### Scoring Philosophy

The system is designed to **protect students and fresh graduates** from getting zero scores just because they have less experience. Each score has a "floor" — a minimum value even in the worst case.

| Score | Max | Floor | What it measures |
|---|---|---|---|
| Semantic Skill Match | 40 | 16 (40%) | Do your skills match the job? |
| Experience Longevity | 35 | 21 (60%) | How much work experience do you have? |
| Context Alignment | 25 | 10 (40%) | Does your overall experience story fit the job? |
| **Total** | **100** | **~47** | |

---

### Score 1: Semantic Skill Match (0–40 pts) — Lines 566–641

**What it does:** For each required skill in the job description, it checks how well your resume matches it.

#### Step 1 — String Normalization (`normalize_string`)

```python
def normalize_string(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"[^a-z0-9]", "", lowered)
```

This converts skills into a comparable form by removing ALL punctuation, spaces, and special characters:

| Input | Output |
|---|---|
| `"React.js"` | `"reactjs"` |
| `"React-JS"` | `"reactjs"` |
| `"ReactJS"` | `"reactjs"` |
| `"FastAPI"` | `"fastapi"` |
| `"REST APIs"` | `"restapis"` |

Now `"React.js"`, `"ReactJS"`, and `"React-JS"` all normalize to the same string `"reactjs"` — so they match!

#### Step 2 — Semantic Clusters

Some skills are different words but the same concept. For example: `"FastAPI"` and `"Django"` are both backend frameworks. If a job asks for "Backend Development", both should match.

```python
_SEMANTIC_CLUSTERS = {
    "backenddev": frozenset({
        "fastapi", "django", "flask", "expressjs", "nodejs",
        "restapi", "python", "java", "golang", ...
    }),
    "machinelearning": frozenset({
        "machinelearning", "ml", "ai", "llm", "nlp",
        "pytorch", "tensorflow", "sklearn", ...
    }),
    "frontend": frozenset({
        "reactjs", "react", "vuejs", "javascript", "html", "css", ...
    }),
    "database": frozenset({
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", ...
    }),
    ...
}
```

The code builds a reverse index:
```
"fastapi"  → "backenddev"
"django"   → "backenddev"
"reactjs"  → "frontend"
"html"     → "frontend"
"mongodb"  → "database"
```

#### Step 3 — `get_semantic_similarity(text_a, text_b)` — The Core Matching

```python
def get_semantic_similarity(text_a: str, text_b: str) -> float:
    norm_a = normalize_string(text_a)
    norm_b = normalize_string(text_b)

    # Level 1: Exact match (e.g., "python" == "python")
    if norm_a == norm_b:
        return 1.0

    # Level 2: Substring match (e.g., "react" in "reactjs")
    if norm_a in norm_b or norm_b in norm_a:
        return 0.95

    # Level 3: Same semantic cluster (e.g., "fastapi" and "django" both in "backenddev")
    cluster_a = _get_cluster(norm_a)
    cluster_b = _get_cluster(norm_b)
    if cluster_a and cluster_b and cluster_a == cluster_b:
        return 0.9

    # No match
    return 0.0
```

**Three matching tiers:**

| Tier | Score | Example |
|---|---|---|
| Exact match | 1.0 (100%) | `"Python"` vs `"python"` |
| Substring | 0.95 (95%) | `"React"` vs `"ReactJS"` |
| Same cluster | 0.9 (90%) | `"FastAPI"` vs `"Django"` (both backend) |
| No match | 0.0 (0%) | `"Python"` vs `"Kubernetes"` |

#### Step 4 — Computing the Full Score

```python
def compute_semantic_skill_score(resume_skills, required_skills, job_description):
    MAX_PTS = 40.0
    FLOOR_RATIO = 0.40      # 40% of 40 = 16 pts minimum
    MATCH_THRESHOLD = 0.9   # Must score >= 0.9 to count as "matched"

    total_similarity = 0.0

    for req_skill in required_skills:          # For each skill the job needs
        best_sim = 0.0

        for res_skill in resume_skills:        # Compare against every resume skill
            sim = get_semantic_similarity(req_skill, res_skill)
            best_sim = max(best_sim, sim)      # Keep the BEST match found
            if best_sim >= 1.0:
                break                          # Perfect match? Stop early

        # Fallback: check if the required skill appears as a word in the job description itself
        if best_sim < MATCH_THRESHOLD:
            req_norm = normalize_string(req_skill)
            if req_norm in jd_norm_tokens:
                best_sim = max(best_sim, 0.95)

        total_similarity += best_sim

        if best_sim >= MATCH_THRESHOLD:
            matched.append(req_skill)
        else:
            missing.append(req_skill)

    raw_ratio = total_similarity / len(required_skills)   # e.g., 0.4
    raw_score = raw_ratio * MAX_PTS                        # e.g., 0.4 × 40 = 16

    floor_pts = MAX_PTS * FLOOR_RATIO                      # 40 × 0.4 = 16 pts minimum
    final_score = max(raw_score, floor_pts)                # Never go below 16
    return final_score, matched, missing
```

**Worked Example:**

Job requires: `["Python", "Docker", "AWS"]`
Your resume has: `["Python", "Flask", "MongoDB"]`

| Required | Best Match in Resume | Score |
|---|---|---|
| Python | Python (exact) | 1.0 |
| Docker | No match found | 0.0 |
| AWS | No match found | 0.0 |

`total_similarity = 1.0 + 0.0 + 0.0 = 1.0`
`raw_ratio = 1.0 / 3 = 0.333`
`raw_score = 0.333 × 40 = 13.33 pts`
`floor = 16 pts`
`final_score = max(13.33, 16) = 16 pts` ← floor kicks in

---

### Score 2: Experience Longevity (0–35 pts) — Lines 644–685

**What it does:** Gives points based on how many months of work experience you have, using a bracket system.

```python
def compute_experience_longevity(experience, resume_skills):
    MAX_PTS = 35.0

    # Sum up all months from all jobs
    total_months = sum(max(item.duration_months, 0) for item in experience)

    # Does the person have at least some skills/projects?
    has_skills_or_projects = bool(resume_skills) or any(
        item.responsibilities for item in experience
    )

    # Bracket system
    if total_months == 0:
        bracket_pct = 0.60 if has_skills_or_projects else 0.40
    elif total_months <= 11:
        bracket_pct = 0.75
    elif total_months <= 35:
        bracket_pct = 0.90
    else:
        bracket_pct = 1.00

    score = round(bracket_pct * MAX_PTS, 2)
    return score, total_months
```

**Bracket table:**

| Experience | % | Score |
|---|---|---|
| 0 months, has skills/projects | 60% | 21.0 pts |
| 0 months, no skills at all | 40% | 14.0 pts |
| 1–11 months (internship) | 75% | **26.25 pts** ← your case |
| 12–35 months | 90% | 31.5 pts |
| 36+ months | 100% | 35.0 pts |

**Why is this student-protective?**

A fresh graduate with 0 experience still gets 21/35 (60%) instead of 0/35. This is a deliberate design choice to avoid unfairly penalizing students who haven't had time to accumulate work experience.

---

### Score 3: Context Alignment (0–25 pts) — Lines 373–439

**What it does:** Sends your actual job responsibilities + the job description to the AI and asks "how well does this person fit?"

```python
async def _contextual_fit_score(responsibilities, job_description):
    # Build a bullet list of all your job responsibilities
    bullet_block = "\n".join(f"- {r}" for r in responsibilities[:50])

    prompt = f"""
    Job Description:
    {job_description[:3000]}

    Candidate Responsibilities:
    {bullet_block}

    On a scale of 0–100, how well does the candidate's experience align with the job?
    Return ONLY a JSON: {{"score": <integer 0-100>, "justification": "<paragraph>"}}
    """

    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0.2,       # Slightly more flexible than parsing (needs some judgment)
        max_tokens=512,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an expert technical recruiter. Evaluate fit."},
            {"role": "user",   "content": prompt},
        ],
    )

    data = json.loads(response.choices[0].message.content)
    raw_score = float(data["score"])           # AI gives 0–100
    justification = str(data["justification"]) # AI's written explanation

    floor_pts = 25 * 0.40   # = 10.0 pts minimum
    normalised = max((raw_score / 100) * 25, floor_pts)  # Scale to 0–25
    return normalised, justification
```

**How the AI scores context:**

The AI is asked to act as a **technical recruiter** and think:
- *"Does this person's work history show the right kind of experience for this role?"*
- *"Did they work on similar technologies/domains?"*
- *"Are their achievements relevant?"*

The AI gives a score 0–100, which gets **scaled down to 0–25**:
- AI says `80` → `(80/100) × 25 = 20 pts`
- AI says `40` → `(40/100) × 25 = 10 pts` (but floor kicks in anyway)
- AI says `100` → `(100/100) × 25 = 25 pts`

**Floor = 10 pts:** Even if the AI says 0, you get 10 pts minimum.

---

## 🎯 Part 7 — Putting It All Together (The Main Endpoint, Lines 718–851)

The `/api/v1/analyze` endpoint is the brain that coordinates everything:

```python
@app.post("/api/v1/analyze")
async def analyze_resume(
    resume: UploadFile,          # The PDF file
    job_description: str,        # Full job description text
    required_skills: str,        # Comma-separated skills: "Python, Docker, AWS"
    experience_target_months: int,  # Override (0 = use default 36 months)
) -> AnalysisResult:

    start_ts = time.monotonic()    # Start timer

    # ── Step 1: Validate inputs ──
    _validate_file(resume)         # Must be PDF
    file_bytes = await resume.read()
    # Check file isn't empty or too large (>10MB)

    # ── Step 2: Extract text from PDF ──
    raw_text, tier_used = await extract_text_pipeline(file_bytes)

    # ── Step 3: LLM parses raw text → structured data ──
    parsed_resume = await parse_resume_with_groq(raw_text)

    # ── Step 4: Run all 3 scores in order ──
    semantic_skill_score, matched_skills, missing_skills = compute_semantic_skill_score(...)
    exp_longevity_score, total_months = compute_experience_longevity(...)
    ctx_alignment_score, context_justification = await _contextual_fit_score(...)

    # ── Step 5: Add them up ──
    raw_total = semantic_skill_score + exp_longevity_score + ctx_alignment_score
    # Max possible: 40 + 35 + 25 = 100

    # ── Step 6: Calibration Bonus ──
    # If total < 70 BUT skill score >= 30 (75% of max), add +10 bonus
    if raw_total < 70.0 and semantic_skill_score >= 30.0:
        raw_total = min(raw_total + 10.0, 100.0)
        calibration_applied = True

    total_score = round(min(max(raw_total, 0.0), 100.0), 2)

    elapsed_ms = int((time.monotonic() - start_ts) * 1000)

    return AnalysisResult(
        candidate_name=parsed_resume.name,
        parsed_resume=parsed_resume,
        total_score=total_score,
        ...
    )
```

### The Calibration Bonus — What is it?

**Problem scenario:** A student has excellent, cutting-edge skills (LangChain, RAG, LLMs) but only 3 months of experience. Their skill score is high (like 32/40) but experience score drags total below 70.

**Solution:** If your total is < 70 AND you scored ≥ 30/40 on skills (showing you're highly skilled), the system adds a +10 bonus. This prevents unfairly punishing highly-skilled candidates who simply haven't had enough time to accumulate experience.

---

## 🔄 Part 8 — The Complete Data Flow (Everything Together)

```
1. User opens index.html in browser
2. Fills in: Job Description, Required Skills, uploads PDF

3. Browser sends HTTP POST to http://localhost:8000/api/v1/analyze
   (multipart/form-data: pdf file + text fields)

4. FastAPI receives the request → calls analyze_resume()

5. PDF bytes go through extract_text_pipeline()
   ├── Tier 1 (PyMuPDF): Fast character extraction
   ├── If not enough text → Tier 2 (pdfplumber): Structural extraction
   └── If still not enough → Tier 3 (Tesseract OCR): Image-based extraction

6. Raw text → parse_resume_with_groq()
   ├── Sends text to Groq's LLaMA 3.3 70B API
   ├── LLM returns structured JSON
   └── Pydantic validates JSON → ParsedResume object

7. Three scores run in parallel (conceptually):
   ├── compute_semantic_skill_score()
   │   ├── normalize_string() both sides
   │   ├── get_semantic_similarity() for each pair
   │   └── Apply 40% floor → /40 pts
   │
   ├── compute_experience_longevity()
   │   ├── Sum all duration_months
   │   ├── Look up bracket (0/1-11/12-35/36+)
   │   └── → /35 pts
   │
   └── _contextual_fit_score()  [async — calls Groq again]
       ├── Build responsibilities bullet list
       ├── Send JD + bullets to LLM
       ├── LLM returns 0–100 score + text justification
       └── Scale to /25 pts with 40% floor

8. Add all three scores → raw_total
9. Apply calibration bonus if eligible (+10 pts)
10. Clamp to [0, 100] → total_score

11. Return AnalysisResult as JSON to browser
12. index.html renders the dashboard
```

---

## 🔑 Key Concepts Summary

| Concept | Simple Explanation |
|---|---|
| **FastAPI** | Web framework that creates API endpoints and auto-generates documentation |
| **Pydantic** | Data validator — ensures data has the right types and shape |
| **LLM** | A huge AI model that reads and understands text like a human |
| **Groq LPU** | Special hardware that runs AI models very fast (~10x GPU speed) |
| **AsyncOpenAI** | Python library to call Groq's API (using OpenAI's format) |
| **`async/await`** | Lets the server handle multiple requests simultaneously without freezing |
| **`run_in_executor`** | Runs blocking CPU code in a thread so async server stays responsive |
| **PyMuPDF (fitz)** | Fast PDF text extractor (works like copy-paste) |
| **pdfplumber** | Smarter PDF extractor that handles tables and columns |
| **Tesseract OCR** | Reads text from images (for scanned PDFs) |
| **normalize_string** | Converts skills to lowercase with no punctuation for fair comparison |
| **Semantic Clusters** | Groups of skills that mean the same concept (all backend frameworks together) |
| **Floor scoring** | Minimum score even if you have nothing — protects students |
| **Calibration bonus** | +10 pts for high-skill, low-experience candidates |
| **CORS** | Allows browser to call the API from a different origin |
| **`temperature`** | Controls AI randomness (0.1 = very consistent, 1.0 = creative/random) |
| **`model_validator`** | Runs custom code before Pydantic validates fields (e.g., string → list) |

---

## 🎓 Why This Architecture is Smart

1. **Three-tier PDF extraction** ensures the system works on any PDF — even scanned photos
2. **LLM parsing** replaces brittle regex — handles any resume format/layout
3. **Student-protective floors** ensure fair scoring for candidates with less experience
4. **Semantic clusters** prevent punishing candidates who know equivalent technologies
5. **Two LLM calls** (parse + context) separate concerns cleanly — one for structure, one for judgment
6. **Pydantic throughout** means data is always validated — no silent bugs from wrong types
7. **Async architecture** means many users can upload resumes simultaneously without the server freezing
