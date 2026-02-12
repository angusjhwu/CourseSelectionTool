# Phase 2 — Drag-and-Drop

## Goal

Enable drag-and-drop of courses from the sidebar into semester columns, between columns, and removal from the grid. Introduce grid state management that tracks which courses are in which semester.

## Prerequisites (from Phase 1)

These files already exist and should be modified, not rewritten:
- `src/index.html` — HTML skeleton with sidebar, grid-container, semester columns
- `src/css/styles.css` — base layout styles
- `src/js/main.js` — app init, `renderSidebar()`, `renderGrid()`
- `src/js/courseData.js` — `CourseDatabase` class

## Constraints

- All code in `./src/`
- SortableJS loaded via CDN in `index.html` (NOT as ES6 module — use global `Sortable`)
- No build step

## Files to Create

```
src/js/
├── gridManager.js    ← NEW: grid state management
└── dragDrop.js       ← NEW: SortableJS integration
```

## Files to Modify

```
src/index.html        ← add SortableJS CDN script tag
src/js/main.js        ← import and initialize gridManager + dragDrop
```

## Detailed Implementation

### 1. Add SortableJS to `src/index.html`

Add before the module script tag:
```html
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
<script type="module" src="js/main.js"></script>
```

### 2. `src/js/gridManager.js`

Manages the in-memory state of which courses are placed in which semester.

```js
// gridManager.js — grid state management

export class GridManager {
  constructor() {
    // Map of semester ID → array of course codes
    // e.g. { "fall-1": ["APS105H1", "APS111H1"], "winter-1": [] }
    this.state = {};
  }

  // Initialize with empty semesters
  initSemesters(semesterIds) {
    for (const id of semesterIds) {
      this.state[id] = [];
    }
  }

  // Add a course to a semester. Returns false if duplicate in grid.
  addCourse(semesterId, courseCode) {
    if (this.findCourse(courseCode)) return false;  // already in grid
    this.state[semesterId].push(courseCode);
    return true;
  }

  // Remove a course from a semester
  removeCourse(semesterId, courseCode) {
    const arr = this.state[semesterId];
    const idx = arr.indexOf(courseCode);
    if (idx !== -1) arr.splice(idx, 1);
  }

  // Move a course between semesters
  moveCourse(fromSemester, toSemester, courseCode) {
    this.removeCourse(fromSemester, courseCode);
    this.state[toSemester].push(courseCode);
  }

  // Find which semester a course is in (or null)
  findCourse(courseCode) {
    for (const [semId, courses] of Object.entries(this.state)) {
      if (courses.includes(courseCode)) return semId;
    }
    return null;
  }

  // Get all courses placed before a given semester (for prereq checking in Phase 3)
  getCoursesBeforeSemester(semesterId, semesterOrder) {
    const targetIdx = semesterOrder.indexOf(semesterId);
    const completed = new Set();
    for (let i = 0; i < targetIdx; i++) {
      for (const code of this.state[semesterOrder[i]]) {
        completed.add(code);
      }
    }
    return completed;
  }

  // Get all courses in and before a given semester (for coreq checking in Phase 3)
  getCoursesUpToSemester(semesterId, semesterOrder) {
    const targetIdx = semesterOrder.indexOf(semesterId);
    const completed = new Set();
    for (let i = 0; i <= targetIdx; i++) {
      for (const code of this.state[semesterOrder[i]]) {
        completed.add(code);
      }
    }
    return completed;
  }

  // Get all courses in the grid
  getAllPlacedCourses() {
    const all = new Set();
    for (const courses of Object.values(this.state)) {
      for (const code of courses) all.add(code);
    }
    return all;
  }

  // Export state for saving (Phase 5)
  getState() { return structuredClone(this.state); }

  // Import state from a saved plan (Phase 5)
  setState(state) { this.state = structuredClone(state); }
}
```

### 3. `src/js/dragDrop.js`

Integrates SortableJS with the sidebar and grid columns.

```js
// dragDrop.js — SortableJS integration

export class DragDropManager {
  constructor(gridManager, onDropCallback) {
    this.gridManager = gridManager;
    this.onDrop = onDropCallback;  // called after every state change (for validation in Phase 3)
    this.sortables = [];
  }

  // Initialize drag-and-drop on the sidebar course list
  initSidebar(sidebarEl) {
    const sortable = Sortable.create(sidebarEl, {
      group: { name: 'courses', pull: 'clone', put: false },
      sort: false,
      // When dragging from sidebar, the card should show the course code
      // The cloned element needs the data-code attribute
    });
    this.sortables.push(sortable);
  }

  // Initialize drag-and-drop on a semester column
  initSemesterColumn(columnEl) {
    const semesterId = columnEl.id;
    const self = this;

    const sortable = Sortable.create(columnEl, {
      group: { name: 'courses', pull: true, put: true },
      sort: true,
      animation: 150,

      onAdd(evt) {
        // Course was added to this column (from sidebar or another column)
        const card = evt.item;
        const courseCode = card.dataset.code;
        const fromSemester = evt.from.id;

        // Check for duplicates
        if (self.gridManager.findCourse(courseCode)) {
          // Already in grid — remove the cloned element and flash the existing one
          card.remove();
          self.flashExisting(courseCode);
          return;
        }

        // If from sidebar (course-list), it's a clone → add to state
        if (fromSemester === 'course-list') {
          self.gridManager.addCourse(semesterId, courseCode);
        } else {
          // From another column → move in state
          self.gridManager.moveCourse(fromSemester, semesterId, courseCode);
        }

        self.onDrop();
      },

      onUpdate(evt) {
        // Reordered within same column — no state change needed
        // (order within a semester doesn't affect validation)
      }
    });

    this.sortables.push(sortable);
  }

  // Flash the existing card to indicate a duplicate drop attempt
  flashExisting(courseCode) {
    const existing = document.querySelector(
      `.semester-courses .course-card[data-code="${courseCode}"]`
    );
    if (existing) {
      existing.classList.add('flash');
      setTimeout(() => existing.classList.remove('flash'), 600);
    }
  }

  // Add remove (X) button behavior to grid course cards
  initRemoveButton(card, semesterId) {
    const btn = card.querySelector('.remove-btn');
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const code = card.dataset.code;
        this.gridManager.removeCourse(semesterId, code);
        card.remove();
        this.onDrop();
      });
    }
  }
}
```

### 4. Modify `src/js/main.js`

Update to integrate grid manager and drag-drop. Key changes:

- Import `GridManager` and `DragDropManager`
- After rendering the grid, initialize `GridManager` with semester IDs
- Initialize `DragDropManager` on sidebar and each semester column
- Course cards in the grid get an X (remove) button
- Add an `onDrop` callback that logs state (validation comes in Phase 3)

The `renderGrid()` function should store semester IDs in order (for Phase 3's `getCoursesBeforeSemester`).

The sidebar course cards need `data-code` attributes (already done in Phase 1).

Grid course cards (created by SortableJS cloning) should get an X button appended. Use a MutationObserver or handle in `onAdd`.

### 5. CSS additions to `src/css/styles.css`

```css
/* Drag-and-drop states */
.course-card.sortable-ghost {
  opacity: 0.4;
}

.course-card.sortable-chosen {
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

/* Flash animation for duplicate rejection */
@keyframes flash {
  0%, 100% { background: white; }
  50% { background: #fff3cd; }
}
.course-card.flash {
  animation: flash 0.3s ease 2;
}

/* Remove button on grid cards */
.remove-btn {
  position: absolute;
  top: 2px;
  right: 4px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #999;
  padding: 2px 4px;
}
.remove-btn:hover { color: #e74c3c; }

/* Course card in grid needs relative positioning for X button */
.semester-courses .course-card {
  position: relative;
  padding-right: 24px;
}
```

## Verification

1. **Serve locally:** `cd src && python3 -m http.server 8000`, open `http://localhost:8000`

2. **Drag from sidebar to grid:** Drag a course (e.g., APS105H1) from the sidebar into the "Fall — Year 1" column. The card should appear in the column. The sidebar should still show the course (clone behavior).

3. **Drag between columns:** Drag a course from one semester column to another. It should move (not clone).

4. **Duplicate rejection:** Try dragging APS105H1 from the sidebar again when it's already in a column. The drop should be rejected and the existing card should flash yellow.

5. **Remove button:** Click the X on a grid course card. It should disappear from the column.

6. **Console state:** After each operation, log `gridManager.state` to the console. Verify the state object matches what's visible on screen.

7. **Multiple courses:** Add 5+ courses to various semesters. Verify no duplicates, moves work correctly, removes update state.
