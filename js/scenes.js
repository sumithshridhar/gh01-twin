// Scene menu (17 Oct 2026): the worlds built for the videos, one click each, next to GH-01 itself.
//   GH-01 farm (default) · hydro box on a roof (hydro.js, 14 Nov) · soil-bed polyhouse with the R1 rover + the Part 3 watering kit (rover.js) ·
//   Build R1: the rover's 43 parts on a tarp, fitted in 9 steps (buildr1.js, 10 Nov) ·
//   Build Part 1 pest-camera bench (bench.js) · melon house (melon.js) · 1-hectare glasshouse with pipe rails (bigfarm.js)
// Each extra world is loaded the first time it is picked, then shown/hidden (its show() hides the rest of the twin).
const SCENES = [
  { id: 'gh01', label: '🏠 Full greenhouse · showroom', title: 'The showroom', note: 'The full greenhouse as a design: 45 m² of tomatoes and its farm. Not built. Click any machine to open it.',
    cam: [[-7.5, -8.5, 4.2], [4.2, 0.2, 1.4]] },
  { id: 'water', label: '💧 Watering box · built first', mod: './rover.js', share: 'rover', title: 'Build Part 3',
    note: 'One box waters one bed: a 12 V valve on the zone feed, an ESP32 and relay in the box, a soil sensor in the bed. If anything is wrong the valve stays shut.',
    cam: [[3.9, -1.9, 1.75], [1.15, -3.45, 0.55]] },
  { id: 'hydro', label: '🥬 Hydro box · new', mod: './hydro.js', title: 'Build Part 5 · the hydro box',
    note: 'An NFT rack that runs itself: the box keeps the pump honest and doses nutrients and pH in tiny steps. If a dose does nothing twice, it stops and tells you. Rules pass 19 laptop checks; not built yet. Click any part to open it.',
    cam: [[4.4, -3.3, 1.9], [1.75, 0.05, 0.5]] },
  { id: 'bench', label: '📷 Pest camera · tutorial', mod: './bench.js', title: 'Build Part 1',
    note: 'Pi Zero 2 W + Camera Module 3 + timer + boost board on the bench, real parts at real size.',
    cam: [[0.32, -0.42, 0.42], [0.02, 0.06, 0.04]] },
  { id: 'rover', label: '🤖 R1 rover · concept', mod: './rover.js', title: 'R1 rover (concept)',
    note: 'A concept, not built. On a real farm a hose, mud or a crate on the path would stop it, and that is not solved yet.',
    cam: [[0.9, -0.75, 1.15], [4.2, -1.575, 0.3]], follow: true },
  { id: 'buildr1', label: '🔧 R1 as a kit · concept', mod: './rover.js', share: 'rover', title: 'R1 as a kit (concept)',
    note: 'Every part of the rover on a tarp, fitted in 9 steps. A concept: it shows what the rover would take, not a finished machine.',
    cam: [[7.6, -11.8, 2.7], [3.2, -7.9, 0.55]] },
];

const wait = () => new Promise((r) => { const t = setInterval(() => { if (window.GH && window.GH.ready) { clearInterval(t); r(); } }, 400); });
await wait();
const GH = window.GH;
const built = {};
let cur = 'gh01', busy = false;

const css = document.createElement('style');
css.textContent = `#scenes-pop{position:fixed;bottom:64px;left:50%;transform:translateX(-50%);display:none;flex-direction:column;gap:4px;padding:8px;
  background:rgba(12,15,20,.92);border:1px solid rgba(255,255,255,.14);border-radius:14px;z-index:40;min-width:250px;backdrop-filter:blur(6px)}
  #scenes-pop.open{display:flex} #scenes-pop button{text-align:left;padding:8px 12px;border-radius:9px;border:0;background:transparent;color:#e8edf3;
  font:600 14px/1.2 inherit;cursor:pointer} #scenes-pop button:hover{background:rgba(255,255,255,.09)}
  #scenes-pop button[aria-current="true"]{background:rgba(69,198,230,.2);color:#9fe6f7}
  #app.alt-scene #left,#app.alt-scene #scen,#app.alt-scene #feedbox,#app.alt-scene #chain,#app.alt-scene .readings,#app.alt-scene #mode,#app.alt-scene #growchip{display:none!important}`;
document.head.appendChild(css);
const pop = document.createElement('div');
pop.id = 'scenes-pop';
pop.innerHTML = SCENES.map((s) => `<button data-id="${s.id}" aria-current="${s.id === cur}">${s.label}</button>`).join('');
document.body.appendChild(pop);
const btn = document.createElement('button');
btn.className = 'btn';
btn.id = 'scenesbtn';
btn.textContent = '🗺 Scenes';
btn.title = 'More to see: the watering box, the pest camera, and the R1 rover concept';
const bottom = document.getElementById('bottom');
bottom.insertBefore(btn, document.getElementById('walk') || null);
btn.addEventListener('click', (e) => { e.stopPropagation(); pop.classList.toggle('open'); });
addEventListener('click', (e) => { if (!pop.contains(e.target)) pop.classList.remove('open'); });

async function go(id) {
  if (busy) return;
  const s = SCENES.find((x) => x.id === id);
  const key = s.share || s.id;
  busy = true;
  const curKey = SCENES.find((x) => x.id === cur).share || cur;
  const shown = () => {                             // the menu and GH-01's panels follow what is really on screen
    document.getElementById('app')?.classList.toggle('alt-scene', cur !== 'gh01');
    pop.querySelectorAll('button').forEach((b) => b.setAttribute('aria-current', b.dataset.id === cur));
    dispatchEvent(new CustomEvent('gh-scene', { detail: cur }));     // frontdoor.js labels the view, breakit.js shows its panel
  };
  try {
    if (curKey !== key && built[curKey]) built[curKey].show(false);
    if (s.mod) {
      if (!built[key]) {
        GH.A.toast(s.title, 'Loading…');
        const M = await import(s.mod);
        built[key] = await M.build(GH);
        GH[key] = built[key];
      }
      GH.deselect?.(true);
      built[key].show(true);
      cur = s.share || id;                          // the shared world is up, even if its extra part fails to load below
      shown();
      await built[key].mode?.(id);
    } else GH.deselect?.(true);
    GH.flyTo(GH.B(...s.cam[0]), GH.B(...s.cam[1]), 1.6);
    GH.A.toast(s.title, s.note);
    cur = id;
    shown();
  } catch (err) {
    console.error(err);
    if (curKey !== key && !built[key]) { built[curKey]?.show(true); }   // nothing new came up: stay where we were
    shown();
    GH.A.toast('Scenes', `Could not load: ${err.message || err}. Check the connection and pick the scene again.`);
  } finally {
    busy = false;
  }
}
pop.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { pop.classList.remove('open'); go(b.dataset.id); } });
const q = new URLSearchParams(location.search).get('scene');
if (q && SCENES.some((s) => s.id === q)) {
  const start = () => setTimeout(() => go(q), 2800);
  if (document.getElementById('loading')?.classList.contains('done')) start();
  else document.getElementById('ld-start')?.addEventListener('click', start, { once: true });
}
GH.scenes = { go, list: SCENES.map((s) => s.id) };
