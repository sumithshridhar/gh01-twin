// The front door (11 Nov 2026). A visitor from GitHub or a reel should know in ten seconds what GH-01 is and what is
// real: two small boxes first (the watering box, the heat-and-dew alarm), and the full greenhouse as a showroom.
//   - three doors on the start screen instead of one "Enter greenhouse"
//   - the view opens clean: the control room (systems list, live numbers, failure tests) is one button away
//   - a chip says what is on screen: being built first / showroom / concept
const $ = (q) => document.querySelector(q);
const app = $('#app'), loading = $('#loading');
const P = new URLSearchParams(location.search);
const until = (f) => new Promise((r) => { const t = setInterval(() => { const v = f(); if (v) { clearInterval(t); r(v); } }, 200); });

// clean view by default; ?control opens with the control room, and video capture keeps its own rules
const ctrl = $('#ctrl');
const setClean = (on) => { app.classList.toggle('clean', on); ctrl?.setAttribute('aria-pressed', String(!on)); };
if (!P.has('capture')) setClean(!P.has('control'));
ctrl?.addEventListener('click', () => {
  const open = app.classList.contains('clean');
  setClean(!open);
  if (open) window.GH?.A.toast('Control room', 'Live numbers on top, every system on the left, failure tests below. The AI advises, a safety PLC decides.');
});

// what is on screen
const WHAT = { gh01: ['Showroom · a design, not built', ''], water: ['Watering box · being built first', 'real'], hydro: ['Hydro box · new, tested on a laptop', ''], bench: ['Pest camera · tutorial', ''],
  rover: ['R1 rover · concept, not built', ''], buildr1: ['R1 as a kit · concept', ''] };
addEventListener('gh-scene', (e) => {
  const [text, cls] = WHAT[e.detail] || WHAT.gh01;
  const w = $('#what');
  if (w) { w.textContent = text; w.className = cls; }
  if (ctrl) ctrl.hidden = e.detail !== 'gh01';                 // the control room belongs to the full greenhouse only
});

// door 1: straight to the watering box (the start screen stays up until the bed is on screen)
$('#door-water')?.addEventListener('click', async () => {
  const step = $('#ld-step');
  if (step) step.textContent = 'Opening the watering box…';
  const GH = await until(() => window.GH?.scenes && window.GH);
  GH.A.sound?.ensure?.();
  await GH.scenes.go('water');
  loading.classList.add('done');
  if (step) step.textContent = 'Ready.';
});
// door: the hydro box (14 Nov 2026), the same way as the watering box
$('#door-hydro')?.addEventListener('click', async () => {
  const step = $('#ld-step');
  if (step) step.textContent = 'Opening the hydro box…';
  const GH = await until(() => window.GH?.scenes && window.GH);
  GH.A.sound?.ensure?.();
  await GH.scenes.go('hydro');
  loading.classList.add('done');
  if (step) step.textContent = 'Ready.';
});
// door 3 (#ld-start, wired in main.js): coming back from another scene, show the greenhouse again first
$('#ld-start')?.addEventListener('click', () => { if (app.classList.contains('alt-scene')) window.GH?.scenes?.go('gh01'); });
// ⌂ Start: back to the three doors
$('#home')?.addEventListener('click', () => { window.GH?.deselect?.(true); loading.classList.remove('done'); });
