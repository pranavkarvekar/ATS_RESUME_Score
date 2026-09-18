# Phases — ATS Resume Analyzer v2
## Iterative Development Plan (10 Phases + Deployment)

> **Document Version**: 1.0  
> **Last Updated**: 2026-09-05  
> **Total Timeline**: ~6 months (part-time)  
> **Prerequisite Reading**: [PRD.md](file:///d:/ATS_Resume_score/docs/PRD.md) → [Architecture.md](file:///d:/ATS_Resume_score/docs/Architecture.md) → [Rules.md](file:///d:/ATS_Resume_score/docs/Rules.md)

---

## Development Principles

1. **Every phase produces a working, demoable increment** — no 3-week phase with nothing to show.
2. **Tests are written in the same phase as the feature** — not deferred to "later".
3. **Backend before frontend** — API must work before UI is built for it.
4. **No feature creep during a phase** — new ideas go to backlog.
5. **Each phase has clear entry criteria, deliverables, and exit criteria.**

---

## Phase Overview

```
Phase   Focus Area                          Duration     Cumulative
─────   ──────────────────────────────────  ──────────   ──────────
  1     Project Setup + Backend Foundation  3 weeks      Week 3
  2     PDF Extraction Pipeline             2 weeks      Week 5
  3     LLM Parsing + Validation Engine     2 weeks      Week 7
  4     Scoring Engine                      2 weeks      Week 9
  5     Database + Score Versioning         2 weeks      Week 11
  6     Frontend Foundation + Upload Flow   3 weeks      Week 14
  7     History, Detail & Feedback UI       2 weeks      Week 16
  8     ONNX Embeddings + Confidence        2 weeks      Week 18
  9     Analytics Dashboard + Comparison    2 weeks      Week 20
 10     Polish, Testing & Documentation     2 weeks      Week 22
  D     Deployment (Docker + Production)    2 weeks      Week 24
```

**Total: ~24 weeks (~6 months part-time)**

---

## Phase 1 — Project Setup + Backend Foundation

### Duration: 3 weeks

### Goal
Set up the complete project structure, tooling, and core backend skeleton. At the end, the backend starts, health check works, and all modules have empty shells ready to fill.

### Entry Criteria
- PRD.md, Architecture.md, Rules.md, Design.md are finalized
- Python 3.12+ installed
- Node.js 18+ installed
- Groq API key obtained (free tier)

### Deliverables

**Week 1 — Project Scaffolding**
- [ ] Initialize Git repository with `.gitignore`
- [ ] Create folder structure per Architecture.md
- [ ] Set up Python virtual environment
- [ ] Create `requirements.txt` with all backend dependencies (pinned versions)
- [ ] Create `config.py` — centralize all env vars
- [ ] Create `.env.example` with all required variables documented
- [ ] Create `backend/main.py` — FastAPI app factory with lifespan, CORS, middleware
- [ ] Create all empty `__init__.py` files

**Week 2 — Core Models + API Shell**
- [ ] Create `models/schemas.py` — all Pydantic models:
  - `ExperienceItem` with validators (_coerce_duration, _coerce_responsibilities)
  - `ProjectItem` (NEW)
  - `ParsedResume` with validators (_coerce_skills, _strip_name, _deduplicate_skills)
  - `AnalysisResult` with all fields including v2 additions
  - `FeedbackRequest`, `FeedbackResponse`
  - `HistoryResponse`, `AnalyticsResponse`
- [ ] Create router shells with placeholder responses:
  - `routers/health.py` → fully implemented
  - `routers/analyze.py` → accepts input, returns mock response
  - `routers/history.py` → returns empty list
  - `routers/feedback.py` → accepts input, returns success
  - `routers/analytics.py` → returns mock stats
- [ ] Create `security/auth.py` — API key middleware
- [ ] Create `security/rate_limiter.py` — slowapi setup

**Week 3 — Testing Foundation**
- [ ] Set up `pytest` + `pytest-asyncio` configuration
- [ ] Create `tests/test_api.py` — test health endpoint, test mock analyze
- [ ] Create `tests/test_schemas.py` — test all Pydantic validators
- [ ] Port `test_fairness.py` from prototype — adapt imports to new structure
- [ ] Verify all tests pass: `pytest -v`
- [ ] Create React frontend project: `npx create-vite@latest frontend --template react`
- [ ] Verify frontend runs: `npm run dev`

### Exit Criteria
- `python main.py` starts the backend on port 8000
- `/health` returns valid JSON
- `/docs` shows Swagger UI with all endpoint definitions
- `pytest` passes all tests
- `npm run dev` starts the React frontend on port 5173
- All files exist per Architecture.md folder structure (even if empty)

---

## Phase 2 — PDF Extraction Pipeline

### Duration: 2 weeks

### Goal
Implement the complete 3-tier PDF extraction pipeline. At the end, the system can extract text from any PDF — text-based, multi-column, or scanned.

### Entry Criteria
- Phase 1 complete (all exit criteria met)
- Tesseract OCR installed on dev machine
- Poppler installed on dev machine

### Deliverables

**Week 4**
- [ ] Implement `extraction/tier1_fitz.py` — PyMuPDF with blocks mode + spatial sorting
- [ ] Implement `extraction/tier2_plumber.py` — pdfplumber with table serialization
- [ ] Implement `extraction/tier3_ocr.py` — Tesseract with PSM 6, confidence logging, path resolution
- [ ] Implement `extraction/pipeline.py` — orchestrator:
  - Concurrent Tier 1+2 via `asyncio.gather` + `run_in_executor`
  - Two-column detection (15% threshold)
  - OCR fallback trigger (< 150 chars threshold)

**Week 5**
- [ ] Implement `extraction/docx_extractor.py` — python-docx text extraction
- [ ] Implement `security/file_validator.py` — magic byte validation, size check, page count limit
- [ ] Create `tests/test_extraction.py`:
  - Test each tier individually with sample PDFs
  - Test pipeline tier-switching logic
  - Test file validation (wrong type, too large, too many pages)
- [ ] Add 3 test PDF fixtures: `fixtures/simple_resume.pdf`, `fixtures/two_column.pdf`, `fixtures/scanned_resume.pdf`
- [ ] Wire extraction into `routers/analyze.py` — real extraction, mock parsing/scoring

### Exit Criteria
- Upload a PDF → get extracted text returned in response (as a debug field)
- All 3 tiers work independently
- Pipeline correctly chooses best tier
- Two-column detection works on test fixture
- `pytest tests/test_extraction.py` passes
- DOCX files accepted and text extracted

---

## Phase 3 — LLM Parsing + Validation Engine

### Duration: 2 weeks

### Goal
Implement the full LLM parsing pipeline: prompt engineering, retry logic, JSON sanitization, regex fallback, and source verification. At the end, a PDF upload returns a fully parsed, validated resume structure.

### Entry Criteria
- Phase 2 complete
- Groq API key configured and working

### Deliverables

**Week 6**
- [ ] Create `parsing/prompts.py` — all LLM prompts centralized:
  - System prompt for resume parsing (with security context, schema, table hint)
  - System prompt for contextual scoring (with security context)
  - User prompt templates with XML delimiters
- [ ] Implement `parsing/json_sanitizer.py` — strip fences, extract `{...}` block
- [ ] Implement `parsing/llm_parser.py`:
  - `parse_resume_with_groq()` — 3-attempt retry
  - Attempt 1: temp=0.1, standard prompt
  - Attempts 2–3: temp=0.0, corrective feedback appended
  - Schema validation via `ParsedResume.model_validate()`
  - Return `ParseResult` dataclass

**Week 7**
- [ ] Implement `parsing/regex_fallback.py` — deterministic fallback for all fields
- [ ] Implement `parsing/verifier.py` — cross-check fields against raw text:
  - Name verification
  - Skills verification (verified vs unverified)
  - Education verification (keyword match)
  - Experience verification (company + role lookup)
- [ ] Implement `security/sanitizer.py`:
  - Unicode control character stripping
  - Whitespace collapse
  - Injection pattern neutralization (9+ patterns)
- [ ] Create `security/injection_patterns.py` — all patterns as constants
- [ ] Wire parsing into `routers/analyze.py` — real extraction + real parsing, mock scoring
- [ ] Create `tests/test_parsing.py`:
  - Test JSON sanitizer with markdown fences
  - Test Pydantic validators with edge cases
  - Test regex fallback produces valid ParsedResume
  - Test verifier correctly identifies verified/unverified skills
- [ ] Create `tests/test_security.py`:
  - Test each injection pattern is filtered
  - Test unicode control characters are stripped
  - Test XML delimiters are in prompts

### Exit Criteria
- Upload a PDF → get fully parsed `ParsedResume` with `name`, `skills`, `experience`, `education`, `projects`, `certifications`
- Source verification tags show `verified` / `partial` / `unverified` per field
- If LLM fails 3 times, regex fallback produces valid output (never crashes)
- All security tests pass
- `pytest tests/test_parsing.py tests/test_security.py` passes

---

## Phase 4 — Scoring Engine

### Duration: 2 weeks

### Goal
Implement all three scoring components. At the end, a PDF upload returns a complete analysis with total score (0–100), all three sub-scores, matched/missing skills, and AI justification.

### Entry Criteria
- Phase 3 complete
- Parsing returns valid `ParsedResume`

### Deliverables

**Week 8**
- [ ] Implement `scoring/skill_normalization.py` — `normalize_string()` with regex replacements
- [ ] Implement `scoring/skill_aliases.py` — alias dictionary + reverse index
- [ ] Implement `scoring/skill_clusters.py` — 8 clusters + reverse index
- [ ] Implement `scoring/skill_match.py`:
  - `get_semantic_similarity()` — 3-tier pipeline (canonical → cluster → 0.0)
  - `compute_semantic_skill_score()` — proportional linear scale, no floor
- [ ] Implement `scoring/experience.py` — `compute_experience_longevity()` — bracket system
- [ ] Port fairness tests from prototype → `tests/test_fairness.py` — adapt to new module paths

**Week 9**
- [ ] Implement `scoring/contextual.py` — `_contextual_fit_score()`:
  - Security-hardened: sanitized inputs, XML delimiters, score clamping
  - Now includes project descriptions alongside responsibilities (v2 upgrade)
  - Floor: 10 pts, anomaly warning at >= 99
- [ ] Implement `scoring/aggregator.py`:
  - Sum three components
  - Clamp total to [0, 100]
  - Apply parallel execution: `asyncio.gather(skill+exp, contextual)`
- [ ] Wire scoring into `routers/analyze.py` — full pipeline: extract → parse → score → return
- [ ] Create `tests/test_skill_matching.py`:
  - Test normalization edge cases
  - Test all alias pairs
  - Test cluster matching
  - Test similarity function symmetry
- [ ] Create `tests/test_experience.py`:
  - Test all bracket boundaries
  - Test student floor protection
  - Test empty everything
- [ ] Verify all fairness tests still pass

### Exit Criteria
- Upload a PDF + JD → get `AnalysisResult` with:
  - `total_score` (0–100)
  - `semantic_skill_match` (0–40)
  - `experience_longevity` (0–35)
  - `context_alignment` (0–25)
  - `matched_skills`, `missing_skills`
  - `context_justification`
- All scoring is parallel (skill+exp concurrent with contextual LLM)
- `pytest` passes all tests (fairness + skill + experience + API)
- Full end-to-end flow works via Swagger UI

---

## Phase 5 — Database + Score Versioning

### Duration: 2 weeks

### Goal
Add data persistence. Every analysis is stored with its scoring configuration. History is queryable. Resume deduplication works.

### Entry Criteria
- Phase 4 complete
- Full analysis pipeline working end-to-end (stateless)

### Deliverables

**Week 10**
- [ ] Implement `models/db_models.py` — SQLAlchemy ORM models:
  - `ScoringConfig` — weights, model name, prompt version, is_active
  - `AnalysisRecord` — all result fields + FK to ScoringConfig
  - `RecruiterFeedback` — feedback_type, reason, FKs to analysis + config
  - `ResumeCache` — resume_hash, parsed_resume JSON, TTL
- [ ] Implement `db/database.py`:
  - Async engine factory (SQLite or PostgreSQL from `DATABASE_URL`)
  - Session factory with context manager
  - `create_tables()` for initial setup
- [ ] Set up Alembic:
  - `alembic init backend/db/migrations`
  - Configure `env.py` to read from `config.py`
  - Generate initial migration
  - Run migration

**Week 11**
- [ ] Implement `db/crud.py`:
  - `create_analysis()` — store AnalysisRecord
  - `get_analysis()` — by UUID
  - `list_analyses()` — paginated, filterable (date range, score range, name search)
  - `create_feedback()` — store RecruiterFeedback
  - `get_or_create_scoring_config()` — find active config or create new
  - `get_cached_resume()` — by SHA-256 hash
  - `cache_resume()` — store parsed resume
- [ ] Implement `services/analysis_service.py`:
  - Orchestrate: extract → check cache → parse (or use cache) → score → store → return
  - Resume dedup via SHA-256 hash
- [ ] Wire database into all routers:
  - `analyze.py` → stores result in DB
  - `history.py` → queries DB
  - `feedback.py` → stores feedback in DB
- [ ] Seed initial `ScoringConfig` on app startup (via lifespan hook)
- [ ] Create `tests/test_database.py`:
  - Test CRUD operations
  - Test resume cache hit/miss
  - Test config versioning
- [ ] Verify all existing tests still pass

### Exit Criteria
- Upload → analyze → result stored in SQLite database file
- GET `/api/v1/history` returns past analyses from DB
- GET `/api/v1/analyses/{id}` returns specific analysis
- Every analysis has `scoring_config_version` in response
- Re-uploading same PDF skips parsing (cache hit), only re-scores
- `ats_data.db` file appears in backend directory
- `pytest` passes all tests

---

## Phase 6 — Frontend Foundation + Upload Flow

### Duration: 3 weeks

### Goal
Build the React frontend with routing, layout, design system, and the complete upload → analyze → results flow. At the end, the system looks and feels professional.

### Entry Criteria
- Phase 5 complete
- Backend API fully functional (all endpoints return real data)
- Design.md finalized (colors, fonts, typography)

### Deliverables

**Week 12 — Design System + Layout**
- [ ] Set up CSS design system per Design.md:
  - `styles/variables.css` — all CSS custom properties
  - `styles/globals.css` — reset, base styles, scrollbar, selection
- [ ] Install dependencies: `react-router-dom`, `axios`, `recharts`, `lucide-react`, `react-hot-toast`
- [ ] Implement layout components:
  - `Sidebar.jsx` — navigation with icons + labels + active state
  - `Header.jsx` — page title + API status indicator
  - `PageWrapper.jsx` — consistent page padding + structure
- [ ] Set up React Router in `App.jsx`:
  - `/` → AnalyzePage
  - `/history` → HistoryPage
  - `/analysis/:id` → DetailPage
  - `/compare` → ComparePage
  - `/analytics` → AnalyticsPage
  - `*` → NotFoundPage
- [ ] Set up `api/client.js` — Axios instance with base URL + API key header

**Week 13 — Upload + Analyze Page**
- [ ] Implement `DropZone.jsx` — drag-and-drop with hover state, file type validation
- [ ] Implement `FileInfo.jsx` — selected file name + size display
- [ ] Implement `AnalyzeForm.jsx` — JD textarea + skills input + experience target + submit
- [ ] Implement `Loader.jsx` — multi-step progress (Extracting → Parsing → Scoring → Contextual)
- [ ] Implement `Toast.jsx` — error notifications with auto-dismiss
- [ ] Wire up `AnalyzePage.jsx`:
  - Form submission → `POST /api/v1/analyze`
  - Loading state during analysis
  - Error handling with specific messages
  - Smooth transition to results on success

**Week 14 — Results View**
- [ ] Implement `ScoreRing.jsx` — animated SVG circular score with color gradient
- [ ] Implement `ScoreBreakdown.jsx` — 3 horizontal progress bars (40/35/25)
- [ ] Implement `SkillTags.jsx` — matched (green) + missing (red) with icons
- [ ] Implement `VerifiedSkills.jsx` — verified (solid) vs unverified (dashed border) panel
- [ ] Implement `ExperienceTimeline.jsx` — vertical timeline with dots + company + role + duration
- [ ] Implement `ProjectCards.jsx` — project name + tech stack badges + description
- [ ] Implement `Justification.jsx` — AI contextual justification paragraph
- [ ] Implement `MetadataChips.jsx` — tier badge, processing time, config version, llm attempts
- [ ] Implement `ReviewBanner.jsx` — manual_review_recommended warning banner
- [ ] Implement JSON export button
- [ ] Assemble all components in results section of `AnalyzePage.jsx`

### Exit Criteria
- Navigate to `/` → see upload form
- Upload a PDF + enter JD → see loading animation → see full results
- Results show: score ring, breakdown bars, matched/missing skills, verified/unverified skills, experience timeline, projects, justification, metadata chips
- Review banner appears when `manual_review_recommended = true`
- JSON export downloads the full analysis
- Sidebar navigation works across all routes
- Design matches Design.md (colors, fonts, spacing)
- Responsive on desktop + laptop widths

---

## Phase 7 — History, Detail & Feedback UI

### Duration: 2 weeks

### Goal
Build the history page, analysis detail page, and recruiter feedback mechanism. At the end, all past analyses are accessible, and recruiters can rate accuracy.

### Entry Criteria
- Phase 6 complete
- Upload + results flow working in the browser

### Deliverables

**Week 15**
- [ ] Implement `HistoryTable.jsx` — sortable table with columns: candidate name, score, date, tier, config version
- [ ] Implement `HistoryFilters.jsx` — date range picker, score range slider, name search
- [ ] Assemble `HistoryPage.jsx` — table + filters + pagination
- [ ] Implement `DetailPage.jsx` — full analysis breakdown:
  - All score components with bars
  - Full parsed resume (skills, experience, education, projects, certs)
  - Field confidence badges per section
  - Extraction metadata
  - Config version used
  - Raw justification text

**Week 16**
- [ ] Implement `FeedbackBar.jsx` — 4 buttons: Accurate / Too High / Too Low / Inaccurate
  - Optional reason text input
  - Submit to `POST /api/v1/feedback`
  - Success confirmation toast
  - Disable after submission (prevent duplicates)
- [ ] Add FeedbackBar to `DetailPage.jsx` and `AnalyzePage.jsx` results section
- [ ] Wire feedback storage — verify it appears in DB
- [ ] Add "View Details" link from HistoryTable rows → DetailPage
- [ ] Add "Analyze Another" button on results → resets form

### Exit Criteria
- Navigate to `/history` → see list of all past analyses
- Filter by name, date, score range — table updates
- Click a row → navigate to `/analysis/:id` → see full detail
- FeedbackBar visible on detail page → submit feedback → success toast
- Feedback stored in database with correct analysis_id and config_id
- Navigate back to history → analysis still there

---

## Phase 8 — ONNX Embeddings + Confidence Weighting

### Duration: 2 weeks

### Goal
Add the ONNX embedding similarity layer (Stage 4 of skill matching) and implement confidence-weighted scoring. At the end, unknown skills get semantic matching, and verified skills count more than unverified ones.

### Entry Criteria
- Phase 7 complete
- Scoring engine working with 3-stage pipeline

### Deliverables

**Week 17**
- [ ] Download and export `all-MiniLM-L6-v2` model to ONNX format
- [ ] Store ONNX model file in `backend/models/` or `backend/assets/`
- [ ] Implement `scoring/embeddings.py`:
  - Load ONNX model via `onnxruntime.InferenceSession`
  - Tokenize input text (basic tokenizer or bundled tokenizer)
  - Generate 384-dim embedding vector
  - Cosine similarity function
  - `get_embedding_similarity(text_a, text_b) → float`
  - Lazy model loading (load on first call, cache session)
- [ ] Integrate into `scoring/skill_match.py`:
  - Stage 4: if stages 1–3 all return 0.0, call `get_embedding_similarity()`
  - If cosine > 0.75 → use as similarity score
  - If cosine <= 0.75 → 0.0

**Week 18**
- [ ] Implement confidence-weighted scoring in `scoring/skill_match.py`:
  - Accept `verified_skills` list as parameter
  - For each matched skill: if skill is in `verified_skills` → weight = 1.0, else → weight = 0.5
  - Adjust final score calculation to use weighted similarities
- [ ] Update `scoring/aggregator.py` to pass verified_skills through
- [ ] Create `tests/test_embeddings.py`:
  - Test ONNX model loads successfully
  - Test "Python" ≈ "Python programming" (high similarity)
  - Test "Python" ≠ "Cooking" (low similarity)
  - Test cosine threshold boundary
- [ ] Update `tests/test_skill_matching.py`:
  - Add tests for confidence weighting (verified vs unverified)
- [ ] Verify all fairness tests still pass (critical!)

### Exit Criteria
- Skill matching now handles unknown skills via embeddings
- "Natural Language Processing" ≈ "Text Mining" scores > 0.75
- Verified skills contribute full weight to score
- Unverified skills contribute half weight
- ONNX model loads in < 2 seconds, inference < 50ms per skill pair
- All fairness tests still pass
- `pytest` passes all tests

---

## Phase 9 — Analytics Dashboard + Comparison

### Duration: 2 weeks

### Goal
Build the analytics dashboard with aggregate stats and the candidate comparison view. At the end, recruiters can see trends and compare candidates side-by-side.

### Entry Criteria
- Phase 8 complete
- History + feedback data exists in database

### Deliverables

**Week 19**
- [ ] Implement `services/analytics_service.py`:
  - `get_summary_stats()` — total analyses, avg score, score distribution
  - `get_skill_gap_data()` — most commonly missing skills across all analyses
  - `get_tier_distribution()` — % of analyses using each extraction tier
  - `get_feedback_stats()` — % accurate, % too high, % too low, % inaccurate
  - `get_score_trend()` — avg score per week/month
- [ ] Implement `routers/analytics.py` — wire to service
- [ ] Implement analytics UI components:
  - `StatCard.jsx` — single metric with label + value + icon
  - `ScoreChart.jsx` — score distribution histogram (Recharts)
  - `SkillGapHeatmap.jsx` — most missing skills bar chart
  - `FeedbackChart.jsx` — feedback distribution pie chart
- [ ] Assemble `AnalyticsPage.jsx` — grid of stat cards + charts

**Week 20**
- [ ] Implement `routers/analyze.py` → add `GET /api/v1/compare?ids=uuid1,uuid2`
  - Returns 2–4 analyses with aligned field structure
- [ ] Implement `ComparePage.jsx`:
  - Side-by-side cards for each candidate
  - Radar chart overlay (Recharts) comparing skill/exp/context scores
  - Color-coded skill matrix: which candidate has which required skill
  - Score difference highlights
- [ ] Add "Compare" button on HistoryPage — select 2–4 analyses → navigate to ComparePage
- [ ] Create `tests/test_analytics.py`:
  - Test summary stats with seeded data
  - Test compare endpoint validation (min 2, max 4)

### Exit Criteria
- Navigate to `/analytics` → see stat cards, charts, feedback breakdown
- Charts render with real data from database
- Skill gap heatmap shows which skills are most commonly missing
- Select 2 analyses from history → compare → see side-by-side radar chart
- All tests pass

---

## Phase 10 — Polish, Testing & Documentation

### Duration: 2 weeks

### Goal
Final polish: dark/light theme toggle, PDF export, resume health check, comprehensive testing, and documentation. At the end, the system is demo-ready and interview-ready.

### Entry Criteria
- Phases 1–9 complete
- All features functional

### Deliverables

**Week 21**
- [ ] Implement dark/light theme toggle:
  - `useTheme.js` hook — reads/writes localStorage
  - CSS variables swap via `[data-theme="light"]` selector
  - Toggle button in sidebar
- [ ] Implement PDF report export:
  - HTML template for report layout
  - `html2pdf.js` to generate PDF client-side
  - Download button on DetailPage
- [ ] Implement resume health check (PREMIUM):
  - `POST /api/v1/health-check` — no JD required
  - Checks: text extractable, contact info found, sections present, ATS-readability score
  - Simple UI page to upload and see health report
- [ ] Responsive design audit — test on 1920px, 1366px, 768px
- [ ] Accessibility audit — keyboard navigation, focus states, ARIA labels

**Week 22**
- [ ] Comprehensive test suite review:
  - Ensure every scoring function has ≥ 3 tests
  - Ensure all alias pairs are tested
  - Ensure all injection patterns are tested
  - Add any missing edge case tests
- [ ] Performance audit:
  - Measure end-to-end analysis latency
  - Log P50 and P95 from 10 test runs
  - Optimize any bottlenecks found
- [ ] Documentation:
  - Update `README.md` with complete setup instructions
  - Add screenshots to README
  - Verify Swagger docs at `/docs` are complete
  - Update all doc files if any detail changed during development
- [ ] Final demo preparation:
  - 3 test resumes (strong candidate, weak candidate, scanned PDF)
  - 2 job descriptions
  - Run full demo flow and record any issues

### Exit Criteria
- Dark/light theme toggle works, persists across sessions
- PDF report downloads correctly
- Resume health check page works
- All tests pass: `pytest -v` (> 50 tests total)
- README.md has complete setup instructions + screenshots
- No known bugs in the demo flow
- System is ready for deployment phase

---

## Phase D — Deployment

### Duration: 2 weeks

### Goal
Containerize the application and prepare for production deployment. At the end, `docker compose up` runs the full system.

### Entry Criteria
- Phase 10 complete (all features + tests + docs)
- Docker Desktop installed

### Deliverables

**Week 23**
- [ ] Create `backend/Dockerfile`:
  - Multi-stage build
  - Base: `python:3.12-slim-bookworm`
  - System deps: `tesseract-ocr`, `poppler-utils`, `libgl1`
  - Copy requirements, install Python deps
  - Copy application code
  - Health check: `CMD curl -f http://localhost:8000/health`
  - Entry: `uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Create `frontend/Dockerfile`:
  - Build stage: `node:18-alpine`, `npm ci`, `npm run build`
  - Production stage: `nginx:alpine`, copy built files
  - Nginx config to serve SPA (all routes → index.html) + proxy `/api` to backend
- [ ] Create `docker-compose.yml`:
  - `backend` service: builds from `./backend`, port 8000, env_file
  - `frontend` service: builds from `./frontend`, port 3000
  - `db` service (optional): PostgreSQL 15 with volume
  - Network linking
- [ ] Create `.dockerignore` files for both backend and frontend
- [ ] Test: `docker compose up --build` — full stack starts

**Week 24**
- [ ] Configure PostgreSQL as production database:
  - Update `.env` with `DATABASE_URL=postgresql+asyncpg://...`
  - Run Alembic migrations against PostgreSQL
  - Verify all CRUD operations work
- [ ] Production hardening:
  - CORS restricted to frontend service URL
  - Rate limiting verified
  - Logging to stdout (Docker captures it)
  - Health check verified via Docker HEALTHCHECK
- [ ] Create `docker-compose.prod.yml` (separate from dev):
  - Environment-specific overrides
  - Resource limits
  - Restart policies
- [ ] Final end-to-end test on Docker:
  - Upload resume → analyze → view history → submit feedback → view analytics
  - Everything works in containers
- [ ] Tag release: `v2.0.0`

### Exit Criteria
- `docker compose up` starts backend + frontend + database
- Full demo flow works in Docker containers
- Database persists across container restarts (volume mount)
- Health check passes in Docker
- Image sizes are reasonable (< 2 GB total)
- Tagged release `v2.0.0` in Git

---

## Phase Progress Tracker

Copy this to track progress during development:

```
Phase  Status    Started      Completed    Notes
─────  ────────  ──────────   ──────────   ──────
  1    [ ]       —            —            Project setup
  2    [ ]       —            —            PDF extraction
  3    [ ]       —            —            LLM parsing
  4    [ ]       —            —            Scoring engine
  5    [ ]       —            —            Database
  6    [ ]       —            —            Frontend foundation
  7    [ ]       —            —            History + feedback UI
  8    [ ]       —            —            ONNX embeddings
  9    [ ]       —            —            Analytics + comparison
 10    [ ]       —            —            Polish + testing
  D    [ ]       —            —            Deployment
```
