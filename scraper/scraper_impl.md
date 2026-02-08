# Scraper Implementation

## Overview

Python web scraper targeting the UofT ECE Engineering Calendar. Scrapes course listings and individual course pages, outputting a structured JSON database.

**Target:** https://engineering.calendar.utoronto.ca/section/Electrical-and-Computer-Engineering
**Output:** `data/course_db.json`

## Architecture

```
scraper/
├── main.py              # Entry point — orchestrates scraping, writes JSON output
├── listing_scraper.py   # Parses the main listing page tables
├── course_scraper.py    # Parses individual course detail pages
└── requirements.txt     # requests, beautifulsoup4, lxml
```

### Two-phase scraping

1. **Listing page** (`listing_scraper.py`): Fetches the main ECE section page and walks through all `<table>` elements. Extracts course code, title, URL, session (F/S/Y), group (A/B/C/Science-Math), section heading, subcategory (Kernel/Technical Elective), and table hours (lecture/lab/tutorial/weight). Deduplicates courses that appear in both Computer Engineering and Electrical Engineering program tables.

2. **Course pages** (`course_scraper.py`): For each course, fetches its individual page (`/course/{CODE}`) and extracts: credit value, hours string, full description, prerequisites, corequisites, exclusions, academic units (Fall/Winter/Full Year), and program tags. Uses Drupal field CSS classes (e.g. `field--name-field-prerequisite`) for reliable extraction.

### Key design decisions

- **Deduplication by (code, session):** The same courses appear under both CE and EE program listings. We keep only the first occurrence per code+session pair.
- **Rate limiting:** 1.5s delay between individual page requests to be polite to the server.
- **Retry with backoff:** Failed requests retry up to 3 times with exponential backoff.
- **Optional fields:** All detail fields (prerequisites, corequisites, etc.) gracefully return `null` when absent.

## Data Schema

Top-level JSON structure:

```json
{
  "metadata": {
    "scraped_at": "2026-02-08T...",
    "source": "https://engineering.calendar.utoronto.ca/section/Electrical-and-Computer-Engineering",
    "total_courses": 112,
    "successful": 112,
    "failed": 0
  },
  "courses": [...]
}
```

Per-course fields:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `code` | string | listing | Course code (e.g. "ECE302H1") |
| `title` | string | listing | Course title |
| `url` | string | listing | Full URL to course page |
| `department` | string | listing | Department prefix (ECE, APS, BME, etc.) |
| `session` | string | listing | F (Fall), S (Winter), Y (Full Year), F/S |
| `group` | string\|null | listing | "Group A Courses", "Group B Courses", "Group C Courses", "SCIENCE/MATH ELECTIVES", or null for core courses |
| `section` | string\|null | listing | Table header (e.g. "Fall Session – Year 1") |
| `subcategory` | string\|null | listing | "KERNEL COURSES" or "TECHNICAL ELECTIVES" |
| `lecture` | float\|null | listing | Weekly lecture hours |
| `lab` | float\|null | listing | Weekly lab hours |
| `tutorial` | float\|null | listing | Weekly tutorial hours |
| `weight` | float\|null | listing | Course weight (typically 0.50) |
| `credit_value` | float\|null | course page | Fixed credit value |
| `hours` | string\|null | course page | Hours string (e.g. "36.6L/24.4T") |
| `description` | string\|null | course page | Full course description |
| `prerequisites` | string\|null | course page | Prerequisite text |
| `corequisites` | string\|null | course page | Corequisite text |
| `exclusions` | string\|null | course page | Exclusion text |
| `academic_units` | object\|null | course page | `{ "fall": 48.1, "winter": 48.1, "full_year": 96.2 }` |
| `program_tags` | string[] | course page | List of program tag strings |

## Usage

```bash
# Install dependencies
python3 -m venv scraper/.venv
scraper/.venv/bin/pip install -r scraper/requirements.txt

# Run scraper
scraper/.venv/bin/python -m scraper.main
```

Runtime: ~3 minutes (1.5s delay × ~112 courses).

## HTML Parsing Details

### Listing page structure
- Each program (CE, EE) has its own set of tables organized by year/session
- Tables use `<th>` for the header row (section name + column labels)
- Mid-table `<td>` rows with no links serve as section breaks or subcategory labels
- Group labels (A/B/C) appear in `<p>` tags immediately before their table
- "SCIENCE/MATH ELECTIVES" label appears in `<p>` before the science/math tables

### Course page structure (Drupal)
- Title: `<h1 class="page-title">ECE302H1: Probability and Applications</h1>`
- Fields use consistent CSS class pattern: `field--name-field-{fieldname}`
- Field values in nested `<div class="field__item">`
- Prerequisites contain `<a>` links to other course pages
- Description in `<p>` tags within the field item div
