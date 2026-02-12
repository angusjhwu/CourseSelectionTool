# Stack Implementation Specification

## 1. Technology Stack

### Core: Vanilla JS (ES6 Modules) + HTML + CSS

No framework. No build step. No npm.

**Why:** You write `.html`, `.css`, and `.js` files, open `index.html` in a browser, and it works. ES6 `import`/`export` statements give you modular code organization without needing a bundler. Chrome DevTools shows your actual source code with matching line numbers.

**Comparison with alternatives:**

| Option | Build step? | Learning curve | Rationale for skipping |
|--------|------------|----------------|----------------------|
| Vanilla JS | No | Lowest | **Selected** |
| React | Yes (Vite/Webpack) | High (JSX, hooks, state) | Too much toolchain for a first project |
| Svelte | Yes (compiler) | Medium | Compiler magic is opaque to debug |
| Vue | Yes (SFCs) | Medium | Still needs build for single-file components |
| Python via Pyodide | No | Medium | 10+ MB WASM download, slow startup |

### External Libraries (loaded via CDN `<script>` tags)

| Library | Purpose | Size | Why this one |
|---------|---------|------|-------------|
| [SortableJS](https://sortablejs.github.io/Sortable/) | Drag-and-drop | ~30 KB | Pure vanilla JS, no framework dependency, mobile touch support built-in |
| [Tippy.js](https://atomiks.github.io/tippyjs/) | Tooltips | ~10 KB | Lightweight, works with vanilla JS, handles positioning automatically |

No other dependencies.

---

## 2. Project Structure

```
src/
├── index.html              ← entry point (open in browser)
├── css/
│   └── styles.css          ← all styles
├── js/
│   ├── main.js             ← app init, wires everything together
│   ├── courseData.js        ← loads course_db.json, indexes courses
│   ├── dependencyGraph.js  ← parses coursesets, validates prerequisites
│   ├── gridManager.js      ← semester grid state + rendering
│   ├── dragDrop.js         ← SortableJS integration
│   └── fileIO.js           ← save/load plan as JSON file
└── data/
    └── course_db.json      ← copied from /data/course_db.json
```

**Key rule:** `src/` is self-contained. It can be deployed as-is to any static host.

---

## 3. Data Model

### Course Database (loaded at startup)

Source: `data/course_db.json` — 97 courses, pre-scraped.

```
Course {
  code: string          "ECE244H1"
  title: string         "Programming Fundamentals"
  group: string|null    "A" | "B" | "C" | "MATH" | "SCIENCE" | null
  session: string       "F" (fall) | "S" (winter) | "B" (both)
  description: string
  prerequisites: string|null    courseset ID, e.g. "APS360H1_p4"
  corequisites: string|null     courseset ID
  exclusions: string|null       courseset ID
}
```

### Coursesets (requirement expressions)

Coursesets encode prerequisite logic using two operators:
- `/` = **OR** (any one satisfies)
- `&` = **AND** (all must be satisfied)

Coursesets can reference other coursesets, creating nested expressions:

```
Simple:    ECE244H1_p1  →  "APS105H1"
OR:        APS360H1_p1  →  "APS105H1 / APS106H1 / ESC180H1 / CSC180H1"
AND:       ECE537H1_p1  →  "ECE355H1 & MIE286H1"
Nested:    ECE435H1_p6  →  "ECE435H1_p1 & ECE435H1_p2 & ... & ECE435H1_p5"
                            (each p1–p5 is itself an OR courseset)
Mixed:     ECE464H1_p3  →  "ECE464H1_p1 / ECE464H1_p2"
                            (OR between two AND coursesets)
```

### Grid State (in-memory)

The planner grid is a list of semesters, each containing course codes:

```
GridState {
  semesters: [
    { id: "fall-1", label: "Fall — Year 1", courses: ["APS105H1", "APS111H1", ...] },
    { id: "winter-1", label: "Winter — Year 1", courses: ["APS112H1", "ECE244H1", ...] },
    ...
  ]
}
```

Default: 8 semesters (Fall + Winter for years 1–4). Users can add/remove.

### Saved Plan (JSON file)

```json
{
  "version": "1.0",
  "created": "2026-02-11T10:00:00Z",
  "semesters": [
    { "id": "fall-1", "label": "Fall — Year 1", "courses": ["APS105H1", "APS111H1"] },
    { "id": "winter-1", "label": "Winter — Year 1", "courses": ["APS112H1"] }
  ]
}
```

---

## 4. Dependency Validation Algorithm

### Step 1: Parse coursesets into expression trees

On page load, parse each courseset into an AST (abstract syntax tree). Each node is one of:

```
COURSE { code: "ECE244H1" }
OR     { children: [node, node, ...] }
AND    { children: [node, node, ...] }
```

**Parsing rule:** Split by `&` first (AND), then by `/` (OR) within each term. If a token matches the pattern `XXX###H1_[pce]#` it's a courseset reference — recursively expand it.

**Example:** `ECE435H1_p6` → `"ECE435H1_p1 & ECE435H1_p2 & ECE435H1_p3 & ECE435H1_p4 & ECE435H1_p5"`

Parses to:
```
AND
├─ OR [ECE216H1, ECE355H1]        ← expanded from ECE435H1_p1
├─ OR [ECE302H1, MIE286H1]        ← expanded from ECE435H1_p2
├─ OR [ECE335H1, ECE350H1]        ← expanded from ECE435H1_p3
├─ OR [ECE231H1, ECE360H1]        ← expanded from ECE435H1_p4
└─ OR [ECE320H1, ECE357H1]        ← expanded from ECE435H1_p5
```

Cache parsed trees — they don't change at runtime.

### Step 2: Validate against completed courses

Given a set of completed course codes and a requirement tree:

```
validate(completedCourses, node):
  COURSE → return completedCourses.has(node.code)
  OR     → return ANY child is satisfied
  AND    → return ALL children are satisfied
```

For error reporting, collect missing courses:
- **OR miss:** list all options (user needs at least one)
- **AND miss:** list each unsatisfied branch

### Step 3: Check placement rules

When a course is placed in semester S:

| Check | "Completed" set |
|-------|----------------|
| **Prerequisites** | All courses in semesters **before** S |
| **Corequisites** | All courses in semesters **before or in** S |
| **Exclusions** | All courses in **any** semester — if the exclusion tree evaluates to `true`, there's a conflict |

### Step 4: Session validation

Additionally, check that a course's `session` field matches its semester:
- `"F"` → can only be placed in Fall semesters
- `"S"` → can only be placed in Winter semesters
- `"B"` → can be placed in either

### Complexity

For N courses in the plan, with M coursesets of average depth D:
- Single validation: O(D) tree traversal (D is small, typically 1–3 levels)
- Full revalidation after a drop: O(N × D) — runs instantly for 97 courses

---

## 5. UI Layout

```
┌────────────────────────────────────────────────────────────────┐
│  Course Selection Tool                     [Save] [Load] [Clear]│
├────────────┬───────────────────────────────────────────────────┤
│            │                                                    │
│  SIDEBAR   │  PLANNER GRID                                     │
│            │                                                    │
│  [Search]  │  ┌─────────┬─────────┬─────────┬─────────┐       │
│  [Filters] │  │ Fall    │ Winter  │ Fall    │ Winter  │ ...   │
│            │  │ Year 1  │ Year 1  │ Year 2  │ Year 2  │       │
│  ┌───────┐ │  ├─────────┼─────────┼─────────┼─────────┤       │
│  │ECE244 │ │  │┌───────┐│         │         │         │       │
│  │Prog F.│ │  ││APS105 ││         │         │         │       │
│  ├───────┤ │  │├───────┤│         │         │         │       │
│  │ECE241 │ │  ││APS111 ││         │         │         │       │
│  │Digital│ │  │└───────┘│         │         │         │       │
│  ├───────┤ │  │         │         │         │         │       │
│  │...    │ │  └─────────┴─────────┴─────────┴─────────┘       │
│  └───────┘ │                                                    │
│            │  [+ Add Semester]                                  │
│  Groups:   │                                                    │
│  [A][B][C] │  VALIDATION PANEL                                 │
│  [MATH]    │  ⚠ ECE435H1: Missing prerequisites               │
│  [SCIENCE] │    Need one of: ECE216H1, ECE355H1               │
│            │    Need one of: ECE302H1, MIE286H1               │
└────────────┴───────────────────────────────────────────────────┘
```

### Sidebar

- **Search box:** filters course list by code or title (case-insensitive substring match)
- **Group filter buttons:** toggle visibility by group (A, B, C, MATH, SCIENCE, ungrouped)
- **Session filter:** toggle F / S / B
- **Course cards:** show code + abbreviated title, draggable into grid
- Dragging from sidebar **clones** (course stays in sidebar list)

### Planner Grid

- **CSS Grid** layout: `grid-template-columns: repeat(N, minmax(160px, 1fr))`
- Each column is a semester drop zone (SortableJS group)
- Column header: editable label (default "Fall — Year 1", etc.)
- Courses within a column can be reordered (visual only, order doesn't affect validation)
- Courses can be dragged between columns
- Right-click or X button to remove a course from the grid

### Course Cards (in grid)

- Border color: green (valid), red (invalid), grey (no requirements to check)
- Hover: Tippy.js tooltip showing course title + any validation errors
- Click: expand to show full description + prerequisites in readable form

### Validation Panel

- Appears below the grid
- Lists all courses with validation errors
- For each error: course code, error type (prerequisite/corequisite/exclusion/session), details
- Updates live on every grid change

### Add/Remove Semesters

- "+" button adds a semester column at the end
- Each column has a delete button (only if empty, or with confirmation if courses present)

---

## 6. Drag-and-Drop Behavior

### SortableJS Configuration

```
Sidebar list:
  group: { name: "courses", pull: "clone", put: false }
  sort: false   (sidebar order is fixed)

Each semester column:
  group: { name: "courses", pull: true, put: true }
  sort: true    (reorder within column)
```

### Event Flow

1. User drags a course card from sidebar or another column
2. SortableJS `onEnd` fires with source + destination info
3. Update `GridState` (add to destination, remove from source if not clone)
4. Run full validation pass on all courses in grid
5. Re-render card border colors + validation panel
6. If session mismatch (e.g., Fall-only course dropped in Winter), show immediate feedback

### Edge Cases

- **Duplicate:** If a course is already in the grid, reject the drop (flash the existing card)
- **Remove:** Drag to a trash zone or click X → remove from grid, revalidate everything (removing a course may break other courses' corequisites)

---

## 7. File I/O

### Save (Download)

1. Serialize `GridState` to the saved plan JSON format
2. Create a `Blob` with MIME type `application/json`
3. Create a temporary `<a>` element with `href = URL.createObjectURL(blob)` and `download` attribute
4. Programmatically click it
5. Revoke the object URL

Filename: `course-plan-YYYY-MM-DD.json`

### Load (Upload)

1. Hidden `<input type="file" accept=".json">` triggered by Load button
2. Read file with `FileReader` or `file.text()`
3. Parse JSON, validate `version` field
4. Verify all course codes exist in the database (warn about unknown codes)
5. Set `GridState` from loaded data
6. Re-render grid + run full validation

### Auto-save (post-MVP)

Store `GridState` in `localStorage` on every change. Restore on page load if no file is explicitly loaded.

### Share via URL (post-MVP)

Encode the plan as base64 in the URL hash: `#plan=eyJ2ZXJzaW9uIj...`
Allows sharing a link without a backend. Limit: ~2000 characters in URL (enough for ~50 courses).

---

## 8. Hosting

### GitHub Pages

- **Cost:** Free
- **Setup:** Repository Settings → Pages → Source: `main` branch, folder: `/src`
- **URL:** `https://<username>.github.io/CourseSelectionTool/`
- **Deploy:** Push to `main` → site updates automatically
- **HTTPS:** Included by default
- **Custom domain:** Optional, configure via CNAME file

No build step. GitHub serves the static files in `/src` directly.

**Alternative:** Netlify (also free, drag-and-drop deploy, slightly easier custom domains).

---

## 9. Build Sequence

### Phase 1 — Static Display

**Goal:** Load data and render UI skeleton.

- Create `index.html` with sidebar + grid layout
- Write `courseData.js`: fetch `course_db.json`, build `Map<code, course>`
- Render course cards in sidebar
- Render 8 empty semester columns
- Basic CSS styling

**Test:** Open `index.html` in browser, see course list and grid.

### Phase 2 — Drag-and-Drop

**Goal:** Courses can be moved between sidebar and grid.

- Add SortableJS via CDN
- Write `dragDrop.js`: initialize SortableJS on sidebar + each column
- Write `gridManager.js`: track which courses are in which semester
- Handle clone from sidebar, move between columns, remove

**Test:** Drag courses around. Grid state updates correctly (log to console).

### Phase 3 — Dependency Validation

**Goal:** Prerequisites are checked and errors are shown.

- Write `dependencyGraph.js`: courseset parser + validator
- On every drop, validate all courses in grid
- Set card border colors (green/red)
- Render validation panel with error details

**Test:** Place ECE435H1 in Year 3 without its prerequisites → red border, panel shows 5 missing requirement groups. Add the prerequisites in earlier semesters → turns green.

### Phase 4 — UI Polish

**Goal:** Usable, polished interface.

- Add search box with real-time filtering
- Add group/session filter buttons
- Add Tippy.js tooltips on course cards
- Add course detail view (click to expand)
- Session validation (F/S course in wrong semester)
- Responsive CSS for smaller screens

**Test:** Search "ECE3", filter by group B, hover over invalid course to see tooltip.

### Phase 5 — File I/O

**Goal:** Users can save and restore plans.

- Write `fileIO.js`: export + import functions
- Add Save/Load/Clear buttons in header
- Validate loaded files (version check, unknown course codes)

**Test:** Build a plan, save it, refresh the page, load the file → same plan restored with correct validation state.
