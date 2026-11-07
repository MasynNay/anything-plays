/* Static interaction showcasing camera zones. This never accesses the camera,
   keyboard globally, ROMs, backend services, or third-party APIs. */
(() => {
  const grid = document.getElementById('demo-grid');
  const tracker = document.getElementById('demo-tracker');
  const output = document.getElementById('selected-input');
  const description = document.getElementById('selected-description');
  const reset = document.getElementById('reset-demo');
  if (!grid || !tracker || !output || !description || !reset) return;

  const labels = {
    LEFT: 'Move left', UP: 'Move up', RIGHT: 'Move right',
    A: 'Button A', START: 'Start', B: 'Button B', DOWN: 'Move down',
    SELECT: 'Select', SHUFFLE: 'Reshuffle control zones'
  };
  const buttons = [...grid.querySelectorAll('.zone')];
  let active = null;
  let lastActive = null;
  let lastMoved = 0;
  const setZone = (name) => {
    if (name === lastActive) return;
    lastActive = name;
    if (active) active.classList.remove('is-active');
    active = buttons.find(button => button.dataset.zone === name) || null;
    if (active) active.classList.add('is-active');
    output.textContent = name || 'READY';
    description.textContent = labels[name] || 'Move the tracker across the grid.';
  };
  const pointTo = (x, y) => {
    const rect = grid.getBoundingClientRect();
    const left = Math.max(5, Math.min(rect.width - 5, x - rect.left));
    const top = Math.max(5, Math.min(rect.height - 5, y - rect.top));
    tracker.style.left = `${left}px`;
    tracker.style.top = `${top}px`;
    const index = Math.min(2, Math.floor(top / (rect.height / 3))) * 3
      + Math.min(2, Math.floor(left / (rect.width / 3)));
    setZone(buttons[index]?.dataset.zone || null);
  };
  grid.addEventListener('pointermove', event => {
    if (event.pointerType === 'touch' && !event.isPrimary) return;
    if (event.pointerType === 'mouse' || event.buttons || event.pointerType === 'pen') {
      const now = performance.now();
      if (now - lastMoved < 30) return;
      lastMoved = now;
      pointTo(event.clientX, event.clientY);
    }
  });
  grid.addEventListener('pointerdown', event => {
    if (event.target.closest('.zone')) pointTo(event.clientX, event.clientY);
  });
  buttons.forEach(button => button.addEventListener('click', () => {
    setZone(button.dataset.zone);
    const region = button.getBoundingClientRect();
    const outer = grid.getBoundingClientRect();
    tracker.style.left = `${region.left - outer.left + region.width / 2}px`;
    tracker.style.top = `${region.top - outer.top + region.height / 2}px`;
  }));
  const resetState = () => {
    if (active) active.classList.remove('is-active');
    active = null;
    lastActive = null;
    output.textContent = 'READY';
    description.textContent = 'Move the tracker across the grid.';
    tracker.style.left = '50%';
    tracker.style.top = '50%';
  };
  reset.addEventListener('click', resetState);
  resetState();
})();
