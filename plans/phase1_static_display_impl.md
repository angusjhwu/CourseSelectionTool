# Phase 1 — Static Display

## Goal

Load the course database and render the full UI skeleton: a sidebar with all 97 courses, placeholder controls, and a planner with 8 semester rows (each containing 5 empty course slots). No interactivity yet — just data loading and rendering.

## Prerequisites

- `data/course_db.json` exists (97 courses, coursesets)
- No prior phases

## Constraints

- All code in `./src/` (HTML, CSS, JS)
- Data stays in `./data/` — JS fetches via relative path `../data/course_db.json`
- No build step. ES6 modules loaded with `<script type="module">`
- External libraries loaded via CDN `<script>` tags (none needed for this phase)

## Files to Create

```
src/
├── index.html          ← entry point
├── css/
│   └── styles.css      ← all styles
└── js/
    ├── main.js         ← app init, wires everything together
    └── courseData.js    ← loads course_db.json, indexes courses
```

## Detailed Implementation

### 1. `src/index.html`

HTML structure with three main regions:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Course Selection Tool</title>
  <link rel="stylesheet" href="css/styles.css">
</head>
<body>
  <header class="header">
    <h1>Course Selection Tool</h1>
    <div class="header-actions">
      <button class="btn" disabled>Load</button>
      <button class="btn" disabled>Save</button>
      <button class="btn" disabled>Clear</button>
    </div>
  </header>

  <main class="app-layout">
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-controls">
        <input class="search-input" type="text" placeholder="Search courses…" disabled>
        <select class="group-filter" disabled>
          <option>All Groups</option>
        </select>
      </div>
      <div class="course-list" id="course-list">
        <!-- Course cards rendered by JS -->
      </div>
    </aside>

    <section class="planner" id="planner">
      <div class="grid-container" id="grid-container">
        <!-- Semester rows rendered by JS -->
      </div>
    </section>
  </main>

  <footer class="validation-panel" id="validation-panel">
    <!-- Validation errors rendered in Phase 3 -->
  </footer>

  <script type="module" src="js/main.js"></script>
</body>
</html>
```

### 2. `src/js/courseData.js`

Responsible for fetching and indexing the course database.

```js
// courseData.js — loads and indexes course_db.json

export class CourseDatabase {
  constructor() {
    this.courses = new Map();      // code → course object
    this.coursesets = {};           // courseset_id → { courses: "..." }
    this.groups = new Set();       // unique group values
  }

  async load() {
    const response = await fetch('../data/course_db.json');
    const data = await response.json();

    for (const course of data.courses) {
      this.courses.set(course.code, course);
      if (course.group) this.groups.add(course.group);
    }

    this.coursesets = data.coursesets || {};
  }

  getCourse(code) { return this.courses.get(code); }
  getAllCourses() { return Array.from(this.courses.values()); }
  getGroups() { return Array.from(this.groups).sort(); }
}
```

### 3. `src/js/main.js`

Entry point that initializes the app.

```js
// main.js — app initialization

import { CourseDatabase } from './courseData.js';

const db = new CourseDatabase();

async function init() {
  await db.load();
  renderSidebar(db.getAllCourses());
  renderGrid();
}

function renderSidebar(courses) {
  const list = document.getElementById('course-list');
  list.innerHTML = '';

  for (const course of courses) {
    const card = document.createElement('div');
    card.className = 'course-card';
    card.dataset.code = course.code;
    card.innerHTML = `
      <span class="course-code">${course.code}</span>
      <span class="course-title">${course.title}</span>
    `;
    list.appendChild(card);
  }
}

function renderGrid() {
  const container = document.getElementById('grid-container');
  container.innerHTML = '';

  const semesters = [];
  for (let year = 1; year <= 4; year++) {
    semesters.push({ id: `fall-${year}`,   label: `Fall — Year ${year}`,   term: 'Fall' });
    semesters.push({ id: `winter-${year}`, label: `Winter — Year ${year}`, term: 'Winter' });
  }

  for (const sem of semesters) {
    const row = document.createElement('div');
    row.className = 'semester-row';
    row.dataset.id = sem.id;

    let slotsHTML = '';
    for (let i = 0; i < 5; i++) {
      slotsHTML += `<div class="course-slot" data-semester="${sem.id}" data-slot="${i}"></div>`;
    }

    row.innerHTML = `
      <div class="semester-label">${sem.label}</div>
      <div class="semester-slots">
        ${slotsHTML}
      </div>
    `;
    container.appendChild(row);
  }
}

init();
```

### 4. `src/css/styles.css`

Layout and basic styling.

**Key layout decisions:**
- `app-layout`: CSS Grid with sidebar (250px fixed) + planner (1fr)
- `grid-container`: vertical stack of semester rows
- Each `semester-row`: label on the left + 5 horizontal course slots
- `course-slot`: rounded rectangle with dashed border (drop target for future phases)
- `course-card`: compact card in sidebar showing code + title

**Specific styles to implement:**

```css
/* Root layout */
body { margin: 0; font-family: system-ui, sans-serif; }

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #1a1a2e;
  color: white;
}
.header h1 { margin: 0; font-size: 18px; }

.header-actions { display: flex; gap: 8px; }
.btn {
  padding: 6px 14px;
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 4px;
  background: transparent;
  color: white;
  cursor: pointer;
  font-size: 13px;
}
.btn:disabled { opacity: 0.4; cursor: default; }

.app-layout {
  display: grid;
  grid-template-columns: 250px 1fr;
  height: calc(100vh - 52px - 50px);  /* minus header and footer */
}

/* Sidebar */
.sidebar {
  border-right: 1px solid #ddd;
  overflow-y: auto;
  padding: 12px;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
}

.sidebar-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.search-input {
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
}

.group-filter {
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
}

.course-list {
  flex: 1;
  overflow-y: auto;
}

.course-card {
  background: white;
  border: 2px solid #ddd;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
  cursor: grab;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.course-code { font-weight: 600; font-size: 13px; }
.course-title { font-size: 11px; color: #666; }

/* Planner grid */
.planner {
  overflow-y: auto;
  padding: 12px;
}

.grid-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.semester-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  align-items: center;
  gap: 12px;
}

.semester-label {
  font-weight: 600;
  font-size: 13px;
  text-align: right;
  padding-right: 8px;
  white-space: nowrap;
}

.semester-slots {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}

.course-slot {
  background: #f0f0f0;
  border: 2px dashed #ccc;
  border-radius: 8px;
  min-height: 60px;
}

/* Validation panel (empty for now) */
.validation-panel {
  border-top: 1px solid #ddd;
  padding: 8px 20px;
  background: #fafafa;
  min-height: 30px;
}
```

## Verification

1. **Serve the files locally.** Since ES6 modules require a server (no `file://` support), use:
   ```bash
   cd src && python3 -m http.server 8000
   ```
   Then open `http://localhost:8000` in a browser.

2. **Check sidebar:** All 97 courses should appear in the sidebar, each showing code and title. Search and filter controls should be visible but disabled.

3. **Check planner:** 8 semester rows should be visible (Fall Year 1 through Winter Year 4), each with a label on the left and 5 empty rounded-rectangle slots.

4. **Check header:** Load, Save, and Clear buttons should be visible but disabled.

5. **Check console:** No errors. `CourseDatabase` should have loaded 97 courses (verify with `console.log` or DevTools).

6. **Check scrolling:** Sidebar should scroll independently. Planner should scroll vertically if window is short.
