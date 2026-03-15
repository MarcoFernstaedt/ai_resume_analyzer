"""
JobSniper — Wellfound (formerly AngelList) scraper.
Wellfound shows salary ranges, which we capture.
"""
import logging
import re
from urllib.parse import urlencode

from playwright.async_api import async_playwright, Page

from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = 'https://wellfound.com'


class WellfoundScraper(BaseScraper):
    def __init__(self, config: dict):
        super().__init__(config)
        self.search_cfg = config.get('search', {}).get('wellfound', {})
        self.queries: list[str] = self.search_cfg.get('queries', [])
        self.pages_per_query: int = self.search_cfg.get('pages_per_query', 2)

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
                    logger.info(f'Wellfound: query "{query}" → {len(jobs)} jobs')
                except Exception as e:
                    logger.error(f'Wellfound: query "{query}" failed — {e}')
                await self._page_delay()

            await browser.close()

        return all_jobs[:self.max_jobs]

    async def _scrape_query(self, page: Page, query: str) -> list[dict]:
        jobs: list[dict] = []

        for page_num in range(self.pages_per_query):
            url = f'{BASE_URL}/jobs?{urlencode({"role": query, "remote": "true", "page": page_num + 1})}'

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                content = await page.content()
                if self._detect_captcha(content) or self._detect_rate_limit(content):
                    logger.warning(f'Wellfound: blocked on page {page_num + 1}')
                    self._rate_limited = True
                    break

                cards = await page.query_selector_all(
                    '[data-test="JobListingCard"], .styles_component__9_8XA, [class*="JobListing"]'
                )

                if not cards:
                    # Broader selector fallback
                    cards = await page.query_selector_all('a[href*="/jobs/"] > div')

                if not cards:
                    logger.debug(f'Wellfound: no cards on page {page_num + 1}')
                    break

                for card in cards:
                    try:
                        job = await self._extract_card(card)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f'Wellfound card error: {e}')

                await self._delay()

            except Exception as e:
                logger.error(f'Wellfound page {page_num + 1} error: {e}')
                break

        return jobs

    async def _extract_card(self, card) -> dict | None:
        try:
            # Title
            title_el = await card.query_selector(
                'h2, [data-test="job-title"], a[href*="/jobs/"] span, .styles_title__xpQDw'
            )
            title = self._clean(await title_el.inner_text() if title_el else '')
            if not title:
                return None

            # Company
            company_el = await card.query_selector(
                '[data-test="company-name"], .styles_company__oiB6h, a[href*="/company/"]'
            )
            company = self._clean(await company_el.inner_text() if company_el else '')

            # Location / Remote
            loc_el = await card.query_selector(
                '[data-test="location"], .styles_locations__MXQi1, span[class*="location"]'
            )
            location = self._clean(await loc_el.inner_text() if loc_el else 'Remote')

            # URL
            link_el = await card.query_selector('a[href*="/jobs/"]')
            href = await link_el.get_attribute('href') if link_el else ''
            url = f'{BASE_URL}{href}' if href and href.startswith('/') else href

            # External ID
            match = re.search(r'/jobs/([^/?]+)', url or '')
            slug = match.group(1) if match else (title + company).replace(' ', '-').lower()
            ext_id = self._make_external_id('wellfound', slug)

            # Salary — Wellfound often shows $80k-$120k
            sal_el = await card.query_selector(
                '[data-test="compensation"], span[class*="salary"], span[class*="compensation"]'
            )
            salary_min, salary_max = None, None
            if sal_el:
                sal_text = await sal_el.inner_text()
                salary_min, salary_max = self._parse_salary(sal_text)

            # Description (from card preview)
            desc_el = await card.query_selector('[data-test="description"], p[class*="description"]')
            description = self._clean(await desc_el.inner_text() if desc_el else '')

            return {
                'external_id': ext_id,
                'source': 'wellfound',
                'title': title,
                'company': company,
                'location': location,
                'remote_type': 'Remote' if 'remote' in location.lower() else 'Hybrid',
                'url': url or '',
                'description': description,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'posted_date': '',
                'easy_apply': 0,
            }
        except Exception as e:
            logger.debug(f'Wellfound card parse: {e}')
            return None

    async def get_job_detail(self, url: str, page: Page) -> dict:
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=25000)
            await page.wait_for_timeout(2000)

            content = await page.content()
            if self._detect_captcha(content):
                return {}

            desc_el = await page.query_selector(
                '[data-test="JobDescription"], .styles_description__vDBAN, section[class*="description"]'
            )
            description = self._clean(await desc_el.inner_text() if desc_el else '')

            # Try to get salary if not on card
            sal_el = await page.query_selector('[data-test="salary-range"], span[class*="salary"]')
            salary_min, salary_max = None, None
            if sal_el:
                salary_min, salary_max = self._parse_salary(await sal_el.inner_text())

            result = {'description': description}
            if salary_min:
                result['salary_min'] = salary_min
            if salary_max:
                result['salary_max'] = salary_max
            return result
        except Exception as e:
            logger.debug(f'Wellfound detail error {url}: {e}')
            return {}
