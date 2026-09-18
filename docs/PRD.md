# PRD — ATS Resume Analyzer v2
## Product Requirements Document

> **Document Version**: 1.0  
> **Last Updated**: 2026-09-05  
> **Status**: Draft — Awaiting Approval  
> **Project Codename**: ATS-v2  
> **Predecessor**: ATS Resume Analyzer Prototype (single-file monolith, proof-of-concept)

---

## 1. Problem Statement

### 1.1 The Problem

Hiring teams spend 6–8 seconds per resume during initial screening. For a role receiving 200+ applications, manual review is:
- **Slow** — hours of repetitive work per open position
- **Inconsistent** — different reviewers evaluate differently; bias is unavoidable
- **Non-transparent** — candidates get a "rejected" email with zero explanation
- **Error-prone** — strong candidates get missed because a human got tired on resume #147

Existing ATS tools (Workday, Greenhouse, Lever) use basic keyword matching — they reject resumes that say "React.js" when the JD says "React", or "Postgres" when the JD says "PostgreSQL". This is not intelligent screening.

### 1.2 What We're Building

**ATS Resume Analyzer v2** is an intelligent resume screening system that:
1. Extracts text from any PDF resume (text-based, multi-column, scanned)
2. Parses the unstructured text into structured data using an LLM — with validation, retry, and fallback
3. Scores the candidate against a specific job description using a **hybrid approach**: rule-based deterministic scoring + LLM-based contextual scoring
4. Presents results in a professional dashboard with score breakdown, visual analytics, candidate history, and recruiter feedback
5. Persists all data with full audit trail — every score is tied to the exact configuration that produced it

### 1.3 What Makes This Different from the Prototype

| Aspect | Prototype (v1) | New System (v2) |
|---|---|---|
| Architecture | Single `main.py` (1,667 lines) | Modular backend + React SPA frontend |
| Frontend | Single `index.html` with inline CSS/JS | Html, state management |
| Database | None — fully stateless | SQLite (local) / PostgreSQL (production) |
| Score history | Lost on page refresh | Persisted with full audit trail |
| Skill matching | Alias dictionary + cluster map only | Alias + cluster + ONNX embedding similarity |
| Projects/Certs | Not parsed at all | Full extraction + verification |
| Feedback loop | None | Recruiter feedback per analysis |
| Security | Basic pattern filter | Multi-layer defense + rate limiting + auth |
| Scoring audit | No versioning | Every score linked to config version |
| Export | None | PDF report + JSON export |

---

## 2. Target Users

### 2.1 Primary Users

#### Persona 1 — HR Recruiter (Priya, 28)
- **Role**: Screens 50–200 resumes per week for 3–5 open positions
- **Pain point**: Spends 3+ hours per position just shortlisting
- **Wants**: Quick score + clear breakdown of why — to defend her shortlist to the hiring manager
- **Technical skill**: Low — needs intuitive UI, no terminal commands
- **Key feature need**: Dashboard with score, matched/missing skills, experience timeline

#### Persona 2 — Hiring Manager (Amit, 35)
- **Role**: Reviews the recruiter's shortlist, makes final interview decisions
- **Pain point**: Doesn't trust recruiter's subjective judgment; wants data-backed decisions
- **Wants**: Comparison view across candidates, historical trends, confidence indicators
- **Technical skill**: Medium — comfortable with dashboards, not with APIs
- **Key feature need**: Candidate comparison, score versioning, export reports

#### Persona 3 — Engineering Lead / Technical Interviewer (Sneha, 30)
- **Role**: Validates if the recruiter's "strong Python candidate" actually has strong Python
- **Pain point**: Gets forwarded resumes with no context about what the system found
- **Wants**: Detailed skill analysis, verified vs unverified skills, project extraction
- **Technical skill**: High — can read JSON, understands technical nuance
- **Key feature need**: Raw parsed data view, API access, skill verification details

### 2.2 Secondary Users

#### Persona 4 — Job Seeker (Rohan, 22, Fresh Graduate)
- **Role**: Wants to check if his resume is ATS-friendly before applying
- **Pain point**: Gets rejected without feedback; doesn't know what to fix
- **Wants**: "Resume health check" — is my resume readable? Are my skills listed properly?
- **Technical skill**: Low to medium
- **Key feature need**: Self-service analysis, improvement suggestions, resume health score

---

## 3. Features

### 3.1 Feature Tiers

Features are organized into three tiers:
- **🔴 CORE** — Must have. System is incomplete without these.
- **🟡 ENHANCED** — Should have. Makes the system production-quality.
- **🟢 PREMIUM** — Nice to have. Differentiators that impress in demo/interview.

---

### 3.2 Feature Matrix

#### A. Resume Ingestion & Extraction

| ID | Feature | Tier | Description |
|---|---|---|---|
| F-A01 | PDF Upload | 🔴 CORE | Accept PDF files via drag-and-drop or file picker. Max 10 MB. |
| F-A02 | 3-Tier PDF Extraction | 🔴 CORE | Tier 1: PyMuPDF (fast text). Tier 2: pdfplumber (complex layouts/tables). Tier 3: Tesseract OCR (scanned PDFs). |
| F-A03 | Concurrent Tier 1+2 | 🔴 CORE | Run PyMuPDF and pdfplumber in parallel threads. Pick the better result. |
| F-A04 | Two-Column Layout Detection | 🔴 CORE | If Tier 2 yields 15%+ more content than Tier 1, prefer Tier 2. |
| F-A05 | OCR Confidence Logging | 🟡 ENHANCED | Per-page OCR confidence score. Warn if avg confidence < 70%. |
| F-A06 | DOCX Support | 🟡 ENHANCED | Accept `.docx` files using `python-docx`. Convert to text before parsing. |
| F-A07 | Page Count Limit | 🟡 ENHANCED | Reject PDFs with > 10 pages (not a resume). |
| F-A08 | File Magic Byte Validation | 🟡 ENHANCED | Verify the file is actually a PDF/DOCX by reading magic bytes, not just the extension. |
| F-A09 | Extraction Tier Metadata | 🔴 CORE | Return which tier was used, characters extracted, and any warnings. |

---

#### B. LLM Resume Parsing

| ID | Feature | Tier | Description |
|---|---|---|---|
| F-B01 | Structured LLM Parsing | 🔴 CORE | Send extracted text to LLM (Groq/LLaMA). Extract: name, skills, experience (company, role, duration, responsibilities), education, **projects**, **certifications**. |
| F-B02 | Strict Schema Validation | 🔴 CORE | Validate LLM output with Pydantic v2 (`extra="forbid"`). Reject hallucinated fields. |
| F-B03 | LLM Retry with Correction | 🔴 CORE | 3 attempts. Attempt 1: temp=0.1. Attempts 2–3: temp=0.0, append previous error to prompt. |
| F-B04 | Regex Fallback Extractor | 🔴 CORE | If all LLM attempts fail, extract name/skills/education/experience via deterministic regex. Never crash. |
| F-B05 | Source Verification | 🔴 CORE | Cross-check every LLM-extracted field against raw text. Tag as `verified`, `partial`, or `unverified`. |
| F-B06 | Table-Aware Prompt | 🟡 ENHANCED | If extracted text contains pipe-delimited content (from tables), inject table-reading hint into system prompt. |
| F-B07 | Layout Sanity Check | 🟡 ENHANCED | Detect garbled/infographic resumes via character ratio + contact pattern presence heuristic. Flag for manual review. |
| F-B08 | Prompt Injection Defense | 🔴 CORE | 3-layer defense: (1) Unicode strip + pattern filter, (2) XML-delimited data/instruction separation, (3) Explicit security context in system prompt. |
| F-B09 | JSON Sanitizer | 🔴 CORE | Strip markdown fences and extract first `{...}` block from LLM response before JSON parsing. |
| F-B10 | Duration Coercion | 🔴 CORE | Handle LLM returning duration as string ("three", "1 year", "6 months") — coerce to int. |
| F-B11 | Skills Deduplication | 🔴 CORE | Remove duplicate skills case-insensitively while preserving insertion order. |

---

#### C. Scoring Engine

| ID | Feature | Tier | Description |
|---|---|---|---|
| F-C01 | Semantic Skill Match (40 pts) | 🔴 CORE | 4-stage pipeline: normalize → canonicalize → cluster check → ONNX embedding fallback. Pure proportional scoring. |
| F-C02 | Skill Normalization | 🔴 CORE | Lowercase + abbreviation expansion (k8s→kubernetes, .js→js) + strip non-alphanumeric. |
| F-C03 | Alias Dictionary | 🔴 CORE | ~40+ technology aliases mapping surface forms to canonical tokens. |
| F-C04 | Semantic Cluster Matching | 🔴 CORE | 8 technology clusters. Same cluster = 0.9 similarity. |
| F-C05 | ONNX Embedding Similarity | 🟡 ENHANCED | `all-MiniLM-L6-v2` via ONNX Runtime (~50 MB). Triggered ONLY when stages 1–3 return 0.0. Cosine threshold: 0.75. |
| F-C06 | Experience Longevity (35 pts) | 🔴 CORE | Bracket system: 0 months+skills=60%, 1–11=75%, 12–35=90%, 36+=100% of 35 pts. Student-protective. |
| F-C07 | Contextual AI Fit (25 pts) | 🔴 CORE | Second LLM call. Inputs: responsibilities + projects + JD. Security-hardened. Floor: 10 pts (40%). |
| F-C08 | Confidence-Weighted Scoring | 🟡 ENHANCED | Verified skills get full weight (1.0×). Unverified skills get half weight (0.5×). |
| F-C09 | Parallel Scoring | 🔴 CORE | Skill match + Experience score run concurrently with Contextual LLM call via `asyncio.gather`. |
| F-C10 | Score Anomaly Detection | 🟡 ENHANCED | Log warning if contextual score >= 99 (possible prompt injection or hallucination). |
| F-C11 | Score Hard Clamping | 🔴 CORE | Clamp all component scores to their valid ranges. Total clamped to [0, 100]. |

---

#### D. Data Persistence & Versioning

| ID | Feature | Tier | Description |
|---|---|---|---|
| F-D01 | Analysis Storage | 🔴 CORE | Every analysis result stored in database with full parsed resume, scores, metadata. |
| F-D02 | Scoring Config Versioning | 🔴 CORE | Store weight configuration (40/35/25), model name, prompt version per config version. Every analysis links to the config that produced it. |
| F-D03 | Resume Deduplication | 🟡 ENHANCED | SHA-256 hash of file bytes. If same resume re-uploaded, return cached parse (scoring may differ per JD). |
| F-D04 | Job Description Storage | 🟡 ENHANCED | Store JD text with hash. Link analyses to JDs for comparison across candidates. |
| F-D05 | SQLite for Local | 🔴 CORE | Zero-config database for local development. Single file, no server. |
| F-D06 | PostgreSQL for Deploy | 🟡 ENHANCED | Production database with connection pooling. Switchable via environment variable. |
| F-D07 | Database Migrations | 🟡 ENHANCED | Schema versioning using Alembic. No manual DROP TABLE. |

---

#### E. Dashboard & UI

| ID | Feature | Tier | Description |
|---|---|---|---|
| F-E01 | Upload & Analyze Page | 🔴 CORE | Drag-and-drop PDF upload, JD text input, required skills input, analyze button. |
| F-E02 | Score Results View | 🔴 CORE | Total score ring, 3-component bar chart, matched/missing skills, experience timeline, AI justification. |
| F-E03 | Parse Confidence Panel | 🔴 CORE | Show verified vs unverified skills (color-coded). Show field confidence per section. Show manual_review_recommended banner. |
| F-E04 | Analysis History Page | 🔴 CORE | List of all past analyses. Filterable by date, score range, candidate name. Sortable. |
| F-E05 | Analysis Detail Page | 🔴 CORE | Full breakdown for a single analysis. All scores, parsed resume, extraction metadata, config version used. |
| F-E06 | Candidate Comparison | 🟡 ENHANCED | Side-by-side comparison of 2–4 candidates analyzed against the same JD. Radar chart overlay. |
| F-E07 | Analytics Dashboard | 🟡 ENHANCED | Aggregate stats: avg score this week, skill gap heatmap (which required skills are most candidates missing), extraction tier distribution. |
| F-E08 | Recruiter Feedback UI | 🔴 CORE | After viewing results: "Was this score accurate?" → Accurate / Too High / Too Low / Inaccurate + optional comment. |
| F-E09 | PDF Report Export | 🟡 ENHANCED | Download a formatted PDF report of analysis results for offline sharing. |
| F-E10 | JSON Export | 🔴 CORE | Download raw JSON of analysis result. |
| F-E11 | Resume Health Check | 🟢 PREMIUM | JD-independent score: Is the resume ATS-readable? Are sections present? Is contact info found? |
| F-E12 | Dark / Light Theme Toggle | 🟢 PREMIUM | User preference for visual theme. Persisted in localStorage. |
| F-E13 | Responsive Design | 🔴 CORE | Works on desktop (1920px), laptop (1366px), tablet (768px). |
| F-E14 | Loading States | 🔴 CORE | Multi-step progress indicator during analysis: Extracting → Parsing → Scoring → Contextual. |
| F-E15 | Error Handling UI | 🔴 CORE | Toast notifications for errors. Specific messages for: file too large, invalid format, API timeout, server error. |

---

#### F. Feedback & Learning

| ID | Feature | Tier | Description |
|---|---|---|---|
| F-F01 | Recruiter Feedback Storage | 🔴 CORE | Store feedback linked to analysis_id + scoring_config_id + timestamp. |
| F-F02 | Feedback Analytics | 🟡 ENHANCED | Dashboard widget: % accurate vs inaccurate, trend over time, breakdown by score range. |
| F-F03 | Feedback-Informed Insights | 🟢 PREMIUM | When "too high" feedback clusters around unverified skills → surface as system insight. |

---

#### G. Security & Operations

| ID | Feature | Tier | Description |
|---|---|---|---|
| F-G01 | API Key Authentication | 🔴 CORE | Simple API key in request header. Configurable via `.env`. |
| F-G02 | Rate Limiting | 🔴 CORE | Max 30 requests/minute per API key. Using `slowapi`. |
| F-G03 | CORS Restriction | 🔴 CORE | Allow only the frontend origin, not `*`. |
| F-G04 | Request ID Tracing | 🟡 ENHANCED | Every request gets a UUID. Logged in all operations. Returned in response headers. |
| F-G05 | Structured Logging | 🔴 CORE | JSON-formatted logs with timestamp, level, request_id, module, message. |
| F-G06 | Health Check | 🔴 CORE | `GET /health` returning status, model name, DB connectivity, API key configured. |
| F-G07 | Docker Containerization | 🔴 CORE | Multi-stage Dockerfile. System deps (Tesseract, Poppler) baked in. |

---

## 4. Functional Requirements — Detailed

### 4.1 Resume Upload Flow

```
User Action                    System Behavior
──────────────────────────────────────────────────────────
Drag PDF onto upload zone  →   Client validates: PDF/DOCX? <10MB? <10 pages?
Click "Analyze"            →   Client sends multipart POST to /api/v1/analyze
                               Server validates: magic bytes, content type, size
                               Server runs 3-tier extraction (Tier1+2 concurrent)
                               Server sanitizes extracted text (unicode + injection)
                               Server sends to LLM parser (3 attempts + fallback)
                               Server verifies parsed output against raw text
                               Server runs 3 scoring components (2 concurrent + 1 LLM)
                               Server stores result in database with config version
                               Server returns AnalysisResult JSON
Frontend renders results   ←   Score ring, breakdown bars, skills, timeline, justification
```

### 4.2 Scoring Formula

$$\text{Total Score} = (\text{Skill Match} \times W_{skill}) + (\text{Experience} \times W_{exp}) + (\text{Context Fit} \times W_{context})$$Architectural Rule: Weights ($W$) are strictly dynamic. They are retrieved from the ScoringConfig database table for each specific job. They must always sum to 1.0 (100%).Standard Default Profile: $35\%$ Skills / $25\%$ Experience / $40\%$ Contextual AI Fit.Component 1 — Semantic Skill Match (Dynamic Weight, Default 35 pts)Mechanism: For each required skill, find the best matching resume skill using the 4-stage semantic pipeline.Stage 1 (Exact): Normalize both $\rightarrow$ exact match? $\rightarrow$ $1.0$Stage 2 (Alias): Canonicalize both $\rightarrow$ alias match? $\rightarrow$ $1.0$Stage 3 (Cluster): Same semantic cluster? $\rightarrow$ $0.90$Stage 4 (Vector): ONNX cosine similarity $> 0.75$? $\rightarrow$ similarity valueAnti-Gaming Penalty: Verified skill $\times 1.0$, Unverified skill $\times 0.5$.Output: (sum of best similarities / count of required skills) * skill_weightComponent 2 — Experience Longevity (Dynamic Weight, Default 25 pts)Mechanism: Sum all duration_months from the parsed W-2 experience.Brackets: $0$ months (with skills) = $60\%$, $1\text{--}11$ = $75\%$, $12\text{--}35$ = $90\%$, $36+$ = $100\%$ of the available bucket weight.Output: bracket_pct * exp_weightComponent 3 — Contextual AI Fit (Dynamic Weight, Default 40 pts)Mechanism: LLM #2 receives the Job Description alongside the candidate's complete "Proof of Work" (Responsibilities, Projects, Certifications, Publications, Internships).Fairness Rule: Prompt strictly instructs the model never to penalize an empty category (e.g., scoring $0$ just because publications is empty).Output Data Contract: Returns an integer ($0\text{--}100$), an evidence_used array for auditability, and a justification paragraph.Calculation: (LLM_Score / 100) * context_weight

### 4.3 Data Model Summary

```
ParsedResume:
  name              string
  skills            string[]
  experience        ExperienceItem[]
  education         string[]
  projects          ProjectItem[]       ← NEW in v2
  certifications    string[]            ← NEW in v2

ExperienceItem:
  company           string
  role              string
  duration_months   int (0–600)
  responsibilities  string[]

ProjectItem:                            ← NEW in v2
  name              string
  tech_stack        string[]
  description       string

AnalysisResult:
  candidate_name             string
  parsed_resume              ParsedResume
  total_score                float (0–100)
  semantic_skill_match       float (0–40)
  experience_longevity       float (0–35)
  context_alignment          float (0–25)
  context_justification      string
  total_experience_months    int
  matched_skills             string[]
  missing_skills             string[]
  extraction_tier_used       int (1/2/3)
  processing_time_ms         int
  llm_parse_attempts         int
  used_regex_fallback        bool
  difficult_layout_detected  bool
  manual_review_recommended  bool
  field_confidence           dict
  verified_skills            string[]
  unverified_skills          string[]
  unverified_fields          string[]
  scoring_config_version     string        ← NEW in v2
```

---

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Single analysis completes in < 8 seconds (including LLM calls). Two LLM calls should not be sequential where avoidable. |
| **Concurrency** | Handle 10 concurrent analysis requests without degradation. |
| **Storage** | SQLite file stays under 1 GB for 10,000 analyses. |
| **Availability** | Local-first. No cloud dependency except Groq API for LLM calls. |
| **Security** | Resume text sanitized before all LLM calls. API key auth on all mutating endpoints. Rate limited. |
| **Portability** | Runs on Windows, macOS, Linux without code changes. Docker available for consistent deployment. |
| **Auditability** | Every score is reproducible: same resume + same JD + same config version = same deterministic scores (Skill + Experience). Contextual score may vary due to LLM non-determinism. |
| **Maintainability** | No file exceeds 300 lines. All modules independently testable. |
| **Testability** | Fairness regression tests run without LLM, network, or database. CI-compatible. |

---

## 6. Success Metrics

| Metric | Target |
|---|---|
| Single analysis latency (P50) | < 5 seconds |
| Single analysis latency (P95) | < 10 seconds |
| Fairness test pass rate | 100% (all 12+ tests) |
| LLM parse success rate (before fallback) | > 90% |
| Source verification: verified skills ratio | > 80% of extracted skills |
| Recruiter feedback: "accurate" rate | > 70% (after system stabilizes) |
| Frontend Lighthouse performance score | > 80 |

---

## 7. Out of Scope (for v2)

- Multi-language resume support (Hindi, French, etc.)
- Video resume analysis
- Real-time collaborative scoring (multiple recruiters simultaneously)
- External certification verification APIs (Coursera, AWS, etc.)
- Mobile native app (iOS / Android)
- Candidate-facing portal with login
- Automated interview scheduling integration
- ATS integration with Workday / Greenhouse / Lever

---

## 8. Glossary

| Term | Definition |
|---|---|
| **ATS** | Applicant Tracking System — software used by companies to manage job applications |
| **JD** | Job Description — the text describing the open position |
| **Groq** | AI inference provider offering fast LLM access via an OpenAI-compatible API |
| **LLaMA** | Large Language Model by Meta, used via Groq for resume parsing and contextual scoring |
| **ONNX** | Open Neural Network Exchange — model format for portable, lightweight inference |
| **Tier** | One level of the PDF extraction pipeline (Tier 1=PyMuPDF, Tier 2=pdfplumber, Tier 3=OCR) |
| **Semantic Cluster** | A group of related technologies (e.g., "React", "Vue", "Angular" are all in the "frontend" cluster) |
| **Canonical Token** | The single standardized form of a skill (e.g., "postgresql" is the canonical form of "Postgres", "psql", "PG") |
| **Source Verification** | Cross-checking LLM-extracted data against the raw resume text to catch hallucinations |
| **Scoring Config** | A versioned snapshot of scoring parameters (weights, model name, prompt version) |
| **Confidence Weighting** | Adjusting a skill's contribution to the score based on whether it was verified in the raw text |
