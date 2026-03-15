"""
JobSniper — Indeed scraper.

2-pass approach:
  Pass 1: paginate search results, collect basic job metadata from cards.
  Pass 2: fetch full job description from each job's detail page.

This keeps the search-results navigation clean and avoids back-navigation
interruptions. Descriptions are fetched on a separate page tab.
"""
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlencode

from playwright.async_api import async_playwright, Page, BrowserContext

from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.indeed.com'

# Selectors — ordered by specificity. First match wins.
CARD_SELECTORS = [
    '[data-testid="slider_item"]',
    '.job_seen_beacon',
    '[data-jk]',
    '.resultContent',
]

TITLE_SELECTORS = [
    '[data-testid="jobTitle"] span',
    '[data-testid="jobTitle"]',
    '.jobTitle a span',
    'h2.jobTitle a span',
    'h2.jobTitle span',
]

COMPANY_SELECTORS = [
    '[data-testid="company-name"]',
    '.companyName',
    'span[data-testid="company-name"]',
]

LOCATION_SELECTORS = [
    '[data-testid="text-location"]',
    '[data-testid="job-location"]',
    '.companyLocation',
]

DESCRIPTION_SELECTORS = [
    '#jobDescriptionText',
    '[data-testid="jobsearch-JobComponent-description"]',
    '.jobDescription',
    '#job-content',
]


class IndeedScraper(BaseScraper):
    def __init__(self, config: dict):
        super().__init__(config)
        self.search_cfg = config.get('search', {}).get('indeed', {})
        self.queries: list[str] = self.search_cfg.get('queries', [])
        self.pages_per_query: int = self.search_cfg.get('pages_per_query', 3)

    async def scrape(self) -> list[dict]:
        if not self.queries:
            logger.warning('No Indeed queries configured in config.yaml')
            return []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=self.user_agent,
                viewport={'width': 1280, 'height': 900},
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'DNT': '1',
                },
                java_script_enabled=True,
            )

            # Pass 1: collect basic job data from all search result pages
            search_page = await context.new_page()
            basic_jobs: list[dict] = []

            for query in self.queries:
                if len(basic_jobs) >= self.max_jobs or self._rate_limited:
                    break
                try:
                    jobs = await self._collect_cards(search_page, query)
                    basic_jobs.extend(jobs)
                    logger.info(f'Indeed pass-1: "{query}" -> {len(jobs)} cards')
                except Exception as exc:
                    logger.error(f'Indeed pass-1 error for "{query}": {exc}')
                if not self._rate_limited:
                    await self._page_delay()

            await search_page.close()

            # Deduplicate by external_id before pass 2
            seen: set[str] = set()
            unique_jobs: list[dict] = []
            for j in basic_jobs:
                if j['external_id'] not in seen:
                    seen.add(j['external_id'])
                    unique_jobs.append(j)

            unique_jobs = unique_jobs[:self.max_jobs]
            logger.info(f'Indeed pass-1 complete: {len(unique_jobs)} unique jobs')

            # Pass 2: fetch descriptions
            if unique_jobs and not self._rate_limited:
                detail_page = await context.new_page()
                await self._fetch_descriptions(detail_page, unique_jobs)
                await detail_page.close()

            await browser.close()

        return unique_jobs

    # ── Pass 1: collect cards ─────────────────────────────────────────────────

    async def _collect_cards(self, page: Page, query: str) -> list[dict]:
        jobs: list[dict] = []

        for page_num in range(self.pages_per_query):
            if self._rate_limited:
                break

            start = page_num * 10
            params = urlencode({
                'q': query,
                'l': 'Remote',
                'remotejob': '032b3046-06a3-4876-8dfd-474eb5e7ed11',
                'start': start,
                'sort': 'date',
            })
            url = f'{BASE_URL}/jobs?{params}'

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30_000)
                # Brief pause for JS to render cards
                await page.wait_for_timeout(2_500)

                html = await page.content()
                if self._detect_captcha(html) or self._detect_rate_limit(html):
                    logger.warning(f'Indeed: blocked on page {page_num + 1} for "{query}"')
                    self._rate_limited = True
                    break

                cards = await self._find_cards(page)
                if not cards:
                    logger.debug(f'Indeed: no cards on page {page_num + 1}, stopping query')
                    break

                page_jobs: list[dict] = []
                for card in cards:
                    try:
                        job = await self._extract_card(card)
                        if job:
                            page_jobs.append(job)
                    except Exception as exc:
                        logger.debug(f'Indeed: card extract error: {exc}')

                jobs.extend(page_jobs)
                logger.debug(f'Indeed: page {page_num + 1} -> {len(page_jobs)} cards for "{query}"')

                # Stop if we got a short page (last page of results)
                if len(page_jobs) < 5:
                    break

            except Exception as exc:
                logger.error(f'Indeed: page {page_num + 1} error for "{query}": {exc}')
                break

            if page_num < self.pages_per_query - 1:
                await self._page_delay()

        return jobs

    async def _find_cards(self, page: Page):
        """Try each card selector in order, return the first non-empty result."""
        for selector in CARD_SELECTORS:
            try:
                cards = await page.query_selector_all(selector)
                if cards:
                    return cards
            except Exception:
                continue
        return []

    async def _extract_card(self, card) -> Optional[dict]:
        """Extract basic job metadata from a search-result card element."""
        # Job key (Indeed's unique ID for the listing)
        jk = await card.get_attribute('data-jk') or ''
        if not jk:
            link = await card.query_selector('a[data-jk]')
            if link:
                jk = await link.get_attribute('data-jk') or ''
        if not jk:
            # Last resort: parse from href
            link = await card.query_selector('h2 a, .jobTitle a')
            if link:
                href = await link.get_attribute('href') or ''
                m = re.search(r'jk=([a-f0-9]+)', href)
                if m:
                    jk = m.group(1)
        if not jk:
            return None

        external_id = self._make_external_id('indeed', jk)

        # Title — required
        title = await self._card_text(card, TITLE_SELECTORS)
        if not title:
            return None

        # Company
        company = await self._card_text(card, COMPANY_SELECTORS) or 'Unknown'

        # Location
        location = await self._card_text(card, LOCATION_SELECTORS)

        # Remote type (from attribute snippets / location text)
        remote_type = self._infer_remote(location)
        snippet_els = await card.query_selector_all('[data-testid="attribute_snippet_testid"]')
        for el in snippet_els:
            txt = self._clean(await el.inner_text())
            if any(r in txt.lower() for r in ('remote', 'hybrid', 'on-site', 'on site')):
                remote_type = txt
                break

        # Salary (may not be present)
        salary_min, salary_max = None, None
        salary_selectors = [
            '[data-testid="salary-snippet"]',
            '.salary-snippet-container',
            '[data-testid="attribute_snippet_testid"]:first-child',
        ]
        for sel in salary_selectors:
            el = await card.query_selector(sel)
            if el:
                sal_text = self._clean(await el.inner_text())
                salary_min, salary_max = self._parse_salary(sal_text)
                if salary_min:
                    break

        # Posted date
        date_el = await card.query_selector(
            '[data-testid="myJobsStateDate"], .date, [data-testid="jobsearch-JobInfoHeader-datePosted"]'
        )
        posted_date = self._clean(await date_el.inner_text() if date_el else '')

        return {
            'external_id': external_id,
            'source': 'indeed',
            'title': title,
            'company': company,
            'location': location or '',
            'remote_type': remote_type,
            'url': f'{BASE_URL}/viewjob?jk={jk}',
            'description': '',   # filled in pass 2
            'salary_min': salary_min,
            'salary_max': salary_max,
            'posted_date': posted_date,
            'easy_apply': 0,
        }

    # ── Pass 2: fetch descriptions ────────────────────────────────────────────

    async def _fetch_descriptions(self, page: Page, jobs: list[dict]) -> None:
        """
        Iterate over jobs and fetch each description from the job detail page.
        Modifies jobs in-place. Stops if rate-limited.
        """
        for i, job in enumerate(jobs):
            if self._rate_limited:
                break
            try:
                detail = await self.get_job_detail(job['url'], page)
                if detail.get('description'):
                    job['description'] = detail['description']
                logger.debug(
                    f'Indeed pass-2: {i + 1}/{len(jobs)} — {job["company"]}: '
                    f'{len(job["description"])} chars'
                )
            except Exception as exc:
                logger.debug(f'Indeed: description fetch failed for {job["url"]}: {exc}')

            # Rate-limit-aware delay between detail fetches
            if i < len(jobs) - 1:
                await self._delay()

    async def get_job_detail(self, url: str, page: Page) -> dict:
        """Fetch full job description from a single detail page."""
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=25_000)
            await page.wait_for_timeout(1_500)

            html = await page.content()
            if self._detect_captcha(html):
                logger.warning(f'Indeed: CAPTCHA on detail page, stopping description fetches')
                self._rate_limited = True
                return {}

            for selector in DESCRIPTION_SELECTORS:
                el = await page.query_selector(selector)
                if el:
                    text = self._clean(await el.inner_text())
                    if text:
                        return {'description': text}

            return {}
        except Exception as exc:
            logger.debug(f'Indeed: detail page error for {url}: {exc}')
            return {}

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _card_text(self, card, selectors: list[str]) -> str:
        """Try each selector; return first non-empty inner text."""
        for sel in selectors:
            try:
                el = await card.query_selector(sel)
                if el:
                    txt = self._clean(await el.inner_text())
                    if txt:
                        return txt
            except Exception:
                continue
        return ''

    @staticmethod
    def _infer_remote(location: str) -> str:
        loc = (location or '').lower()
        if 'remote' in loc:
            return 'Remote'
        if 'hybrid' in loc:
            return 'Hybrid'
        return ''
