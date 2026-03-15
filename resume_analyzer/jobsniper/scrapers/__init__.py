"""Scraper registry — maps source name to scraper class."""
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .wellfound import WellfoundScraper

SCRAPERS = {
    'indeed': IndeedScraper,
    'linkedin': LinkedInScraper,
    'wellfound': WellfoundScraper,
}
