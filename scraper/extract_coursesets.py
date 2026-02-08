#!/usr/bin/env python3
"""
Extract course sets from prerequisites, corequisites, and exclusions.

This script parses bracketed groups in requirement fields and creates
reusable course sets that can be referenced by ID.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def find_matching_bracket(text: str, start: int) -> int:
    """Find the closing bracket matching the opening bracket at start position."""
    if text[start] != '[':
        raise ValueError(f"Expected '[' at position {start}")

    depth = 0
    for i in range(start, len(text)):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return i

    raise ValueError(f"No matching closing bracket found for position {start}")


def extract_coursesets_from_field(
    course_code: str,
    field_value: Optional[str],
    field_type: str
) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Extract bracketed groups from a field and create course sets.

    Args:
        course_code: The course code (e.g., "APS360H1")
        field_value: The field value with brackets (e.g., "[A / B] & [C / D]")
        field_type: 'p' (prerequisites), 'c' (corequisites), or 'e' (exclusions)

    Returns:
        Tuple of (updated_field_value, coursesets_dict)
        - updated_field_value: Field with brackets replaced by set IDs
        - coursesets_dict: Mapping of set_id -> course string
    """
    if not field_value:
        return field_value, {}

    coursesets = {}
    counter = 1
    updated_value = field_value

    # Keep extracting bracketed groups until none remain
    # Process innermost brackets first by finding the last '[' before each ']'
    while '[' in updated_value:
        # Find the innermost bracketed group
        # Strategy: find rightmost '[' that comes before the first ']'
        first_close = updated_value.index(']')

        # Find the last '[' before this ']'
        start = -1
        for i in range(first_close - 1, -1, -1):
            if updated_value[i] == '[':
                start = i
                break

        if start == -1:
            # Malformed brackets - stop extraction
            break

        # Extract the content (without brackets)
        content = updated_value[start + 1:first_close].strip()

        # Create a set ID
        set_id = f"{course_code}_{field_type}{counter}"

        # Store the course set
        coursesets[set_id] = content

        # Replace the bracketed group with the set ID
        # Include the brackets in the replacement to maintain exact positions
        updated_value = updated_value[:start] + set_id + updated_value[first_close + 1:]

        counter += 1

    return updated_value, coursesets


def extract_all_coursesets(courses: List[Dict]) -> Tuple[List[Dict], Dict[str, Dict[str, str]]]:
    """
    Extract all course sets from all courses.

    Args:
        courses: List of course dictionaries

    Returns:
        Tuple of (updated_courses, all_coursesets)
        - updated_courses: Courses with updated requirement fields
        - all_coursesets: Dictionary mapping set_id -> {"courses": "..."}
    """
    all_coursesets = {}
    updated_courses = []

    for course in courses:
        course_code = course['code']
        updated_course = course.copy()

        # Process prerequisites
        if course.get('prerequisites'):
            updated_prereq, prereq_sets = extract_coursesets_from_field(
                course_code,
                course['prerequisites'],
                'p'
            )
            updated_course['prerequisites'] = updated_prereq
            all_coursesets.update(prereq_sets)

        # Process corequisites
        if course.get('corequisites'):
            updated_coreq, coreq_sets = extract_coursesets_from_field(
                course_code,
                course['corequisites'],
                'c'
            )
            updated_course['corequisites'] = updated_coreq
            all_coursesets.update(coreq_sets)

        # Process exclusions
        if course.get('exclusions'):
            updated_excl, excl_sets = extract_coursesets_from_field(
                course_code,
                course['exclusions'],
                'e'
            )
            updated_course['exclusions'] = updated_excl
            all_coursesets.update(excl_sets)

        updated_courses.append(updated_course)

    # Convert coursesets to the required format: {set_id: {"courses": "..."}}
    formatted_coursesets = {
        set_id: {"courses": courses_str}
        for set_id, courses_str in all_coursesets.items()
    }

    return updated_courses, formatted_coursesets


def main():
    """Main execution function."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / 'data' / 'course_db.json'

    print(f"Loading course database from: {db_path}")

    # Load the current database
    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)

    # Extract course sets
    print("Extracting course sets...")
    updated_courses, coursesets = extract_all_coursesets(db['courses'])

    # Update the database structure
    db['courses'] = updated_courses
    db['coursesets'] = coursesets

    # Write back to file
    print(f"Writing updated database with {len(coursesets)} course sets...")
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print(f"✓ Successfully extracted {len(coursesets)} course sets")
    print(f"✓ Updated {len(updated_courses)} courses")

    # Print some statistics
    prereq_sets = sum(1 for k in coursesets if '_p' in k)
    coreq_sets = sum(1 for k in coursesets if '_c' in k)
    excl_sets = sum(1 for k in coursesets if '_e' in k)

    print(f"\nBreakdown:")
    print(f"  - Prerequisite sets: {prereq_sets}")
    print(f"  - Corequisite sets: {coreq_sets}")
    print(f"  - Exclusion sets: {excl_sets}")

    # Show some examples
    print(f"\nExample course sets:")
    for i, (set_id, data) in enumerate(list(coursesets.items())[:5]):
        print(f"  {set_id}: {data['courses']}")
        if i >= 4:
            break


if __name__ == '__main__':
    main()
