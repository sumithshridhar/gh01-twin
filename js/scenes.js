// Scene menu (17 Oct 2026): the worlds built for the videos, one click each, next to GH-01 itself.
//   GH-01 farm (default) · soil-bed polyhouse with the R1 rover + the Part 3 watering kit (rover.js) ·
//   Build Part 1 pest-camera bench (bench.js) · melon house (melon.js) · 1-hectare glasshouse with pipe rails (bigfarm.js)
// Each extra world is loaded the first time it is picked, then shown/hidden (its show() hides the rest of the twin).
const SCENES = [
  { id: 'gh01', label: '🍅 GH-01 farm', title: 'GH-01', note: '45 m² tomato greenhouse and its farm. Click any machine to explode it.',
    cam: [[-7.5, -8.5, 4.2], [4.2, 0.2, 1.4]] },
  { id: 'rover', label: '🤖 R1 rover · soil polyhouse', mod: './rover.js', title: 'Soil-bed polyhouse',
    note: 'Strawberry beds under silver mulch, the R1 rover scouting a path, and the Part 3 watering box on the corner column.',
    cam: [[0.9, -0.75, 1.15], [4.2, -1.575, 0.3]], follow: true },
  { id: 'water', label: '💧 Part 3 watering kit', mod: './rover.js', share: 'rover', title: 'Build Part 3',
    note: '12 V valve on the zone feed, ESP32 + relay in the box, soil sensor in the bed. Guide: github.com/sumithshridhar/gh01-twin',
    cam: [[1.75, -2.65, 1.1], [0.25, -3.8, 0.82]] },
  { id: 'bench', label: '📷 Part 1 pest camera', mod: './bench.js', title: 'Build Part 1',
    note: 'Pi Zero 2 W + Camera Module 3 + timer + boost board on the bench, real parts at real size.',
    cam: [[0.32, -0.42, 0.42], [0.02, 0.06, 0.04]] },
  { id: 'melon', label: '🍈 Melon house', mod: './melon.js', title: 'Melon house',
    note: 'Muskmelons up strings in net bags, watermelons on the ground, and the scout robot with a camera boom.',
    cam: [[1.8, 2.9, 2.1], [5.4, 0.2, 0.6]] },
  { id: 'bigfarm', label: '🏭 1-hectare glasshouse', mod: './bigfarm.js', title: '1-hectare glasshouse',
    note: '76 aisles of heating-pipe rails: how rail robots work at scale.',
    cam: [[-6, -30, 13], [22, -1, 2.5]] },
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
btn.title = 'More worlds: the R1 rover in a soil polyhouse, the build kits, a melon house, a 1-hectare glasshouse';
const bottom = document.getElementById('bottom');
bottom.insertBefore(btn, document.getElementById('walk') || null);
btn.addEventListener('click', (e) => { e.stopPropagation(); pop.classList.toggle('open'); });
addEventListener('click', (e) => { if (!pop.contains(e.target)) pop.classList.remove('open'); });

async function go(id) {
  if (busy) return;
  const s = SCENES.find((x) => x.id === id);
  const key = s.share || s.id;
  busy = true;
  try {
    const curKey = SCENES.find((x) => x.id === cur).share || cur;
    if (curKey !== key && built[curKey]) built[curKey].show(false);
    if (s.mod) {
      if (!built[key]) {
        GH.A.toast(s.title, 'Loading…');
        const M = await import(s.mod);
        built[key] = await M.build(GH);
        GH[key === 'bigfarm' ? 'bigFarm' : key] = built[key];
      }
      built[key].show(true);
    }
    GH.deselect?.(true);
    GH.flyTo(GH.B(...s.cam[0]), GH.B(...s.cam[1]), 1.6);
    GH.A.toast(s.title, s.note);
    cur = id;
    document.getElementById('app')?.classList.toggle('alt-scene', id !== 'gh01');   // GH-01's control panels only belong to GH-01
    pop.querySelectorAll('button').forEach((b) => b.setAttribute('aria-current', b.dataset.id === id));
  } catch (err) {
    console.error(err);
    GH.A.toast('Scenes', `Could not load: ${err.message || err}`);
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
