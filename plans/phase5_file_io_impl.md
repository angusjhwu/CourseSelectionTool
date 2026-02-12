# Phase 5 — File I/O

## Goal

Allow users to save their course plan as a JSON file (download), load a previously saved plan (upload), and clear the grid. This completes the MVP.

## Prerequisites (from Phases 1–4)

These files exist and should be modified:
- `src/index.html` — has `header-actions` div (empty), fully functional grid + sidebar
- `src/css/styles.css` — full styles
- `src/js/main.js` — app init with validation, renderGrid, onDrop
- `src/js/gridManager.js` — `GridManager` with `getState()`, `setState()`, `initSemesters()`

## Constraints

- All code in `./src/`
- No external libraries needed
- Save format must be a standalone JSON file (no server)
- Load must validate the file before applying

## Saved Plan Format

```json
{
  "version": "1.0",
  "created": "2026-02-11T10:00:00Z",
  "semesters": [
    { "id": "fall-1", "label": "Fall — Year 1", "courses": ["APS105H1", "APS111H1"] },
    { "id": "winter-1", "label": "Winter — Year 1", "courses": ["APS112H1", "ECE244H1"] },
    { "id": "fall-2", "label": "Fall — Year 2", "courses": [] },
    ...
  ]
}
```

Only semesters that have been created are saved (if the user added/removed semesters, the file reflects that). Empty semesters are included to preserve grid structure.

## Files to Create

```
src/js/
└── fileIO.js    ← NEW: save/load/clear functions
```

## Files to Modify

```
src/index.html        ← add Save/Load/Clear buttons in header
src/js/main.js        ← import fileIO, wire button handlers
src/css/styles.css    ← button styles
```

## Detailed Implementation

### 1. `src/js/fileIO.js`

```js
// fileIO.js — save/load/clear plan

export function exportPlan(gridManager, semesterOrder, semesterLabels) {
  const plan = {
    version: '1.0',
    created: new Date().toISOString(),
    semesters: semesterOrder.map(id => ({
      id,
      label: semesterLabels[id],
      courses: gridManager.state[id] || []
    }))
  };

  const json = JSON.stringify(plan, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `course-plan-${new Date().toISOString().split('T')[0]}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function importPlan(file, courseDatabase) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const plan = JSON.parse(e.target.result);

        // Validate structure
        if (!plan.version || !plan.semesters || !Array.isArray(plan.semesters)) {
          reject(new Error('Invalid plan file: missing version or semesters'));
          return;
        }

        if (plan.version !== '1.0') {
          reject(new Error(`Unsupported plan version: ${plan.version}`));
          return;
        }

        // Validate semesters have required fields
        for (const sem of plan.semesters) {
          if (!sem.id || !sem.label || !Array.isArray(sem.courses)) {
            reject(new Error(`Invalid semester entry: ${JSON.stringify(sem)}`));
            return;
          }
        }

        // Check for unknown course codes (warn but don't reject)
        const warnings = [];
        for (const sem of plan.semesters) {
          for (const code of sem.courses) {
            if (!courseDatabase.getCourse(code)) {
              warnings.push(`Unknown course: ${code} (in ${sem.label})`);
            }
          }
        }

        resolve({ plan, warnings });
      } catch (err) {
        reject(new Error(`Failed to parse plan file: ${err.message}`));
      }
    };

    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}
```

### 2. Add buttons to `src/index.html`

Inside `header-actions`:
```html
<div class="header-actions">
  <button id="btn-save" class="header-btn">Save Plan</button>
  <button id="btn-load" class="header-btn">Load Plan</button>
  <button id="btn-clear" class="header-btn header-btn-danger">Clear</button>
  <input type="file" id="file-input" accept=".json" style="display:none">
</div>
```

### 3. Wire buttons in `src/js/main.js`

```js
import { exportPlan, importPlan } from './fileIO.js';

function initFileIO() {
  // Save
  document.getElementById('btn-save').addEventListener('click', () => {
    exportPlan(gridManager, semesterOrder, semesterLabels);
  });

  // Load — trigger hidden file input
  document.getElementById('btn-load').addEventListener('click', () => {
    document.getElementById('file-input').click();
  });

  document.getElementById('file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const { plan, warnings } = await importPlan(file, db);

      if (warnings.length > 0) {
        const proceed = confirm(
          `Warning: ${warnings.length} unknown course(s) found:\n\n` +
          warnings.join('\n') +
          '\n\nLoad anyway?'
        );
        if (!proceed) return;
      }

      // Apply the loaded plan
      loadPlanIntoGrid(plan);
    } catch (err) {
      alert(`Error loading plan: ${err.message}`);
    }

    // Reset file input so the same file can be loaded again
    e.target.value = '';
  });

  // Clear
  document.getElementById('btn-clear').addEventListener('click', () => {
    if (!confirm('Clear all courses from the grid?')) return;
    clearGrid();
  });
}

function loadPlanIntoGrid(plan) {
  // Reset grid to match loaded plan's semesters
  semesterOrder.length = 0;
  for (const sem of plan.semesters) {
    semesterOrder.push(sem.id);
    semesterLabels[sem.id] = sem.label;
  }

  // Re-render grid columns
  renderGrid();

  // Populate grid state
  gridManager.initSemesters(semesterOrder);
  for (const sem of plan.semesters) {
    for (const code of sem.courses) {
      gridManager.addCourse(sem.id, code);
    }
  }

  // Render course cards into the grid columns
  renderGridCourses();

  // Re-initialize drag-drop on new columns
  initDragDrop();

  // Run validation
  onDrop();
}

function clearGrid() {
  gridManager.initSemesters(semesterOrder);
  // Remove all course cards from grid columns
  for (const id of semesterOrder) {
    const col = document.getElementById(id);
    col.innerHTML = '';
  }
  onDrop();  // clear validation panel
}

function renderGridCourses() {
  // For each semester, render its course cards into the DOM
  for (const semId of semesterOrder) {
    const col = document.getElementById(semId);
    col.innerHTML = '';
    for (const code of gridManager.state[semId]) {
      const course = db.getCourse(code);
      if (!course) continue;
      const card = createGridCourseCard(course);
      col.appendChild(card);
    }
  }
}
```

`createGridCourseCard()` should be extracted from wherever grid course cards are currently created (Phase 2's drag-drop cloning) into a reusable function. It creates a course card with the X button and data attributes.

### 4. CSS additions

```css
/* Header buttons */
.header-btn {
  padding: 6px 14px;
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 4px;
  background: rgba(255,255,255,0.1);
  color: white;
  font-size: 13px;
  cursor: pointer;
  margin-left: 8px;
}
.header-btn:hover {
  background: rgba(255,255,255,0.2);
}
.header-btn-danger {
  border-color: #ef5350;
  color: #ef9a9a;
}
.header-btn-danger:hover {
  background: rgba(239,83,80,0.3);
}
```

## Verification

### Test 1: Save an empty plan
1. Without placing any courses, click "Save Plan"
2. **Expected:** Browser downloads `course-plan-YYYY-MM-DD.json`
3. Open the file — should contain version, timestamp, 8 semesters with empty course arrays

### Test 2: Save a populated plan
1. Place several courses into various semesters
2. Click "Save Plan"
3. Open the downloaded file
4. **Expected:** JSON contains the correct course codes in the correct semester entries

### Test 3: Load a plan
1. Save a plan (Test 2)
2. Click "Clear" to empty the grid
3. Click "Load Plan", select the saved file
4. **Expected:** Grid repopulates with the same courses in the same semesters
5. Validation runs — same green/red states as before saving

### Test 4: Load with unknown courses
1. Manually edit a saved plan JSON, adding a fake course code like "FAKE999H1"
2. Load the modified file
3. **Expected:** Warning dialog listing the unknown course. If user proceeds, grid loads (unknown course may appear as card without data)

### Test 5: Load invalid file
1. Try loading a non-JSON file or a JSON file without `version`/`semesters`
2. **Expected:** Error alert with descriptive message

### Test 6: Clear
1. Place several courses, click "Clear"
2. **Expected:** Confirmation dialog. If confirmed, all courses removed from grid, validation panel clears.

### Test 7: Round-trip integrity
1. Build a complex plan (10+ courses across multiple semesters)
2. Save → Clear → Load
3. **Expected:** Identical grid state. Run through all validation test cases from Phase 3 to confirm validation still works correctly after load.

### Test 8: Re-load different file
1. Load plan A, then immediately load plan B
2. **Expected:** Grid fully replaced with plan B's contents (no remnants of plan A)
