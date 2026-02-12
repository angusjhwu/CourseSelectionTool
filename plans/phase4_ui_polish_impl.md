# Phase 4 — UI Polish

## Goal

Make the interface usable and polished: add course search and filtering, tooltips on course cards, session validation (F/S courses in correct semesters), course detail view, and responsive design.

## Prerequisites (from Phases 1–3)

These files exist and should be modified:
- `src/index.html` — has `sidebar-controls` div (empty), grid, validation panel
- `src/css/styles.css` — base layout + validation styles
- `src/js/main.js` — app init, renderSidebar, renderGrid, onDrop with validation
- `src/js/courseData.js` — `CourseDatabase` with `getGroups()` method
- `src/js/dependencyGraph.js` — `DependencyValidator` with `validatePlacement()`
- `src/js/gridManager.js` — grid state management

## Constraints

- All code in `./src/`
- Add Tippy.js via CDN for tooltips
- Add Popper.js via CDN (Tippy.js dependency)
- Session data: course.session is `"F"` (fall), `"S"` (winter), or `"B"` (both)
- Semester IDs encode the term: `"fall-1"`, `"winter-1"`, etc.

## Files to Modify

```
src/index.html              ← add Tippy.js CDN, search/filter markup
src/css/styles.css           ← filter buttons, tooltips, responsive, detail modal
src/js/main.js               ← search/filter logic, tooltips, session validation, detail view
src/js/dependencyGraph.js    ← add session validation to validatePlacement()
```

No new JS files needed.

## Detailed Implementation

### 1. Add Tippy.js to `src/index.html`

Add CDN scripts before SortableJS:
```html
<script src="https://unpkg.com/@popperjs/core@2"></script>
<script src="https://unpkg.com/tippy.js@6"></script>
```

Add search and filter controls inside `sidebar-controls`:
```html
<div class="sidebar-controls">
  <input type="text" id="course-search" placeholder="Search courses..." class="search-input">
  <div class="filter-group" id="group-filters">
    <span class="filter-label">Groups:</span>
    <!-- Buttons rendered by JS based on available groups -->
  </div>
  <div class="filter-group" id="session-filters">
    <span class="filter-label">Session:</span>
    <button class="filter-btn active" data-session="all">All</button>
    <button class="filter-btn" data-session="F">Fall</button>
    <button class="filter-btn" data-session="S">Winter</button>
    <button class="filter-btn" data-session="B">Both</button>
  </div>
</div>
```

Add a course detail modal (hidden by default):
```html
<div class="modal-overlay" id="modal-overlay" style="display:none">
  <div class="modal" id="course-modal">
    <button class="modal-close" id="modal-close">&times;</button>
    <h2 id="modal-title"></h2>
    <p id="modal-description"></p>
    <div id="modal-requirements"></div>
  </div>
</div>
```

### 2. Search and Filter Logic (in `main.js`)

#### Search

```js
function initSearch() {
  const input = document.getElementById('course-search');
  input.addEventListener('input', () => {
    const query = input.value.toLowerCase();
    applyFilters(query);
  });
}

function applyFilters(searchQuery) {
  const cards = document.querySelectorAll('#course-list .course-card');
  const activeGroup = getActiveGroupFilter();   // null = all
  const activeSession = getActiveSessionFilter(); // 'all', 'F', 'S', 'B'

  for (const card of cards) {
    const code = card.dataset.code.toLowerCase();
    const title = card.dataset.title.toLowerCase();
    const group = card.dataset.group || '';
    const session = card.dataset.session || '';

    const matchesSearch = !searchQuery ||
      code.includes(searchQuery) ||
      title.includes(searchQuery);

    const matchesGroup = !activeGroup || group === activeGroup;

    const matchesSession = activeSession === 'all' || session === activeSession;

    card.style.display = (matchesSearch && matchesGroup && matchesSession) ? '' : 'none';
  }
}
```

Store `data-title`, `data-group`, and `data-session` on sidebar course cards (update `renderSidebar`).

#### Group Filter Buttons

Render dynamically from `db.getGroups()`:

```js
function initGroupFilters() {
  const container = document.getElementById('group-filters');
  const groups = db.getGroups(); // ['A', 'B', 'C', 'MATH', 'SCIENCE']

  // "All" button
  const allBtn = createFilterBtn('All', null, true);
  container.appendChild(allBtn);

  for (const group of groups) {
    container.appendChild(createFilterBtn(group, group, false));
  }

  // Click handler: toggle active, reapply filters
  container.addEventListener('click', (e) => {
    if (!e.target.classList.contains('filter-btn')) return;
    container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    applyFilters(document.getElementById('course-search').value.toLowerCase());
  });
}
```

#### Session Filter Buttons

Same pattern — click toggles `active` class, reapply filters.

### 3. Tooltips on Grid Course Cards

After validation runs, attach/update tooltips on each grid course card:

```js
function updateTooltips(validationResults) {
  const gridCards = document.querySelectorAll('.semester-courses .course-card');
  for (const card of gridCards) {
    const code = card.dataset.code;
    const course = db.getCourse(code);
    const result = validationResults.get(code);

    // Build tooltip content
    let content = `<strong>${course.title}</strong>`;

    if (result && !result.valid) {
      content += '<hr>';
      for (const err of result.errors) {
        if (err.type === 'prerequisite') {
          content += '<div class="tip-error">Missing prerequisites:</div>';
          content += formatMissing(err.missing);
        } else if (err.type === 'corequisite') {
          content += '<div class="tip-error">Missing corequisites:</div>';
          content += formatMissing(err.missing);
        } else if (err.type === 'exclusion') {
          content += `<div class="tip-error">Conflicts with: ${err.conflicting.join(', ')}</div>`;
        } else if (err.type === 'session') {
          content += `<div class="tip-error">${err.message}</div>`;
        }
      }
    }

    // Destroy existing tippy instance if any, then create new
    if (card._tippy) card._tippy.setContent(content);
    else tippy(card, { content, allowHTML: true, theme: 'light-border', placement: 'right' });
  }
}
```

### 4. Session Validation (in `dependencyGraph.js`)

Add to `validatePlacement()`:

```js
// Session validation
// Determine the term from the semester ID (e.g., "fall-1" → "Fall", "winter-2" → "Winter")
const term = semesterId.startsWith('fall') ? 'F' : 'S';

if (course.session === 'F' && term !== 'F') {
  errors.push({ type: 'session', message: `${courseCode} is only offered in Fall` });
}
if (course.session === 'S' && term !== 'S') {
  errors.push({ type: 'session', message: `${courseCode} is only offered in Winter` });
}
// session === 'B' can go in either term
```

### 5. Course Detail Modal

Click a course card (in sidebar or grid) → show modal with full details:

```js
function showCourseDetail(courseCode) {
  const course = db.getCourse(courseCode);
  if (!course) return;

  document.getElementById('modal-title').textContent = `${course.code} — ${course.title}`;
  document.getElementById('modal-description').textContent = course.description;

  // Format requirements in readable form
  const reqDiv = document.getElementById('modal-requirements');
  reqDiv.innerHTML = '';

  if (course.prerequisites) {
    reqDiv.innerHTML += `<p><strong>Prerequisites:</strong> ${formatRequirementReadable(course.prerequisites)}</p>`;
  }
  if (course.corequisites) {
    reqDiv.innerHTML += `<p><strong>Corequisites:</strong> ${formatRequirementReadable(course.corequisites)}</p>`;
  }
  if (course.exclusions) {
    reqDiv.innerHTML += `<p><strong>Exclusions:</strong> ${formatRequirementReadable(course.exclusions)}</p>`;
  }
  if (!course.prerequisites && !course.corequisites && !course.exclusions) {
    reqDiv.innerHTML = '<p>No requirements</p>';
  }

  reqDiv.innerHTML += `<p><strong>Session:</strong> ${
    course.session === 'F' ? 'Fall' : course.session === 'S' ? 'Winter' : 'Fall or Winter'
  }</p>`;

  if (course.group) {
    reqDiv.innerHTML += `<p><strong>Group:</strong> ${course.group}</p>`;
  }

  document.getElementById('modal-overlay').style.display = 'flex';
}

// Format a courseset ID into readable text
// e.g., ECE435H1_p6 → "(ECE216H1 or ECE355H1) and (ECE302H1 or MIE286H1) and ..."
function formatRequirementReadable(coursesetId) {
  const tree = validator.parseCourseset(coursesetId);
  return treeToString(tree);
}

function treeToString(node) {
  if (!node) return '';
  if (node.type === 'COURSE') return node.code;
  if (node.type === 'OR') {
    const parts = node.children.map(c => treeToString(c));
    return parts.length === 1 ? parts[0] : `(${parts.join(' or ')})`;
  }
  if (node.type === 'AND') {
    const parts = node.children.map(c => treeToString(c));
    return parts.join(' and ');
  }
}
```

Close modal on clicking overlay or X button:
```js
document.getElementById('modal-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});
document.getElementById('modal-close').addEventListener('click', closeModal);

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}
```

Attach click handler to course cards (avoiding conflict with drag):
- Use `mousedown` + `mouseup` timing: only fire if no drag occurred (SortableJS sets a `sortable-chosen` class during drag)
- Or use a dedicated info icon button on each card

### 6. CSS Additions

```css
/* Search input */
.search-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 8px;
  box-sizing: border-box;
}

/* Filter buttons */
.filter-group {
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}
.filter-label { font-size: 11px; color: #666; margin-right: 4px; }
.filter-btn {
  padding: 3px 8px;
  border: 1px solid #ccc;
  border-radius: 12px;
  background: white;
  font-size: 11px;
  cursor: pointer;
}
.filter-btn.active {
  background: #1a1a2e;
  color: white;
  border-color: #1a1a2e;
}

/* Tooltip error styling */
.tip-error { color: #e53935; font-size: 12px; margin-top: 4px; }

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: white;
  border-radius: 8px;
  padding: 24px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
}
.modal-close {
  position: absolute;
  top: 8px; right: 12px;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

/* Session mismatch styling */
.semester-courses .course-card[data-session-error="true"] {
  border-color: #ff9800;
  background: #fff8e1;
}

/* Responsive */
@media (max-width: 768px) {
  .app-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
  .sidebar {
    border-right: none;
    border-bottom: 1px solid #ddd;
    max-height: 200px;
  }
  .grid-container {
    grid-template-columns: repeat(4, minmax(140px, 1fr));
  }
}
```

## Verification

### Test 1: Search
1. Type "ECE3" in the search box
2. **Expected:** Only courses with codes or titles containing "ece3" (case-insensitive) are visible in the sidebar

### Test 2: Group filters
1. Click the "B" group filter button
2. **Expected:** Only group B courses visible. Click "All" → all courses visible again.

### Test 3: Session filters
1. Click "Fall" session filter
2. **Expected:** Only courses with session "F" visible

### Test 4: Combined filters
1. Search "ECE", select group "A", session "Fall"
2. **Expected:** Only ECE courses in group A offered in fall

### Test 5: Tooltips
1. Place a course with missing prerequisites into the grid
2. Hover over it
3. **Expected:** Tooltip shows course title + "Missing prerequisites: ..." in red

### Test 6: Session validation
1. Drag APS105H1 (session "S" = winter only) into a Fall semester column
2. **Expected:** Orange border, validation panel shows "APS105H1 is only offered in Winter"

### Test 7: Course detail modal
1. Click on a course card (not drag)
2. **Expected:** Modal appears with full description, prerequisites in readable form (e.g., "(ECE216H1 or ECE355H1) and (ECE302H1 or MIE286H1)")
3. Click overlay or X → modal closes

### Test 8: Responsive
1. Resize browser to <768px width
2. **Expected:** Sidebar collapses above the grid, grid shows 4 columns per row
