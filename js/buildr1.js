// "Build R1" (10 Nov 2026): the rover as a kit. Its 43 parts lie on a blue tarp beside the soil-bed polyhouse and fly
// onto the rover one build step at a time: the 9 steps of build/02-r1-rover/README.md, the same order as the Build R1
// videos. Parts + tarp layout come from Blender (blender/build_r1_kit_web.py -> assets/r1_kit.glb.json + r1_kit.json).
// Part of the soil-polyhouse scene (js/rover.js switches it on for the 'buildr1' entry of the scene menu).
//
//   GH.rover.kit.go(3)   fit everything up to step 3 · go(0) puts every part back on the tarp
import { loadGLB } from './rover.js';

const GUIDE = 'https://github.com/sumithshridhar/gh01-twin/tree/main/build/02-r1-rover';
const SPOT = [4.0, -6.6, 0];                       // Blender coordinates: open ground 2.6 m off the house's long wall
const nodeName = (n) => n.replace(/\s/g, '_').replace(/[[\].:/]/g, '');   // what GLTFLoader turns a Blender name into
const TIPS = [                                     // one line per step, from the build guide
  'Square each corner before the final tightening.',
  'Line the flats on the axle up with the slot in the plate, so the axle cannot turn.',
  'Battery and tank sit low, so the tall mast cannot tip the rover.',
  'The e-stop and both bumpers are wired in series: any one of them cuts the motors, whatever the software is doing.',
  'If a wheel hums instead of turning, swap two of its three thick wires (power off first).',
  'The Pi is fused before the contactor, so it stays on when you press the e-stop.',
  'The lowest pair of cameras tilts 25° up, to see under the leaves.',
  'The pump only runs while a valve is open.',
  'First test: wheels off the ground, on blocks.',
];
// a farm tarpaulin: woven plastic, fold creases from the pack, a little dust
function tarpTexture(T, w, h) {
  const c = document.createElement('canvas');
  c.width = 1024;
  c.height = Math.round(1024 * h / w);
  const x = c.getContext('2d'), W = c.width, H = c.height;
  x.fillStyle = '#143f88';
  x.fillRect(0, 0, W, H);
  for (let i = 0; i < W; i += 5) { x.fillStyle = i % 10 ? 'rgba(255,255,255,.045)' : 'rgba(0,0,30,.06)'; x.fillRect(i, 0, 2, H); }
  for (let j = 0; j < H; j += 5) { x.fillStyle = j % 10 ? 'rgba(0,0,30,.05)' : 'rgba(255,255,255,.04)'; x.fillRect(0, j, W, 2); }
  let s = 7;
  const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
  for (let k = 0; k < 260; k++) {                  // dust and scuffs
    const r = 6 + rnd() * 50;
    const g = x.createRadialGradient(0, 0, 0, 0, 0, r);
    g.addColorStop(0, `rgba(150,110,80,${0.03 + rnd() * 0.05})`);
    g.addColorStop(1, 'rgba(150,110,80,0)');
    x.setTransform(1, 0, 0, 1, rnd() * W, rnd() * H);
    x.fillStyle = g;
    x.fillRect(-r, -r, 2 * r, 2 * r);
  }
  x.setTransform(1, 0, 0, 1, 0, 0);
  const crease = (x0, y0, x1, y1) => {             // a fold: a dark line with a light edge beside it
    for (const [dx, col, lw] of [[0, 'rgba(0,10,50,.3)', 3], [3, 'rgba(255,255,255,.2)', 2], [-4, 'rgba(255,255,255,.07)', 5]]) {
      x.strokeStyle = col; x.lineWidth = lw;
      x.beginPath(); x.moveTo(x0 + (y0 === y1 ? 0 : dx), y0 + (y0 === y1 ? dx : 0)); x.lineTo(x1 + (y0 === y1 ? 0 : dx), y1 + (y0 === y1 ? dx : 0)); x.stroke();
    }
  };
  for (let i = 1; i < 4; i++) crease(W * i / 4, 0, W * i / 4, H);
  for (let j = 1; j < 4; j++) crease(0, H * j / 4, W, H * j / 4);
  const t = new T.CanvasTexture(c);
  t.colorSpace = T.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export async function build(GH, parent) {
  const T = GH.THREE, B = GH.B;
  const [g, meta] = await Promise.all([loadGLB('assets/r1_kit.glb.json'), fetch('assets/r1_kit.json').then((r) => r.json())]);
  const root = new T.Group();
  root.name = 'r1kit';
  root.visible = false;
  root.position.copy(B(...SPOT));
  root.add(g.scene);
  g.scene.traverse((o) => { if (o.isMesh) { o.castShadow = !o.material.transparent; o.receiveShadow = true; } });
  // the tarp: a blue farm tarpaulin with a darker hem and eyelets
  const tc = meta.tarp, tarp = new T.Group();
  const tex = tarpTexture(T, tc.w, tc.h);
  const sheet = new T.Mesh(new T.PlaneGeometry(tc.w, tc.h), new T.MeshStandardMaterial({ map: tex, bumpMap: tex, bumpScale: 0.6, roughness: 0.58, metalness: 0.0 }));
  sheet.rotation.x = -Math.PI / 2;
  sheet.receiveShadow = true;
  const hem = new T.Mesh(new T.PlaneGeometry(tc.w + 0.06, tc.h + 0.06), new T.MeshStandardMaterial({ color: 0x143f86, roughness: 0.7 }));
  hem.rotation.x = -Math.PI / 2;
  hem.position.y = -0.001;
  hem.receiveShadow = true;
  tarp.add(hem, sheet);
  const eye = new T.MeshStandardMaterial({ color: 0xc9ccd0, roughness: 0.35, metalness: 0.9 });
  for (const sx of [-1, 1]) for (const sy of [-1, 0, 1]) {
    const e = new T.Mesh(new T.RingGeometry(0.008, 0.016, 16), eye);
    e.rotation.x = -Math.PI / 2;
    e.position.set(sx * (tc.w / 2 - 0.04), 0.0012, sy * (tc.h / 2 - 0.04));
    tarp.add(e);
  }
  tarp.position.set(tc.c[0], 0.004, -tc.c[1]);
  root.add(tarp);
  parent.add(root);

  // every part: where it is fitted (as exported) and where it lies on the tarp
  const pieces = [];
  for (const p of meta.pieces) {
    const node = g.scene.getObjectByName(nodeName(p.node));
    if (!node) { console.warn('Build R1: part missing in the model', p.node); continue; }
    const it = { ...p, node, a: { p: node.position.clone(), q: node.quaternion.clone() }, t: null, u: 0, to: 0, wait: 0 };
    if (p.tarp) {
      const [x, y, z, qw, qx, qy, qz] = p.tarp;
      it.t = { p: new T.Vector3(x, z, -y), q: new T.Quaternion(qx, qz, -qy, qw) };
      it.lift = 0.3 + 0.18 * it.t.p.distanceTo(it.a.p);
    }
    pieces.push(it);
  }
  const N = meta.steps.length;
  const api = { root, meta, pieces, step: 0, playing: false };
  const pose = (it) => {
    const e = it.u * it.u * (3 - 2 * it.u);
    if (!it.t) {                                    // cables and tubes: they grow in once their step is fitted
      it.node.visible = it.u > 0.001;
      it.node.scale.setScalar(Math.max(e, 0.001));
      return;
    }
    it.node.position.lerpVectors(it.t.p, it.a.p, e);
    it.node.position.y += Math.sin(Math.PI * e) * it.lift;
    it.node.quaternion.slerpQuaternions(it.t.q, it.a.q, e);
  };
  pieces.forEach(pose);

  // ── the step card ──
  const css = document.createElement('style');
  css.textContent = `#kitcard{position:fixed;top:74px;left:12px;width:286px;max-height:calc(100vh - 160px);overflow:hidden auto;box-sizing:border-box;display:none;z-index:30;
    padding:12px 12px 10px;background:rgba(12,15,20,.9);border:1px solid rgba(255,255,255,.14);border-radius:14px;color:#e8edf3;backdrop-filter:blur(6px)}
  #kitcard.open{display:block} #kitcard h3{margin:0;font:700 11px/1 var(--mono,monospace);letter-spacing:.12em;color:#9fe6f7;text-transform:uppercase}
  #kitcard .now{margin:8px 0 2px;font:700 17px/1.2 inherit} #kitcard .sub{margin:0 0 8px;font:400 12.5px/1.35 inherit;color:#a9b4c0}
  #kitcard .dots{display:flex;gap:4px;margin:8px 0} #kitcard .dots button{flex:1;height:22px;padding:0;border-radius:6px;border:0;cursor:pointer;
    background:rgba(255,255,255,.1);color:#cfd8e1;font:600 11px/1 inherit} #kitcard .dots button.done{background:rgba(69,198,230,.32);color:#fff}
  #kitcard .dots button.cur{background:#45c6e6;color:#06222b}
  #kitcard .row{display:flex;gap:6px} #kitcard .row button{flex:1;padding:8px 6px;border-radius:9px;border:1px solid rgba(255,255,255,.16);
    background:rgba(255,255,255,.06);color:#e8edf3;font:600 13px/1 inherit;cursor:pointer} #kitcard .row button:hover{background:rgba(255,255,255,.14)}
  #kitcard .row button:disabled{opacity:.35;cursor:default} #kitcard .row button.go{background:#45c6e6;border-color:#45c6e6;color:#06222b}
  #kitcard ul{list-style:none;margin:10px 0 0;padding:0} #kitcard li{padding:5px 0;border-top:1px solid rgba(255,255,255,.08);font:600 13px/1.25 inherit}
  #kitcard .kit-tip{position:static;margin:10px 0 0;padding:8px 10px;border-left:3px solid #ffb547;border-radius:4px;background:rgba(255,181,71,.1);font:400 12.5px/1.4 inherit;color:#ffe2b0}
  #kitcard li small{display:block;font:400 11.5px/1.3 inherit;color:#a9b4c0}
  #kitcard .foot{margin:10px 0 0;font:400 11.5px/1.4 inherit;color:#a9b4c0} #kitcard a{color:#9fe6f7}
  #app.focus~#kitcard,body:has(#app.focus) #kitcard{display:none}
  @media (max-width:700px){#kitcard{top:auto;bottom:66px;left:8px;right:8px;width:auto;max-height:36vh}}`;
  document.head.appendChild(css);
  const card = document.createElement('div');
  card.id = 'kitcard';
  document.body.appendChild(card);
  const draw = () => {
    const k = api.step, mine = pieces.filter((p) => p.step === k);
    const fitted = pieces.filter((p) => p.step <= k).length;
    card.innerHTML = `<h3>Build R1 · ${fitted} of ${pieces.length} parts fitted</h3>
      <p class="now">${k ? `Step ${k} of ${N} · ${esc(meta.steps[k - 1])}` : 'Every part, on the tarp'}</p>
      <p class="sub">${k ? `${mine.length} part${mine.length === 1 ? '' : 's'} go on in this step.` : `${pieces.length} parts, ${N} steps. Press Next to fit the frame.`}</p>
      <div class="dots">${meta.steps.map((s, i) => `<button data-k="${i + 1}" title="Step ${i + 1}: ${esc(s)}" class="${i + 1 < k ? 'done' : i + 1 === k ? 'cur' : ''}">${i + 1}</button>`).join('')}</div>
      <div class="row"><button data-k="${k - 1}" ${k ? '' : 'disabled'}>◀ Back</button><button data-k="${k + 1}" ${k < N ? '' : 'disabled'}>Next ▶</button>
        <button data-play class="go">${api.playing ? '❚❚ Pause' : k >= N ? '↺ Again' : '▶ Play'}</button></div>
      ${k ? `<p class="kit-tip">${esc(TIPS[k - 1])}</p>` : ''}
      <ul>${mine.map((p) => `<li>${esc(p.label || p.name.replaceAll('_', ' '))}${p.note ? `<small>${esc(p.note)}</small>` : ''}</li>`).join('')}</ul>
      <p class="foot">The full-height R1 for tomato rows. About ₹2.0–2.1 lakh in parts (Nov 2026 estimate, check before buying).
        R1 is a concept: a hose, mud or a crate on the path would stop it, and that is not solved. The code is starter
        code, not run on hardware.
        <a href="${GUIDE}" target="_blank" rel="noopener">Parts list, wiring and code</a></p>`;
  };
  api.go = (k, quick = false) => {
    k = Math.max(0, Math.min(N, k));
    const up = k > api.step;
    let i = 0;
    for (const it of pieces) {
      const to = it.step <= k ? 1 : 0;
      if (to === it.to) continue;
      it.to = to;
      it.wait = quick ? 0 : up ? (it.step - api.step - 1) * 0.5 + 0.11 * i++ + (it.t ? 0 : 0.7) : 0.03 * i++;
      if (quick) { it.u = to; pose(it); }
    }
    api.step = k;
    draw();
    GH.dirtyShadows?.();
  };
  let playT = 0;
  api.play = (on) => {
    api.playing = on;
    if (on && api.step >= N) api.go(0);
    playT = on ? 0.9 : 0;
    draw();
  };
  card.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b || b.disabled) return;
    if ('play' in b.dataset) { api.play(!api.playing); return; }
    api.playing = false;
    api.go(+b.dataset.k);
  });
  api.update = (dt) => {
    if (!root.visible) return;
    let moving = false;
    for (const it of pieces) {
      if (it.u === it.to) continue;
      moving = true;
      if (it.wait > 0) { it.wait -= dt; continue; }
      const d = dt / (it.t ? 0.95 : 0.5);
      it.u = it.to > it.u ? Math.min(1, it.u + d) : Math.max(0, it.u - d * 1.6);
      pose(it);
    }
    if (moving) GH.dirtyShadows?.();
    if (api.playing && !moving) {
      playT -= dt;
      if (playT <= 0) {
        if (api.step >= N) api.play(false);
        else { api.go(api.step + 1); playT = 1.1; }
      }
    }
  };
  api.show = (on) => {
    root.visible = on;
    card.classList.toggle('open', on);
    if (on) draw(); else api.playing = false;
  };
  return api;
}
