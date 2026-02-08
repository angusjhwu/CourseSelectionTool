"""
Simplifies course_db_full.json by merging duplicate courses and keeping only essential fields.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# Define the project root and file paths
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "course_db_full.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "course_db.json"

# Fields to keep in the simplified database
KEEP_FIELDS = [
    "code",
    "title",
    "url",
    "group",
    "session",
    "description",
    "prerequisites",
    "corequisites",
    "exclusions",
]


def simplify_course(course):
    """Extract only the fields we want to keep."""
    return {field: course.get(field) for field in KEEP_FIELDS}


def merge_courses(courses):
    """
    Merge courses with the same code.
    If a course exists in both F and S sessions, merge to session B.
    """
    # Group courses by code
    by_code = defaultdict(list)
    for course in courses:
        by_code[course["code"]].append(course)

    merged = []
    merge_count = 0

    for code, course_list in sorted(by_code.items()):
        if len(course_list) == 1:
            # Single entry, keep as-is
            merged.append(simplify_course(course_list[0]))
        elif len(course_list) == 2:
            # Check if we have F and S sessions
            sessions = {c["session"] for c in course_list}
            if sessions == {"F", "S"}:
                # Merge into session B
                base_course = course_list[0].copy()
                base_course["session"] = "B"
                merged.append(simplify_course(base_course))
                merge_count += 1
                print(f"Merged {code}: F + S → B")
            else:
                # Different sessions, keep both
                for course in course_list:
                    merged.append(simplify_course(course))
                print(f"Warning: {code} has duplicate entries but not F+S: {sessions}")
        else:
            # More than 2 entries - unusual
            print(f"Warning: {code} has {len(course_list)} entries")
            for course in course_list:
                merged.append(simplify_course(course))

    return merged, merge_count


def main():
    print(f"Reading from {INPUT_FILE}...")

    # Load the full database
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    original_count = len(data["courses"])
    print(f"Original course count: {original_count}")

    # Merge and simplify courses
    simplified_courses, merge_count = merge_courses(data["courses"])

    print(f"Simplified course count: {len(simplified_courses)}")
    print(f"Merged {merge_count} duplicate course pairs")

    # Create output structure
    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_file": "course_db_full.json",
            "total_courses": len(simplified_courses),
            "merged_count": merge_count,
        },
        "courses": simplified_courses,
    }

    # Write to output file
    print(f"Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Done!")


if __name__ == "__main__":
    main()
