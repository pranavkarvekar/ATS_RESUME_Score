# 📊 ATS Score Calculation — Complete Guide with Examples

> This document explains **exactly** how each score is calculated, step by step,
> using a real example from a resume submitted against a job description.

---

## The Big Formula (One Line)

```
Total Score = Semantic Skill Score  +  Experience Score  +  Context Score          
                    (0-40 pts)              (0-35 pts)       (0-25 pts)         = max 100 pts
                                                                              
```

It is NOT an average. It is a **direct sum** of three independent scores.

```python
# From main.py line 879
raw_total = semantic_skill_score + exp_longevity_score + ctx_alignment_score
total_score = round(min(max(raw_total, 0.0), 100.0), 2)
```

`min(..., 100.0)` makes sure the score never exceeds 100.
`max(..., 0.0)` makes sure the score never goes below 0.

---

## Real Example We Will Use Throughout

**Candidate:**    Rahul Sharma
**Resume Skills:** Python, Django, MongoDB, HTML, CSS, JavaScript, FastAPI,
                  Streamlit, Groq API, Git, LLMs, RAG, LangChain,
                  Hugging Face Transformers, Prompt Engineering,
                  Semantic Search, NLP, MySQL, C++, Java

**Work Experience:**
- Software Development Intern @ Ascent Cyber Solutions — 3 months

**Job Description (JD):**
"We are hiring a Python Backend Developer. Required skills: Python,
Django, REST APIs, PostgreSQL, Docker. Experience with cloud is a plus."

**Required Skills entered by user:** Python, Django, REST APIs, PostgreSQL, Docker

---

---

## SCORE 1 — Semantic Skill Match (0–40 pts)

### What does it measure?

How many of the **job's required skills** can be found in your resume.
Each required skill is compared against every skill on your resume.
The best match wins. All matches are averaged and scaled to 40 points.

---

### Step 1 — Normalize Every Skill String

Before comparing, all skills are cleaned up by this function:

```python
def normalize_string(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"[^a-z0-9]", "", lowered)
    # Removes ALL spaces, dashes, dots, slashes — keeps only letters/numbers
```

Examples:
```
"REST APIs"   →  "restapis"
"PostgreSQL"  →  "postgresql"
"LangChain"   →  "langchain"
"C++"         →  "c"
"React.js"    →  "reactjs"
"Node.js"     →  "nodejs"
```

This ensures "REST APIs", "REST-APIs", "rest apis" all become the same string for comparison.

---

### Step 2 — Compare Each Required Skill Against Resume

The function `get_semantic_similarity(text_a, text_b)` returns a score from 0.0 to 1.0.
It checks three matching levels in order:

```
Level 1 — Exact match          → returns 1.0
Level 2 — Substring match      → returns 0.95
Level 3 — Same concept cluster → returns 0.9
Level 4 — No match             → returns 0.0
```

**Level 1 — Exact Match (score = 1.0)**
After normalization, if both strings are identical:
```
"Python" normalized → "python"
"python" normalized → "python"
"python" == "python"  →  score = 1.0  ✅ PERFECT MATCH
```

**Level 2 — Substring Match (score = 0.95)**
If one string is found inside the other:
```
"REST" normalized   → "rest"
"REST APIs" normalized → "restapis"
"rest" is inside "restapis"  →  score = 0.95  ✅ PARTIAL MATCH
```

**Level 3 — Same Semantic Cluster (score = 0.9)**
Some skills mean the same concept but have different names.
The code has a built-in dictionary called `_SEMANTIC_CLUSTERS`:

```python
_SEMANTIC_CLUSTERS = {
    "backenddev": frozenset({
        "fastapi", "django", "flask", "nodejs", "python",
        "restapi", "restapis", "java", "golang", ...
    }),
    "database": frozenset({
        "postgresql", "postgres", "mysql", "mongodb",
        "redis", "sqlite", "dynamodb", ...
    }),
    "machinelearning": frozenset({
        "machinelearning", "ml", "ai", "nlp", "llm", "llms",
        "pytorch", "tensorflow", "sklearn", ...
    }),
    "frontend": frozenset({
        "reactjs", "react", "html", "css", "javascript",
        "typescript", "vuejs", "angular", ...
    }),
    "clouddevops": frozenset({
        "docker", "aws", "gcp", "azure", "kubernetes",
        "terraform", "jenkins", "linux", ...
    }),
    ...
}
```

Example:
```
"Django"     → cluster: "backenddev"
"REST APIs"  → cluster: "backenddev"
Same cluster → score = 0.9  ✅ CONCEPT MATCH

"PostgreSQL" → cluster: "database"
"MySQL"      → cluster: "database"
Same cluster → score = 0.9  ✅ CONCEPT MATCH

"Docker"     → cluster: "clouddevops"
"Python"     → cluster: "backenddev"
Different clusters → score = 0.0  ❌ NO MATCH
```

**Level 4 — No Match (score = 0.0)**
```
"Docker"  vs  "NLP"  →  different clusters, no substring  →  score = 0.0
```

---

### Step 3 — For Each Required Skill, Find the BEST Match

For every required skill, the code loops through ALL your resume skills
and picks the highest similarity score found:

```python
for req_skill in required_skills:       # loop required skills
    best_sim = 0.0
    for res_skill in resume_skills:     # loop ALL resume skills
        sim = get_semantic_similarity(req_skill, res_skill)
        if sim > best_sim:
            best_sim = sim              # keep the highest score
        if best_sim >= 1.0:
            break                       # perfect match, stop early
```

---

### Step 4 — Work Through Our Example

Required skills: **Python, Django, REST APIs, PostgreSQL, Docker**

Resume skills: Python, Django, MongoDB, HTML, CSS, JavaScript, FastAPI,
               Streamlit, Groq API, Git, LLMs, RAG, LangChain,
               Hugging Face Transformers, Prompt Engineering,
               Semantic Search, NLP, MySQL, C++, Java

#### Required Skill 1: "Python"

Compare "python" against every resume skill:
```
"python" vs "python"     → exact match → 1.0  ← BEST
"python" vs "django"     → no match    → 0.0
... (stops early because we already found 1.0)
```
best_sim for Python = **1.0** → counted as MATCHED ✅

#### Required Skill 2: "Django"

```
"django" vs "python"     → same cluster (backenddev) → 0.9
"django" vs "django"     → exact match               → 1.0  ← BEST
```
best_sim for Django = **1.0** → counted as MATCHED ✅

#### Required Skill 3: "REST APIs"

Normalized: "restapis"
```
"restapis" vs "python"       → 0.0
"restapis" vs "django"       → 0.0
"restapis" vs "mongodb"      → 0.0
"restapis" vs "fastapi"      → "restapi" is NOT inside "fastapi" → 0.0
                               BUT wait — both are "backenddev" cluster → 0.9
"restapis" vs "javascript"   → 0.0
...
```
Best match in resume = **0.9** (via backenddev cluster through FastAPI) → MATCHED ✅

#### Required Skill 4: "PostgreSQL"

Normalized: "postgresql"
```
"postgresql" vs "python"     → 0.0
"postgresql" vs "django"     → 0.0
"postgresql" vs "mongodb"    → same cluster (database) → 0.9  ← BEST
"postgresql" vs "mysql"      → same cluster (database) → 0.9
"postgresql" vs "fastapi"    → 0.0
...
```
Best match = **0.9** (MongoDB and MySQL are both in "database" cluster) → MATCHED ✅

#### Required Skill 5: "Docker"

Normalized: "docker"
```
"docker" vs "python"     → 0.0
"docker" vs "django"     → 0.0
"docker" vs "mongodb"    → 0.0
"docker" vs "html"       → 0.0
"docker" vs "git"        → 0.0
"docker" vs "llms"       → 0.0
"docker" vs "mysql"      → 0.0
... (no resume skill is Docker or in clouddevops cluster)
```
Best match = **0.0** → counted as MISSING ❌

---

### Step 5 — Calculate the Score

Collect all best_sim values:
```
Python      → 1.0
Django      → 1.0
REST APIs   → 0.9
PostgreSQL  → 0.9
Docker      → 0.0
             ─────
Total sim   = 3.8
```

```python
raw_ratio = total_similarity / number_of_required_skills
          = 3.8 / 5
          = 0.76

final_score = raw_ratio × MAX_PTS
            = 0.76 × 40
            = 30.4 pts
```

**Semantic Skill Score = 30.4 / 40**

Skills matched: Python, Django, REST APIs, PostgreSQL
Skills missing: Docker

---

---

## SCORE 2 — Experience Longevity (0–35 pts)

### What does it measure?

Total months of professional work experience across ALL jobs in the resume.
The score is NOT calculated linearly — it uses a BRACKET system (like tax brackets).

---

### Step 1 — Add Up All Months

```python
total_months = sum(max(item.duration_months, 0) for item in experience)
```

From our example:
- Ascent Cyber Solutions Intern: 3 months

```
total_months = 3
```

---

### Step 2 — Look Up the Bracket

```python
if total_months == 0:
    bracket_pct = 0.60  # (if has skills/projects)
    bracket_pct = 0.40  # (if truly empty resume)

elif total_months <= 11:
    bracket_pct = 0.75  # 1 to 11 months

elif total_months <= 35:
    bracket_pct = 0.90  # 12 to 35 months

else:
    bracket_pct = 1.00  # 36 months or more
```

**Bracket table — simple view:**

```
0 months (has skills)   →  60% of 35  =  21.00 pts  (student with no job yet)
0 months (no skills)    →  40% of 35  =  14.00 pts  (empty resume)
1 to 11 months          →  75% of 35  =  26.25 pts  (intern/fresher)
12 to 35 months         →  90% of 35  =  31.50 pts  (junior developer)
36+ months              → 100% of 35  =  35.00 pts  (experienced developer)
```

---

### Step 3 — Calculate Score

```python
score = bracket_pct × MAX_PTS
      = 0.75 × 35
      = 26.25 pts
```

**Experience Score = 26.25 / 35**

### Why brackets and not a straight line?

If it were a straight line: 3 months / 36 months target = 8.3% → only 2.9 pts out of 35.
That would massively penalize students who literally CANNOT have 36 months of experience
(they're still in college!). The bracket system protects fresh candidates by giving them
75% of the experience score for just having any internship at all.

---

---

## SCORE 3 — Context Alignment (0–25 pts)

### What does it measure?

This score answers a different question than the skill score.
Skill score asks: "Do you HAVE the skills?"
Context score asks: "Does your EXPERIENCE STORY match this job?"

For example, you may have Python on your resume. But did you USE Python
for backend APIs (what the job wants), or did you use Python for data analysis
(not what the job wants)? The skill score cannot tell the difference.
Only the AI reading the actual job description + your responsibilities can tell.

---

### Step 1 — Collect All Responsibilities from Resume

```python
all_responsibilities = []
for exp in parsed_resume.experience:
    all_responsibilities.extend(exp.responsibilities)
```

From our example:
```
- Developed a web-based ATM Electronic Journal Parser
- Designed Regex-based parsing engine for transaction details
- Implemented rule-based transaction classification module
- Developed interactive analytics dashboard with CSV export
```

---

### Step 2 — Build the Prompt for the AI

```python
bullet_block = "\n".join(f"- {r}" for r in responsibilities[:50])

prompt = f"""
Job Description:
{job_description[:3000]}

Candidate Responsibilities:
{bullet_block}

On a scale of 0-100, how well does the candidate's experience align
with the job description?

Return ONLY JSON: {{"score": <integer 0-100>, "justification": "<paragraph>"}}
"""
```

The actual prompt sent to the AI looks like:

```
Job Description:
We are hiring a Python Backend Developer. Required skills: Python,
Django, REST APIs, PostgreSQL, Docker. Experience with cloud is a plus.

Candidate Responsibilities:
- Developed a web-based ATM Electronic Journal Parser using Python, Django, MongoDB
- Designed Regex-based parsing engine for transaction details
- Implemented rule-based transaction classification module
- Developed interactive analytics dashboard with CSV export

On a scale of 0-100, how well does the candidate's experience align
with the job description?
Return ONLY JSON: {"score": <integer 0-100>, "justification": "<paragraph>"}
```

---

### Step 3 — AI Evaluates and Returns Score

The AI (LLaMA 3.3 70B) reads both texts like a human recruiter would.
It thinks about things like:
- Did the candidate build backend systems? (Yes — Django, REST-like APIs)
- Did they work with databases? (Yes — MongoDB, but not PostgreSQL)
- Do their responsibilities match the job role? (Mostly yes)
- Any gaps? (No Docker, no cloud, no PostgreSQL specifically)

The AI might return:
```json
{
  "score": 68,
  "justification": "The candidate has solid Python/Django backend experience
  demonstrated through a real-world ATM parser project. They show competence
  in database-backed web development. However, no PostgreSQL, Docker, or
  REST API experience is explicitly shown. The experience is relevant but
  not a complete match for all job requirements."
}
```

---

### Step 4 — Scale the Score to 0–25

```python
raw_score = 68        # AI gave 68 out of 100
floor_pts = 25 × 0.40 = 10.0   # minimum 10 pts always

normalised = (raw_score / 100) × 25
           = (68 / 100) × 25
           = 0.68 × 25
           = 17.0 pts

final = max(normalised, floor_pts)
      = max(17.0, 10.0)
      = 17.0 pts
```

**Context Alignment Score = 17.0 / 25**

The `floor_pts = 10` means: even if the AI gives 0, you still get 10 pts minimum.
This protects candidates when the job description is vague or too short.

---

---

## FINAL TOTAL — Adding All Three Scores

```
Semantic Skill Score  =  30.4  / 40
Experience Score      =  26.25 / 35
Context Score         =  17.0  / 25
                         ─────────
Raw Total             =  73.65 / 100
```

```python
raw_total = 30.4 + 26.25 + 17.0 = 73.65
total_score = round(min(max(73.65, 0.0), 100.0), 2)
            = 73.65
```

**Final ATS Score = 73.65 / 100**

---

---

## Comparison — Different Candidate Profiles

This shows how different people score on the same job:

### Profile A — Fresh Graduate (No Experience, Strong Skills)

Resume skills: Python, Django, FastAPI, PostgreSQL, Docker
Experience: 0 months, but has personal projects

```
Required skills: Python, Django, REST APIs, PostgreSQL, Docker

Skill Score:
  Python      → 1.0
  Django      → 1.0
  REST APIs   → 0.9  (FastAPI in same cluster)
  PostgreSQL  → 1.0
  Docker      → 1.0
  Total = 4.9 / 5 = 0.98 ratio
  Score = 0.98 × 40 = 39.2 pts

Experience Score:
  0 months + has skills → 60% × 35 = 21.0 pts

Context Score (AI rates projects as relevant):
  AI gives 55 → (55/100) × 25 = 13.75 pts

Total = 39.2 + 21.0 + 13.75 = 73.95 / 100
```

### Profile B — Senior Developer (3 Years, Partial Skill Match)

Resume skills: Python, Flask, MySQL, Linux, AWS
Experience: 36 months

```
Required skills: Python, Django, REST APIs, PostgreSQL, Docker

Skill Score:
  Python      → 1.0  (exact)
  Django      → 0.9  (Flask in same backenddev cluster)
  REST APIs   → 0.9  (Flask/Python in backenddev cluster)
  PostgreSQL  → 0.9  (MySQL in database cluster)
  Docker      → 0.0  (no Docker/cloud skill in resume)
  Total = 3.7 / 5 = 0.74 ratio
  Score = 0.74 × 40 = 29.6 pts

Experience Score:
  36+ months → 100% × 35 = 35.0 pts

Context Score (AI sees deep backend experience):
  AI gives 78 → (78/100) × 25 = 19.5 pts

Total = 29.6 + 35.0 + 19.5 = 84.1 / 100
```

### Profile C — Wrong Field (Data Scientist Applying for Backend Role)

Resume skills: Python, TensorFlow, Pandas, Jupyter, R, Matplotlib
Experience: 18 months

```
Required skills: Python, Django, REST APIs, PostgreSQL, Docker

Skill Score:
  Python      → 1.0  (exact)
  Django      → 0.0  (no backend skills)
  REST APIs   → 0.0  (no backend skills)
  PostgreSQL  → 0.0  (no database skills in resume)
  Docker      → 0.0  (no cloud/devops skills)
  Total = 1.0 / 5 = 0.20 ratio
  Score = 0.20 × 40 = 8.0 pts

Experience Score:
  18 months → 90% × 35 = 31.5 pts

Context Score (AI sees mismatched domain):
  AI gives 25 → (25/100) × 25 = 6.25 pts
  Floor kicks in → max(6.25, 10) = 10.0 pts

Total = 8.0 + 31.5 + 10.0 = 49.5 / 100
```

---

---

## Why This is NOT an Average

Many systems calculate score as: `(A + B + C) / 3`

This system calculates: `A + B + C` where A+B+C max = 100

The difference:
- Average spreads marks equally across all 3 areas (33.3 each)
- This system assigns different WEIGHTS to each area:
  - Skills = 40% weight → most important (job match is primary)
  - Experience = 35% weight → second most important (depth of knowledge)
  - Context = 25% weight → least weight (supporting evidence)

```
Weight Distribution:
Skills     ████████████████████████████████████████  40%
Experience ███████████████████████████████████       35%
Context    █████████████████████████                 25%
```

This design choice means: A highly skilled candidate with less experience
will naturally score better than a long-experienced candidate with wrong skills,
which is the correct behavior for modern tech hiring.

---

---

## Score Interpretation Guide

| Score Range | Interpretation |
|---|---|
| 85 – 100 | Excellent match — strong candidate, recommend interview |
| 70 – 84  | Good match — candidate meets most requirements |
| 55 – 69  | Partial match — some gaps, may be worth discussing |
| 40 – 54  | Weak match — significant skill or experience gaps |
| Below 40 | Poor match — candidate profile does not align with role |

---

## Quick Reference Formula Card

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCORE 1 — Semantic Skills (0-40 pts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each required skill:
  - Exact match       → similarity = 1.0
  - Substring match   → similarity = 0.95
  - Same cluster      → similarity = 0.9
  - No match          → similarity = 0.0

ratio  = sum(all similarities) / count(required skills)
score  = ratio × 40

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCORE 2 — Experience (0-35 pts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
months = sum of all job durations

0 months + skills   → 60% × 35 = 21.00
0 months, no skills → 40% × 35 = 14.00
1-11 months         → 75% × 35 = 26.25
12-35 months        → 90% × 35 = 31.50
36+ months          →100% × 35 = 35.00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCORE 3 — Context (0-25 pts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI reads JD + your responsibilities → gives 0-100
score = (ai_score / 100) × 25
floor = 10 pts minimum always

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
total = skill_score + experience_score + context_score
final = clamp(total, 0, 100)
```
