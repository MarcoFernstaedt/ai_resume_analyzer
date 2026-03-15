"""
JobSniper — LinkedIn scraper.
Scrapes public LinkedIn job listings. Does NOT auto-click Easy Apply.
Flags easy_apply=1 for listings with the Easy Apply badge.
"""
import logging
from urllib.parse import urlencode

from playwright.async_api import async_playwright, Page

from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.linkedin.com'


class LinkedInScraper(BaseScraper):
    def __init__(self, config: dict):
        super().__init__(config)
        self.search_cfg = config.get('search', {}).get('linkedin', {})
        self.queries: list[str] = self.search_cfg.get('queries', [])
        self.pages_per_query: int = self.search_cfg.get('pages_per_query', 2)
        self.easy_apply_only: bool = self.search_cfg.get('easy_apply_only', False)

    async def scrape(self) -> list[dict]:
        if not self.queries:
            return []

        all_jobs: list[dict] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=self.user_agent,
                viewport={'width': 1440, 'height': 900},
            )
            page = await context.new_page()

            for query in self.queries:
                if len(all_jobs) >= self.max_jobs or self._rate_limited:
                    break
                try:
                    jobs = await self._scrape_query(page, query)
                    all_jobs.extend(jobs)
                    logger.info(f'LinkedIn: query "{query}" → {len(jobs)} jobs')
                except Exception as e:
                    logger.error(f'LinkedIn: query "{query}" failed — {e}')
                await self._page_delay()

            await browser.close()

        return all_jobs[:self.max_jobs]

    async def _scrape_query(self, page: Page, query: str) -> list[dict]:
        jobs: list[dict] = []

        for page_num in range(self.pages_per_query):
            params = {
                'keywords': query,
                'location': 'United States',
                'f_WT': '2',  # Remote
                'start': page_num * 25,
            }
            if self.easy_apply_only:
                params['f_LF'] = 'f_AL'  # Easy Apply filter

            url = f'{BASE_URL}/jobs/search/?{urlencode(params)}'

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                content = await page.content()
                if self._detect_captcha(content) or self._detect_rate_limit(content):
                    logger.warning(f'LinkedIn: blocked on page {page_num + 1}')
                    self._rate_limited = True
                    break

                # LinkedIn public job listings
                cards = await page.query_selector_all(
                    '.jobs-search__results-list li, .job-search-card, [data-entity-urn*="jobPosting"]'
                )

                if not cards:
                    logger.debug(f'LinkedIn: no cards on page {page_num + 1}')
                    break

                for card in cards:
                    try:
                        job = await self._extract_card(card)
                        if job:
                            # Fetch description
                            if job.get('url'):
                                detail = await self.get_job_detail(job['url'], page)
                                job.update(detail)
                                await self._delay()
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f'LinkedIn card error: {e}')

                await self._delay()

            except Exception as e:
                logger.error(f'LinkedIn page {page_num + 1} error: {e}')
                break

        return jobs

    async def _extract_card(self, card) -> dict | None:
        try:
            # Title
            title_el = await card.query_selector(
                'h3.base-search-card__title, .job-search-card__title, h3 a'
            )
            title = self._clean(await title_el.inner_text() if title_el else '')
            if not title:
                return None

            # Company
            company_el = await card.query_selector(
                'h4.base-search-card__subtitle, .job-search-card__subtitle-link, h4 a'
            )
            company = self._clean(await company_el.inner_text() if company_el else '')

            # Location
            loc_el = await card.query_selector(
                '.job-search-card__location, span.job-result-card__location'
            )
            location = self._clean(await loc_el.inner_text() if loc_el else '')

            # URL
            link_el = await card.query_selector('a.base-card__full-link, a[href*="/jobs/view/"]')
            url = ''
            if link_el:
                href = await link_el.get_attribute('href') or ''
                url = href.split('?')[0] if href else ''

            # External ID from URL
            import re
            match = re.search(r'/jobs/view/(\d+)', url)
            ext_id = self._make_external_id('linkedin', match.group(1) if match else url)

            # Easy Apply badge
            easy_el = await card.query_selector('.job-search-card__easy-apply-label, [aria-label*="Easy Apply"]')
            easy_apply = 1 if easy_el else 0

            # Posted date
            date_el = await card.query_selector('time, .job-search-card__listdate')
            posted_date = ''
            if date_el:
                posted_date = (await date_el.get_attribute('datetime') or
                               self._clean(await date_el.inner_text()))

            return {
                'external_id': ext_id,
                'source': 'linkedin',
                'title': title,
                'company': company,
                'location': location,
                'remote_type': 'Remote' if 'remote' in location.lower() else '',
                'url': url,
                'description': '',
                'salary_min': None,
                'salary_max': None,
                'posted_date': posted_date,
                'easy_apply': easy_apply,
            }
        except Exception as e:
            logger.debug(f'LinkedIn card parse: {e}')
            return None

    async def get_job_detail(self, url: str, page: Page) -> dict:
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=25000)
            await page.wait_for_timeout(2000)

            content = await page.content()
            if self._detect_captcha(content):
                return {}

            desc_el = await page.query_selector(
                '.description__text, .jobs-description__content, #job-details'
            )
            description = self._clean(await desc_el.inner_text() if desc_el else '')

            return {'description': description}
        except Exception as e:
            logger.debug(f'LinkedIn detail error {url}: {e}')
            return {}
