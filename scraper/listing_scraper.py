"""Scrapes the main ECE listing page for course tables, groups, and semesters."""

import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://engineering.calendar.utoronto.ca"
LISTING_URL = f"{BASE_URL}/section/Electrical-and-Computer-Engineering"


def scrape_listing_page():
    """Fetch the listing page and extract all course entries from tables.

    Returns a list of dicts, each with keys:
        code, title, url, department, session, group, section, subcategory,
        lecture, lab, tutorial, weight
    """
    resp = requests.get(LISTING_URL, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    courses = []
    seen = set()  # (code, session) to deduplicate across CE/EE programs

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # Determine group from previous sibling <p> (e.g. "Group A Courses")
        group = _find_group_label(table)

        # The first row header tells us the section (e.g. "Fall Session – Year 1")
        header_cell = rows[0].find(["td", "th"])
        section = header_cell.get_text(strip=True) if header_cell else None

        subcategory = None  # KERNEL COURSES, TECHNICAL ELECTIVES, etc.

        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            first_text = cells[0].get_text(strip=True)

            # Check for mid-table section break (e.g. "Winter Term – Year 3 or 4")
            if _is_section_header(first_text):
                section = first_text
                subcategory = None
                continue

            # Check for subcategory row (KERNEL COURSES, TECHNICAL ELECTIVES, etc.)
            if _is_subcategory(first_text):
                subcategory = _normalize_whitespace(first_text)
                continue

            # Otherwise it should be a course row
            link = cells[0].find("a")
            if not link:
                continue

            code, title = _parse_course_link(link)
            if not code:
                continue

            session_val = cells[1].get_text(strip=True)
            key = (code, session_val)
            if key in seen:
                continue
            seen.add(key)

            href = link["href"]
            url = href if href.startswith("http") else f"{BASE_URL}{href}"

            courses.append({
                "code": code,
                "title": title,
                "url": url,
                "department": re.match(r"([A-Z]+)", code).group(1),
                "session": session_val,
                "group": group,
                "section": _normalize_whitespace(section) if section else None,
                "subcategory": subcategory,
                "lecture": _parse_hours(cells[2]),
                "lab": _parse_hours(cells[3]),
                "tutorial": _parse_hours(cells[4]),
                "weight": _parse_hours(cells[5]),
            })

    return courses


def _find_group_label(table):
    """Walk previous siblings to find a group label like 'Group A Courses'."""
    node = table.find_previous_sibling()
    # Look back a few siblings (sometimes there are whitespace nodes)
    for _ in range(5):
        if node is None:
            break
        text = node.get_text(strip=True)
        if re.search(r"Group\s+[A-Z]", text, re.IGNORECASE):
            return text
        if "SCIENCE/MATH ELECTIVES" in text.upper():
            return text
        # Stop searching if we hit another table or heading
        if node.name in ("table", "h2"):
            break
        node = node.find_previous_sibling()
    return None


def _is_section_header(text):
    """Check if a row's first cell is a section header like 'Winter Term – Year 3 or 4'."""
    normalized = _normalize_whitespace(text).lower()
    return bool(re.search(r"(fall|winter|required)\s+(session|term|course)", normalized))


def _is_subcategory(text):
    """Check if a row is a subcategory label like 'KERNEL COURSES'."""
    normalized = _normalize_whitespace(text).upper()
    return normalized in (
        "KERNEL COURSES",
        "TECHNICAL ELECTIVES",
    ) or "KERNEL" in normalized or "ELECTIVE" in normalized


def _parse_course_link(link_tag):
    """Extract (code, title) from a link like 'ECE302H1: Probability and Applications'."""
    text = link_tag.get_text(strip=True)
    # The link text is just the code; the title follows after ": " in the parent cell
    full_text = link_tag.parent.get_text(strip=True)
    match = re.match(r"([A-Z]{2,4}\d{3}[HY]\d)\s*:\s*(.+)", full_text)
    if match:
        return match.group(1), match.group(2)
    return text, ""


def _parse_hours(cell):
    """Parse a numeric cell value, returning float or None for '-'."""
    text = cell.get_text(strip=True)
    if text == "-" or text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_whitespace(text):
    """Replace non-breaking spaces and multiple spaces with single space."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
