"""
JobSniper — Tailor engine.
Generates cover letters via Claude API with retry logic.
"""
import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cover letter writer for a software developer job search.
You will receive the candidate's resume and a job description.
Write a concise, natural cover letter (3-4 short paragraphs, under 250 words).
Rules:
- Open with the specific role and company name
- Connect 2-3 specific resume achievements to job requirements
- Sound human and direct, not corporate or generic
- Never use phrases like "I am writing to express my interest" or "I believe I would be a great fit"
- End with a simple call to action
- Do not invent skills or experience not in the resume
Output only the cover letter text, no subject line or headers."""

RETRY_DELAYS = [2, 4, 8]  # exponential backoff


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    return anthropic.Anthropic(api_key=api_key)


def _get_resume_text(resume_path: Optional[str] = None) -> str:
    if not resume_path:
        resume_path = os.environ.get('RESUME_PATH', '')
    if not resume_path:
        # Default relative to project root
        resume_path = str(Path(__file__).resolve().parents[3] / 'data' / 'resume.txt')
    p = Path(resume_path)
    if p.exists():
        return p.read_text(encoding='utf-8')
    logger.warning(f'Resume not found at {resume_path}')
    return ''


def generate_cover_letter(
    job: dict,
    resume_text: Optional[str] = None,
    config: Optional[dict] = None,
) -> str:
    """
    Generate a tailored cover letter for a job.
    Retries up to 3 times with exponential backoff on API failures.
    """
    if resume_text is None:
        resume_text = _get_resume_text()

    if not resume_text:
        raise RuntimeError('No resume text available. Add your resume to data/resume.txt')

    tailor_cfg = (config or {}).get('tailor', {})
    model = tailor_cfg.get('model', 'claude-sonnet-4-6')
    max_tokens = tailor_cfg.get('max_tokens', 600)

    description = job.get('description', '') or ''
    # Truncate very long descriptions
    if len(description) > 3000:
        description = description[:3000] + '\n...[truncated]'

    user_prompt = f"""RESUME:
{resume_text}

JOB TITLE: {job.get('title', '')}
COMPANY: {job.get('company', '')}
JOB DESCRIPTION:
{description}

Write a tailored cover letter for this role."""

    client = _get_client()
    last_error = None

    for attempt, delay in enumerate([0] + RETRY_DELAYS, start=1):
        if delay:
            logger.info(f'Retrying cover letter for job {job.get("id")} (attempt {attempt}, wait {delay}s)...')
            time.sleep(delay)
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{'role': 'user', 'content': user_prompt}],
            )
            return response.content[0].text.strip()
        except anthropic.RateLimitError as e:
            logger.warning(f'Rate limit hit for job {job.get("id")}: {e}')
            last_error = e
        except anthropic.APITimeoutError as e:
            logger.warning(f'Timeout for job {job.get("id")}: {e}')
            last_error = e
        except anthropic.APIError as e:
            logger.error(f'API error for job {job.get("id")}: {e}')
            last_error = e
            break  # Don't retry non-transient errors

    raise RuntimeError(f'Failed to generate cover letter after {attempt} attempts: {last_error}')


def tailor_all_queued(
    config: Optional[dict] = None,
    db_path: Optional[str] = None,
    resume_path: Optional[str] = None,
) -> dict:
    """Process all queued jobs and generate cover letters."""
    from .store import get_jobs, save_cover_letter, update_status

    resume_text = _get_resume_text(resume_path)
    queued = get_jobs(status='queued', db_path=db_path)
    logger.info(f'Generating cover letters for {len(queued)} queued jobs...')

    success = failed = 0
    for job in queued:
        try:
            letter = generate_cover_letter(job, resume_text=resume_text, config=config)
            save_cover_letter(job['id'], letter, db_path=db_path)
            update_status(job['id'], 'tailored', db_path=db_path)
            success += 1
            logger.info(f'✓ Generated cover letter for job #{job["id"]} — {job["company"]}: {job["title"]}')
            # Small delay between API calls to be respectful
            time.sleep(0.5)
        except Exception as e:
            logger.error(f'✗ Failed cover letter for job #{job["id"]} — {job.get("company")}: {e}')
            failed += 1

    return {'total': len(queued), 'success': success, 'failed': failed}


def tailor_single(
    job_id: int,
    config: Optional[dict] = None,
    db_path: Optional[str] = None,
    resume_path: Optional[str] = None,
) -> str:
    """Generate (or regenerate) a cover letter for a single job by ID."""
    from .store import get_job, save_cover_letter, update_status

    job = get_job(job_id, db_path=db_path)
    if not job:
        raise ValueError(f'Job #{job_id} not found')

    resume_text = _get_resume_text(resume_path)
    letter = generate_cover_letter(job, resume_text=resume_text, config=config)
    save_cover_letter(job_id, letter, db_path=db_path)

    # Promote to tailored if it was queued
    if job['status'] in ('queued', 'new'):
        update_status(job_id, 'tailored', db_path=db_path)

    return letter
