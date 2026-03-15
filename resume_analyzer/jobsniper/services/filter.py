"""
JobSniper — Filter and scoring engine.
Scores jobs 0.0–1.0 based on profile config.
Uses word-boundary matching to avoid false positives (e.g. React != Reactive).
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Scoring weights (must sum to 1.0)
WEIGHTS = {
    'title_match':       0.30,
    'must_have_skills':  0.25,
    'nice_to_have':      0.15,
    'remote_match':      0.15,
    'no_excludes':       0.10,
    'salary_in_range':   0.05,
}

QUEUE_THRESHOLD = 0.40  # below this → 'filtered' (auto-skip)


def _word_match(text: str, term: str) -> bool:
    """Case-insensitive whole-word match. Avoids substring false-positives."""
    if not text or not term:
        return False
    # Escape special regex chars in term, then wrap in word boundaries
    pattern = r'\b' + re.escape(term) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _any_word_match(text: str, terms: list[str]) -> list[str]:
    """Return which terms match in text."""
    return [t for t in terms if _word_match(text, t)]


def score_job(job: dict, profile: dict) -> float:
    """
    Score a single job dict against the candidate profile.
    Returns float 0.0–1.0.
    """
    title = job.get('title', '')
    description = job.get('description', '') or ''
    location = job.get('location', '') or ''
    remote_type = job.get('remote_type', '') or ''
    salary_min = job.get('salary_min')
    salary_max = job.get('salary_max')

    full_text = f'{title} {description}'

    scores: dict[str, float] = {}

    # 1. Title match — how well does the job title align with target titles
    target_titles: list[str] = profile.get('target_titles', [])
    matched_titles = [t for t in target_titles if _word_match(title, t.split()[0])]
    if matched_titles:
        scores['title_match'] = min(1.0, len(matched_titles) / max(len(target_titles), 1) * 3)
    else:
        # Partial: check individual words from target titles
        title_words = set()
        for tt in target_titles:
            title_words.update(tt.lower().split())
        title_lower = title.lower()
        word_matches = sum(1 for w in title_words if w in title_lower and len(w) > 3)
        scores['title_match'] = min(0.5, word_matches * 0.1)

    # 2. Must-have skills — all must match for full score
    must_haves: list[str] = profile.get('must_have_skills', [])
    if must_haves:
        found = _any_word_match(full_text, must_haves)
        scores['must_have_skills'] = len(found) / len(must_haves)
    else:
        scores['must_have_skills'] = 1.0

    # 3. Nice-to-have skills
    nice_to_haves: list[str] = profile.get('nice_to_have_skills', [])
    if nice_to_haves:
        found = _any_word_match(full_text, nice_to_haves)
        scores['nice_to_have'] = min(1.0, len(found) / max(len(nice_to_haves) * 0.5, 1))
    else:
        scores['nice_to_have'] = 0.5

    # 4. Remote match
    remote_pref = profile.get('remote_preference', 'remote').lower()
    remote_indicators = ['remote', 'work from home', 'wfh', 'distributed', 'anywhere']
    location_text = f'{location} {remote_type}'.lower()
    desc_remote = any(ind in full_text.lower() for ind in remote_indicators)
    location_remote = any(ind in location_text for ind in remote_indicators)

    if remote_pref == 'remote':
        scores['remote_match'] = 1.0 if (desc_remote or location_remote) else 0.2
    elif remote_pref == 'hybrid':
        scores['remote_match'] = 1.0 if 'hybrid' in location_text else 0.5
    else:
        scores['remote_match'] = 0.7  # neutral

    # 5. Exclude keywords — title match = hard reject (return 0); body match = soft penalty
    excludes: list[str] = profile.get('exclude_keywords', [])
    if excludes:
        title_excludes = [e for e in excludes if _word_match(title, e)]
        if title_excludes:
            # Exclude keyword in job title → immediate disqualification
            logger.debug(f'Title excludes matched for "{title}": {title_excludes}')
            return 0.0
        body_excludes = _any_word_match(description, excludes)
        scores['no_excludes'] = 0.0 if body_excludes else 1.0
    else:
        scores['no_excludes'] = 1.0

    # 6. Salary range
    min_desired = profile.get('min_salary', 0)
    if salary_min is not None and salary_min > 0:
        if salary_min >= min_desired:
            scores['salary_in_range'] = 1.0
        elif salary_max and salary_max >= min_desired:
            scores['salary_in_range'] = 0.5
        else:
            scores['salary_in_range'] = 0.0
    else:
        scores['salary_in_range'] = 0.5  # unknown, neutral

    # Weighted total
    total = sum(WEIGHTS[k] * scores.get(k, 0) for k in WEIGHTS)
    total = round(min(1.0, max(0.0, total)), 4)

    logger.debug(
        f'Scored "{title}" at {job.get("company", "?")} : {total:.2f} — '
        + ', '.join(f'{k}={v:.2f}' for k, v in scores.items())
    )
    return total


def filter_and_score_jobs(jobs: list[dict], profile: dict) -> tuple[list[dict], list[dict]]:
    """
    Score all jobs. Returns (queued, filtered).
    Queued = score >= threshold. Filtered = below threshold.
    """
    queued, filtered_out = [], []

    for job in jobs:
        score = score_job(job, profile)
        job['relevance_score'] = score
        if score >= QUEUE_THRESHOLD:
            job['status'] = 'queued'
            queued.append(job)
        else:
            job['status'] = 'filtered'
            filtered_out.append(job)

    # Sort queue by score desc
    queued.sort(key=lambda j: j['relevance_score'], reverse=True)
    return queued, filtered_out


def run_filter(config: dict, db_path: Optional[str] = None) -> dict:
    """
    Pull all 'new' jobs from DB, score them, update their status and score.
    Returns summary dict.
    """
    from .store import get_new_jobs, update_score, update_status

    profile = config.get('profile', {})
    jobs = get_new_jobs(db_path=db_path)
    logger.info(f'Scoring {len(jobs)} new jobs...')

    queued_count = filtered_count = 0
    for job in jobs:
        score = score_job(job, profile)
        update_score(job['id'], score, db_path=db_path)

        if score >= QUEUE_THRESHOLD:
            update_status(job['id'], 'queued', db_path=db_path)
            queued_count += 1
        else:
            update_status(job['id'], 'filtered', db_path=db_path)
            filtered_count += 1

    return {
        'total': len(jobs),
        'queued': queued_count,
        'filtered': filtered_count,
    }
