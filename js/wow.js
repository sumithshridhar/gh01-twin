// The showroom's look (11 Nov 2026): the farm as a slice of land lifted out of the ground, like the cut-away in reel #45.
//   1. the land ends at the farm's edge: a cut slab of red soil floats in the sky (the village, hills and fields that
//      surrounded it are hidden; `?world=full` brings them back, and video capture keeps them)
//   2. morning light with the sun 48° up, the same height as the sun in the photographed sky, so shadows match it
//   3. a slow orbit until the visitor touches the view
//   4. the pond ripples
//   5. ✂ Slice: drag to cut the greenhouse open like a cake and look inside
// Everything here is added on top of main.js through window.GH; nothing in the simulation changes.
const P = new URLSearchParams(location.search);
const until = (f, ms = 200) => new Promise((r) => { const t = setInterval(() => { const v = f(); if (v) { clearInterval(t); r(v); } }, ms); });
const GH = await until(() => window.GH);
const T = GH.THREE, { scene, world, renderer, controls } = GH;
const FULL = P.has('capture') || P.get('world') === 'full';
let current = 'gh01';

// ---------------------------------------------------------------- 1. the slab
const SLAB = { x0: -19, x1: 59, z0: -31, z1: 27, depth: 11 };
const slabPlanes = [new T.Plane(new T.Vector3(1, 0, 0), -SLAB.x0), new T.Plane(new T.Vector3(-1, 0, 0), SLAB.x1),
  new T.Plane(new T.Vector3(0, 0, 1), -SLAB.z0), new T.Plane(new T.Vector3(0, 0, -1), SLAB.z1)];
const groundMats = new Set();
let skirt = null;
function buildSlab() {
  renderer.localClippingEnabled = true;
  const site = GH.A.comps.get('site');
  site?.meshes.forEach((m) => (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) => groundMats.add(x)));
  const w = SLAB.x1 - SLAB.x0, d = SLAB.z1 - SLAB.z0;
  const geo = new T.BoxGeometry(w, SLAB.depth, d, 1, 10, 1);
  const pos = geo.attributes.position, col = new Float32Array(pos.count * 3), c = new T.Color();
  for (let i = 0; i < pos.count; i++) {                    // topsoil, then darker and cooler with depth, like a real cut
    const k = (SLAB.depth / 2 - pos.getY(i)) / SLAB.depth;
    c.setRGB(1, 0.93, 0.88).lerp(new T.Color(0.42, 0.33, 0.3), Math.min(1, k * 1.25)).multiplyScalar(k < 0.06 ? 1 : 0.9);
    col.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new T.BufferAttribute(col, 3));
  GH.boxUV(geo, 4.2);
  const side = new T.MeshStandardMaterial({ color: 0x8a4b33, roughness: 1, vertexColors: true });
  side.name = 'slab_side';
  const tl = new T.TextureLoader();
  const ld = (f, srgb, put) => tl.load(`assets/tex/${f}`, (t) => { t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 8; if (srgb) t.colorSpace = T.SRGBColorSpace; put(t); side.needsUpdate = true; });
  ld('soil_diff.jpg', true, (t) => { side.map = t; side.color.set(0xffffff); });
  ld('soil_nor.jpg', false, (t) => { side.normalMap = t; side.normalScale.set(1.6, 1.6); });
  const none = new T.MeshBasicMaterial({ visible: false });
  const under = new T.MeshStandardMaterial({ color: 0x2a1d18, roughness: 1 });
  skirt = new T.Mesh(geo, [side, side, none, under, side, side]);      // no top face: the real ground (and the pond dug into it) is the top
  skirt.position.set((SLAB.x0 + SLAB.x1) / 2, -SLAB.depth / 2 - 0.06, (SLAB.z0 + SLAB.z1) / 2);
  skirt.receiveShadow = true;
  skirt.userData.fx = true;                                // not pickable, never highlighted
  scene.add(skirt);
}
function applySlab() {
  const on = !FULL && current === 'gh01';
  groundMats.forEach((m) => { m.clippingPlanes = on ? slabPlanes : null; m.needsUpdate = true; });
  if (skirt) skirt.visible = on;
  if (world.backdrop && !FULL) world.backdrop.visible = !on;   // other scenes keep the village and the hills behind them
  GH.dirtyShadows?.();
}

// ---------------------------------------------------------------- 4. the pond ripples
const ripple = (() => {
  const n = 256, c = document.createElement('canvas');
  c.width = c.height = n;
  const g = c.getContext('2d'), img = g.createImageData(n, n);
  const h = (x, y) => {                                    // tileable: whole numbers of waves across the tile
    const u = (x / n) * Math.PI * 2, v = (y / n) * Math.PI * 2;
    return Math.sin(u + 3 * v) + 0.8 * Math.sin(3 * u - v + 1.3) + 0.6 * Math.sin(4 * u + 2 * v + 2.1) + 0.5 * Math.sin(5 * v - 2 * u + 0.7)
      + 0.35 * Math.sin(6 * u + v + 4.0) + 0.3 * Math.sin(u - 6 * v + 5.2) + 0.2 * Math.sin(9 * u + 7 * v + 0.4) + 0.15 * Math.sin(11 * v - 8 * u + 3.3);
  };
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const dx = h(x + 1, y) - h(x - 1, y), dy = h(x, y + 1) - h(x, y - 1), i = (y * n + x) * 4;
    const v = new T.Vector3(-dx * 3.0, -dy * 3.0, 1).normalize();
    img.data[i] = (v.x * 0.5 + 0.5) * 255; img.data[i + 1] = (v.y * 0.5 + 0.5) * 255; img.data[i + 2] = (v.z * 0.5 + 0.5) * 255; img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const t = new T.CanvasTexture(c);
  t.wrapS = t.wrapT = T.RepeatWrapping;
  return t;
})();
let pondFound = false;
function findPond() {
  scene.traverse((o) => {
    if (!o.isMesh || Array.isArray(o.material) || !(o.material?.name || '').startsWith('pond_water') || o.material.normalMap) return;
    GH.boxUV(o.geometry, 5.5);
    Object.assign(o.material, { normalMap: ripple, roughness: 0.04, metalness: 0, opacity: 0.9, envMapIntensity: 1.5 });
    o.material.normalScale = new T.Vector2(0.3, 0.3);
    o.material.color.set(0x3f6f66);
    o.material.needsUpdate = true;
    pondFound = true;
  });
  return pondFound;
}

// ---------------------------------------------------------------- 5. slice the greenhouse open
const HOUSE = { x0: -3.4, x1: 10.2, zFront: 3.9, reach: 5.1 };          // GH-01 stands at x -2..9, z -3.4..2.5
const cut = new T.Plane(new T.Vector3(0, 0, -1), HOUSE.zFront);
// with clipIntersection a fragment goes only if it is on the minus side of ALL of these = inside the cut-away box
const slicePlanes = [cut, new T.Plane(new T.Vector3(0, 0, 1), -HOUSE.zFront), new T.Plane(new T.Vector3(-1, 0, 0), HOUSE.x0), new T.Plane(new T.Vector3(1, 0, 0), -HOUSE.x1)];
const sliced = new Map();                                 // material -> its own side
let slicing = false;
function setSlice(v) {                                      // 0 whole .. 1 cut past the middle
  cut.constant = HOUSE.zFront - v * HOUSE.reach;
  const on = v > 0.005;
  if (on !== slicing) {
    slicing = on;
    if (on) scene.traverse((o) => {
      if (!(o.isMesh || o.isInstancedMesh) || o === skirt || o.userData.fx) return;
      (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => {
        if (!m || m.isShaderMaterial || sliced.has(m) || groundMats.has(m) || (m.name || '').startsWith('real_')) return;
        sliced.set(m, m.side);
        m.clippingPlanes = slicePlanes;
        m.clipIntersection = true;
        m.clipShadows = true;
      });
    });
    sliced.forEach((side, m) => { m.side = on ? T.DoubleSide : side; m.needsUpdate = true; });   // cut shells show their inside
  }
  GH.dirtyShadows?.();
}
function sliceUI() {
  const css = document.createElement('style');
  css.textContent = `#slicepop{position:fixed;bottom:64px;left:50%;transform:translateX(-50%);display:none;gap:10px;align-items:center;padding:10px 14px;
    background:rgba(12,15,20,.92);border:1px solid rgba(255,255,255,.14);border-radius:14px;z-index:40;backdrop-filter:blur(6px);font-size:13px}
    #slicepop.open{display:flex}#slicepop input{width:min(46vw,320px);accent-color:#F2C230}#app.alt-scene #slicebtn{display:none}`;
  document.head.appendChild(css);
  const pop = document.createElement('div');
  pop.id = 'slicepop';
  pop.innerHTML = '<span>Whole</span><input type="range" min="0" max="100" value="0" aria-label="Slice the greenhouse open"><span>Cut open</span>';
  document.body.appendChild(pop);
  const btn = document.createElement('button');
  btn.className = 'btn';
  btn.id = 'slicebtn';
  btn.textContent = '✂ Slice';
  btn.title = 'Cut the greenhouse open and look inside';
  btn.setAttribute('aria-pressed', 'false');
  document.getElementById('bottom')?.insertBefore(btn, document.getElementById('walk') || null);
  const range = pop.querySelector('input');
  let shown = false;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = pop.classList.toggle('open');
    if (open && !shown) {                                  // first time: face the cut and open it halfway, so the idea is seen at once
      shown = true;
      GH.deselect?.(true);
      GH.flyTo(GH.B(3.4, -13.0, 8.2), GH.B(3.6, 0.6, 0.9), 1.4);     // from over the pond, looking down into the cut house
      let k = 0;
      const t = setInterval(() => { k += 0.04; range.value = String(Math.round(62 * Math.min(1, k))); setSlice(range.value / 100); btn.setAttribute('aria-pressed', 'true'); if (k >= 1) clearInterval(t); }, 30);
    }
  });
  range.addEventListener('input', () => { setSlice(range.value / 100); btn.setAttribute('aria-pressed', String(range.value > 0)); });
  addEventListener('click', (e) => { if (!pop.contains(e.target)) pop.classList.remove('open'); });
  addEventListener('gh-scene', (e) => { if (e.detail !== 'gh01') { pop.classList.remove('open'); range.value = '0'; setSlice(0); btn.setAttribute('aria-pressed', 'false'); } });
}

// ---------------------------------------------------------------- film and glass in HQ
// With HQ on, see-through film is blended before tone mapping, so the bright sky it mirrors turned the houses milky.
// Mirror less sky there; fast graphics keep the stronger reflection that suits them.
function tuneFilm() {
  const hq = document.querySelector('#toggles [data-t="hq"]')?.getAttribute('aria-pressed') === 'true';
  scene.traverse((o) => {
    if (!o.isMesh) return;
    (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => {
      const n = m?.name || '';
      if (n.startsWith('polycarb')) { m.envMapIntensity = hq ? 0.5 : 1.6; m.opacity = hq ? 0.07 : 0.1; }
      else if (/^(uv_film|acrylic|glass)/.test(n)) m.envMapIntensity = hq ? 0.5 : 1;
    });
  });
}

// ---------------------------------------------------------------- go
if (!P.has('capture')) {
  buildSlab();
  applySlab();
  addEventListener('gh-scene', (e) => { current = e.detail; applySlab(); });
  sliceUI();
  // 2. morning: the sun as high as it stands in the sky photograph (48°), long enough shadows to give things weight
  await until(() => GH.sim);
  GH.sim.t = 8 * 60 + 45;
  world.setTime(GH.sim.t, GH.sim.cloud);
  GH.dirtyShadows?.();
  // 3. a slow drift until the visitor takes over
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.28;
  const stop = () => { controls.autoRotate = false; };
  for (const ev of ['pointerdown', 'wheel', 'touchstart']) renderer.domElement.addEventListener(ev, stop, { once: true, passive: true });
  addEventListener('keydown', stop, { once: true });
  // 4. the pond arrives with the farm file a little later
  until(() => { tuneFilm(); return findPond(); }, 1200);
  const hqBtn = document.querySelector('#toggles [data-t="hq"]');
  if (hqBtn) new MutationObserver(tuneFilm).observe(hqBtn, { attributes: true, attributeFilter: ['aria-pressed'] });
  addEventListener('gh-scene', () => setTimeout(tuneFilm, 600));
  const upd = GH.farm4.update.bind(GH.farm4);
  GH.farm4.update = (dt, ct) => { upd(dt, ct); ripple.offset.x += dt * 0.012; ripple.offset.y += dt * 0.007; };
}
GH.wow = { setSlice, SLAB };
