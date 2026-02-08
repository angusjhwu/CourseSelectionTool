"""Scrapes individual course pages for detailed information."""

import re
import time
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_DELAY = 1.5  # seconds between requests
MAX_RETRIES = 3
TIMEOUT = 15


def scrape_course_page(course):
    """Enrich a course dict with details from its individual page.

    Adds: credit_value, hours, description, prerequisites, corequisites,
          exclusions, academic_units, program_tags.
    Sets scrape_error on failure.
    """
    url = course["url"]

    resp = _fetch_with_retry(url)
    if resp is None:
        course["scrape_error"] = f"Failed to fetch {url}"
        return course

    soup = BeautifulSoup(resp.text, "lxml")

    course["credit_value"] = _extract_field_text(soup, "field--name-field-credit")
    course["hours"] = _extract_field_text(soup, "field--name-field-hours")
    course["description"] = _extract_description(soup)
    course["prerequisites"] = _extract_field_text(soup, "field--name-field-prerequisite", separator=" ")
    course["corequisites"] = _extract_field_text(soup, "field--name-field-corequisite", separator=" ")
    course["exclusions"] = _extract_field_text(soup, "field--name-field-exclusion", separator=" ")
    course["academic_units"] = _parse_academic_units(
        _extract_field_text(soup, "field--name-field-totalaus")
    )
    course["program_tags"] = _extract_program_tags(soup)

    # Try to parse credit_value as float
    if course["credit_value"]:
        try:
            course["credit_value"] = float(course["credit_value"])
        except ValueError:
            pass

    return course


def _fetch_with_retry(url):
    """Fetch URL with retries and exponential backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait = 2 ** attempt
            logger.warning("Attempt %d failed for %s: %s", attempt + 1, url, e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(wait)
    logger.error("All retries exhausted for %s", url)
    return None


def _extract_field_text(soup, class_name, separator=""):
    """Extract text from a Drupal field div by its class name."""
    div = soup.find("div", class_=class_name)
    if not div:
        return None
    item = div.find("div", class_="field__item")
    if not item:
        return None
    text = item.get_text(separator=separator, strip=True)
    return text if text else None


def _extract_description(soup):
    """Extract the course description text."""
    div = soup.find("div", class_="field--name-field-desc")
    if not div:
        return None
    item = div.find("div", class_="field__item")
    if not item:
        return None
    # Get all paragraph text joined
    paragraphs = item.find_all("p")
    if paragraphs:
        return "\n\n".join(p.get_text(strip=True) for p in paragraphs)
    return item.get_text(strip=True) or None


def _parse_academic_units(text):
    """Parse AU string like '48.1 (Fall), 48.1 (Winter), 96.2 (Full Year)' into dict."""
    if not text:
        return None
    result = {}
    for match in re.finditer(r"([\d.]+)\s*\((\w[\w\s]*?)\)", text):
        value = float(match.group(1))
        label = match.group(2).strip().lower().replace(" ", "_")
        result[label] = value
    return result if result else None


def _extract_program_tags(soup):
    """Extract program tags as a list of strings."""
    div = soup.find("div", class_="field--name-field-program-tags")
    if not div:
        return []
    items = div.find_all("div", class_="field__item")
    return [item.get_text(strip=True) for item in items if item.get_text(strip=True)]
