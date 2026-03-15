"""
JobSniper — Abstract scraper base class.
All scrapers return list[dict] matching the jobs table columns.
"""
import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.scraping_cfg = config.get('scraping', {})
        self.base_delay = self.scraping_cfg.get('delay_between_requests_seconds', 1)
        self.page_delay = self.scraping_cfg.get('delay_between_pages_seconds', 3)
        self.headless = self.scraping_cfg.get('headless', True)
        self.user_agent = self.scraping_cfg.get('user_agent', 'Mozilla/5.0')
        self.max_jobs = self.scraping_cfg.get('max_jobs_per_run', 100)
        self._rate_limited = False

    @abstractmethod
    async def scrape(self) -> list[dict]:
        """Run all configured queries and return list of job dicts."""
        ...

    @abstractmethod
    async def get_job_detail(self, url: str, page) -> dict:
        """Fetch detailed job info from a single listing URL."""
        ...

    async def _delay(self, base: Optional[float] = None) -> None:
        """Sleep with random jitter."""
        d = base if base is not None else self.base_delay
        jitter = random.uniform(0, 2.0)
        await asyncio.sleep(d + jitter)

    async def _page_delay(self) -> None:
        await self._delay(self.page_delay)

    def _detect_captcha(self, content: str) -> bool:
        indicators = [
            'captcha', 'robot', 'verify you are human',
            'cloudflare', 'access denied', 'unusual traffic',
            'security check', 'please verify',
        ]
        cl = content.lower()
        return any(ind in cl for ind in indicators)

    def _detect_rate_limit(self, content: str, status: int = 200) -> bool:
        if status in (429, 503):
            return True
        indicators = ['too many requests', 'rate limit', 'slow down']
        cl = content.lower()
        return any(ind in cl for ind in indicators)

    def _make_external_id(self, source: str, identifier: str) -> str:
        return f'{source}::{identifier}'

    @staticmethod
    def _clean(text: Optional[str]) -> str:
        if not text:
            return ''
        return ' '.join(text.split())

    @staticmethod
    def _parse_salary(text: str) -> tuple[Optional[int], Optional[int]]:
        """Extract (min, max) salary integers from a salary string."""
        import re
        if not text:
            return None, None
        text = text.replace(',', '').replace('$', '').lower()
        # Match patterns like 80k-100k, 80,000-100,000, $80k/yr
        nums = re.findall(r'(\d+(?:\.\d+)?)\s*k?', text)
        if not nums:
            return None, None
        vals = []
        for n in nums[:2]:
            v = float(n)
            if v < 1000:
                v *= 1000  # convert k to full number
            vals.append(int(v))
        if len(vals) == 1:
            return vals[0], None
        return min(vals), max(vals)
