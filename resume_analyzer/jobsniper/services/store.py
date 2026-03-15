"""
JobSniper — Database store.
All SQLite operations for jobs, cover letters, and application log.
No ORM. Raw sqlite3 with explicit transactions.
"""
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parents[3] / 'db' / 'schema.sql'
VALID_STATUSES = {'new', 'filtered', 'queued', 'tailored', 'applied', 'skipped', 'rejected'}


def _get_db_path() -> str:
    from django.conf import settings
    return getattr(settings, 'JOBSNIPER_DB_PATH', str(Path(__file__).resolve().parents[3] / 'data' / 'jobsniper.db'))


@contextmanager
def _conn(db_path: Optional[str] = None):
    path = db_path or _get_db_path()
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Create tables from schema if they don't exist."""
    path = db_path or _get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    schema = SCHEMA_PATH.read_text()
    with _conn(path) as con:
        con.executescript(schema)
    logger.info(f'Database initialised at {path}')


def upsert_job(job: dict, db_path: Optional[str] = None) -> int:
    """
    Insert or update a job. Keyed on external_id for deduplication.
    Returns the row id.
    """
    fields = [
        'external_id', 'source', 'title', 'company', 'location',
        'remote_type', 'url', 'description', 'salary_min', 'salary_max',
        'posted_date', 'easy_apply',
    ]
    data = {f: job.get(f) for f in fields}

    with _conn(db_path) as con:
        cur = con.execute(
            '''INSERT INTO jobs (external_id, source, title, company, location,
                remote_type, url, description, salary_min, salary_max,
                posted_date, easy_apply)
               VALUES (:external_id, :source, :title, :company, :location,
                :remote_type, :url, :description, :salary_min, :salary_max,
                :posted_date, :easy_apply)
               ON CONFLICT(external_id) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                salary_min=excluded.salary_min,
                salary_max=excluded.salary_max,
                easy_apply=excluded.easy_apply''',
            data,
        )
        if cur.lastrowid:
            return cur.lastrowid
        row = con.execute('SELECT id FROM jobs WHERE external_id=?', (data['external_id'],)).fetchone()
        return row['id']


def get_jobs(
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    source: Optional[str] = None,
    limit: int = 200,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Fetch jobs with optional filters, sorted by score desc."""
    query = 'SELECT j.*, (SELECT content FROM cover_letters WHERE job_id=j.id ORDER BY version DESC LIMIT 1) as cover_letter FROM jobs j WHERE 1=1'
    params: list = []

    if status:
        query += ' AND j.status=?'
        params.append(status)
    if min_score is not None:
        query += ' AND j.relevance_score>=?'
        params.append(min_score)
    if source:
        query += ' AND j.source=?'
        params.append(source)

    query += ' ORDER BY j.relevance_score DESC LIMIT ?'
    params.append(limit)

    with _conn(db_path) as con:
        rows = con.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_job(job_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with _conn(db_path) as con:
        row = con.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        return dict(row) if row else None


def get_latest_cover_letter(job_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with _conn(db_path) as con:
        row = con.execute(
            'SELECT * FROM cover_letters WHERE job_id=? ORDER BY version DESC LIMIT 1',
            (job_id,),
        ).fetchone()
        return dict(row) if row else None


def update_status(job_id: int, status: str, db_path: Optional[str] = None) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f'Invalid status: {status}. Must be one of {VALID_STATUSES}')
    with _conn(db_path) as con:
        con.execute('UPDATE jobs SET status=? WHERE id=?', (status, job_id))


def update_score(job_id: int, score: float, db_path: Optional[str] = None) -> None:
    with _conn(db_path) as con:
        con.execute('UPDATE jobs SET relevance_score=? WHERE id=?', (round(score, 4), job_id))


def save_cover_letter(job_id: int, content: str, db_path: Optional[str] = None) -> int:
    with _conn(db_path) as con:
        # Increment version
        row = con.execute(
            'SELECT COALESCE(MAX(version), 0) as v FROM cover_letters WHERE job_id=?',
            (job_id,),
        ).fetchone()
        next_version = row['v'] + 1
        cur = con.execute(
            'INSERT INTO cover_letters (job_id, version, content) VALUES (?, ?, ?)',
            (job_id, next_version, content),
        )
        return cur.lastrowid


def log_application(job_id: int, method: str, notes: Optional[str] = None, db_path: Optional[str] = None) -> None:
    with _conn(db_path) as con:
        con.execute(
            'INSERT INTO application_log (job_id, method, notes) VALUES (?, ?, ?)',
            (job_id, method, notes),
        )


def get_stats(db_path: Optional[str] = None) -> dict:
    with _conn(db_path) as con:
        def scalar(q, *p):
            return con.execute(q, p).fetchone()[0] or 0

        today = date.today().isoformat()
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

        total = scalar('SELECT COUNT(*) FROM jobs')
        by_status = {}
        for row in con.execute('SELECT status, COUNT(*) as n FROM jobs GROUP BY status').fetchall():
            by_status[row['status']] = row['n']

        cover_letters_total = scalar('SELECT COUNT(DISTINCT job_id) FROM cover_letters')
        applied_today = scalar(
            "SELECT COUNT(*) FROM application_log WHERE date(applied_at)=?", today
        )
        applied_week = scalar(
            "SELECT COUNT(*) FROM application_log WHERE date(applied_at)>=?", week_start
        )
        top_companies = [
            dict(r)
            for r in con.execute(
                '''SELECT j.company, COUNT(*) as n
                   FROM application_log al
                   JOIN jobs j ON j.id=al.job_id
                   GROUP BY j.company ORDER BY n DESC LIMIT 5'''
            ).fetchall()
        ]
        avg_score_applied = scalar(
            '''SELECT AVG(j.relevance_score)
               FROM application_log al JOIN jobs j ON j.id=al.job_id'''
        )
        sources = {}
        for row in con.execute('SELECT source, COUNT(*) as n FROM jobs GROUP BY source').fetchall():
            sources[row['source']] = row['n']

        return {
            'total': total,
            'by_status': by_status,
            'filtered': by_status.get('filtered', 0),
            'queued': by_status.get('queued', 0),
            'tailored': by_status.get('tailored', 0),
            'applied': by_status.get('applied', 0),
            'skipped': by_status.get('skipped', 0),
            'cover_letters_total': cover_letters_total,
            'applied_today': applied_today,
            'applied_week': applied_week,
            'top_companies': top_companies,
            'avg_score_applied': round(avg_score_applied or 0, 2),
            'sources': sources,
        }


def get_new_jobs(db_path: Optional[str] = None) -> list[dict]:
    return get_jobs(status='new', db_path=db_path)
