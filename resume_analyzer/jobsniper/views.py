"""
JobSniper — Dashboard views.
Routes mirror the spec: queue, detail, stats, apply/skip/regenerate actions.
"""
import logging
import os
from pathlib import Path

import yaml
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('jobsniper')


def _config() -> dict:
    cfg_path = os.environ.get('CONFIG_PATH', '')
    if not cfg_path:
        cfg_path = str(Path(__file__).resolve().parents[2] / 'config.yaml')
    try:
        with open(cfg_path) as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


def _db_path() -> str:
    from django.conf import settings
    return getattr(settings, 'JOBSNIPER_DB_PATH',
                   str(Path(__file__).resolve().parents[2] / 'data' / 'jobsniper.db'))


def _ensure_db():
    from jobsniper.services.store import init_db
    init_db(_db_path())


# ── Queue ─────────────────────────────────────────────────────────────────────

@login_required
def queue_view(request):
    _ensure_db()
    from jobsniper.services.store import get_jobs, get_stats

    status_filter = request.GET.get('status', '')
    valid_statuses = ['queued', 'tailored', 'applied', 'skipped', 'new', 'filtered']

    # Tab counts
    stats = get_stats(_db_path())
    by_status = stats.get('by_status', {})
    tab_counts = {s: by_status.get(s, 0) for s in valid_statuses}
    tab_counts['all'] = stats.get('total', 0)

    # Active filter
    if status_filter and status_filter not in valid_statuses:
        status_filter = ''

    # Default: show review-ready jobs (queued + tailored)
    if not status_filter:
        jobs = get_jobs(status='queued', db_path=_db_path()) + get_jobs(status='tailored', db_path=_db_path())
        jobs.sort(key=lambda j: j['relevance_score'], reverse=True)
        active_tab = 'review'
    elif status_filter == 'all':
        jobs = get_jobs(db_path=_db_path())
        active_tab = 'all'
    else:
        jobs = get_jobs(status=status_filter, db_path=_db_path())
        active_tab = status_filter

    tabs = [
        ('review', 'Review Ready'),
        ('all', 'All Jobs'),
        ('queued', 'Queued'),
        ('tailored', 'Tailored'),
        ('applied', 'Applied'),
        ('skipped', 'Skipped'),
        ('new', 'New'),
        ('filtered', 'Filtered'),
    ]
    return render(request, 'jobsniper/queue.html', {
        'jobs': jobs,
        'active_tab': active_tab,
        'tab_counts': tab_counts,
        'total_review': tab_counts.get('queued', 0) + tab_counts.get('tailored', 0),
        'tabs': tabs,
    })


# ── Detail ────────────────────────────────────────────────────────────────────

@login_required
def detail_view(request, job_id: int):
    _ensure_db()
    from jobsniper.services.store import get_job, get_latest_cover_letter

    job = get_job(job_id, db_path=_db_path())
    if not job:
        messages.error(request, f'Job #{job_id} not found.')
        return redirect('snipe_queue')

    cover_letter = get_latest_cover_letter(job_id, db_path=_db_path())
    return render(request, 'jobsniper/detail.html', {
        'job': job,
        'cover_letter': cover_letter,
    })


# ── Actions ───────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def apply_view(request, job_id: int):
    from jobsniper.services.store import update_status, log_application, get_job

    job = get_job(job_id, db_path=_db_path())
    if not job:
        return JsonResponse({'error': 'Job not found'}, status=404)

    method = request.POST.get('method', 'manual')
    notes = request.POST.get('notes', '')
    update_status(job_id, 'applied', db_path=_db_path())
    log_application(job_id, method=method, notes=notes, db_path=_db_path())
    messages.success(request, f'✓ Marked "{job["title"]}" at {job["company"]} as applied!')
    return redirect('snipe_queue')


@login_required
@require_http_methods(['POST'])
def skip_view(request, job_id: int):
    from jobsniper.services.store import update_status, get_job

    job = get_job(job_id, db_path=_db_path())
    if not job:
        return JsonResponse({'error': 'Job not found'}, status=404)

    update_status(job_id, 'skipped', db_path=_db_path())
    messages.info(request, f'Skipped "{job["title"]}" at {job["company"]}.')
    return redirect('snipe_queue')


@login_required
@require_http_methods(['POST'])
def regenerate_view(request, job_id: int):
    from jobsniper.services.store import get_job
    from jobsniper.services.tailor import tailor_single

    if not os.environ.get('ANTHROPIC_API_KEY'):
        messages.error(request, 'ANTHROPIC_API_KEY not configured.')
        return redirect('snipe_detail', job_id=job_id)

    job = get_job(job_id, db_path=_db_path())
    if not job:
        messages.error(request, 'Job not found.')
        return redirect('snipe_queue')

    try:
        config = _config()
        tailor_single(job_id, config=config, db_path=_db_path())
        messages.success(request, 'Cover letter regenerated!')
    except Exception as e:
        logger.error(f'Regenerate failed for #{job_id}: {e}')
        messages.error(request, f'Generation failed: {e}')

    return redirect('snipe_detail', job_id=job_id)


# ── Stats ──────────────────────────────────────────────────────────────────────

@login_required
def stats_view(request):
    _ensure_db()
    from jobsniper.services.store import get_stats
    stats = get_stats(_db_path())
    pipeline_stages = [
        ('new', 'New', 'gray'),
        ('queued', 'Queued', 'yellow'),
        ('tailored', 'Tailored', 'blue'),
        ('applied', 'Applied', 'green'),
        ('skipped', 'Skipped', 'gray'),
        ('filtered', 'Filtered', 'red'),
    ]
    return render(request, 'jobsniper/stats.html', {
        'stats': stats,
        'pipeline_stages': pipeline_stages,
    })


# ── API: quick scrape trigger (async background) ───────────────────────────────

@login_required
@require_http_methods(['POST'])
def trigger_pipeline(request):
    """Kick off filter+tailor for already-scraped 'new' jobs (sync, quick)."""
    from jobsniper.services.filter import run_filter
    from jobsniper.services.tailor import tailor_all_queued

    if not os.environ.get('ANTHROPIC_API_KEY'):
        messages.error(request, 'ANTHROPIC_API_KEY not configured.')
        return redirect('snipe_queue')

    config = _config()
    db_path = _db_path()

    try:
        filter_result = run_filter(config, db_path=db_path)
        tailor_result = tailor_all_queued(config=config, db_path=db_path)
        messages.success(
            request,
            f'Pipeline complete: {filter_result["queued"]} jobs queued, '
            f'{tailor_result["success"]} cover letters generated.'
        )
    except Exception as e:
        messages.error(request, f'Pipeline error: {e}')

    return redirect('snipe_queue')
