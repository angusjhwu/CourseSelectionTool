# Phase 3 — Dependency Validation

## Goal

Parse the courseset data into expression trees (ASTs) and validate course placements against prerequisites, corequisites, and exclusions. Show visual feedback (green/red card borders) and a validation panel listing all errors.

## Prerequisites (from Phases 1–2)

These files exist and should be modified:
- `src/js/courseData.js` — `CourseDatabase` with `courses` Map and `coursesets` object
- `src/js/gridManager.js` — `GridManager` with `getCoursesBeforeSemester()`, `getCoursesUpToSemester()`, `getAllPlacedCourses()`
- `src/js/main.js` — app init, `onDrop` callback (currently just logs)
- `src/css/styles.css` — base styles
- `src/index.html` — has `#validation-panel` footer element

## Constraints

- All code in `./src/`
- Data in `./data/course_db.json` — coursesets use `&` (AND) and `/` (OR) operators, with nested courseset references
- No external libraries needed for this phase

## Data Format Reference

Coursesets from `data/course_db.json`:
```json
"ECE435H1_p1": { "courses": "ECE216H1 / ECE355H1" }          // OR
"ECE537H1_p1": { "courses": "ECE355H1 & MIE286H1" }          // AND
"ECE435H1_p6": { "courses": "ECE435H1_p1 & ECE435H1_p2 & ECE435H1_p3 & ECE435H1_p4 & ECE435H1_p5" }  // nested AND of ORs
"ECE464H1_p3": { "courses": "ECE464H1_p1 / ECE464H1_p2" }    // OR of ANDs
```

Courseset ID pattern: `{COURSE_CODE}_{type}{number}` where type is `p` (prerequisite), `c` (corequisite), or `e` (exclusion).

A token is a courseset reference if it matches: `/^[A-Z]{2,4}\d{3}[HY]\d_[pce]\d+$/`

## Files to Create

```
src/js/
└── dependencyGraph.js    ← NEW: courseset parser + validator
```

## Files to Modify

```
src/js/main.js            ← wire validation into onDrop callback
src/css/styles.css         ← add validation visual styles
```

## Detailed Implementation

### 1. `src/js/dependencyGraph.js`

The core algorithm module. Two responsibilities: (1) parse coursesets into ASTs, (2) validate a course placement.

#### AST Node Types

```js
// Node types for the expression tree
// { type: 'COURSE', code: 'ECE244H1' }
// { type: 'OR', children: [node, node, ...] }
// { type: 'AND', children: [node, node, ...] }
```

#### Parser

```js
export class DependencyValidator {
  constructor(courseDatabase) {
    this.db = courseDatabase;
    this.treeCache = new Map();  // courseset ID → parsed AST (cache for performance)
  }

  // Parse a courseset ID into an expression tree
  parseCourseset(setId) {
    if (!setId) return null;
    if (this.treeCache.has(setId)) return this.treeCache.get(setId);

    const cs = this.db.coursesets[setId];
    if (!cs) return null;

    const tree = this.parseExpression(cs.courses);
    this.treeCache.set(setId, tree);
    return tree;
  }

  // Parse an expression string like "A & B & C" or "X / Y"
  parseExpression(expr) {
    const trimmed = expr.trim();

    // Check for AND (split by ' & ')
    if (trimmed.includes(' & ')) {
      const parts = trimmed.split(' & ').map(s => s.trim());
      return {
        type: 'AND',
        children: parts.map(p => this.parseToken(p))
      };
    }

    // Check for OR (split by ' / ')
    if (trimmed.includes(' / ')) {
      const parts = trimmed.split(' / ').map(s => s.trim());
      return {
        type: 'OR',
        children: parts.map(p => this.parseToken(p))
      };
    }

    // Single token
    return this.parseToken(trimmed);
  }

  // Parse a single token — either a courseset reference or a course code
  parseToken(token) {
    // Is it a courseset reference? (e.g., ECE435H1_p1)
    if (/^[A-Z]{2,4}\d{3}[HY]\d_[pce]\d+$/.test(token)) {
      return this.parseCourseset(token);  // recursive expansion
    }
    // It's a course code
    return { type: 'COURSE', code: token };
  }
}
```

**Important:** The parser assumes `&` and `/` do NOT appear in the same expression at the same level (they don't in the current data — mixed logic is handled by nesting coursesets).

#### Validator

```js
  // Validate a requirement tree against a set of completed course codes
  // Returns { satisfied: boolean, missing: MissingInfo[] }
  //
  // MissingInfo for OR: { type: 'OR', options: ['ECE216H1', 'ECE355H1'] }
  //   → "Need one of: ECE216H1, ECE355H1"
  // MissingInfo for AND: { type: 'AND', items: [MissingInfo, ...] }
  //   → each unsatisfied branch
  // MissingInfo for COURSE: { type: 'COURSE', code: 'ECE244H1' }
  //   → "Missing: ECE244H1"

  validate(completedCourses, tree) {
    if (!tree) return { satisfied: true, missing: [] };

    switch (tree.type) {
      case 'COURSE': {
        const sat = completedCourses.has(tree.code);
        return {
          satisfied: sat,
          missing: sat ? [] : [{ type: 'COURSE', code: tree.code }]
        };
      }

      case 'OR': {
        // Any ONE child must be satisfied
        for (const child of tree.children) {
          const result = this.validate(completedCourses, child);
          if (result.satisfied) return { satisfied: true, missing: [] };
        }
        // None satisfied — collect all options as a single OR-miss
        const options = this.collectLeafCodes(tree);
        return {
          satisfied: false,
          missing: [{ type: 'OR', options }]
        };
      }

      case 'AND': {
        // ALL children must be satisfied
        const allMissing = [];
        let allSatisfied = true;
        for (const child of tree.children) {
          const result = this.validate(completedCourses, child);
          if (!result.satisfied) {
            allSatisfied = false;
            allMissing.push(...result.missing);
          }
        }
        return { satisfied: allSatisfied, missing: allMissing };
      }
    }
  }

  // Collect all leaf course codes from a tree (for OR miss reporting)
  collectLeafCodes(tree) {
    if (tree.type === 'COURSE') return [tree.code];
    return tree.children.flatMap(c => this.collectLeafCodes(c));
  }
```

#### Course Placement Validation

```js
  // Validate a single course in the grid
  // Returns { valid: boolean, errors: Error[] }
  // Error: { type: 'prerequisite'|'corequisite'|'exclusion', missing: MissingInfo[] }
  validatePlacement(courseCode, semesterId, gridManager, semesterOrder) {
    const course = this.db.getCourse(courseCode);
    if (!course) return { valid: true, errors: [] };

    const errors = [];

    // Prerequisites: must be in semesters BEFORE this one
    if (course.prerequisites) {
      const completed = gridManager.getCoursesBeforeSemester(semesterId, semesterOrder);
      const prereqTree = this.parseCourseset(course.prerequisites);
      const result = this.validate(completed, prereqTree);
      if (!result.satisfied) {
        errors.push({ type: 'prerequisite', missing: result.missing });
      }
    }

    // Corequisites: must be in semesters BEFORE or IN this one
    if (course.corequisites) {
      const completed = gridManager.getCoursesUpToSemester(semesterId, semesterOrder);
      const coreqTree = this.parseCourseset(course.corequisites);
      const result = this.validate(completed, coreqTree);
      if (!result.satisfied) {
        errors.push({ type: 'corequisite', missing: result.missing });
      }
    }

    // Exclusions: must NOT have taken any excluded course
    if (course.exclusions) {
      const allPlaced = gridManager.getAllPlacedCourses();
      // Remove the course itself from the set (it shouldn't exclude itself)
      allPlaced.delete(courseCode);
      const exclTree = this.parseCourseset(course.exclusions);
      const result = this.validate(allPlaced, exclTree);
      if (result.satisfied) {
        // Exclusion IS satisfied → conflict exists
        const conflicting = this.collectLeafCodes(exclTree)
          .filter(code => allPlaced.has(code));
        errors.push({ type: 'exclusion', conflicting });
      }
    }

    return { valid: errors.length === 0, errors };
  }

  // Validate ALL courses currently in the grid
  // Returns Map<courseCode, { valid, errors }>
  validateAll(gridManager, semesterOrder) {
    const results = new Map();
    for (const semId of semesterOrder) {
      for (const code of gridManager.state[semId]) {
        results.set(code, this.validatePlacement(code, semId, gridManager, semesterOrder));
      }
    }
    return results;
  }
```

### 2. Modify `src/js/main.js`

Wire validation into the drop callback:

```js
import { DependencyValidator } from './dependencyGraph.js';

// After db.load():
const validator = new DependencyValidator(db);

// The semester order array (maintained alongside the grid)
const semesterOrder = ['fall-1', 'winter-1', 'fall-2', 'winter-2',
                       'fall-3', 'winter-3', 'fall-4', 'winter-4'];

// onDrop callback (passed to DragDropManager):
function onDrop() {
  const results = validator.validateAll(gridManager, semesterOrder);
  updateCardStyles(results);
  renderValidationPanel(results);
}
```

**`updateCardStyles(results)`:** For each course card in the grid, set `data-valid="true"` or `data-valid="false"` based on the validation result.

**`renderValidationPanel(results)`:** Render the `#validation-panel` with a list of errors:
```
For each course with errors:
  <div class="validation-error">
    <strong>ECE435H1</strong>: Missing prerequisites
    <ul>
      <li>Need one of: ECE216H1, ECE355H1</li>
      <li>Need one of: ECE302H1, MIE286H1</li>
    </ul>
  </div>
```

Format `MissingInfo` for display:
- `{ type: 'COURSE', code }` → "Missing: {code}"
- `{ type: 'OR', options }` → "Need one of: {options joined by ', '}"

### 3. CSS additions to `src/css/styles.css`

```css
/* Validation states on course cards */
.semester-courses .course-card[data-valid="true"] {
  border-color: #4caf50;
  background: #f1f8e9;
}

.semester-courses .course-card[data-valid="false"] {
  border-color: #e53935;
  background: #ffebee;
}

/* Cards with no requirements (no data-valid attribute) keep default grey border */

/* Validation panel */
.validation-panel:empty { display: none; }

.validation-error {
  padding: 8px 12px;
  margin-bottom: 6px;
  background: #fff3e0;
  border-left: 4px solid #ff9800;
  border-radius: 4px;
  font-size: 13px;
}

.validation-error strong { color: #e65100; }

.validation-error ul {
  margin: 4px 0 0 0;
  padding-left: 20px;
}

.validation-error li { margin: 2px 0; }
```

## Verification

### Test Case 1: Simple prerequisite

1. Drag **APS112H1** (Engineering Strategies & Practice II) into Winter — Year 1
2. It requires `APS112H1_p1` → `APS111H1`
3. **Expected:** Red border, validation panel shows "Missing: APS111H1"
4. Now drag **APS111H1** into Fall — Year 1
5. **Expected:** APS112H1 turns green, validation panel clears

### Test Case 2: Complex nested prerequisites

1. Drag **ECE435H1** into Fall — Year 3 (without any prerequisites)
2. It requires `ECE435H1_p6` → AND of 5 OR coursesets
3. **Expected:** Red border, panel shows 5 "Need one of:" lines:
   - Need one of: ECE216H1, ECE355H1
   - Need one of: ECE302H1, MIE286H1
   - Need one of: ECE335H1, ECE350H1
   - Need one of: ECE231H1, ECE360H1
   - Need one of: ECE320H1, ECE357H1
4. Add one course from each OR group into earlier semesters
5. **Expected:** ECE435H1 turns green

### Test Case 3: Exclusions

1. Drag **ECE430H1** into a semester
2. It has exclusion `ECE430H1_e1` → `ECE530H1`
3. Also drag **ECE530H1** into any semester
4. **Expected:** ECE430H1 shows exclusion error mentioning ECE530H1

### Test Case 4: Removal cascading

1. Set up APS111H1 (Fall Y1) → APS112H1 (Winter Y1) with valid prerequisites
2. Remove APS111H1 from the grid
3. **Expected:** APS112H1 turns red (prerequisite broken)

### Test Case 5: OR between AND coursesets

1. Drag **ECE464H1** into a late semester
2. It requires `ECE464H1_p3` → `ECE464H1_p1 / ECE464H1_p2`
   - `ECE464H1_p1` = `ECE302H1 & ECE316H1 & ECE417H1` (AND)
   - `ECE464H1_p2` = `ECE417H1 & MIE286H1` (AND)
3. Satisfy `ECE464H1_p2` by adding ECE417H1 and MIE286H1 in earlier semesters
4. **Expected:** ECE464H1 turns green (OR is satisfied by p2 path)

### Console verification

After each test, check browser console for errors. The `DependencyValidator.treeCache` should be populated (inspect in DevTools).
