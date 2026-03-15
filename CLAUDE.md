# DevResume AI + JobSniper — Developer Guide

## Project Overview
An all-in-one platform for junior developers:
1. **DevResume AI** — Resume analysis, skill assessment, company tracker, resume builder
2. **JobSniper** — Semi-automated job application pipeline with scraping, scoring, and AI cover letter generation

## Running the App
```bash
cd resume_analyzer
export ANTHROPIC_API_KEY=sk-ant-...
python manage.py runserver
```
Visit: http://localhost:8000

## JobSniper CLI Commands
```bash
# Full pipeline: scrape → score → generate cover letters
python manage.py snipe pipeline

# Individual steps
python manage.py snipe scrape                    # scrape all enabled sources
python manage.py snipe scrape --source indeed    # scrape one source
python manage.py snipe filter                    # score and rank new jobs
python manage.py snipe tailor                    # generate cover letters for queued jobs
python manage.py snipe tailor --job-id 42        # generate for one job
python manage.py snipe stats                     # print pipeline stats
python manage.py snipe reset                     # clear all data (with confirmation)
```

## Project Structure
```
/
├── config.yaml                    # JobSniper search config and profile
├── data/
│   ├── resume.txt                 # Marco's resume (plain text for AI)
│   └── jobsniper.db               # SQLite job database
├── db/
│   └── schema.sql                 # Database schema
└── resume_analyzer/               # Django project
    ├── resumes/                   # Resume upload, analysis, builder
    ├── assessments/               # Skill assessment engine
    ├── companies/                 # Company tracker
    └── jobsniper/                 # Job scraper pipeline
        ├── scrapers/              # Indeed, LinkedIn, Wellfound
        ├── services/
        │   ├── store.py           # Raw SQLite operations
        │   ├── filter.py          # Scoring engine (0.0–1.0)
        │   └── tailor.py          # Claude API cover letter generation
        └── management/commands/
            └── snipe.py           # CLI entry point
```

## Key Config Files
- `config.yaml` — target roles, skills, search queries, scraping settings
- `data/resume.txt` — update this with your actual resume for best cover letters
- `.env` (create from `.env.example`) — ANTHROPIC_API_KEY

## Scoring Weights (filter.py)
| Factor | Weight |
|--------|--------|
| Title match | 0.30 |
| Must-have skills | 0.25 |
| Nice-to-have skills | 0.15 |
| Remote match | 0.15 |
| No exclude keywords | 0.10 |
| Salary in range | 0.05 |

Jobs scoring < 0.40 are auto-filtered. Jobs ≥ 0.40 are queued for tailoring.

## Dashboard URLs
- `/` — DevResume AI dashboard
- `/resumes/` — Resume list and analysis
- `/assessments/` — Skill assessment engine
- `/companies/` — Company tracker
- `/snipe/` — JobSniper review queue
- `/snipe/stats/` — Pipeline statistics

## Testing
```bash
# Test filter with mock data
python manage.py shell -c "
from jobsniper.services.filter import score_job
job = {'title': 'React Developer', 'description': 'React, JavaScript, TypeScript, remote', 'location': 'Remote'}
profile = {'target_titles': ['React Developer'], 'must_have_skills': ['React', 'JavaScript'], 'nice_to_have_skills': ['TypeScript'], 'remote_preference': 'remote', 'exclude_keywords': ['Senior'], 'min_salary': 60000}
print(score_job(job, profile))
"
```

## Important Notes
- **No auto-apply** — system queues + generates letters, human clicks Apply
- **Scraping has delays** — 3s between pages, 1-2s between requests
- **Rate limits** — scrapers detect CAPTCHA and stop gracefully
- **Cover letter retries** — 3 attempts with 2s/4s/8s backoff on API failures
