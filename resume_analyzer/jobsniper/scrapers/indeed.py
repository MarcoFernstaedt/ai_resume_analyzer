"""
JobSniper — Indeed scraper.
Navigates indeed.com/jobs with query params. Paginates via start=0,10,20...
"""
import asyncio
import hashlib
import logging
import re
from typing import Optional
from urllib.parse import quote_plus, urlencode

from playwright.async_api import async_playwright, Page, BrowserContext

from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.indeed.com'


class IndeedScraper(BaseScraper):
    def __init__(self, config: dict):
        super().__init__(config)
        self.search_cfg = config.get('search', {}).get('indeed', {})
        self.queries: list[str] = self.search_cfg.get('queries', [])
        self.pages_per_query: int = self.search_cfg.get('pages_per_query', 2)

    async def scrape(self) -> list[dict]:
        if not self.queries:
            logger.warning('No Indeed queries configured')
            return []

        all_jobs: list[dict] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=self.user_agent,
                viewport={'width': 1280, 'height': 800},
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                },
            )
            page = await context.new_page()

            for query in self.queries:
                if len(all_jobs) >= self.max_jobs:
                    break
                try:
                    jobs = await self._scrape_query(page, context, query)
                    all_jobs.extend(jobs)
                    logger.info(f'Indeed: query "{query}" → {len(jobs)} jobs')
                except Exception as e:
                    logger.error(f'Indeed: query "{query}" failed — {e}')
                await self._page_delay()

            await browser.close()

        return all_jobs[:self.max_jobs]

    async def _scrape_query(self, page: Page, context: BrowserContext, query: str) -> list[dict]:
        jobs: list[dict] = []

        for page_num in range(self.pages_per_query):
            start = page_num * 10
            params = urlencode({'q': query, 'l': 'Remote', 'remotejob': '032b3046-06a3-4876-8dfd-474eb5e7ed11', 'start': start})
            url = f'{BASE_URL}/jobs?{params}'

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)

                content = await page.content()
                if self._detect_captcha(content) or self._detect_rate_limit(content):
                    logger.warning(f'Indeed: rate limited or CAPTCHA on page {page_num + 1} for "{query}"')
                    self._rate_limited = True
                    break

                cards = await page.query_selector_all('[data-testid="slider_item"], .job_seen_beacon, [data-jk]')
                if not cards:
                    # Try alternate selectors
                    cards = await page.query_selector_all('.resultContent, .jobCard_mainContent')

                if not cards:
                    logger.debug(f'Indeed: no job cards found on page {page_num + 1}')
                    break

                for card in cards:
                    try:
                        job = await self._extract_card(card, context)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f'Indeed: card extraction error — {e}')

                await self._delay()

            except Exception as e:
                logger.error(f'Indeed: page {page_num + 1} for "{query}" failed — {e}')
                break

        return jobs

    async def _extract_card(self, card, context: BrowserContext) -> Optional[dict]:
        try:
            # Job ID
            jk = await card.get_attribute('data-jk') or ''
            if not jk:
                link_el = await card.query_selector('a[data-jk]')
                if link_el:
                    jk = await link_el.get_attribute('data-jk') or ''
            if not jk:
                return None

            external_id = self._make_external_id('indeed', jk)

            # Title
            title_el = await card.query_selector('[data-testid="jobTitle"], .jobTitle a, h2.jobTitle a span')
            title = self._clean(await title_el.inner_text() if title_el else '')
            if not title:
                return None

            # Company
            company_el = await card.query_selector('[data-testid="company-name"], .companyName, span[data-testid="company-name"]')
            company = self._clean(await company_el.inner_text() if company_el else '')

            # Location
            loc_el = await card.query_selector('[data-testid="job-location"], .companyLocation')
            location = self._clean(await loc_el.inner_text() if loc_el else '')

            # Remote type
            remote_type = ''
            remote_el = await card.query_selector('[data-testid="attribute_snippet_testid"]')
            if remote_el:
                rt = self._clean(await remote_el.inner_text())
                if any(r in rt.lower() for r in ['remote', 'hybrid', 'on-site']):
                    remote_type = rt

            # URL
            url = f'{BASE_URL}/viewjob?jk={jk}'

            # Salary (sometimes in card)
            salary_min, salary_max = None, None
            salary_el = await card.query_selector('[data-testid="attribute_snippet_testid"]:first-child, .salary-snippet-container, [data-testid="salary-snippet"]')
            if salary_el:
                sal_text = await salary_el.inner_text()
                salary_min, salary_max = self._parse_salary(sal_text)

            # Posted date
            date_el = await card.query_selector('[data-testid="myJobsStateDate"], .date')
            posted_date = self._clean(await date_el.inner_text() if date_el else '')

            return {
                'external_id': external_id,
                'source': 'indeed',
                'title': title,
                'company': company,
                'location': location,
                'remote_type': remote_type or ('Remote' if 'remote' in location.lower() else ''),
                'url': url,
                'description': '',  # fetched separately
                'salary_min': salary_min,
                'salary_max': salary_max,
                'posted_date': posted_date,
                'easy_apply': 0,
            }
        except Exception as e:
            logger.debug(f'Indeed card parse error: {e}')
            return None

    async def get_job_detail(self, url: str, page: Page) -> dict:
        """Fetch full job description from detail page."""
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=25000)
            await page.wait_for_timeout(1500)

            content = await page.content()
            if self._detect_captcha(content):
                logger.warning(f'Indeed: CAPTCHA on detail page {url}')
                return {}

            desc_el = await page.query_selector(
                '#jobDescriptionText, [data-testid="jobsearch-JobComponent-description"], .jobDescription'
            )
            if desc_el:
                description = await desc_el.inner_text()
            else:
                description = ''

            return {'description': self._clean(description)}
        except Exception as e:
            logger.debug(f'Indeed detail error for {url}: {e}')
            return {}
