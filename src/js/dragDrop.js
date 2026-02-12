// dragDrop.js — SortableJS integration (per-slot drop targets)

export class DragDropManager {
  constructor(gridManager, onDropCallback) {
    this.gridManager = gridManager;
    this.onDrop = onDropCallback;
    this.sortables = [];
  }

  // Initialize drag-and-drop on the sidebar course list
  initSidebar(sidebarEl) {
    const sortable = Sortable.create(sidebarEl, {
      group: { name: 'courses', pull: 'clone', put: false },
      sort: false,
    });
    this.sortables.push(sortable);
  }

  // Initialize drag-and-drop on a single course slot
  initSlot(slotEl) {
    const self = this;

    const sortable = Sortable.create(slotEl, {
      group: { name: 'courses', pull: true, put: true },
      animation: 150,

      onAdd(evt) {
        const card = evt.item;
        const courseCode = card.dataset.code;
        const semesterId = slotEl.dataset.semester;
        const slotIndex = parseInt(slotEl.dataset.slot, 10);
        const fromEl = evt.from;

        // If slot already has a course (the one we just dropped + existing), reject
        if (slotEl.querySelectorAll('.course-card').length > 1) {
          card.remove();
          return;
        }

        // Check if course is already elsewhere in the grid
        const existing = self.gridManager.findCourse(courseCode);

        if (fromEl.id === 'course-list') {
          // From sidebar — clone
          if (existing) {
            // Already in grid — reject and flash
            card.remove();
            self.flashExisting(courseCode);
            return;
          }
          self.gridManager.addCourse(semesterId, slotIndex, courseCode);
          self.addRemoveButton(card, semesterId, slotIndex);
        } else {
          // From another slot — move
          const fromSemester = fromEl.dataset.semester;
          const fromSlot = parseInt(fromEl.dataset.slot, 10);
          self.gridManager.moveCourse(fromSemester, fromSlot, semesterId, slotIndex);
          self.updateRemoveButton(card, semesterId, slotIndex);
        }

        self.onDrop();
      },
    });

    this.sortables.push(sortable);
  }

  // Add remove (X) button to a course card in the grid
  addRemoveButton(card, semesterId, slotIndex) {
    if (card.querySelector('.remove-btn')) return;
    const btn = document.createElement('button');
    btn.className = 'remove-btn';
    btn.textContent = '\u00d7';
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.gridManager.removeCourse(semesterId, slotIndex);
      card.remove();
      this.onDrop();
    });
    card.appendChild(btn);
  }

  // Update remove button's closure after a move
  updateRemoveButton(card, semesterId, slotIndex) {
    const oldBtn = card.querySelector('.remove-btn');
    if (oldBtn) oldBtn.remove();
    this.addRemoveButton(card, semesterId, slotIndex);
  }

  // Flash the existing card to indicate a duplicate drop attempt
  flashExisting(courseCode) {
    const existing = document.querySelector(
      `.course-slot .course-card[data-code="${courseCode}"]`
    );
    if (existing) {
      existing.classList.add('flash');
      setTimeout(() => existing.classList.remove('flash'), 600);
    }
  }
}
