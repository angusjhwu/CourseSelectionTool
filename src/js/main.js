// main.js — app initialization

import { CourseDatabase } from './courseData.js';
import { GridManager } from './gridManager.js';
import { DragDropManager } from './dragDrop.js';

const db = new CourseDatabase();
const gridManager = new GridManager();
const dragDrop = new DragDropManager(gridManager, onDrop);

// Ordered semester IDs (used for prereq/coreq checking in later phases)
const semesterOrder = [];

// Currently selected course code for the info panel (null if closed)
let selectedCourse = null;

async function init() {
  await db.load();
  renderSidebar(db.getAllCourses());
  renderGrid();
  initDragDrop();
  initInfoPanel();
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
  semesterOrder.length = 0;

  const semesters = [];
  for (let year = 1; year <= 4; year++) {
    semesters.push({ id: `fall-${year}`,   label: `Fall — Year ${year}`,   term: 'Fall' });
    semesters.push({ id: `winter-${year}`, label: `Winter — Year ${year}`, term: 'Winter' });
  }

  for (const sem of semesters) {
    semesterOrder.push(sem.id);

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

  gridManager.initSemesters(semesterOrder);
}

function initDragDrop() {
  // Sidebar as drag source
  dragDrop.initSidebar(document.getElementById('course-list'));

  // Each slot as a drop target
  const slots = document.querySelectorAll('.course-slot');
  for (const slot of slots) {
    dragDrop.initSlot(slot);
  }
}

function onDrop() {
  // Log state for debugging (validation comes in Phase 3)
  console.log('Grid state:', gridManager.getState());
}

// --- Course Information Panel ---

function initInfoPanel() {
  // Close button
  document.getElementById('info-panel-close').addEventListener('click', closeInfoPanel);

  // Delegate click on course cards (sidebar + grid)
  document.addEventListener('click', (e) => {
    const card = e.target.closest('.course-card');
    if (!card) return;
    // Don't open panel when clicking the remove button
    if (e.target.closest('.remove-btn')) return;

    const code = card.dataset.code;
    if (selectedCourse === code) {
      closeInfoPanel();
    } else {
      showCourseInfo(code);
    }
  });
}

function showCourseInfo(code) {
  const course = db.getCourse(code);
  if (!course) return;

  selectedCourse = code;

  const sessionLabels = { F: 'Fall', S: 'Winter', B: 'Fall & Winter' };
  const session = sessionLabels[course.session] || course.session;

  let html = `
    <h2>${course.code}</h2>
    <p class="info-subtitle">${course.title}</p>
    <div class="info-meta">
      <span>Session: ${session}</span>
      ${course.group ? `<span>Group: ${course.group}</span>` : ''}
    </div>
  `;

  if (course.description) {
    html += `
      <div class="info-section">
        <div class="info-section-label">Description</div>
        <p>${course.description}</p>
      </div>
    `;
  }

  // Resolve courseset references to readable strings
  const reqFields = [
    { key: 'prerequisites', label: 'Prerequisites' },
    { key: 'corequisites', label: 'Corequisites' },
    { key: 'exclusions', label: 'Exclusions' },
  ];

  for (const { key, label } of reqFields) {
    if (!course[key]) continue;
    const resolved = resolveRequirement(course[key]);
    html += `
      <div class="info-section">
        <div class="info-section-label">${label}</div>
        <p>${resolved}</p>
      </div>
    `;
  }

  document.getElementById('info-panel-content').innerHTML = html;
  document.querySelector('.app-layout').classList.add('info-open');
}

function closeInfoPanel() {
  selectedCourse = null;
  document.querySelector('.app-layout').classList.remove('info-open');
}

// Resolve a requirement string (which may contain courseset IDs) into readable course codes
function resolveRequirement(reqStr) {
  if (!reqStr) return '';
  // Split by & and / while preserving operators
  return reqStr.replace(/([A-Z]{2,4}\d{3}H1_[pce]\d+)/g, (match) => {
    const cs = db.coursesets[match];
    if (cs) return cs.courses;
    return match;
  });
}

init();
