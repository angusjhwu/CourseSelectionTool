// courseData.js — loads and indexes course_db.json

export class CourseDatabase {
  constructor() {
    this.courses = new Map();      // code → course object
    this.coursesets = {};           // courseset_id → { courses: "..." }
    this.groups = new Set();       // unique group values
  }

  async load() {
    const response = await fetch('/data/course_db.json');
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
