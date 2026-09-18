# Design — ATS Resume Analyzer v2
## UI Design System: Colors, Typography, Components & Layout

> **Document Version**: 1.0  
> **Last Updated**: 2026-09-05  
> **Design Philosophy**: Professional, data-dense, dark-first. Built for recruiters who spend hours in the dashboard — it should feel calm, clear, and powerful.
> **Prerequisite Reading**: [PRD.md](file:///d:/ATS_Resume_score/docs/PRD.md) (Feature E — Dashboard & UI)

---

## 1. Design Principles

| Principle | What It Means | How We Apply It |
|---|---|---|
| **Data-Dense, Not Cluttered** | Show a lot of information without overwhelming | Cards, sections, collapsible panels. Never one-metric-per-page. |
| **Scannable** | A recruiter should understand the score in 2 seconds | Large score ring, color-coded skill tags, clear hierarchy. |
| **Professional** | Looks like a real SaaS tool, not a hackathon demo | Consistent spacing, refined colors, proper typography. |
| **Dark-First** | Dark theme is default. Light theme available. | Easier on eyes during long screening sessions. |
| **Informative Errors** | Never show generic "Something went wrong" | Specific: "PDF is scanned. OCR extraction used — accuracy may be lower." |
| **Micro-Animations** | Subtle motion adds perceived quality | Score ring animates, bars slide, toasts fade. Never distracting. |

---

## 2. Color Palette

### 2.1 Dark Theme (Default)

```css
:root[data-theme="dark"] {
  /* ── Backgrounds ────────────────────────────────── */
  --bg-primary:         #0B0F19;     /* Main page background — deep navy black */
  --bg-secondary:       #111827;     /* Card/panel background — slightly lighter */
  --bg-tertiary:        #1F2937;     /* Nested elements, hover states */
  --bg-elevated:        #1a2332;     /* Modals, dropdowns, popovers */
  --bg-glass:           rgba(17, 24, 39, 0.7);  /* Glassmorphism panels */

  /* ── Borders ────────────────────────────────────── */
  --border-primary:     #1F2937;     /* Default borders */
  --border-secondary:   #374151;     /* Emphasized borders */
  --border-accent:      #3B82F6;     /* Active/focus border — blue */

  /* ── Text ───────────────────────────────────────── */
  --text-primary:       #F9FAFB;     /* Main text — near white */
  --text-secondary:     #9CA3AF;     /* Descriptions, metadata — gray */
  --text-tertiary:      #6B7280;     /* Disabled, placeholder — dim gray */
  --text-inverse:       #111827;     /* Text on light backgrounds */

  /* ── Brand / Accent ─────────────────────────────── */
  --accent-primary:     #3B82F6;     /* Blue — primary actions, links */
  --accent-primary-hover: #2563EB;   /* Darker blue on hover */
  --accent-secondary:   #8B5CF6;     /* Purple — secondary accent */
  --accent-glow:        rgba(59, 130, 246, 0.15); /* Subtle blue glow */

  /* ── Semantic Colors ────────────────────────────── */
  --color-success:      #10B981;     /* Green — matched skills, verified, pass */
  --color-success-bg:   rgba(16, 185, 129, 0.10);
  --color-warning:      #F59E0B;     /* Amber — unverified, caution */
  --color-warning-bg:   rgba(245, 158, 11, 0.10);
  --color-error:        #EF4444;     /* Red — missing skills, errors, fail */
  --color-error-bg:     rgba(239, 68, 68, 0.10);
  --color-info:         #3B82F6;     /* Blue — informational */
  --color-info-bg:      rgba(59, 130, 246, 0.10);

  /* ── Score Ring Gradient ────────────────────────── */
  --score-low:          #EF4444;     /* 0–39: Red */
  --score-medium:       #F59E0B;     /* 40–69: Amber */
  --score-high:         #10B981;     /* 70–89: Green */
  --score-excellent:    #3B82F6;     /* 90–100: Blue */

  /* ── Component-Specific ─────────────────────────── */
  --sidebar-bg:         #0D1117;     /* Slightly different from page bg */
  --sidebar-active:     rgba(59, 130, 246, 0.12);
  --sidebar-hover:      rgba(255, 255, 255, 0.04);
  --table-row-hover:    rgba(255, 255, 255, 0.03);
  --table-row-stripe:   rgba(255, 255, 255, 0.02);
  --input-bg:           #1F2937;
  --input-border:       #374151;
  --input-focus-border: #3B82F6;

  /* ── Shadows ────────────────────────────────────── */
  --shadow-sm:          0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md:          0 4px 6px rgba(0, 0, 0, 0.4);
  --shadow-lg:          0 10px 25px rgba(0, 0, 0, 0.5);
  --shadow-glow:        0 0 20px rgba(59, 130, 246, 0.15);
}
```

### 2.2 Light Theme

```css
:root[data-theme="light"] {
  --bg-primary:         #F9FAFB;
  --bg-secondary:       #FFFFFF;
  --bg-tertiary:        #F3F4F6;
  --bg-elevated:        #FFFFFF;
  --bg-glass:           rgba(255, 255, 255, 0.8);

  --border-primary:     #E5E7EB;
  --border-secondary:   #D1D5DB;
  --border-accent:      #3B82F6;

  --text-primary:       #111827;
  --text-secondary:     #6B7280;
  --text-tertiary:      #9CA3AF;
  --text-inverse:       #F9FAFB;

  --accent-primary:     #2563EB;
  --accent-primary-hover: #1D4ED8;
  --accent-secondary:   #7C3AED;
  --accent-glow:        rgba(37, 99, 235, 0.10);

  --color-success:      #059669;
  --color-success-bg:   rgba(5, 150, 105, 0.08);
  --color-warning:      #D97706;
  --color-warning-bg:   rgba(217, 119, 6, 0.08);
  --color-error:        #DC2626;
  --color-error-bg:     rgba(220, 38, 38, 0.08);
  --color-info:         #2563EB;
  --color-info-bg:      rgba(37, 99, 235, 0.08);

  --sidebar-bg:         #FFFFFF;
  --sidebar-active:     rgba(37, 99, 235, 0.08);
  --sidebar-hover:      rgba(0, 0, 0, 0.03);
  --table-row-hover:    rgba(0, 0, 0, 0.02);
  --table-row-stripe:   rgba(0, 0, 0, 0.01);
  --input-bg:           #FFFFFF;
  --input-border:       #D1D5DB;
  --input-focus-border: #3B82F6;

  --shadow-sm:          0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md:          0 4px 6px rgba(0, 0, 0, 0.07);
  --shadow-lg:          0 10px 25px rgba(0, 0, 0, 0.10);
  --shadow-glow:        0 0 20px rgba(37, 99, 235, 0.08);
}
```

### 2.3 Color Usage Rules

| Color Variable | When to Use | When NOT to Use |
|---|---|---|
| `--color-success` | Matched skills, verified fields, pass status | Not for generic "good" text |
| `--color-warning` | Unverified skills, manual review, caution states | Not for errors |
| `--color-error` | Missing skills, failed extraction, error messages | Not for low scores (use `--score-low` instead) |
| `--accent-primary` | Buttons, links, active states, focus rings | Not for text (too bright on dark bg) |
| `--text-secondary` | Descriptions, timestamps, metadata labels | Not for headings or important data |

---

## 3. Typography

### 3.1 Font Stack

```css
/* Import in index.html or globals.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --font-sans:    'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono:    'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}
```

| Font | Usage | Why |
|---|---|---|
| **Inter** | All body text, headings, labels, buttons | Clean, highly legible, great at small sizes, free |
| **JetBrains Mono** | Scores, code, metadata values, config versions | Monospaced digits for clean number alignment |

### 3.2 Type Scale

```css
:root {
  /* ── Font Sizes ─────────────────────────────── */
  --text-xs:      0.75rem;    /* 12px — tiny metadata, timestamps */
  --text-sm:      0.875rem;   /* 14px — secondary text, table cells */
  --text-base:    1rem;       /* 16px — body text, inputs */
  --text-lg:      1.125rem;   /* 18px — card titles */
  --text-xl:      1.25rem;    /* 20px — section headings */
  --text-2xl:     1.5rem;     /* 24px — page titles */
  --text-3xl:     1.875rem;   /* 30px — large headings */
  --text-4xl:     2.25rem;    /* 36px — hero numbers */
  --text-score:   3.5rem;     /* 56px — main score number inside ring */

  /* ── Font Weights ───────────────────────────── */
  --font-normal:  400;
  --font-medium:  500;
  --font-semibold: 600;
  --font-bold:    700;

  /* ── Line Heights ───────────────────────────── */
  --leading-tight:   1.25;
  --leading-normal:  1.5;
  --leading-relaxed: 1.625;

  /* ── Letter Spacing ─────────────────────────── */
  --tracking-tight:  -0.025em;
  --tracking-normal: 0em;
  --tracking-wide:   0.025em;
  --tracking-wider:  0.05em;
}
```

### 3.3 Typography Hierarchy

| Element | Font | Size | Weight | Color | Tracking |
|---|---|---|---|---|---|
| **Page Title** | Inter | `--text-2xl` (24px) | 700 (bold) | `--text-primary` | `--tracking-tight` |
| **Section Heading** | Inter | `--text-xl` (20px) | 600 (semibold) | `--text-primary` | `--tracking-tight` |
| **Card Title** | Inter | `--text-lg` (18px) | 600 (semibold) | `--text-primary` | normal |
| **Body Text** | Inter | `--text-base` (16px) | 400 (normal) | `--text-primary` | normal |
| **Secondary Text** | Inter | `--text-sm` (14px) | 400 (normal) | `--text-secondary` | normal |
| **Label** | Inter | `--text-sm` (14px) | 500 (medium) | `--text-secondary` | `--tracking-wide` |
| **Metadata** | JetBrains Mono | `--text-xs` (12px) | 400 | `--text-tertiary` | `--tracking-wider` |
| **Score Number** | JetBrains Mono | `--text-score` (56px) | 700 (bold) | Dynamic (by score range) | `--tracking-tight` |
| **Sub-Score** | JetBrains Mono | `--text-xl` (20px) | 600 (semibold) | `--text-primary` | normal |
| **Button** | Inter | `--text-sm` (14px) | 600 (semibold) | white / `--text-primary` | `--tracking-wide` |
| **Input Text** | Inter | `--text-base` (16px) | 400 | `--text-primary` | normal |
| **Placeholder** | Inter | `--text-base` (16px) | 400 | `--text-tertiary` | normal |
| **Table Header** | Inter | `--text-xs` (12px) | 600 (semibold) | `--text-secondary` | `--tracking-wider` |
| **Table Cell** | Inter | `--text-sm` (14px) | 400 | `--text-primary` | normal |
| **Tag/Badge** | Inter | `--text-xs` (12px) | 500 (medium) | varies | `--tracking-wide` |
| **Toast Message** | Inter | `--text-sm` (14px) | 500 (medium) | `--text-primary` | normal |

---

## 4. Spacing System

```css
:root {
  --space-1:   0.25rem;   /* 4px */
  --space-2:   0.5rem;    /* 8px */
  --space-3:   0.75rem;   /* 12px */
  --space-4:   1rem;      /* 16px */
  --space-5:   1.25rem;   /* 20px */
  --space-6:   1.5rem;    /* 24px */
  --space-8:   2rem;      /* 32px */
  --space-10:  2.5rem;    /* 40px */
  --space-12:  3rem;      /* 48px */
  --space-16:  4rem;      /* 64px */

  /* ── Border Radius ──────────────────────────── */
  --radius-sm:    4px;
  --radius-md:    8px;
  --radius-lg:    12px;
  --radius-xl:    16px;
  --radius-full:  9999px;   /* Pill shape */
}
```

### Spacing Rules

| Context | Spacing |
|---|---|
| Between cards in a grid | `--space-6` (24px) |
| Inside a card (padding) | `--space-5` (20px) |
| Between sections on a page | `--space-8` (32px) |
| Between form fields | `--space-4` (16px) |
| Between a label and its input | `--space-2` (8px) |
| Sidebar padding | `--space-4` (16px) |
| Page padding | `--space-6` to `--space-8` |
| Between tag/badge items | `--space-2` (8px) |

---

## 5. Component Specifications

### 5.1 Sidebar Navigation

```
┌──────────────────────┐
│  🔍 ATS Analyzer     │  ← Logo/title area (--space-6 padding)
│                      │
│  ────────────────────│  ← Divider (--border-primary)
│                      │
│  📄  Analyze    ←────│  ← Active: bg = --sidebar-active, text = --accent-primary
│  📋  History         │  ← Inactive: text = --text-secondary
│  📊  Analytics       │  
│  ⚖️  Compare         │
│                      │
│  ────────────────────│
│                      │
│  🌙  Dark / Light    │  ← Theme toggle at bottom
│  ❤️  v2.0.0          │  ← Version badge
└──────────────────────┘

Width: 240px (desktop), collapsible to 64px (icon-only on tablet)
Background: --sidebar-bg
Border-right: 1px solid --border-primary
```

### 5.2 Score Ring

```
        ╭──────────╮
       ╱   72.5    ╲      ← Number: --font-mono, --text-score (56px)
      │   / 100     │     ← Denominator: --text-sm, --text-tertiary
       ╲            ╱
        ╰──────────╯      ← Ring: SVG circle, stroke-dashoffset animation
                           ← Ring color: dynamic by score range
                           ← Background ring: --border-primary (dim track)
```

**Score-to-color mapping**:
```css
.score-ring[data-range="low"]       { stroke: var(--score-low);       }  /* 0–39 */
.score-ring[data-range="medium"]    { stroke: var(--score-medium);    }  /* 40–69 */
.score-ring[data-range="high"]      { stroke: var(--score-high);      }  /* 70–89 */
.score-ring[data-range="excellent"] { stroke: var(--score-excellent);  }  /* 90–100 */
```

**Animation**: `stroke-dashoffset` transition over 1.6s with cubic-bezier easing.

### 5.3 Score Breakdown Bars

```
Semantic Skill Match        32.0 / 35
████████████████████░░░░░    80%
                             ← bar-bg: --bg-tertiary, bar-fill: --accent-primary

Experience Longevity        21.25 / 25
███████████████████░░░░░░    75%
                             ← bar-fill: --accent-secondary (purple)

Contextual AI Fit           14.25 / 40
██████████████░░░░░░░░░░░    57%
                             ← bar-fill: --color-info
```

**Bar dimensions**: Height 10px, border-radius `--radius-full`, width 100% of container.
**Label**: `--text-sm`, `--font-medium`, left-aligned.
**Value**: `--font-mono`, `--text-sm`, right-aligned.

### 5.4 Skill Tags

```
Matched Skills:
┌──────────┐  ┌──────────┐  ┌──────────┐
│ ✓ Python │  │ ✓ FastAPI │  │ ✓ React  │
└──────────┘  └──────────┘  └──────────┘
bg: --color-success-bg    text: --color-success    border: 1px solid --color-success

Missing Skills:
┌──────────────┐  ┌──────────┐
│ ✗ Docker     │  │ ✗ K8s    │
└──────────────┘  └──────────┘
bg: --color-error-bg      text: --color-error      border: 1px solid --color-error

Unverified Skills:
┌──────────────┐
│ ⚠ AWS       │
└──────────────┘
bg: --color-warning-bg    text: --color-warning    border: 1px dashed --color-warning
```

**Tag**: padding `--space-1` `--space-3`, border-radius `--radius-full`, font `--text-xs` `--font-medium`.

### 5.5 Experience Timeline

```
● ── Software Engineer at Acme Corp                    ← dot: 10px, --accent-primary
│    Duration: 24 months                               ← --font-mono, --text-xs
│    • Built REST APIs using Python and FastAPI         ← --text-sm
│    • Managed Kubernetes clusters on AWS               ← max 5 bullets
│    • Developed React frontends
│
● ── Intern at StartupXYZ                              ← dot: 10px, --accent-secondary
│    Duration: 6 months
│    • Assisted with backend development
│
○ ── Education: B.Tech CSE, SPPU 2025                  ← hollow dot for education
```

**Connector line**: 2px solid `--border-primary`, runs vertically between dots.
**Dot**: 10px circle, filled = experience, hollow = education.

### 5.6 Card Component

```
┌─────────────────────────────────────────────┐
│  Card Title                    Badge        │  ← padding: --space-5
│                                             │
│  Card content goes here...                  │  ← bg: --bg-secondary
│                                             │  ← border: 1px solid --border-primary
│                                             │  ← border-radius: --radius-lg
│                                             │  ← shadow: --shadow-sm
└─────────────────────────────────────────────┘
   ← hover: border → --border-secondary, shadow → --shadow-md
```

### 5.7 Button Styles

```css
/* Primary — main actions */
.btn-primary {
  background: var(--accent-primary);
  color: #ffffff;
  border: none;
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-md);
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-primary:hover {
  background: var(--accent-primary-hover);
  box-shadow: var(--shadow-glow);
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Secondary — cancel, back */
.btn-secondary {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-secondary);
  /* same padding/radius as primary */
}

/* Ghost — subtle actions */
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: none;
  /* hover: bg → --bg-tertiary */
}

/* Danger — destructive */
.btn-danger {
  background: var(--color-error);
  color: #ffffff;
}
```

### 5.8 Input Fields

```
Label Text                                    ← --text-sm, --font-medium, --text-secondary
┌──────────────────────────────────────────┐
│ Placeholder text                         │  ← bg: --input-bg
│                                          │  ← border: 1px solid --input-border
│                                          │  ← border-radius: --radius-md
└──────────────────────────────────────────┘  ← height: 40px (single line), auto (textarea)
                                              ← padding: --space-2 --space-3
   Focus: border → --input-focus-border
          box-shadow: 0 0 0 3px var(--accent-glow)
```

### 5.9 Table (History Page)

```
┌─────────────┬────────┬───────────┬──────┬─────────┐
│ Candidate ▼ │ Score  │ Date      │ Tier │ Config  │  ← header: --text-xs, --font-semibold
│             │        │           │      │         │     uppercase, --tracking-wider
├─────────────┼────────┼───────────┼──────┼─────────┤     bg: --bg-tertiary
│ Rahul S.    │  72.5  │ Sep 5, 26 │  T1  │  v1.0   │  ← row: --text-sm, hover: --table-row-hover
│ Priya M.    │  88.0  │ Sep 4, 26 │  T2  │  v1.0   │     stripe: --table-row-stripe (even rows)
│ Amit K.     │  45.2  │ Sep 3, 26 │  T1  │  v1.0   │
└─────────────┴────────┴───────────┴──────┴─────────┘
```

**Score cell**: Color-coded by range (low=red, medium=amber, high=green, excellent=blue).
**Tier badge**: Small pill badge with Tier 1 (blue), Tier 2 (purple), Tier 3 (amber).
**Row click**: Navigates to detail page.

### 5.10 Feedback Bar

```
Was this score accurate?

┌───────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐
│ ✓ Accurate│  │ ↑ Too High │  │ ↓ Too Low  │  │ ✗ Inaccurate│
└───────────┘  └────────────┘  └────────────┘  └─────────────┘
  green           amber            amber            red

→ Click → expand optional reason input → submit → disable + show "Thank you"
```

### 5.11 Toast Notifications

```
                               ┌──────────────────────────────────┐
                               │ ✓  Analysis complete (3.4s)     │  ← success toast
                               │    Score: 72.5 / 100             │     bg: --color-success-bg
                               └──────────────────────────────────┘     border-left: 3px --color-success

                               ┌──────────────────────────────────┐
                               │ ✗  File too large (12 MB)       │  ← error toast
                               │    Maximum file size is 10 MB    │     bg: --color-error-bg
                               └──────────────────────────────────┘     border-left: 3px --color-error
```

**Position**: Top-right. Stack vertically.
**Auto-dismiss**: 5 seconds for success, 7 seconds for errors.
**Manual dismiss**: Click × button.

### 5.12 Loading / Progress Stepper

```
Step 1           Step 2           Step 3           Step 4
  ●─────────────── ○─────────────── ○─────────────── ○
Extracting       Parsing          Scoring          Contextual

  Active step: ● pulsing blue, label --text-primary
  Pending step: ○ dim, --text-tertiary
  Done step: ✓ green checkmark, --color-success
```

**Pulse animation**: `box-shadow` pulse on active step dot, 1.5s cycle.

---

## 6. Page Layouts

### 6.1 Analyze Page (Main)

```
┌────────┬──────────────────────────────────────────────────────────┐
│        │                                                          │
│ SIDE   │  ┌─────────────────────────────────────────────────────┐ │
│ BAR    │  │              UPLOAD SECTION                         │ │
│        │  │  ┌────────────────────────────────────────────┐     │ │
│ 📄     │  │  │          Drop PDF here                     │     │ │
│ Analyze│  │  │          or click to browse                │     │ │
│        │  │  └────────────────────────────────────────────┘     │ │
│ 📋     │  │                                                     │ │
│ History│  │  Job Description:  [textarea ....................... ]│ │
│        │  │  Required Skills:  [text input .................... ]│ │
│ 📊     │  │  Exp. Target:      [number input ] months           │ │
│Analytics│ │                                                     │ │
│        │  │                         [ 🔍 Analyze Resume ]       │ │
│ ⚖️     │  └─────────────────────────────────────────────────────┘ │
│ Compare│                                                          │
│        │  ┌──── RESULTS (appears after analysis) ──────────────┐ │
│        │  │                                                     │ │
│        │  │  ┌──────────┐  ┌──────────────────────────────────┐│ │
│        │  │  │  SCORE   │  │ BREAKDOWN BARS                   ││ │
│        │  │  │  RING    │  │ Skill:  ██████████████░░  32/40  ││ │
│        │  │  │  72.5    │  │ Exp:    █████████████░░░  26/35  ││ │
│        │  │  │  /100    │  │ Ctx:    ██████████░░░░░░  14/25  ││ │
│        │  │  └──────────┘  └──────────────────────────────────┘│ │
│        │  │                                                     │ │
│        │  │  ┌──── SKILLS ────────────────────────────────────┐│ │
│        │  │  │ Matched: [✓ Python] [✓ FastAPI] [✓ React]      ││ │
│        │  │  │ Missing: [✗ Docker] [✗ K8s]                    ││ │
│        │  │  │ Unverified: [⚠ AWS]                            ││ │
│        │  │  └────────────────────────────────────────────────┘│ │
│        │  │                                                     │ │
│        │  │  ┌──── EXPERIENCE TIMELINE ───────────────────────┐│ │
│        │  │  │ ● Software Engineer at Acme Corp (24 mo)       ││ │
│        │  │  │ │  • Built REST APIs using FastAPI              ││ │
│        │  │  │ ● Intern at StartupXYZ (6 mo)                  ││ │
│        │  │  │ ○ B.Tech CSE, SPPU 2025                        ││ │
│        │  │  └────────────────────────────────────────────────┘│ │
│        │  │                                                     │ │
│        │  │  ┌──── PROJECTS ──────────────────────────────────┐│ │
│        │  │  │ [Card: ATS Analyzer | Python, FastAPI, Groq]   ││ │
│        │  │  │ [Card: SmartDoc | MERN, JWT, MongoDB]          ││ │
│        │  │  └────────────────────────────────────────────────┘│ │
│        │  │                                                     │ │
│        │  │  ┌──── AI JUSTIFICATION ──────────────────────────┐│ │
│        │  │  │ "The candidate shows strong backend..."        ││ │
│        │  │  └────────────────────────────────────────────────┘│ │
│        │  │                                                     │ │
│        │  │  ┌──── METADATA ──────────────────────────────────┐│ │
│        │  │  │ [Tier 1] [3.4s] [1 attempt] [Config v1.0]     ││ │
│        │  │  └────────────────────────────────────────────────┘│ │
│        │  │                                                     │ │
│        │  │  ┌──── FEEDBACK ──────────────────────────────────┐│ │
│        │  │  │ Was this accurate? [✓] [↑] [↓] [✗]            ││ │
│        │  │  └────────────────────────────────────────────────┘│ │
│        │  │                                                     │ │
│        │  │  [📥 Download JSON]  [📄 Download PDF Report]      │ │
│        │  └─────────────────────────────────────────────────────┘ │
└────────┴──────────────────────────────────────────────────────────┘
```

### 6.2 History Page

```
┌────────┬──────────────────────────────────────────────────────────┐
│ SIDE   │  History                                  [Search 🔍]   │
│ BAR    │                                                          │
│        │  Filters: [Date range ▼] [Score range ▼] [Name search]  │
│        │                                                          │
│        │  ┌──────────┬───────┬────────────┬──────┬────────┬────┐ │
│        │  │Candidate │ Score │ Date       │ Tier │Config  │ ⋮  │ │
│        │  ├──────────┼───────┼────────────┼──────┼────────┼────┤ │
│        │  │Rahul S.  │ 72.5  │ Sep 5 '26  │ T1   │ v1.0   │ →  │ │
│        │  │Priya M.  │ 88.0  │ Sep 4 '26  │ T2   │ v1.0   │ →  │ │
│        │  │Amit K.   │ 45.2  │ Sep 3 '26  │ T1   │ v1.0   │ →  │ │
│        │  └──────────┴───────┴────────────┴──────┴────────┴────┘ │
│        │                                                          │
│        │  Showing 1–20 of 156     [← Prev] [1] [2] [3] [Next →] │
│        │                                                          │
│        │  [☐ Select for comparison]        [⚖️ Compare Selected] │
└────────┴──────────────────────────────────────────────────────────┘
```

### 6.3 Analytics Page

```
┌────────┬──────────────────────────────────────────────────────────┐
│ SIDE   │  Analytics                                               │
│ BAR    │                                                          │
│        │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│        │  │  156    │ │  68.4   │ │  82%    │ │  71%    │      │
│        │  │ Total   │ │ Avg     │ │ LLM     │ │ Feedback│      │
│        │  │Analyses │ │ Score   │ │ Success │ │Accurate │      │
│        │  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│        │                                                          │
│        │  ┌──── Score Distribution ────┐ ┌──── Tier Usage ─────┐ │
│        │  │  ▓▓                        │ │                      │ │
│        │  │  ▓▓ ▓▓                     │ │  T1: ████████ 72%   │ │
│        │  │  ▓▓ ▓▓ ▓▓                  │ │  T2: ████ 20%      │ │
│        │  │  ▓▓ ▓▓ ▓▓ ▓▓               │ │  T3: ██ 8%        │ │
│        │  │  0-39 40-69 70-89 90+      │ │                      │ │
│        │  └────────────────────────────┘ └──────────────────────┘ │
│        │                                                          │
│        │  ┌──── Most Missing Skills ───────────────────────────┐ │
│        │  │  Docker       ████████████████ 67%                 │ │
│        │  │  Kubernetes   ████████████ 52%                     │ │
│        │  │  AWS          █████████ 41%                        │ │
│        │  │  GraphQL      ███████ 33%                          │ │
│        │  └────────────────────────────────────────────────────┘ │
│        │                                                          │
│        │  ┌──── Feedback Breakdown ────────────────────────────┐ │
│        │  │  ✓ Accurate:   71%  ████████████████               │ │
│        │  │  ↑ Too High:   12%  ████                           │ │
│        │  │  ↓ Too Low:     9%  ███                            │ │
│        │  │  ✗ Inaccurate:  8%  ██                             │ │
│        │  └────────────────────────────────────────────────────┘ │
└────────┴──────────────────────────────────────────────────────────┘
```

---

## 7. Animations & Transitions

```css
:root {
  /* ── Durations ──────────────────────────────── */
  --duration-fast:     0.15s;    /* Hover states, focus */
  --duration-normal:   0.25s;    /* Panel toggles, dropdowns */
  --duration-slow:     0.4s;     /* Page transitions */
  --duration-score:    1.6s;     /* Score ring animation */

  /* ── Easings ────────────────────────────────── */
  --ease-out:          cubic-bezier(0.33, 1, 0.68, 1);
  --ease-in-out:       cubic-bezier(0.65, 0, 0.35, 1);
  --ease-bounce:       cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-score:        cubic-bezier(0.16, 1, 0.3, 1);
}
```

| Element | Animation | Duration | Easing |
|---|---|---|---|
| Button hover | Background color | `--duration-fast` | `--ease-out` |
| Card hover | Border color + shadow | `--duration-fast` | `--ease-out` |
| Score ring | `stroke-dashoffset` from full to target | `--duration-score` | `--ease-score` |
| Score number | Counter from 0 to value | `--duration-score` | `--ease-score` |
| Breakdown bars | Width from 0% to target% | `--duration-score` | `--ease-score` |
| Progress stepper dot | `box-shadow` pulse | 1.5s | infinite ease-in-out |
| Toast enter | Slide in from right + fade | `--duration-normal` | `--ease-bounce` |
| Toast exit | Fade out | `--duration-fast` | `--ease-out` |
| Sidebar nav item | Background on hover | `--duration-fast` | `--ease-out` |
| Table row hover | Background | `--duration-fast` | `--ease-out` |
| Input focus | Border color + glow ring | `--duration-fast` | `--ease-out` |
| Modal open | Fade in + slight scale (0.95 → 1.0) | `--duration-normal` | `--ease-bounce` |
| Page route change | Fade | `--duration-slow` | `--ease-in-out` |

---

## 8. Responsive Breakpoints

```css
/* Desktop-first approach */
:root {
  --bp-desktop:  1920px;   /* Full width */
  --bp-laptop:   1366px;   /* Standard laptop */
  --bp-tablet:   768px;    /* Tablet / narrow browser */
}

/* Main content area */
.page-content {
  max-width: 1200px;       /* Content doesn't stretch on ultra-wide */
  margin: 0 auto;
}

/* Sidebar behavior */
@media (max-width: 768px) {
  .sidebar {
    width: 64px;           /* Collapse to icon-only */
  }
  .sidebar .nav-label {
    display: none;          /* Hide text labels */
  }
}
```

| Breakpoint | Sidebar | Content Grid | Cards |
|---|---|---|---|
| > 1366px | Full (240px) | 3-column grid | Side-by-side score + breakdown |
| 769px – 1366px | Full (240px) | 2-column grid | Stacked score then breakdown |
| ≤ 768px | Icon-only (64px) | 1-column | Full width |

---

## 9. Iconography

**Icon Library**: Lucide React (open source, consistent, tree-shakeable)

| Context | Icon Name | Usage |
|---|---|---|
| Analyze | `FileSearch` | Sidebar nav |
| History | `ClipboardList` | Sidebar nav |
| Analytics | `BarChart3` | Sidebar nav |
| Compare | `Scale` | Sidebar nav |
| Upload | `Upload` | Drop zone |
| Score | `Target` | Score section header |
| Skills | `Code2` | Skills section header |
| Experience | `Briefcase` | Experience section header |
| Projects | `FolderGit2` | Projects section header |
| Education | `GraduationCap` | Education tag |
| Verified | `ShieldCheck` | Verified skill |
| Unverified | `ShieldAlert` | Unverified skill |
| Warning | `AlertTriangle` | Review banner |
| Success | `CheckCircle` | Matched skill, toast |
| Error | `XCircle` | Missing skill, toast |
| Download | `Download` | Export buttons |
| Settings | `Settings` | Config info |
| Clock | `Clock` | Processing time |
| Layers | `Layers` | Extraction tier |
| Moon / Sun | `Moon` / `Sun` | Theme toggle |
| ChevronRight | `ChevronRight` | Table row navigation |
| Search | `Search` | Filter/search inputs |

---

## 10. Design Checklist (Per Component)

Before marking any component as "done", verify:

- [ ] Uses CSS custom properties — no hardcoded colors or sizes
- [ ] Has hover state
- [ ] Has focus state (keyboard accessible)
- [ ] Has disabled state (if applicable)
- [ ] Has loading state (if async)
- [ ] Has empty state (if data-dependent)
- [ ] Has error state (if can fail)
- [ ] Typography matches the hierarchy table
- [ ] Spacing matches the spacing system
- [ ] Works at 1920px, 1366px, and 768px widths
- [ ] Respects the current theme (dark/light)
- [ ] Animations use design token durations and easings
- [ ] Tooltips on non-obvious labels
