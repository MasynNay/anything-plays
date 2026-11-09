/* Static camera-zone concept. No camera, global keyboard, ROMs, or backend.
   Public release detection below reads only GitHub's unauthenticated release API. */
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


/* Upgrade the site's public download ONLY after GitHub confirms that the
   genuine stable 3.0.0 release is public AND exposes all four installers.
   Network failure, draft, prerelease, missing assets, or API throttling:
   keep the honest, working stable 2.0 link and copy already in the HTML.
   This static portfolio site does not require GitHub login or an API key. */
(async () => {
  const api = 'https://api.github.com/repos/MasynNay/anything-plays/releases/tags/v3.0.0';
  const stableUrl = 'https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0';
  const required = [
    'AnythingPlaysSetup-3.0.0.exe',
    'anything-plays_3.0.0_amd64.deb',
    'AnythingPlays-3.0.0-macos-arm64.dmg',
    'AnythingPlays-3.0.0-macos-x64.dmg',
    'SHA256SUMS.txt'
  ];
  try {
    const response = await fetch(api, {cache: 'no-store', mode: 'cors'});
    if (!response.ok) return;
    const published = await response.json();
    if (published.tag_name !== 'v3.0.0' ||
        published.draft !== false || published.prerelease !== false ||
        !Array.isArray(published.assets)) return;
    const available = new Set(published.assets.filter(item =>
      item && item.state === 'uploaded' && item.size > 0
    ).map(item => item.name));
    if (!required.every(name => available.has(name))) return;

    const copy = (id, value) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value;
    };
    const link = document.getElementById('public-stable-download');
    if (link) {
      link.href = stableUrl;
      link.textContent = 'Download Anything Plays 3.0 ↗';
    }
    copy('download-summary', 'Anything Plays 3.0 is publicly available with all 18 console profiles and eleven bundled original-source emulator libraries. Download the installer for Windows, Linux, Intel Mac, or Apple Silicon. No ROMs or console firmware are included.');
    copy('consoles-summary', 'Anything Plays 3.0 is publicly released with 18 offline console profiles, built around eleven original-source native emulator cores. Nintendo 64 and GameCube are included; compatibility with every game and computer is not guaranteed.');
    copy('roadmap-summary', 'Anything Plays 3.0 has been released with genuine four-platform installers, source archives and checksum verification. The roadmap continues with game compatibility, camera performance, saves and long-run reliability improvements.');
    copy('stable-profiles-count', '18');
    copy('stable-profiles-label', 'Console profiles in stable 3.0');

    const status = document.getElementById('download-release-status');
    if (status && status.lastChild) status.lastChild.textContent = ' STABLE 3.0 AVAILABLE';

    document.querySelectorAll('.console-grid article:not(.console-preview) small')
      .forEach(tag => { tag.textContent = 'SUPPORTED IN 3.0'; });
    const expanded = document.querySelector('.console-grid .console-preview small');
    if (expanded) expanded.textContent = 'STABLE 3.0 · N64 + GAMECUBE';

    const released = document.getElementById('roadmap-release-phase');
    if (released) {
      released.classList.remove('phase-current');
      released.classList.add('phase-released');
      const serial = released.querySelector('.phase-serial');
      if (serial) serial.textContent = '03 / RELEASED';
      const title = released.querySelector('strong');
      if (title) title.textContent = '3.0 · All 18 profiles';
      const detail = released.querySelector('small');
      if (detail) detail.textContent = 'Public source-first four-platform release';
    }
    const next = document.getElementById('roadmap-next-phase');
    if (next) {
      const serial = next.querySelector('.phase-serial');
      if (serial) serial.textContent = '04 / CONTINUING';
      const title = next.querySelector('strong');
      if (title) title.textContent = '3.0 · Reliability roadmap';
      const detail = next.querySelector('small');
      if (detail) detail.textContent = 'Compatibility, saves and hardware QA';
    }
    const quality = document.getElementById('release-quality-card');
    if (quality) {
      const title = quality.querySelector('h3');
      if (title) title.textContent = 'Maintain 3.0 responsibly.';
      const small = quality.querySelector('small');
      if (small) small.textContent = 'ONGOING';
      const paragraph = quality.querySelector('p');
      if (paragraph) paragraph.textContent = 'Public installers and all pinned original sources are available now. Continue validating retail-game compatibility, camera hardware, saves, long sessions and future platform updates.';
    }
  } catch (_) {
    // Preserve already-visible 2.0 link when GitHub cannot be reached.
  }
})();
