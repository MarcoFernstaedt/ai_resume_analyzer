"""
JobSniper CLI — Django management commands.
Usage:
  python manage.py snipe scrape [--source linkedin|indeed|wellfound]
  python manage.py snipe filter
  python manage.py snipe tailor [--job-id 42]
  python manage.py snipe pipeline
  python manage.py snipe stats
  python manage.py snipe reset
"""
import asyncio
import json
import logging
import os
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand

logger = logging.getLogger('jobsniper')


def _load_config() -> dict:
    cfg_path = os.environ.get('CONFIG_PATH', '')
    if not cfg_path:
        cfg_path = str(Path(__file__).resolve().parents[4] / 'config.yaml')
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def _get_db_path() -> str:
    from django.conf import settings
    return getattr(settings, 'JOBSNIPER_DB_PATH',
                   str(Path(__file__).resolve().parents[4] / 'data' / 'jobsniper.db'))


class Command(BaseCommand):
    help = 'JobSniper — semi-automated job application pipeline'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', required=True)

        # scrape
        scrape_p = subparsers.add_parser('scrape', help='Scrape Indeed job listings')
        scrape_p.add_argument('--source', choices=['indeed'],
                              help='Source to scrape (only indeed supported in Phase 1)')

        # filter
        subparsers.add_parser('filter', help='Score and filter all new jobs')

        # tailor
        tailor_p = subparsers.add_parser('tailor', help='Generate cover letters')
        tailor_p.add_argument('--job-id', type=int, help='Generate for a single job ID')

        # pipeline
        subparsers.add_parser('pipeline', help='Run scrape → filter → tailor in sequence')

        # stats
        subparsers.add_parser('stats', help='Print pipeline stats to terminal')

        # reset
        subparsers.add_parser('reset', help='Clear all data (with confirmation)')

    def handle(self, *args, **options):
        action = options['action']
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S',
        )

        config = _load_config()
        db_path = _get_db_path()

        from jobsniper.services.store import init_db
        init_db(db_path)

        if action == 'scrape':
            self._run_scrape(config, db_path, source=options.get('source'))
        elif action == 'filter':
            self._run_filter(config, db_path)
        elif action == 'tailor':
            self._run_tailor(config, db_path, job_id=options.get('job_id'))
        elif action == 'pipeline':
            self._run_pipeline(config, db_path)
        elif action == 'stats':
            self._run_stats(db_path)
        elif action == 'reset':
            self._run_reset(db_path)

    # ── Scrape ────────────────────────────────────────────────────────────────

    def _run_scrape(self, config: dict, db_path: str, source: str = None) -> None:
        from jobsniper.scrapers import SCRAPERS
        from jobsniper.services.store import upsert_job

        enabled_sources = []
        search_cfg = config.get('search', {})

        for name, cls in SCRAPERS.items():
            if source and name != source:
                continue
            if not search_cfg.get(name, {}).get('enabled', False):
                if not source:
                    continue
            enabled_sources.append((name, cls))

        if not enabled_sources:
            self.stderr.write(f'No scrapers enabled for: {source or "any source"}')
            return

        total_new = 0

        for name, ScraperClass in enabled_sources:
            self.stdout.write(f'\n🔍 Scraping {name.title()}...')
            try:
                scraper = ScraperClass(config)
                jobs = asyncio.run(scraper.scrape())
                self.stdout.write(f'   Found {len(jobs)} listings')

                new = 0
                for job in jobs:
                    try:
                        upsert_job(job, db_path=db_path)
                        new += 1
                    except Exception as e:
                        logger.warning(f'Failed to store job from {name}: {e}')

                total_new += new
                self.stdout.write(self.style.SUCCESS(f'   ✓ Stored {new} jobs from {name}'))
            except Exception as e:
                self.stderr.write(f'   ✗ {name} scraper failed: {e}')

        self.stdout.write(f'\n✅ Total jobs stored: {total_new}')

    # ── Filter ────────────────────────────────────────────────────────────────

    def _run_filter(self, config: dict, db_path: str) -> None:
        from jobsniper.services.filter import run_filter

        self.stdout.write('🔎 Scoring and filtering new jobs...')
        result = run_filter(config, db_path=db_path)
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Processed {result["total"]} jobs — '
                f'{result["queued"]} queued, {result["filtered"]} filtered out'
            )
        )

    # ── Tailor ────────────────────────────────────────────────────────────────

    def _run_tailor(self, config: dict, db_path: str, job_id: int = None) -> None:
        if not os.environ.get('ANTHROPIC_API_KEY'):
            self.stderr.write('⚠️  ANTHROPIC_API_KEY not set. Add it to your .env file.')
            return

        if job_id:
            from jobsniper.services.tailor import tailor_single
            self.stdout.write(f'✍️  Generating cover letter for job #{job_id}...')
            try:
                letter = tailor_single(job_id, config=config, db_path=db_path)
                self.stdout.write(self.style.SUCCESS(f'✓ Generated cover letter ({len(letter)} chars)'))
                self.stdout.write('\n' + '─' * 60)
                self.stdout.write(letter)
            except Exception as e:
                self.stderr.write(f'✗ Failed: {e}')
        else:
            from jobsniper.services.tailor import tailor_all_queued
            self.stdout.write('✍️  Generating cover letters for all queued jobs...')
            result = tailor_all_queued(config=config, db_path=db_path)
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Cover letters: {result["success"]} generated, {result["failed"]} failed'
                )
            )

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def _run_pipeline(self, config: dict, db_path: str) -> None:
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('🚀 JobSniper Pipeline: scrape → filter → tailor')
        self.stdout.write('=' * 60 + '\n')

        self._run_scrape(config, db_path)
        self.stdout.write('')
        self._run_filter(config, db_path)
        self.stdout.write('')
        self._run_tailor(config, db_path)
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('✅ Pipeline complete. Open the dashboard to review.')
        self.stdout.write('   python manage.py runserver')
        self.stdout.write('   Then visit: http://localhost:8000/snipe/')

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _run_stats(self, db_path: str) -> None:
        from jobsniper.services.store import get_stats

        stats = get_stats(db_path=db_path)

        self.stdout.write('\n' + '=' * 40)
        self.stdout.write('📊 JobSniper Stats')
        self.stdout.write('=' * 40)
        self.stdout.write(f'Total scraped:        {stats["total"]}')
        self.stdout.write(f'Filtered out:         {stats["filtered"]}')
        self.stdout.write(f'In queue:             {stats["queued"]}')
        self.stdout.write(f'Tailored:             {stats["tailored"]}')
        self.stdout.write(f'Applied:              {stats["applied"]}')
        self.stdout.write(f'Skipped:              {stats["skipped"]}')
        self.stdout.write(f'Cover letters made:   {stats["cover_letters_total"]}')
        self.stdout.write(f'Applied today:        {stats["applied_today"]}')
        self.stdout.write(f'Applied this week:    {stats["applied_week"]}')
        self.stdout.write(f'Avg score (applied):  {stats["avg_score_applied"]:.2f}')

        if stats['sources']:
            self.stdout.write('\nBy source:')
            for src, n in stats['sources'].items():
                self.stdout.write(f'  {src}: {n}')

        if stats['top_companies']:
            self.stdout.write('\nTop companies applied to:')
            for c in stats['top_companies']:
                self.stdout.write(f'  {c["company"]}: {c["n"]} application(s)')

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _run_reset(self, db_path: str) -> None:
        confirm = input(
            '⚠️  This will DELETE all jobs, cover letters, and application logs.\n'
            'Type "yes" to confirm: '
        )
        if confirm.strip().lower() != 'yes':
            self.stdout.write('Cancelled.')
            return

        import sqlite3
        with sqlite3.connect(db_path) as con:
            con.execute('DELETE FROM application_log')
            con.execute('DELETE FROM cover_letters')
            con.execute('DELETE FROM jobs')
            con.execute('DELETE FROM sqlite_sequence WHERE name IN ("jobs","cover_letters","application_log")')
            con.commit()

        self.stdout.write(self.style.SUCCESS('✓ Database cleared.'))
