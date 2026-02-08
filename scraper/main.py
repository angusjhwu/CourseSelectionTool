"""UofT ECE Course Scraper — entry point.

Usage:
    python scraper/main.py
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from scraper.listing_scraper import scrape_listing_page
from scraper.course_scraper import scrape_course_page, REQUEST_DELAY

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "course_db.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting UofT ECE course scraper")

    # Phase 1: listing page
    logger.info("Scraping listing page...")
    courses = scrape_listing_page()
    logger.info("Found %d course entries on listing page", len(courses))

    # Phase 2: individual course pages
    logger.info("Scraping individual course pages (%.0fs estimated)...", len(courses) * REQUEST_DELAY)
    success = 0
    fail = 0
    for i, course in enumerate(courses):
        logger.info("  [%d/%d] %s", i + 1, len(courses), course["code"])
        scrape_course_page(course)
        if course.get("scrape_error"):
            fail += 1
            logger.warning("    Error: %s", course["scrape_error"])
        else:
            success += 1
        if i < len(courses) - 1:
            time.sleep(REQUEST_DELAY)

    # Phase 3: write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "metadata": {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source": "https://engineering.calendar.utoronto.ca/section/Electrical-and-Computer-Engineering",
            "total_courses": len(courses),
            "successful": success,
            "failed": fail,
        },
        "courses": sorted(courses, key=lambda c: c["code"]),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d courses to %s", len(courses), OUTPUT_PATH)
    logger.info("Done — %d succeeded, %d failed", success, fail)


if __name__ == "__main__":
    main()
