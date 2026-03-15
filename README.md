# DevResume AI

> An all-in-one AI-powered career platform for junior developers — from resume optimization to automated job hunting.

---

## What It Does

DevResume AI combines two tools into a single platform:

**1. Resume & Career Suite**
Upload your resume and get instant AI feedback, skill gap analysis, job description matching, and exportable templates (Harvard + Google Docs format). Practice for interviews with AI-generated skill assessments tailored to your tech stack.

**2. JobSniper** — Automated Job Pipeline
Scrapes Indeed daily, scores every listing against your profile (0.0–1.0), filters out irrelevant roles automatically, then generates a personalized cover letter for every job worth applying to — all without touching a job board manually.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x, Python 3.11+ |
| AI | Claude claude-sonnet-4-6 (Anthropic) |
| Scraping | Playwright (headless Chromium) |
| Database | SQLite (Django ORM + raw SQL for JobSniper) |
| Resume parsing | pdfplumber, python-docx |
| Frontend | Vanilla JS, CSS custom properties, dark theme |

---

## Getting Started

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- Playwright browsers installed

### Installation

```bash
git clone <repo-url>
cd ai_resume_analyzer

# Create and activate virtualenv
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Environment
cp .env.example .env
# Edit .env and add:  ANTHROPIC_API_KEY=sk-ant-...

# Database setup
cd resume_analyzer
python manage.py migrate

# Run
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000)

---

## User Flow

```
Register → Onboarding Wizard (8 steps) → Dashboard
                                              │
              ┌───────────────────────────────┤
              │                               │
         Resume Suite                    JobSniper
              │                               │
    Upload PDF/DOCX                   python manage.py snipe pipeline
    AI analysis + score               │
    Skill gap report                  ├─ Scrapes Indeed (up to 75 jobs)
    Export Harvard/Google             ├─ Scores each 0.0–1.0
    Job description match             ├─ Filters < 0.40 automatically
    Skill assessment quiz             ├─ Generates AI cover letters
    Company research tool             └─ Dashboard: Review → Apply / Skip
```

---

## JobSniper CLI

```bash
# Run the full pipeline end-to-end
python manage.py snipe pipeline

# Or step by step:
python manage.py snipe scrape          # Pull from Indeed
python manage.py snipe filter          # Score and rank new jobs
python manage.py snipe tailor          # Generate cover letters (Claude API)
python manage.py snipe tailor --job-id 42  # Regenerate one letter
python manage.py snipe stats           # Pipeline stats summary
python manage.py snipe reset           # Clear all data (with confirmation)
```

---

## Configuration

Edit `config.yaml` to personalize the pipeline:

```yaml
profile:
  name: "Your Name"
  target_titles:
    - "Frontend Developer"
    - "React Developer"
  must_have_skills:
    - "React"
    - "JavaScript"
  nice_to_have_skills:
    - "TypeScript"
    - "Node.js"
  exclude_keywords:
    - "Senior"
    - "Lead"
    - "10+ years"
  remote_preference: "remote"
  min_salary: 60000

search:
  indeed:
    enabled: true
    queries:
      - "React Developer remote"
      - "Frontend Developer remote"
    pages_per_query: 5
```

Place your plain-text resume at `data/resume.txt` for the best cover letter output.

---

## Scoring System

Every scraped job is scored 0.0–1.0 against your profile:

| Factor | Weight | Notes |
|---|---|---|
| Title match | 30% | Word-boundary matching against target titles |
| Must-have skills | 25% | All must appear in title + description |
| Nice-to-have skills | 15% | Partial credit, capped at 100% |
| Remote match | 15% | Hard check against location + description |
| No exclude keywords | 10% | Title match = instant 0.0 (hard reject) |
| Salary in range | 5% | Neutral (0.5) if not listed |

Jobs below **0.40** are filtered automatically. Jobs at **0.40+** are queued for cover letter generation.

---

## Cost

The goal is under **$5 to run 200+ applications** through the full pipeline.

| Service | Cost |
|---|---|
| Indeed scraping | Free (local Playwright) |
| SQLite database | Free |
| Django server | Free |
| Claude AI (cover letters) | ~$0.01–0.02 per letter |
| **200 cover letters** | **~$3 total** |

---

## Roadmap

- [x] Phase 1 — Indeed scraper, filter engine, cover letter generation, dashboard
- [ ] Phase 2 — LinkedIn scraper, Wellfound scraper
- [ ] Phase 3 — Duplicate detection across sources, CSV export, email digest

---

## Project Structure

```
ai_resume_analyzer/
├── config.yaml              # Search config, profile, scraping settings
├── data/
│   ├── resume.txt           # Your resume (plain text) for cover letter AI
│   └── jobsniper.db         # SQLite job pipeline database
├── db/
│   └── schema.sql           # JobSniper table definitions
└── resume_analyzer/         # Django project root
    ├── resumes/             # Resume upload, AI analysis, builder, exporter
    ├── assessments/         # Skill assessment engine
    ├── companies/           # Company research tracker
    ├── onboarding/          # Registration, 8-step onboarding wizard
    └── jobsniper/           # Job pipeline
        ├── scrapers/
        │   ├── base.py      # Shared scraper utilities (delays, CAPTCHA)
        │   └── indeed.py    # Indeed scraper (2-pass: cards → descriptions)
        ├── services/
        │   ├── store.py     # Raw SQLite — jobs, cover letters, app log
        │   ├── filter.py    # Scoring engine
        │   └── tailor.py    # Claude API cover letter generation
        └── management/commands/snipe.py  # CLI
```

---

## Important Notes

- **No auto-apply.** The pipeline stops at generating cover letters. You review each job and click Apply yourself.
- **Scraping is conservative by default** — 4s between pages, 2s between requests, max 75 jobs per run — to avoid rate limits.
- **CAPTCHA detection** stops the scraper gracefully if Indeed blocks the session.
- **Cover letter retries** — 3 attempts with 2s / 4s / 8s exponential backoff on API failures.

---

## License

MIT
