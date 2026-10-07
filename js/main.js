// GH-01 digital twin — main: loading, rendering, picking, explode + blueprint, walk mode, actuator animation, HUD.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { computeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh';
import { World, B, Bv } from './world.js';
import { FX } from './fx.js';
import { Blueprint } from './blueprint.js';
import { Sim } from './sim.js';
import { Sound } from './sound.js';

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;
const $ = (s) => document.querySelector(s);
const V3 = THREE.Vector3;
const clamp = THREE.MathUtils.clamp;
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const easeOutBack = (t) => { const c1 = 1.5, c3 = c1 + 1; return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2; };
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const MOBILE = matchMedia('(max-width: 820px)').matches;

// ?capture: the video recorder drives frames itself (GH.frame) and the HTML HUD is hidden; overlays are added in Remotion
const CAPTURE = new URLSearchParams(location.search).has('capture');

// ── renderer / scene / post (two quality tiers) ────────────────
const canvas = $('#c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
const GPU = (() => { const gl = renderer.getContext(); const d = gl.getExtension('WEBGL_debug_renderer_info'); return d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : ''; })();
let HIGH = !MOBILE && /NVIDIA|GeForce|RTX|GTX|Radeon RX|Radeon Pro|Arc A/i.test(GPU);
try { const q = localStorage.getItem('gh-quality'); if (q) HIGH = q === 'high'; } catch (e) { /* storage blocked */ }
let PR = 1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.autoUpdate = false;
renderer.toneMapping = THREE.AgXToneMapping;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.03, 1200);
camera.position.set(-16, 7, 16);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI * 0.495;
controls.minDistance = 0.12;
controls.maxDistance = 95;
controls.target.set(4.5, 1.2, 0);
let composer = null, bloom = null;
function buildComposer() {
  const rt = new THREE.WebGLRenderTarget(innerWidth * PR, innerHeight * PR, { type: THREE.HalfFloatType, samples: 4 });
  composer = new EffectComposer(renderer, rt);
  composer.addPass(new RenderPass(scene, camera));
  bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.3, 0.45, 1.6);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());
  composer.setPixelRatio(PR);
  composer.setSize(innerWidth, innerHeight);
}
const world = new World(renderer, scene);
let shadowEvery = 6, shadowDirty = true;
function applyQuality() {
  PR = HIGH ? Math.min(devicePixelRatio, 1.5) : 1;
  renderer.setPixelRatio(PR);
  renderer.setSize(innerWidth, innerHeight, false);
  renderer.shadowMap.type = HIGH ? THREE.PCFSoftShadowMap : THREE.PCFShadowMap;
  const ms = HIGH ? 2048 : 1024;
  world.sun.shadow.mapSize.set(ms, ms);
  if (world.sun.shadow.map) { world.sun.shadow.map.dispose(); world.sun.shadow.map = null; }
  shadowEvery = HIGH ? 4 : 10;
  shadowDirty = true;
  if (HIGH && !composer) buildComposer();
  document.querySelector('#toggles [data-t="hq"]')?.setAttribute('aria-pressed', HIGH);
}
applyQuality();

// ── app object shared with sim + fx ───────────────────────────
const A = { scene, camera, renderer, comps: new Map(), sound: new Sound(), alarmText: '' };
const fx = new FX(A);
A.fx = fx;
const blueprint = new Blueprint($('#bp'));
const hlCache = new Map();
let hlMeshes = [];
function hlMat(m) {
  let h = hlCache.get(m);
  if (!h) {
    h = m.clone();
    if (h.emissive) { h.emissive = new THREE.Color(0xf2c230); h.emissiveIntensity = 0.3; }
    hlCache.set(m, h);
  }
  return h;
}
function highlight(objs) {
  for (const m of hlMeshes) if (m.userData.hlOrig) { m.material = m.userData.hlOrig; delete m.userData.hlOrig; }
  hlMeshes = [];
  for (const o of objs) o.traverse((m) => {
    if (!m.isMesh || m.userData.fx || m.userData.hlOrig || m.material === ghostMat) return;
    m.userData.hlOrig = m.material;
    m.material = hlMat(m.material);
    hlMeshes.push(m);
  });
}

// ── loading ───────────────────────────────────────────────────
const FILES = [['assets/gh_env.glb.json', 0.8, 'Structure, rows, water mains'], ['assets/gh_tech.glb.json', 1.5, 'Tanks, fertigation skid, control cabinet'],
  ['assets/gh_equip.glb.json', 1.4, 'Fans, sensors, cameras, robot'], ['assets/gh_plants.glb.json', 3.9, '54 tomato plants with IDs'],
  ['assets/gh_farm.glb.json', 0.9, 'The farm: solar packhouse, pond, entry room, shade net']];
const loaded = FILES.map(() => 0);
const FIRST = 3;   // structure, tech corner, equipment: enough to start; the plants stream in afterwards
const setProgress = (msg) => {
  const fs = FILES.slice(0, FIRST);
  const tot = fs.reduce((s, f) => s + f[1], 0);
  const got = fs.reduce((s, f, i) => s + f[1] * loaded[i], 0);
  $('#ld-bar').style.width = `${Math.round((got / tot) * 100)}%`;
  if (msg) $('#ld-step').textContent = msg;
};
const growChip = (text) => { const el = $('#growchip'); if (!el) return; el.hidden = !text; if (text) el.textContent = text; };
const gltfLoader = new GLTFLoader();
// 3D files are shipped as {"gz": base64(gzip(glb))} so any static host can serve them; unpacked here
async function loadGLB(f, i) {
  const res = await fetch(f[0]);
  if (!res.ok) throw new Error(`${f[0]}: HTTP ${res.status}`);
  const total = +res.headers.get('content-length') || f[1] * 1e6;
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); got += value.length;
    loaded[i] = Math.min(0.97, got / total);
    if (i < FIRST) setProgress(`Loading ${f[2]}… ${Math.round(loaded[i] * 100)} %`);
    else if (i === 3) growChip(`Planting 54 plants · ${Math.round(loaded[i] * 100)} %`);
  }
  const text = new TextDecoder().decode(await new Blob(chunks).arrayBuffer());
  const { gz } = JSON.parse(text);
  const bin = Uint8Array.from(atob(gz), (c) => c.charCodeAt(0));
  const glb = await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const g = await gltfLoader.parseAsync(glb, '');
  loaded[i] = 1;
  if (i < FIRST) setProgress(`Loaded: ${f[2]}`);
  return g;
}

let SIMDATA, sim;
const SEE = ['polycarb', 'net', 'glass', 'acrylic', 'water', 'nutrient', 'silicone_clear', 'chainlink', 'aluminet', 'pond_water',
  'disinfectant'];
const PLANTMAT = ['leaf', 'stem', 'sepal', 'flower', 'cotyledon', 'fruit', 'twine', 'stem_old', 'anther'];
const NOPICK_PARTS = new Set(['foundation_floor', 'polycarbonate_walls', 'polycarbonate_roof', 'insect_net']);
const pickables = [];
const growLED = new THREE.MeshStandardMaterial({ color: 0xfff1e0, emissive: 0xffd9c2, emissiveIntensity: 0, roughness: 0.3 });
const ghostMat = new THREE.MeshBasicMaterial({ color: 0x3aa6d8, transparent: true, opacity: 0.07, depthWrite: false, blending: THREE.AdditiveBlending });
const ghostEdgeMat = new THREE.MeshBasicMaterial({ color: 0x4fc3f7, wireframe: true, transparent: true, opacity: 0.05, depthWrite: false, blending: THREE.AdditiveBlending });
let holo = null;
function makeHolo() {
  const g = new THREE.Group();
  const grid = new THREE.GridHelper(4, 40, 0x4fc3f7, 0x1d5a7a);
  grid.material.transparent = true; grid.material.opacity = 0.55; grid.material.depthWrite = false;
  const ring = new THREE.Mesh(new THREE.RingGeometry(1.9, 2.0, 96), new THREE.MeshBasicMaterial({ color: 0x4fc3f7, transparent: true, opacity: 0.6, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }));
  ring.rotation.x = -Math.PI / 2;
  const disc = new THREE.Mesh(new THREE.CircleGeometry(2, 96), new THREE.MeshBasicMaterial({ color: 0x0a2a3a, transparent: true, opacity: 0.55, depthWrite: false }));
  disc.rotation.x = -Math.PI / 2; disc.position.y = -0.002;
  g.add(disc, grid, ring);
  g.userData = { ring, grid };
  g.renderOrder = 1;
  scene.add(g);
  return g;
}
let padMat = null;

function register(root) {
  const added = [];
  root.traverse((o) => {
    const u = o.userData;
    if (u.gh_type !== 'component' || A.comps.has(u.gh_id) || String(u.gh_id).startsWith('_')) return;
    let state = {};
    try { state = JSON.parse(u.state || '{}'); } catch (e) { /* keep empty */ }
    const c = { id: u.gh_id, root: o, meta: { title: u.title, category: u.category, summary: u.summary, how: u.how_it_works,
      sensors: u.sensors, control: u.control, real: u.real_part, cost: u.cost, state, view: u.view }, parts: [], nodes: [], meshes: [],
    explodeT: 0, explodeTarget: 0, status: null };
    o.children.forEach((ch) => { if (ch.userData.gh_type === 'part' || ch.userData.gh_type === 'group') c.parts.push({ obj: ch, name: ch.userData.part_name, desc: ch.userData.desc }); });
    c.parts.forEach((p, k) => p.obj.traverse((n) => {
      if (n.isMesh) { n.userData.partIdx = k; }
      const e = n.userData.explode;
      if (e && n !== o) n.userData._n = { base: n.position.clone(), dir: new V3(e[0], e[2], -e[1]), baseScale: n.scale.clone(), k };
    }));
    o.traverse((n) => {
      if (n.userData._n) c.nodes.push(n);
      if (n.isMesh) { n.userData.comp = c.id; c.meshes.push(n); }
    });
    A.comps.set(c.id, c);
    added.push(c);
  });
  return added;
}

// ── real surfaces (6 Oct 2026): photographed CC0 textures from Poly Haven (assets/tex/CREDITS.txt) ──────────
const texLoader = new THREE.TextureLoader();
const REAL = {};
function realMat(key, opts = {}) {
  if (REAL[key]) return REAL[key];
  const ld = (f, srgb) => {
    const t = texLoader.load(`assets/tex/${f}`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 8;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    return t;
  };
  const m = new THREE.MeshStandardMaterial({ map: ld(`${key}_diff.jpg`, true), normalMap: ld(`${key}_nor.jpg`, false),
    roughness: opts.roughness ?? 0.92, metalness: opts.metalness ?? 0, color: opts.color ?? 0xffffff });
  m.name = `real_${key}`;
  return (REAL[key] = m);
}
// UVs from position, picking the plane each face mostly faces (meshes from Blender boxes have no UVs of their own)
function boxUV(geo, tile, swap = false) {
  const p = geo.attributes.position, n = geo.attributes.normal;
  if (!p || !n) return;
  const uv = new Float32Array(p.count * 2);
  for (let i = 0; i < p.count; i++) {
    const ax = Math.abs(n.getX(i)), ay = Math.abs(n.getY(i)), az = Math.abs(n.getZ(i));
    let u, v;
    if (ay >= ax && ay >= az) { u = p.getX(i); v = p.getZ(i); } else if (ax >= az) { u = p.getZ(i); v = p.getY(i); } else { u = p.getX(i); v = p.getY(i); }
    if (swap) [u, v] = [v, u];
    uv[i * 2] = u / tile; uv[i * 2 + 1] = v / tile;
  }
  geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
}
const REALMAP = [['concrete', 'concrete', 2.0], ['brick', 'brick', 1.4], ['plaster_white', 'plaster', 2.5]];

function prepareMaterials(root, comps) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    let see = false;
    mats.forEach((m) => {
      const n = m.name || '';
      if (SEE.some((k) => n.startsWith(k))) {
        see = true; m.transparent = true; m.depthWrite = false; m.side = THREE.DoubleSide;
        if (n.startsWith('polycarb')) { m.opacity = 0.1; m.roughness = 0.06; m.metalness = 0; m.envMapIntensity = 1.6; }
        if (n.startsWith('net')) m.opacity = 0.2;
        if (n.startsWith('chainlink')) m.opacity = 0.32;
        if (n.startsWith('aluminet')) { m.opacity = 0.7; m.metalness = 0.8; m.roughness = 0.4; }
        if (n.startsWith('pond_water')) { m.opacity = 0.86; m.roughness = 0.05; }
      }
      if (PLANTMAT.some((k) => n.startsWith(k))) m.side = THREE.DoubleSide;
      if (n.startsWith('pad')) padMat = m;
    });
    const real = REALMAP.find(([k]) => mats.some((m) => (m.name || '').startsWith(k)));
    if (real) {
      boxUV(o.geometry, real[2]);
      if (Array.isArray(o.material)) o.material = o.material.map((m) => ((m.name || '').startsWith(real[0]) ? realMat(real[1]) : m));
      else o.material = realMat(real[1]);
    }
    o.castShadow = !see;
    o.receiveShadow = true;
    o.userData.see = see;
  });
  const site = comps.find((c) => c.id === 'site');
  if (site) site.meshes.filter((m) => site.parts[m.userData.partIdx]?.name === 'ground').forEach((m) => {
    boxUV(m.geometry, 3.5);                                         // Kolar red laterite soil, a 3.5 m photo tile
    m.material = realMat('soil', { color: 0xf2e6dc });
    m.castShadow = false;
  });
  const ph = comps.find((c) => c.id === 'packhouse');
  if (ph) ph.meshes.filter((m) => ph.parts[m.userData.partIdx]?.name === 'roof').forEach((m) => {
    boxUV(m.geometry, 1.2, true);                                   // ribs run down the slope
    m.material = realMat('corrugated', { metalness: 0.55, roughness: 0.45 });
  });
  for (const c of comps) {
    if (!c.id.startsWith('led_r')) continue;
    c.meshes.forEach((m) => {
      if (Array.isArray(m.material)) m.material = m.material.map((mm) => (mm.name.startsWith('led_white') ? growLED : mm));
      else if (m.material.name.startsWith('led_white')) m.material = growLED;
    });
  }
  for (const c of comps) {
    if (c.id === 'site') continue;
    c.meshes.forEach((m) => {
      if (m.userData.see) return;
      const partName = c.parts[m.userData.partIdx]?.name;
      if (NOPICK_PARTS.has(partName)) return;
      pickables.push(m);
    });
  }
}

async function buildBVH() {
  const geos = new Set(pickables.map((m) => m.geometry));
  let t0 = performance.now();
  for (const g of geos) {
    if (!g.boundsTree) g.computeBoundsTree();
    if (performance.now() - t0 > 10) { await new Promise((r) => setTimeout(r, 0)); t0 = performance.now(); }
  }
}

// ── plant instancing: 54 plants drawn as ~40 instanced batches; a plant is "promoted" to its real
//    (explodable) meshes while hovered or selected ──────────────────────────────────────────────
const plantInst = [];
const plantSlots = new Map();
const ZERO = new THREE.Matrix4().makeScale(0, 0, 0);
function instancePlants() {
  const groups = new Map();
  for (const c of A.comps.values()) {
    if (!c.id.startsWith('plant_')) continue;
    c.root.updateWorldMatrix(true, true);
    c.instanced = [];
    c.meshes.forEach((m) => {
      const part = c.parts[m.userData.partIdx]?.name;
      if (m.material.map) return;                                   // the unique QR/ID print stays a normal mesh
      const key = part === 'id_tag' ? `tag|${m.material.uuid}|${m.geometry.attributes.position.count}` : `${m.geometry.uuid}|${m.material.uuid}`;
      if (!groups.has(key)) groups.set(key, { geo: m.geometry, mat: m.material, items: [] });
      groups.get(key).items.push({ m, c });
      c.instanced.push(m);
    });
  }
  for (const g of groups.values()) {
    const im = new THREE.InstancedMesh(g.geo, g.mat, g.items.length);
    g.items.forEach(({ m, c }, i) => {
      im.setMatrixAt(i, m.matrixWorld);
      if (!plantSlots.has(c.id)) plantSlots.set(c.id, []);
      plantSlots.get(c.id).push({ im, i, mat: m.matrixWorld.clone(), pivot: c.root.getWorldPosition(new V3()), delay: 0 });
      m.visible = false;
    });
    im.castShadow = true; im.receiveShadow = true;
    im.computeBoundingSphere();
    im.userData.fx = true;
    scene.add(im);
    plantInst.push(im);
  }
  for (const slots of plantSlots.values()) for (const s of slots) s.delay = Math.max(0, (s.pivot.x - 1.9) * 0.16);   // a wave from the tech corner to the pad wall
}
function promote(c, on) {
  if (!c || !c.id.startsWith('plant_') || !plantSlots.has(c.id) || !!c.promoted === on) return;
  c.promoted = on;
  for (const s of plantSlots.get(c.id)) { s.im.setMatrixAt(s.i, on ? ZERO : s.mat); s.im.instanceMatrix.needsUpdate = true; }
  c.instanced.forEach((m) => { m.visible = on; });
  shadowDirty = true;
}
// plants grow in when their file arrives (they load after the rest of the house)
let growT = -1;
const _gm = new THREE.Matrix4(), _gs = new THREE.Matrix4(), _gt = new THREE.Matrix4();
function growPlants(dt) {
  if (growT < 0) return;
  growT += dt;
  let busy = false;
  for (const [id, slots] of plantSlots) {
    const c = A.comps.get(id);
    if (c?.promoted) continue;
    for (const s of slots) {
      const u = Math.min(1, Math.max(0, (growT - s.delay) / 0.8));
      if (u < 1) busy = true;
      const k = u >= 1 ? 1 : easeOutBack(u);
      _gt.makeTranslation(s.pivot.x, s.pivot.y, s.pivot.z);
      _gs.makeScale(Math.max(k, 1e-4), Math.max(k, 1e-4), Math.max(k, 1e-4));
      _gm.copy(_gt).multiply(_gs).multiply(_gt.makeTranslation(-s.pivot.x, -s.pivot.y, -s.pivot.z)).multiply(s.mat);
      s.im.setMatrixAt(s.i, _gm);
      s.im.instanceMatrix.needsUpdate = true;
    }
  }
  shadowDirty = true;
  if (!busy) { growT = -1; plantInst.forEach((im) => im.computeBoundingSphere()); }
}

let hoverComp = null;
function setHover(c) {
  if (hoverComp === c) return;
  if (hoverComp && hoverComp !== sel) promote(hoverComp, false);
  hoverComp = c;
  if (c) { promote(c, true); highlight(c.meshes.length > 400 ? [] : [c.root]); } else highlight([]);
}

// ── actuator hooks ────────────────────────────────────────────
const H = {};
const partObj = (cid, name) => A.comps.get(cid)?.parts.find((p) => p.name === name)?.obj;
function hookActuators() {
  H.fans = ['exhaust_fan_1', 'exhaust_fan_2'].map((id) => partObj(id, 'blades'));
  H.haf = ['haf_fan_1', 'haf_fan_2'].map((id) => partObj(id, 'blades'));
  H.vent = partObj('greenhouse_structure', 'vent_window');
  if (H.vent) H.vent.userData.q0 = H.vent.quaternion.clone();
  H.pumpShaft = partObj('irrigation_pump', 'rotor_shaft');
  H.pumpFan = partObj('irrigation_pump', 'cooling_fan');
  H.pumpRoot = A.comps.get('irrigation_pump')?.root;
  if (H.pumpRoot) H.pumpRoot.userData.p0 = H.pumpRoot.position.clone();
  H.mixer = partObj('mix_tank', 'mixer');
  H.dosing = ['A', 'B', 'acid'].map((k) => partObj(`dosing_pump_${k}`, 'rotor'));
  H.robot = A.comps.get('scout_robot')?.root;
  H.head = partObj('scout_robot', 'sensor_head');
  H.solenoids = [1, 2, 3].map((z) => {
    const s = partObj(`zone_valve_${z}`, 'solenoid');
    const mats = [];
    s?.traverse((m) => { if (m.isMesh) { m.material = (Array.isArray(m.material) ? m.material : [m.material]).map((mm) => { const c = mm.clone(); mats.push(c); return c; }); if (m.material.length === 1) m.material = m.material[0]; } });
    return mats;
  });
  // scan cones on the robot head
  if (H.head) {
    const cone = new THREE.ConeGeometry(0.42, 0.95, 28, 1, true);
    cone.translate(0, -0.475, 0);
    cone.rotateX(-Math.PI / 2);
    const mk = (rotY, z) => { const m = new THREE.Mesh(cone, fx.scanMat); m.rotation.y = rotY; m.position.set(0.03, 0.04, z); m.userData.fx = true; m.renderOrder = 4; return m; };
    H.head.add(mk(Math.PI, -0.3), mk(0, 0.3));
  }
  // robot status beacon
  if (H.robot) {
    H.beaconMat = new THREE.MeshBasicMaterial({ color: 0x6fd08c });
    const b = new THREE.Mesh(new THREE.SphereGeometry(0.045, 16, 10), H.beaconMat);
    b.position.set(-0.02, 0.146 + 0.1 + 2.2 + 0.2, 0);
    b.userData.fx = true;
    H.robot.add(b);
    H.robotLight = new THREE.PointLight(0x6fd08c, 0.8, 1.6, 2);
    H.robotLight.position.copy(b.position);
    H.robot.add(H.robotLight);
  }
  // water network
  const W = SIMDATA.water;
  H.flowMain = fx.flowTube([...W.tank_to_pump, ...W.pump_to_manifold], 0.022);
  H.flowZones = W.zones.map((z) => ({
    man: fx.flowTube(z.manifold, 0.022), drop: fx.flowTube(z.drop, 0.018), lat: fx.flowTube(z.lateral, 0.012, 0x45c6e6, 0.8),
    drips: z.drippers.map((p) => B(p[0], p[1], p[2] + 0.06)),
  }));
  H.fogTubes = [fx.flowTube(SIMDATA.fog.feed, 0.01, 0xdff4ff, 1.8), ...SIMDATA.fog.lines.map((l) => fx.flowTube(l, 0.01, 0xdff4ff, 1.8))];
  H.nozzles = SIMDATA.fog.nozzles.map(Bv);
  H.padTube = fx.flowTube([...SIMDATA.pad.riser, ...SIMDATA.pad.top], 0.024, 0x45c6e6, 1.0);
}

const compCenter = (id) => {
  const c = A.comps.get(id);
  if (!c) return null;
  if (!c._center) c._center = new THREE.Box3().setFromObject(c.root).getCenter(new V3());
  return id === 'scout_robot' ? new THREE.Box3().setFromObject(c.root).getCenter(new V3()) : c._center;
};
A.pulse = (from, to, kind) => {
  const a = compCenter(from), b = compCenter(to);
  if (!a || !b) return;
  const key = `${from}>${to}`;
  const L = fx.link(key, a, b, kind === 'cmd' ? 'cmd' : 'sense');
  fx.pulse(L, kind === 'cmd' ? 0xf2c230 : 0x45c6e6, 1.0);
};
const SENSORS = ['climate_box_1', 'climate_box_2', 'par_sensor', 'weather_station', 'level_water_tank', 'level_mix_tank', 'flow_meter',
  'pressure_tx', 'substrate_sensor', 'drain_meter', 'slab_scale', 'sticky_trap_1', 'sticky_trap_2', 'sticky_trap_3', 'canopy_camera_1',
  'canopy_camera_2', 'sensor_flow_cell', 'esp32_node_crop', 'esp32_node_fert', 'level_pond', 'hybrid_inverter'];
const ACTUATORS = ['irrigation_pump', 'zone_valve_1', 'zone_valve_2', 'zone_valve_3', 'exhaust_fan_1', 'exhaust_fan_2', 'cooling_pad',
  'vent_drive', 'fog_pump', 'dosing_pump_A', 'dosing_pump_B', 'dosing_pump_acid', 'haf_fan_1', 'haf_fan_2', 'pond_pump', 'borewell',
  'source_valves'];
function buildNetwork() {
  SENSORS.forEach((s) => { const a = compCenter(s), b = compCenter('control_cabinet'); if (a && b) fx.link(`${s}>control_cabinet`, a, b, 'sense'); });
  ACTUATORS.forEach((s) => { const a = compCenter('control_cabinet'), b = compCenter(s); if (a && b) fx.link(`control_cabinet>${s}`, a, b, 'cmd'); });
}

// ── HUD helpers ───────────────────────────────────────────────
const logEl = $('#log');
A.log = (stage, text) => {
  const li = document.createElement('li');
  li.className = `s-${stage}`;
  li.innerHTML = `<time>${sim ? sim.clock().split('· ')[1] : ''}</time><b>${stage}</b><span>${esc(text)}</span>`;
  logEl.prepend(li);
  while (logEl.children.length > 70) logEl.lastChild.remove();
};
let chainTimer = 0;
A.chain = (stage) => {
  chainTimer = 3.5;
  document.querySelectorAll('#chain span').forEach((s) => {
    const on = stage && (s.dataset.s === stage || (stage === 'ALARM' && s.dataset.s === 'PLC'));
    s.className = on ? `on s-${stage}` : '';
  });
};
A.toast = (title, text) => {
  const d = document.createElement('div');
  d.className = 'toast';
  d.innerHTML = `<b>${esc(title)}</b>${esc(text)}`;
  $('#toasts').prepend(d);
  setTimeout(() => d.remove(), 8000);
  while ($('#toasts').children.length > 3) $('#toasts').lastChild.remove();
};
A.alarm = (text) => {
  A.alarmText = text || '';
  const a = $('#alarm');
  a.hidden = !text;
  if (text) a.textContent = `⚠ ${text}`;
  $('#mode').textContent = text ? 'ALARM · safe mode' : 'AUTO · AI advising';
  $('#mode').classList.toggle('fault', !!text);
};
A.flagComponent = (id, state) => {
  if (id === null) { for (const c of A.comps.values()) c.status = null; fx.markers.forEach((_, k) => fx.clearMarker(k)); drawSystems(); return; }
  const c = A.comps.get(id);
  if (!c) return;
  c.status = state;
  if (state === 'fault') {
    const bb = new THREE.Box3().setFromObject(c.root);
    fx.marker(id, new V3((bb.min.x + bb.max.x) / 2, bb.max.y + 0.25, (bb.min.z + bb.max.z) / 2), 0xff5a3c, '!');
  } else fx.clearMarker(id);
  drawSystems();
};
A.markPlant = (id) => {
  const c = A.comps.get(id);
  if (!c) return;
  c.status = 'fault';
  const p = c.root.getWorldPosition(new V3());
  fx.marker(id, p.add(new V3(0, 2.05, 0)), 0xff5a3c, '!');
  drawSystems();
};
A.clearMarkers = () => { fx.markers.forEach((_, k) => fx.clearMarker(k)); };
A.focusOn = (id) => { if (!touring) select(id); };

// systems list
const CAT_ORDER = ['Structure', 'Plants', 'Irrigation', 'Fertigation', 'Climate', 'Lighting', 'Sensors', 'Cameras', 'Control', 'Interface', 'Robot'];
let openCats = new Set(['Irrigation']);
function drawSystems() {
  const groups = {};
  for (const c of A.comps.values()) {
    if (['site', 'cable_tray'].includes(c.id)) continue;
    (groups[c.meta.category] = groups[c.meta.category] || []).push(c);
  }
  const cats = Object.keys(groups).sort((a, b) => CAT_ORDER.indexOf(a) - CAT_ORDER.indexOf(b));
  $('#systems').innerHTML = cats.map((cat) => {
    const list = groups[cat].sort((a, b) => a.id.localeCompare(b.id));
    const open = openCats.has(cat);
    const fault = list.some((c) => c.status === 'fault');
    const sub = !open ? '' : cat === 'Plants'
      ? `<div class="sub" style="grid-template-columns:repeat(6,1fr);display:grid;gap:2px">${list.map((c) => `<button data-id="${c.id}" style="padding:3px 2px;justify-content:center;${c.status === 'fault' ? 'color:#ff5a3c' : ''}">${esc(c.meta.state.plant_id || c.id).replace('#', '')}</button>`).join('')}</div>`
      : `<div class="sub">${list.map((c) => `<button data-id="${c.id}"><span style="color:inherit;font:inherit">${esc(shortTitle(c))}</span><i class="dot ${c.status === 'fault' ? 'fault' : isRunning(c.id) ? 'run' : ''}"></i></button>`).join('')}</div>`;
    return `<button data-cat="${esc(cat)}">${esc(cat)}${fault ? ' <b style="color:#ff5a3c">!</b>' : ''}<span>${list.length}</span></button>${sub}`;
  }).join('');
}
const shortTitle = (c) => (c.meta.title || c.id).replace(/\s*\(.*?\)\s*/g, ' ').trim();
function isRunning(id) {
  if (!sim) return false;
  const a = sim.act;
  if (id === 'irrigation_pump') return a.pump;
  if (id.startsWith('zone_valve')) return a.valve[+id.slice(-1) - 1];
  if (id.startsWith('exhaust_fan')) return a.fans >= +id.slice(-1);
  if (id === 'cooling_pad') return a.pad;
  if (id === 'fog_pump' || id === 'fog_line') return a.fog;
  if (id.startsWith('led_')) return a.led;
  if (id.startsWith('haf')) return a.haf;
  if (id.startsWith('dosing_pump')) return a.dosing.some(Boolean);
  if (id === 'scout_robot') return !sim.robot.stuck;
  if (id === 'pond_pump') return a.pondPump;
  if (id === 'borewell') return a.borePump;
  if (id === 'source_valves') return a.pondPump || a.borePump;
  if (id === 'solar_array') return sim.power.pv > 0.05;
  if (id === 'battery_bank') return sim.power.battKW < -0.02;
  return false;
}
$('#systems').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  A.sound.tick();
  if (b.dataset.cat) { const c = b.dataset.cat; openCats.has(c) ? openCats.delete(c) : openCats.add(c); drawSystems(); }
  if (b.dataset.id) { stopTour(); select(b.dataset.id); }
});

function drawReadings() {
  const r = sim.readings, w = sim.w, o = sim.out;
  const cells = [
    ['Air', `${r.T.toFixed(1)}°`, r.T > 30 ? 'bad' : r.T > 27 ? 'warn' : ''], ['RH', `${r.RH.toFixed(0)}%`, r.RH > 90 ? 'warn' : ''],
    ['VPD', r.vpd.toFixed(2), r.vpd < 0.4 || r.vpd > 1.6 ? 'warn' : ''], ['CO₂', r.CO2.toFixed(0), ''], ['Sun', `${o.solar.toFixed(0)}`, ''],
    ['EC', w.ec.toFixed(2), ''], ['pH', w.ph.toFixed(2), ''], ['Tank', `${w.tank.toFixed(0)}%`, w.tank < 20 ? 'bad' : ''],
    ['Flow', `${w.flow.toFixed(2)}`, sim.act.pump && w.flow === 0 ? 'bad' : ''],
  ];
  $('#readings').innerHTML = cells.map(([k, v, cls]) => `<div class="rd ${cls}"><i>${k}</i><b>${v}</b></div>`).join('');
  $('#clock').textContent = sim.clock();
  $('#outside').textContent = `${o.solar > 40 ? '☀' : '☾'} out ${o.T.toFixed(1)} °C · ${o.RH.toFixed(0)} %`;
  if (document.activeElement !== $('#tod')) $('#tod').value = Math.floor(sim.t);
}

// ── panel ─────────────────────────────────────────────────────
let tab = 'live';
function openPanel(c) {
  $('#panel').hidden = false;
  $('#p-cat').textContent = c.meta.category || '';
  $('#p-title').textContent = c.meta.title || c.id;
  $('#p-sum').textContent = c.meta.summary || '';
  drawTab();
}
function spark(key, label) {
  const hs = sim.hist.slice(-120);
  if (hs.length < 3) return '';
  const vals = hs.map((h) => h[key]);
  const lo = Math.min(...vals), hi = Math.max(...vals), rng = hi - lo || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * 300},${58 - ((v - lo) / rng) * 50}`).join(' ');
  return `<div><h4 style="margin:8px 0 4px;font:600 11px/1 var(--mono);letter-spacing:.1em;color:var(--muted);text-transform:uppercase">${esc(label)} · last ${Math.round((hs.length * 5) / 60)} h</h4>
    <svg class="spark" viewBox="0 0 300 62" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="#45c6e6" stroke-width="2" vector-effect="non-scaling-stroke"/>
    <text x="2" y="10" font-size="10" fill="#93a89f">${hi.toFixed(1)}</text><text x="2" y="60" font-size="10" fill="#93a89f">${lo.toFixed(1)}</text></svg></div>`;
}
function drawTab() {
  if (!sel) return;
  document.querySelectorAll('.tabs button').forEach((b) => b.setAttribute('aria-selected', b.dataset.tab === tab));
  const c = sel, m = c.meta;
  let h = '';
  if (tab === 'live') {
    const L = sim.live(c.id);
    const rows = L.rows.length ? L.rows : Object.entries(m.state || {}).map(([k, v]) => [k.replaceAll('_', ' '), typeof v === 'object' ? JSON.stringify(v) : v]);
    h = `<div class="live">${rows.map(([k, v]) => `<div><i>${esc(k)}</i><b>${esc(v)}</b></div>`).join('')}</div>${L.spark ? spark(L.spark.key, L.spark.label) : ''}`;
    if (c.status === 'fault') h = `<p style="color:#ff5a3c;font-weight:600;margin:0 0 8px">⚠ Fault flagged on this component — see the control-room feed.</p>` + h;
  } else if (tab === 'parts') {
    h = `<ol class="plist">${c.parts.map((p, i) => `<li data-i="${i}"><i>${i + 1}</i><span><b>${esc(p.name.replaceAll('_', ' '))}</b><small>${esc(p.desc)}</small></span></li>`).join('')}</ol>`;
  } else {
    h = `<div class="kvs"><div><h4>How it works</h4><p>${esc(m.how)}</p></div><div><h4>Measured / confirmed by</h4><p>${esc(m.sensors || '—')}</p></div>
      <div><h4>Controlled by</h4><p>${esc(m.control || '—')}</p></div><div><h4>Based on</h4><p>${esc(m.real || '—')}</p></div>
      <div><h4>Rough cost</h4><p>${esc(m.cost || '—')}</p></div></div>`;
  }
  $('#tabbody').innerHTML = h;
}
document.querySelector('.tabs').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { tab = b.dataset.tab; A.sound.tick(); drawTab(); } });
$('#tabbody').addEventListener('mouseover', (e) => { const li = e.target.closest('li[data-i]'); if (li) hoverPart(+li.dataset.i); });
$('#tabbody').addEventListener('mouseleave', () => hoverPart(-1));
$('#p-close').addEventListener('click', () => deselect());

// ── selection: explode + labels + blueprint ───────────────────
let sel = null, saved = null, panelK = 0, hoverPartIdx = -1;
const labels = [];
const ghosted = [];
function ghost(c) {
  setHover(null);
  promote(c, true);
  for (const im of plantInst) { im.userData.orig = im.material; im.material = ghostMat; im.castShadow = false; }
  const all = [];
  for (const x of A.comps.values()) if (x.id !== c.id) all.push(...x.meshes);
  for (const m of all) {
    if (m.userData.comp === c.id) continue;
    m.userData.orig = m.material;
    m.userData.cs = m.castShadow;
    m.material = m.userData.comp === 'site' ? ghostEdgeMat : ghostMat;
    m.castShadow = false;
    ghosted.push(m);
  }
  document.getElementById('app').classList.add('focus');
  world.sky.visible = false;
  world.backdrop.visible = false;
  scene.background = new THREE.Color(0x061219);
  A.focusFog = scene.fog.color.clone();
  scene.fog.color.set(0x061219);
  if (!holo) holo = makeHolo();
  const bb = new THREE.Box3().setFromObject(c.root);
  const sz = bb.getSize(new V3());
  const r = Math.max(sz.x, sz.z, 0.35) * 1.6;
  holo.position.set((bb.min.x + bb.max.x) / 2, bb.min.y - 0.01, (bb.min.z + bb.max.z) / 2);
  holo.scale.setScalar(r / 2);
  holo.visible = true;
  holo.userData.t = 0;
}
function unghost() {
  for (const m of ghosted) { m.material = m.userData.orig; m.castShadow = m.userData.cs; }
  for (const im of plantInst) { if (im.userData.orig) im.material = im.userData.orig; im.castShadow = true; }
  shadowDirty = true;
  if (T.sys) setTimeout(applySystemsView, 0);
  ghosted.length = 0;
  document.getElementById('app').classList.remove('focus');
  world.sky.visible = true;
  world.backdrop.visible = true;
  scene.background = null;
  if (A.focusFog) scene.fog.color.copy(A.focusFog);
  if (holo) holo.visible = false;
}
function explodedBox(c) {
  const box = new THREE.Box3().setFromObject(c.root);
  const tmp = new THREE.Box3();
  c.root.updateWorldMatrix(true, true);
  for (const p of c.parts) {
    const n = p.obj.userData._n;
    if (!n) continue;
    tmp.setFromObject(p.obj);
    const wd = n.dir.clone().multiplyScalar(1.25).transformDirection(p.obj.parent.matrixWorld).multiplyScalar(n.dir.length() * 1.25 * p.obj.parent.getWorldScale(new V3()).x);
    tmp.translate(wd);
    box.union(tmp);
  }
  return box;
}
let fly = null;
function flyTo(pos, target, dur = 1.1) { fly = { p0: camera.position.clone(), t0: controls.target.clone(), p1: pos, t1: target, t: 0, dur }; }

function select(id) {
  const c = A.comps.get(id);
  if (!c || c.id === 'site') return;
  if (sel === c) return;
  if (sel) deselect(true);
  if (walking) setWalk(false);
  sel = c;
  A.sound.explode();
  blueprint.draw(c);
  ghost(c);
  const box0 = new THREE.Box3().setFromObject(c.root);
  const c0 = box0.getCenter(new V3());
  const r0 = box0.getSize(new V3()).length() / 2;
  fx.burst(c0, r0);
  const box = explodedBox(c);
  const center = box.getCenter(new V3());
  const size = Math.max(box.getSize(new V3()).length(), 0.25);
  let dir = camera.position.clone().sub(controls.target).normalize();
  if (c.meta.view) {
    const [az, el] = c.meta.view.map((d) => THREE.MathUtils.degToRad(d));
    const dB = new V3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));   // Blender (x, -y…) → three
    dir = dB.applyQuaternion(c.root.getWorldQuaternion(new THREE.Quaternion())).normalize();
  } else if (dir.y < 0.15) dir.y = 0.3;
  dir.normalize();
  const dist = (size / 2) / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * (MOBILE ? 1.15 : 0.9) + 0.08;
  if (!saved) saved = { pos: camera.position.clone(), target: controls.target.clone() };
  flyTo(center.clone().addScaledVector(dir, dist), center, 1.1);
  c.explodeTarget = 1;
  c.explodeClock = 0;
  // labels
  labels.forEach((l) => l.el.remove());
  labels.length = 0;
  c.parts.forEach((p, i) => {
    const bb = new THREE.Box3().setFromObject(p.obj);
    if (bb.isEmpty()) return;
    const local = p.obj.worldToLocal(bb.getCenter(new V3()));
    const el = document.createElement('div');
    el.className = 'plab';
    el.innerHTML = `<i>${i + 1}</i>${esc(p.name.replaceAll('_', ' '))}`;
    el.addEventListener('mouseenter', () => hoverPart(i));
    el.addEventListener('mouseleave', () => hoverPart(-1));
    el.addEventListener('click', (e) => { e.stopPropagation(); tab = 'parts'; drawTab(); hoverPart(i); });
    $('#labels').appendChild(el);
    labels.push({ el, p, local, i, shown: false });
    setTimeout(() => { el.classList.add('show'); }, 450 + i * 45);
  });
  tab = c.id.startsWith('plant_') ? 'live' : tab;
  openPanel(c);
}

function deselect(immediate = false) {
  if (!sel) return;
  const c = sel;
  c.explodeTarget = 0;
  c.explodeClock = 0;
  if (immediate) { c.explodeT = 0; applyExplode(c, 0); } else A.sound.implode();
  unghost();
  labels.forEach((l) => l.el.remove());
  labels.length = 0;
  $('#leaders').innerHTML = '';
  $('#panel').hidden = true;
  highlight([]);
  if (c.id.startsWith('plant_')) setTimeout(() => { if (sel !== c) promote(c, false); }, immediate ? 0 : 650);
  if (!immediate && saved) flyTo(saved.pos, saved.target, 0.9);
  if (!immediate) saved = null;
  sel = null;
  hoverPartIdx = -1;
}

function applyExplode(c, t) {
  const T = t * 1.35;
  for (const n of c.nodes) {
    const d = n.userData._n;
    const delay = d.k * 0.035;
    const u = clamp((T - delay) / 0.85, 0, 1);
    const e = c.explodeTarget ? easeOutBack(u) : easeInOut(u);
    n.position.copy(d.base).addScaledVector(d.dir, e * 1.25);
    const pop = c.explodeTarget ? 1 + 0.1 * Math.sin(u * Math.PI) : 1;
    n.scale.copy(d.baseScale).multiplyScalar(pop);
  }
}
function updateExplode(dt) {
  for (const c of A.comps.values()) {
    if (c.explodeT === c.explodeTarget && !c.explodeClock) continue;
    if (c.explodeTarget === 1) {
      c.explodeT = Math.min(1, c.explodeT + dt / 1.2);
      applyExplode(c, c.explodeT);
      if (c.explodeT >= 1) c.explodeClock = 0;
    } else {
      c.explodeT = Math.max(0, c.explodeT - dt / 0.6);
      // implode: run the same curve backwards
      for (const n of c.nodes) { const d = n.userData._n; n.position.copy(d.base).addScaledVector(d.dir, easeInOut(c.explodeT) * 1.25); n.scale.copy(d.baseScale); }
      if (c.explodeT <= 0) c.explodeClock = 0;
    }
  }
}

function hoverPart(i) {
  if (hoverPartIdx === i || !sel) return;
  hoverPartIdx = i;
  blueprint.highlight(i);
  labels.forEach((l) => l.el.classList.toggle('hl', l.i === i));
  document.querySelectorAll('.plist li').forEach((li) => li.classList.toggle('hl', +li.dataset.i === i));
  highlight(i >= 0 ? [sel.parts[i].obj] : []);
}

function updateLabels() {
  const svg = $('#leaders');
  if (!sel || !labels.length) { if (svg.innerHTML) svg.innerHTML = ''; return; }
  const W = innerWidth, Hh = innerHeight;
  const cc = new THREE.Box3().setFromObject(sel.root).getCenter(new V3()).project(camera);
  const cx = (cc.x * 0.5 + 0.5) * W, cy = (-cc.y * 0.5 + 0.5) * Hh;
  let lines = '';
  for (const l of labels) {
    const wp = l.local.clone().applyMatrix4(l.p.obj.matrixWorld);
    const s = wp.project(camera);
    if (s.z > 1) { l.el.style.display = 'none'; continue; }
    l.el.style.display = '';
    const x = (s.x * 0.5 + 0.5) * W, y = (-s.y * 0.5 + 0.5) * Hh;
    let dx = x - cx, dy = y - cy;
    const d = Math.hypot(dx, dy) || 1;
    dx /= d; dy /= d;
    const lx = x + dx * 54, ly = y + dy * 38;
    l.el.style.left = `${lx}px`;
    l.el.style.top = `${ly}px`;
    if (sel.explodeT > 0.5) lines += `<line x1="${x.toFixed(1)}" y1="${y.toFixed(1)}" x2="${lx.toFixed(1)}" y2="${ly.toFixed(1)}"/><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.6"/>`;
  }
  svg.innerHTML = lines;
}

// ── picking ───────────────────────────────────────────────────
const ray = new THREE.Raycaster();
ray.firstHitOnly = true;
const ndc = new THREE.Vector2();
function pick(x, y, list) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(list, false)[0];
  return hit ? hit.object : null;
}
let pointer = { x: 0, y: 0, moved: true, down: null };
canvas.addEventListener('pointermove', (e) => { pointer.x = e.clientX; pointer.y = e.clientY; pointer.moved = true; });
canvas.addEventListener('pointerdown', (e) => { pointer.down = { x: e.clientX, y: e.clientY, t: performance.now() }; A.sound.ensure(); stopTour(); });
canvas.addEventListener('pointerup', (e) => {
  const d = pointer.down;
  pointer.down = null;
  if (!d || Math.hypot(e.clientX - d.x, e.clientY - d.y) > 6 || performance.now() - d.t > 500) return;
  if (sel) {
    const m = pick(e.clientX, e.clientY, sel.meshes);
    if (m) { tab = 'parts'; drawTab(); hoverPart(m.userData.partIdx); A.sound.tick(); return; }
    const other = pick(e.clientX, e.clientY, pickables.filter((mm) => mm.userData.comp !== sel.id));
    if (other) { select(other.userData.comp); return; }
    deselect();
    return;
  }
  const m = pick(e.clientX, e.clientY, pickables);
  if (m) select(m.userData.comp);
});
let hoverFrame = 0;
function updateHover() {
  if (!pointer.moved || ++hoverFrame % 2 || pointer.down) return;
  pointer.moved = false;
  const tip = $('#tip');
  if (sel) {
    const m = pick(pointer.x, pointer.y, sel.meshes);
    if (m) {
      const p = sel.parts[m.userData.partIdx];
      hoverPart(m.userData.partIdx);
      tip.hidden = false;
      tip.innerHTML = `<b>${m.userData.partIdx + 1} · ${esc(p.name.replaceAll('_', ' '))}</b>${esc(p.desc)}`;
      tip.style.left = `${pointer.x}px`; tip.style.top = `${pointer.y}px`;
    } else { tip.hidden = true; }
    canvas.style.cursor = m ? 'pointer' : 'default';
    return;
  }
  const m = pick(pointer.x, pointer.y, pickables);
  if (!m) { tip.hidden = true; setHover(null); canvas.style.cursor = 'default'; return; }
  const c = A.comps.get(m.userData.comp);
  setHover(c);
  const L = sim.live(c.id);
  const first = L.rows.slice(0, 2).map(([k, v]) => `${k} ${v}`).join(' · ');
  tip.hidden = false;
  tip.innerHTML = `<b>${esc(c.meta.title || c.id)}</b>${first ? `<small>${esc(first)}</small>` : ''}${c.status === 'fault' ? '<small style="color:#ff5a3c">FAULT</small>' : ''}<div class="hint">Click to explode</div>`;
  tip.style.left = `${pointer.x}px`; tip.style.top = `${pointer.y}px`;
  canvas.style.cursor = 'pointer';
}
canvas.addEventListener('pointerleave', () => { $('#tip').hidden = true; });

// ── walk mode (first-person look via orbit around a point just ahead) ──
let walking = false;
const keys = {};
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  keys[e.code] = true;
  if (e.code === 'Escape') { if (sel) deselect(); else if (walking) setWalk(false); $('#help').hidden = true; }
  if (e.code === 'KeyF') setWalk(!walking);
  if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
  if (e.code === 'KeyX') toggle('xray');
  if (e.code === 'KeyN') toggle('net');
  if (e.code === 'KeyV') toggle('sys');
});
addEventListener('keyup', (e) => { keys[e.code] = false; });
function setWalk(on) {
  walking = on;
  $('#walk').setAttribute('aria-pressed', on);
  if (on) {
    if (sel) deselect(true);
    const eye = new V3(1.0, 1.62, 0.35);
    flyTo(eye, eye.clone().add(new V3(1, -0.02, 0).multiplyScalar(0.05)), 1.0);
    controls.enableZoom = false; controls.enablePan = false; controls.rotateSpeed = -0.35; controls.minDistance = 0; controls.maxPolarAngle = Math.PI * 0.95;
    A.toast('Walk mode', 'W A S D to walk · drag to look · Shift to run · click anything to explode it · F or Esc to leave.');
  } else {
    controls.enableZoom = true; controls.enablePan = true; controls.rotateSpeed = 1; controls.minDistance = 0.12; controls.maxPolarAngle = Math.PI * 0.495;
    const fwd = controls.target.clone().sub(camera.position).normalize();
    controls.target.copy(camera.position).addScaledVector(fwd, 3);
  }
}
$('#walk').addEventListener('click', () => { A.sound.tick(); setWalk(!walking); });
function walkMove(dt) {
  if (!walking || fly) return;
  const sp = (keys.ShiftLeft || keys.ShiftRight ? 3.4 : 1.5) * dt;
  const f = controls.target.clone().sub(camera.position); f.y = 0; f.normalize();
  const r = new V3().crossVectors(f, new V3(0, 1, 0));
  const mv = new V3();
  if (keys.KeyW || keys.ArrowUp) mv.add(f); if (keys.KeyS || keys.ArrowDown) mv.sub(f);
  if (keys.KeyD || keys.ArrowRight) mv.add(r); if (keys.KeyA || keys.ArrowLeft) mv.sub(r);
  if (mv.lengthSq()) {
    mv.normalize().multiplyScalar(sp);
    camera.position.add(mv); controls.target.add(mv);
    camera.position.x = clamp(camera.position.x, -14, 22); camera.position.z = clamp(camera.position.z, -14, 14);
    camera.position.y = 1.62; controls.target.y = clamp(controls.target.y, 0.2, 3.5);
  }
}

// ── toggles, time, speed, scenarios ───────────────────────────
const T = { xray: false, net: false, air: false, sound: true, hq: HIGH, sys: false };
function toggle(k) {
  T[k] = !T[k];
  document.querySelector(`#toggles [data-t="${k}"]`)?.setAttribute('aria-pressed', T[k]);
  if (k === 'xray') ['polycarbonate_roof', 'insect_net', 'vent_window'].forEach((p) => { const o = partObj('greenhouse_structure', p); if (o) o.visible = !T.xray; });
  if (k === 'net') fx.showNetwork(T.net);
  if (k === 'sound') A.sound.on = T.sound;
  if (k === 'sys') applySystemsView();
  if (k === 'hq') { HIGH = !HIGH; T.hq = HIGH; try { localStorage.setItem('gh-quality', HIGH ? 'high' : 'fast'); } catch (e) { /* ignore */ } applyQuality(); resize(); }
}
$('#toggles').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { toggle(b.dataset.t); A.sound.tick(); } });
const sysGhost = new THREE.MeshBasicMaterial({ color: 0x2f9e6a, transparent: true, opacity: 0.09, depthWrite: false, blending: THREE.AdditiveBlending });
function applySystemsView() {
  const on = T.sys && !sel;
  document.querySelector('#toggles [data-t="sys"]')?.setAttribute('aria-pressed', T.sys);
  for (const im of plantInst) {
    if (on) { if (im.material !== sysGhost) { im.userData.sysOrig = im.material; im.material = sysGhost; } im.castShadow = false; }
    else if (im.userData.sysOrig && im.material === sysGhost) { im.material = im.userData.sysOrig; im.castShadow = true; }
  }
  ['polycarbonate_roof', 'insect_net', 'vent_window', 'polycarbonate_walls'].forEach((p) => { const o = partObj('greenhouse_structure', p); if (o) o.visible = !on && !(T.xray && p !== 'polycarbonate_walls'); });
  fx.showNetwork(on || T.net);
  shadowDirty = true;
}
A.systemsView = (on) => { if (T.sys !== on) toggle('sys'); };
function togglePlay() { sim.running = !sim.running; $('#play').textContent = sim.running ? '⏸' : '▶'; $('#play').setAttribute('aria-label', sim.running ? 'Pause simulation' : 'Play simulation'); }
$('#play').addEventListener('click', () => { A.sound.tick(); togglePlay(); });
document.querySelectorAll('[data-speed]').forEach((b) => b.addEventListener('click', () => {
  sim.speed = +b.dataset.speed; A.sound.tick();
  document.querySelectorAll('[data-speed]').forEach((x) => x.setAttribute('aria-pressed', x === b));
}));
$('#tod').addEventListener('input', (e) => { sim.t = +e.target.value; world.setTime(sim.t, sim.cloud); });
$('#scen').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-s]');
  if (!b) return;
  A.sound.tick();
  stopTour();
  if (sel && b.dataset.s !== 'reset') deselect();
  if (!['reset', 'robot', 'disease', 'sensor'].includes(b.dataset.s)) A.systemsView(true);
  if (b.dataset.s === 'reset') A.systemsView(false);
  sim.scenario(b.dataset.s);
  if (b.dataset.s === 'irrigate' || b.dataset.s === 'pump') flyTo(B(3.5, -0.15, 2.45), B(1.35, -0.95, 1.0), 1.4);
  if (b.dataset.s === 'heat' && !T.air) toggle('air');
  if (b.dataset.s === 'heat') flyTo(B(4.8, 0.6, 2.4), B(0.2, 0, 1.9), 1.4);
  if (b.dataset.s === 'water') flyTo(B(3.3, 0.2, 2.2), B(1.2, -1.9, 0.6), 1.4);
  if (b.dataset.s === 'disease') flyTo(B(2.4, 0.9, 1.9), B(4.3, 1.2, 1.0), 1.4);
  if (b.dataset.s === 'power') flyTo(B(-6.5, 14.0, 4.5), B(3.6, 7.0, 1.5), 1.6);
  if (b.dataset.s === 'pond') flyTo(B(-3.2, -3.6, 3.4), B(5.2, -10.8, -1.2), 1.6);
});
$('#helpbtn').addEventListener('click', () => { $('#help').hidden = false; });
$('#help-ok').addEventListener('click', () => { $('#help').hidden = true; });

// ── tour ──────────────────────────────────────────────────────
let touring = false, tourTimers = [];
function stopTour() { if (!touring) return; touring = false; tourTimers.forEach(clearTimeout); tourTimers = []; $('#tour').setAttribute('aria-pressed', false); }
function tour() {
  if (touring) { stopTour(); return; }
  touring = true;
  $('#tour').setAttribute('aria-pressed', true);
  const steps = [
    [0, () => { if (sel) deselect(true); flyTo(B(-7.5, -8.5, 4.2), B(4.2, 0.2, 1.4), 2); A.toast('GH-01', '45 m² tomato greenhouse. Sensors measure, the AI advises, a safety PLC decides, machines act.'); }],
    [5000, () => { flyTo(B(2.9, 0.9, 2.2), B(0.8, -1.6, 0.9), 2); A.toast('Technical corner', 'Fresh water, stock tanks A/B/acid, dosing pumps, pH/EC flow cell, pump, filter and flow meter on one skid.'); }],
    [10000, () => select('irrigation_pump')],
    [16000, () => { deselect(); A.toast('Scout robot', 'Drives the pipe rails, photographs every plant from 5 heights and pollinates open flowers with air pulses.'); flyTo(B(3.0, -0.6, 1.5), B(5.5, -0.8, 1.0), 2); }],
    [22000, () => select('plant_042')],
    [28000, () => { deselect(); A.systemsView(true); sim.scenario('irrigate'); flyTo(B(3.5, -0.15, 2.45), B(1.35, -0.95, 1.0), 2); A.toast('Watch the chain', 'Sensors → data → AI → decision → safety PLC → pump + valves → flow confirmed.'); }],
    [40000, () => { A.systemsView(false); flyTo(B(-7.5, 8.5, 5.5), B(4.5, 0, 1.2), 2.5); A.toast('Your turn', 'Click anything to explode it. Try a failure scenario bottom-left.'); stopTour(); }],
  ];
  steps.forEach(([ms, fn]) => tourTimers.push(setTimeout(() => { if (touring || ms === 0) fn(); }, ms)));
}
$('#tour').addEventListener('click', () => { A.sound.tick(); tour(); });

// ── per-frame actuator animation ──────────────────────────────
const ax = { X: new V3(1, 0, 0), Y: new V3(0, 1, 0), Z: new V3(0, 0, 1) };
let fanSpeed = [0, 0], ventAngle = 12, padWet = 0, ledOn = 0;
function updateActuators(dt) {
  const a = sim.act;
  H.fans.forEach((b, i) => { if (!b) return; const tgt = a.fans > i ? 16 : 0; fanSpeed[i] += (tgt - fanSpeed[i]) * Math.min(1, dt * 1.2); b.rotateOnAxis(ax.Z, fanSpeed[i] * dt); });
  H.haf.forEach((b) => b && b.rotateOnAxis(ax.X, (a.haf ? 20 : 0) * dt));
  if (H.vent) {
    const tgt = a.vent * 0.35;
    ventAngle += (tgt - ventAngle) * Math.min(1, dt * 0.8);
    H.vent.quaternion.copy(H.vent.userData.q0).multiply(new THREE.Quaternion().setFromAxisAngle(ax.X, THREE.MathUtils.degToRad(ventAngle - 12)));
  }
  const pumpRun = a.pump;
  if (H.pumpShaft && pumpRun) { H.pumpShaft.rotateOnAxis(ax.X, 40 * dt); H.pumpFan?.rotateOnAxis(ax.X, 40 * dt); }
  if (H.pumpRoot) { H.pumpRoot.position.copy(H.pumpRoot.userData.p0); if (pumpRun && !sim.faults.pump) H.pumpRoot.position.y += Math.sin(performance.now() * 0.09) * 0.0012; }
  if (H.mixer && a.mixer) H.mixer.rotateOnAxis(ax.Y, 6 * dt);
  H.dosing.forEach((r, i) => { if (r && a.dosing[i]) r.rotateOnAxis(ax.Z, 5 * dt); });
  H.solenoids.forEach((mats, i) => mats.forEach((m) => { if (m.emissive) { m.emissive.set(0x45c6e6); m.emissiveIntensity = a.valve[i] ? 2.2 : 0; } }));
  if (!H.pondWater) {
    const pc = A.comps.get('farm_pond');
    const wp = pc && pc.parts.find((q) => q.name === 'water');
    if (wp) {
      const mesh = wp.obj.isMesh ? wp.obj : wp.obj.getObjectByProperty('isMesh', true);
      mesh.geometry.computeBoundingBox();
      const c0 = mesh.geometry.boundingBox.getCenter(new V3());
      mesh.geometry.translate(-c0.x, -c0.y, -c0.z);
      mesh.position.add(c0);
      if (mesh.userData._n) mesh.userData._n.base.copy(mesh.position);
      H.pondWater = { mesh, y0: mesh.position.y };
    }
  }
  if (H.pondWater) {
    const z = sim.pondLevelM() - 3.0;                               // water surface height (ground = 0)
    const k = Math.max(0.05, (4 + z) / 2.8);
    const m = H.pondWater.mesh;
    m.position.y = H.pondWater.y0 + (z + 1.2);
    if (m.userData._n) m.userData._n.base.y = m.position.y;
    m.scale.set(k, 1, k);
  }
  ledOn += ((a.led ? 1 : 0) - ledOn) * Math.min(1, dt * 2);
  growLED.emissiveIntensity = ledOn * 6;
  padWet += ((a.pad ? 1 : 0) - padWet) * Math.min(1, dt * 0.6);
  if (padMat) padMat.color.setRGB(0.55 - padWet * 0.28, 0.38 - padWet * 0.2, 0.19 - padWet * 0.1);
  // water
  const flowing = a.pump && sim.w.flow > 0 && sim.irr.confirmed;
  fx.setFlow(H.flowMain, a.pump && sim.w.flow > 0);
  H.flowZones.forEach((z, i) => { const on = a.pump && sim.w.flow > 0 && a.valve[i]; fx.setFlow(z.man, on); fx.setFlow(z.drop, on); fx.setFlow(z.lat, on && flowing); if (on && flowing) fx.dripAt(z.drips); });
  H.fogTubes.forEach((t) => fx.setFlow(t, a.fog));
  if (a.fog) fx.fogAt(H.nozzles);
  fx.setFlow(H.padTube, a.pad);
  if (T.air && a.fans > 0) fx.airflow(8.8, 0.4, [0.4, 2.4], [-2.1, 2.1], a.fans);
  // robot
  const R = sim.robot;
  if (H.robot && !(sel && sel.id === 'scout_robot')) H.robot.position.copy(B(R.x, R.y, SIMDATA.robot.rail_z));
  if (H.head && H.head.userData._n && !(sel && sel.id === 'scout_robot')) H.head.position.copy(H.head.userData._n.base).add(new V3(0, R.lift - 1.1, 0));
  fx.scanMat.opacity += ((R.scanning ? 0.16 : 0) - fx.scanMat.opacity) * Math.min(1, dt * 6);
  if (R.puff && H.head) { R.puff = 0; const p = H.head.getWorldPosition(new V3()); fx.puff(p.clone().add(new V3(0, 0.1, -0.35)), new V3(0, 0.2, -1)); fx.puff(p.clone().add(new V3(0, 0.1, 0.35)), new V3(0, 0.2, 1)); }
  if (H.beaconMat) {
    const col = R.stuck ? (Math.floor(performance.now() / 300) % 2 ? 0xff5a3c : 0x401010) : R.scanning ? 0x45c6e6 : 0x6fd08c;
    H.beaconMat.color.setHex(col); H.robotLight.color.setHex(col);
  }
}

// ── resize ────────────────────────────────────────────────────
function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  if (composer) { composer.setPixelRatio(PR); composer.setSize(w, h); }
}
addEventListener('resize', () => { resize(); layoutHUD(); });
function layoutHUD() {
  const b = document.querySelector('.top').getBoundingClientRect().bottom + 8;
  ['#chain', '#left', '#feedbox'].forEach((q) => { const e = $(q); if (e) e.style.top = `${b}px`; });
  $('#alarm').style.top = `${b + 48}px`;
}
layoutHUD();
function applyViewOffset() {
  const w = innerWidth, h = innerHeight;
  if (CAPTURE || panelK < 0.001) { camera.clearViewOffset(); return; }
  if (MOBILE) { const P = h * 0.62 * panelK; camera.setViewOffset(w, h + P, 0, P, w, h); }
  else { const P = (Math.min(600, w * 0.46) + 20) * panelK; camera.setViewOffset(w + P, h, P, 0, w, h); }
}

// ── main loop ─────────────────────────────────────────────────
const clock = new THREE.Clock();
let uiTimer = 0, lastWorldT = -1, fpsAcc = 0, fpsN = 0, degraded = false, shadowFrame = 0;
function loop() {
  frame(Math.min(clock.getDelta(), 0.05));
  requestAnimationFrame(loop);
}
function frame(dt) {
  sim.tick(dt);
  if (Math.abs(sim.t - lastWorldT) > 0.5) { world.setTime(sim.t, sim.heat ? 0 : sim.cloud); lastWorldT = sim.t; if (sel) scene.fog.color.set(0x061219); }
  updateActuators(dt);
  growPlants(dt);
  updateExplode(dt);
  if (fly) {
    fly.t += dt / fly.dur;
    const k = easeInOut(Math.min(1, fly.t));
    camera.position.lerpVectors(fly.p0, fly.p1, k);
    controls.target.lerpVectors(fly.t0, fly.t1, k);
    if (fly.t >= 1) fly = null;
  }
  const pk = sel ? 1 : 0;
  panelK += (pk - panelK) * Math.min(1, dt * 5);
  applyViewOffset();
  walkMove(dt);
  controls.update();
  fx.update(dt);
  if (holo && holo.visible) { holo.userData.t += dt; const k = Math.min(1, holo.userData.t * 2); holo.userData.ring.scale.setScalar(0.4 + 0.6 * easeOutBack(k)); holo.userData.ring.rotation.z += dt * 0.4; holo.userData.grid.material.opacity = 0.55 * k; }
  updateHover();
  updateLabels();
  if (chainTimer > 0) { chainTimer -= dt; if (chainTimer <= 0) A.chain(null); }
  uiTimer -= dt;
  if (uiTimer <= 0) { uiTimer = 0.3; drawReadings(); if (sel && tab === 'live') drawTab(); drawSystemsLite(); }
  if (++shadowFrame % shadowEvery === 0 || shadowDirty) { renderer.shadowMap.needsUpdate = true; shadowDirty = false; }
  if (HIGH && composer) composer.render(); else renderer.render(scene, camera);
  // adaptive quality
  fpsAcc += dt; fpsN++;
  if (fpsAcc > 5) {
    const fps = fpsN / fpsAcc; fpsAcc = 0; fpsN = 0;
    if (fps < 24 && HIGH) { HIGH = false; applyQuality(); resize(); A.toast('Graphics', 'Switched to fast graphics for a smoother frame rate (toggle "HQ" to change).'); }
    else if (fps < 18 && !degraded) { degraded = true; PR = 0.8; renderer.setPixelRatio(PR); resize(); shadowEvery = 20; }
  }
}
let sysTick = 0;
function drawSystemsLite() { if (++sysTick % 10 === 0) drawSystems(); }

async function loadWithRetry(i) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try { return await loadGLB(FILES[i], i); } catch (e) {
      if (i < FIRST) setProgress(`Retrying ${FILES[i][2]}…`);
      await new Promise((r) => setTimeout(r, 600 * (attempt + 1)));
    }
  }
  throw new Error(`could not download ${FILES[i][0]}`);
}
async function loadPlants() {
  growChip('Planting 54 plants · 0 %');
  let g;
  try { g = await loadWithRetry(3); } catch (e) { growChip('Plants did not load · reload the page'); console.error(e); return; }
  scene.add(g.scene);
  prepareMaterials(g.scene, register(g.scene));
  instancePlants();
  growT = CAPTURE ? -1 : 0;   // the recorder wants the plants in place at once
  growPlants(0);
  if (T.sys) applySystemsView();
  drawSystems();
  buildBVH();
  growChip('');
  A.log('OK', `${SIMDATA.plants.length} plants in place · each has its own ID tag`);
}

async function loadFarm() {   // 6 Oct 2026: the farm round the house (solar packhouse, pond, entry room, shade net)
  let g;
  try { g = await loadWithRetry(4); } catch (e) { console.error(e); return; }
  scene.add(g.scene);
  prepareMaterials(g.scene, register(g.scene));
  if (T.sys) applySystemsView();
  buildBVH();
  A.log('OK', 'Farm in place · solar packhouse, farm pond, entry room, shade net');
}

// ── boot ──────────────────────────────────────────────────────
(async function boot() {
  try {
    setProgress('Loading simulation data…');
    SIMDATA = await fetch('assets/sim.json').then((r) => r.json());
    const gl = [];
    for (let i = 0; i < FIRST; i++) gl.push(await loadWithRetry(i));
    setProgress('Preparing materials, lights and shadows…');
    gl.forEach((g) => { scene.add(g.scene); prepareMaterials(g.scene, register(g.scene)); });
    hookActuators();
    sim = new Sim(A, SIMDATA);
    A.sim = sim;
    world.setTime(sim.t, sim.cloud);
    buildNetwork();
    drawSystems();
    drawReadings();
    A.log('OK', `Twin online · ${A.comps.size} components · ${SIMDATA.plants.length} plants registered (3D plants loading)`);
    A.log('AI', 'Advising: climate targets day 24 °C / night 18.5 °C · VPD 0.8–1.2 kPa · irrigation by radiation sum');
    setProgress('Ready.');
    $('#ld-bar').style.width = '100%';
    $('#ld-start').hidden = false;
    $('#ld-start').focus();
    if (CAPTURE) $('#app').classList.add('capture');
    else loop();
    buildBVH();
    loadPlants();
    loadFarm();
    window.GH = { A, select, deselect, flyTo, camera, controls, B, get sim() { return sim; }, step: (n = 30, dt = 1 / 30) => { fpsAcc = -1e9; for (let i = 0; i < n; i++) frame(dt); }, regrow: () => { if (plantSlots.size) growT = 0; },
      frame: (dt = 1 / 30) => { fpsAcc = -1e9; frame(dt); }, get sel() { return sel; }, get ready() { return plantSlots.size > 0 && growT < 0; }, toggle };   // console handle for demos
    if (location.hash === '#go') $('#ld-start').click();
  } catch (err) {
    console.error(err);
    $('#ld-step').textContent = `Could not load the twin: ${err.message || err}`;
  }
})();
$('#ld-start').addEventListener('click', () => {
  A.sound.ensure();
  $('#loading').classList.add('done');
  camera.position.copy(B(-22, -20, 12));
  controls.target.copy(B(4.2, 0, 1.2));
  flyTo(B(-7.5, -8.5, 4.2), B(4.2, 0.2, 1.4), 2.6);
  setTimeout(() => A.toast('Welcome to GH-01', 'Click any machine, sensor or plant to explode it into its parts with a blueprint. 🎬 Tour shows the highlights.'), 1500);
});
