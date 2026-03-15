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
# Full pipeline: scrape -> score -> generate cover letters
python manage.py snipe pipeline

# Individual steps
python manage.py snipe scrape          # scrape Indeed (only source in Phase 1)
python manage.py snipe filter          # score and rank new jobs
python manage.py snipe tailor          # generate cover letters for queued jobs
python manage.py snipe tailor --job-id 42  # generate for one job
python manage.py snipe stats           # print pipeline stats
python manage.py snipe reset           # clear all data (with confirmation)
```

## Project Structure
```
/
+-- config.yaml                    # JobSniper search config and profile
+-- data/
|   +-- resume.txt                 # Your resume (plain text for AI)
|   +-- jobsniper.db               # SQLite job database
+-- db/
|   +-- schema.sql                 # Database schema
+-- resume_analyzer/               # Django project
    +-- resumes/                   # Resume upload, analysis, builder
    +-- assessments/               # Skill assessment engine
    +-- companies/                 # Company tracker
    +-- jobsniper/                 # Job scraper pipeline
        +-- scrapers/
        |   +-- base.py            # Abstract base class with delay/CAPTCHA helpers
        |   +-- indeed.py          # Indeed scraper (ONLY source in Phase 1)
        +-- services/
        |   +-- store.py           # Raw SQLite operations (no ORM)
        |   +-- filter.py          # Scoring engine (0.0-1.0)
        |   +-- tailor.py          # Claude API cover letter generation
        +-- management/commands/
            +-- snipe.py           # CLI entry point
```

## MVP Phases

### Phase 1 - Built
1. Database schema and store.py
2. Indeed scraper (only source)
3. Filter engine
4. Tailor engine (Claude API)
5. CLI: scrape, filter, tailor, pipeline, stats, reset
6. Dashboard: queue page, detail page, stats page

### Phase 2 - Do NOT build yet
7. LinkedIn scraper
8. Wellfound scraper
9. Duplicate detection across sources
10. Export to CSV

## Key Config Files
- `config.yaml` - target roles, skills, search queries, scraping settings
- `data/resume.txt` - update with your actual resume for best cover letters
- `.env` - ANTHROPIC_API_KEY

## Scoring Weights (filter.py)
| Factor              | Weight |
|---------------------|--------|
| Title match         |  0.30  |
| Must-have skills    |  0.25  |
| Nice-to-have skills |  0.15  |
| Remote match        |  0.15  |
| No exclude keywords |  0.10  |
| Salary in range     |  0.05  |

Jobs scoring < 0.40 are auto-filtered. Jobs >= 0.40 are queued for tailoring.

## Cost Model
- Goal: under $5 to process 200+ applications through the full pipeline
- Paid: Claude API only - cover letter generation (~$0.01-0.02 per letter)
- Free: Indeed scraping (Playwright, local), SQLite, Django, all filtering
- 200 cover letters x ~$0.015 avg = ~$3 - well within budget

## Scraping Defaults (conservative)
- 4s delay between pages, 2s between requests (+ random jitter)
- Max 75 jobs per run (adjust max_jobs_per_run in config.yaml)
- Headless Chromium via Playwright
- CAPTCHA/rate-limit detection stops gracefully
- 2-pass approach: Pass 1 collects job cards, Pass 2 fetches full descriptions

## Dashboard URLs
- `/` - DevResume AI dashboard
- `/snipe/` - JobSniper review queue
- `/snipe/stats/` - Pipeline statistics

## Testing the Filter
```bash
python manage.py shell -c "
from jobsniper.services.filter import score_job
job = {
    'title': 'React Developer',
    'description': 'React, JavaScript, TypeScript, remote work',
    'location': 'Remote',
    'remote_type': 'Remote',
}
profile = {
    'target_titles': ['React Developer'],
    'must_have_skills': ['React', 'JavaScript'],
    'nice_to_have_skills': ['TypeScript'],
    'remote_preference': 'remote',
    'exclude_keywords': ['Senior'],
    'min_salary': 60000,
}
print(score_job(job, profile))
"
```

## Important Notes
- No auto-apply - system queues + generates letters, human clicks Apply
- Indeed only - LinkedIn and Wellfound scrapers are Phase 2 (not built)
- 2-pass scraping - Pass 1 collects job cards, Pass 2 fetches full descriptions
- Cover letter retries - 3 attempts with 2s/4s/8s exponential backoff
- Rate limit safe - CAPTCHA detection stops scraping gracefully
