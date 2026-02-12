// gridManager.js — grid state management (slot-based)

export class GridManager {
  constructor() {
    // Map of semester ID → array of 5 slots (courseCode or null)
    // e.g. { "fall-1": ["APS105H1", null, null, null, null] }
    this.state = {};
    this.slotsPerSemester = 5;
  }

  // Initialize with empty semesters
  initSemesters(semesterIds) {
    for (const id of semesterIds) {
      this.state[id] = new Array(this.slotsPerSemester).fill(null);
    }
  }

  // Place a course in a specific slot. Returns false if slot occupied or course already in grid.
  addCourse(semesterId, slotIndex, courseCode) {
    if (this.findCourse(courseCode)) return false;
    if (this.state[semesterId][slotIndex] !== null) return false;
    this.state[semesterId][slotIndex] = courseCode;
    return true;
  }

  // Remove a course from a specific slot
  removeCourse(semesterId, slotIndex) {
    this.state[semesterId][slotIndex] = null;
  }

  // Move a course from one slot to another
  moveCourse(fromSemester, fromSlot, toSemester, toSlot) {
    const code = this.state[fromSemester][fromSlot];
    this.state[fromSemester][fromSlot] = null;
    this.state[toSemester][toSlot] = code;
  }

  // Find which semester and slot a course is in (or null)
  findCourse(courseCode) {
    for (const [semId, slots] of Object.entries(this.state)) {
      const idx = slots.indexOf(courseCode);
      if (idx !== -1) return { semesterId: semId, slotIndex: idx };
    }
    return null;
  }

  // Get all courses placed before a given semester (for prereq checking)
  getCoursesBeforeSemester(semesterId, semesterOrder) {
    const targetIdx = semesterOrder.indexOf(semesterId);
    const completed = new Set();
    for (let i = 0; i < targetIdx; i++) {
      for (const code of this.state[semesterOrder[i]]) {
        if (code) completed.add(code);
      }
    }
    return completed;
  }

  // Get all courses in and before a given semester (for coreq checking)
  getCoursesUpToSemester(semesterId, semesterOrder) {
    const targetIdx = semesterOrder.indexOf(semesterId);
    const completed = new Set();
    for (let i = 0; i <= targetIdx; i++) {
      for (const code of this.state[semesterOrder[i]]) {
        if (code) completed.add(code);
      }
    }
    return completed;
  }

  // Get all courses in the grid
  getAllPlacedCourses() {
    const all = new Set();
    for (const slots of Object.values(this.state)) {
      for (const code of slots) {
        if (code) all.add(code);
      }
    }
    return all;
  }

  // Export state for saving
  getState() { return structuredClone(this.state); }

  // Import state from a saved plan
  setState(state) { this.state = structuredClone(state); }
}
