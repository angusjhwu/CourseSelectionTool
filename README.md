# CourseSelectionTool

A course selection tool for UofT Engineering courses.

## Data Format

### `data/course_db.json`

The course database uses a normalized structure with course sets:

```json
{
  "metadata": {
    "generated_at": "ISO8601 timestamp",
    "total_courses": 97
  },
  "courses": [
    {
      "code": "ECE244H1",
      "title": "Programming Fundamentals",
      "session": "F",
      "prerequisites": "ECE244H1_p1",
      "corequisites": null,
      "exclusions": null
    }
  ],
  "coursesets": {
    "ECE244H1_p1": {"courses": "APS105H1"}
  }
}
```

**Course Sets**: All requirements (prerequisites, corequisites, exclusions) reference course set IDs using the format `{course_code}_{p|c|e}{number}`. The actual course strings are stored in the `coursesets` section.

**Operators**:
- `/` = OR (any one course satisfies)
- `&` = AND (all courses required)

**Example**: `"APS360H1_p1 & APS360H1_p2"` means both course sets must be satisfied, where `APS360H1_p1` might contain `"APS105H1 / APS106H1"` (either course works).

## Running Locally

The frontend uses ES6 modules, which require a local server (they won't work via `file://`).

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000/src/ in your browser.