"""Scraper registry — Phase 1: Indeed only."""
from .indeed import IndeedScraper

SCRAPERS = {
    'indeed': IndeedScraper,
}
