// The tutorial workbench (14 Oct 2026): real parts at real size (blender/components/bench.py -> assets/bench_pestcam.glb)
// on a cutting mat, for the "Build GH-01" tutorial videos. Episode 1 = the sticky-trap pest camera.
//
//   const BN = await import('./js/bench.js'); GH.bench = await BN.build(GH); GH.bench.show(true);
//
// Inside, everything is in Blender-style coordinates (metres, z up, mat top at z = 0) under one group turned to three's
// y-up, so GH.flyTo(GH.B(x, y, z), ...) frames bench points directly. Animation runs on "knobs" (numbers the video
// timeline tweens: bench.to('latch', 1, 0.4)). Wires, the camera ribbon and the probe leads are rebuilt from their end
// points whenever a part moves, so the parts can fly into the box with their wires still attached.
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const MM = 0.001;
// ---- mirrors blender/components/bench.py (mm)
const ZW = 65, ZH = 30, ZT = 1.0;
const zeroXY = (X, Y) => [X - ZW / 2, ZH / 2 - Y];
export const zeroPin = (n) => { const c = Math.floor((n - 1) / 2); return zeroXY(8.37 + 2.54 * c, n % 2 ? 4.77 : 2.23); };
const CH = 23.862, LENS_Y = 14.4 - CH / 2;
const TPL_H = 17.8, TPL_PADS = ['VDD', 'GND', 'DRV', 'DONE', 'DLY'];
const tplPad = (nm) => [-5.08 + 2.54 * TPL_PADS.indexOf(nm), -TPL_H / 2 + 1.6];
const MT_PADS = { 'VIN+': [-15.6, 5.6], 'VIN-': [-15.6, -5.6], 'VOUT+': [15.6, 5.6], 'VOUT-': [15.6, -5.6] };
const BB_T = 8.5, ROWS = 'abcdefghij';
const bbHole = (col, row) => { const ri = ROWS.indexOf(row); return [(col - 9) * 2.54, ri < 5 ? 3.81 + (4 - ri) * 2.54 : -(3.81 + (ri - 5) * 2.54)]; };
const ringPad = (s) => { const a = (s === '+' ? -100 : -80) * Math.PI / 180; return [20 * Math.cos(a), 20 * Math.sin(a)]; };
const BOX_H = 55, CAM_DIST = 200, LENS_IN_BOX = 51.4, BOX_BACK = CAM_DIST + LENS_IN_BOX;
const DUP_Z = ZT + 2.5 + 14;           // top of a female jumper pushed onto a Zero header pin (mm above the board bottom)
const MALE_Z = BB_T + 12;              // top of a male jumper in the breadboard

// ---- where everything sits on the bench: [x, y, z] mm, rotation about z (deg)
export const POSE = {
  zero: [0, 0, 3.1, 0], cam3: [75, 0, 2.4, -90], tpl: [-30, 112, 0, 0], boost: [-30, 60, 0, 0], cell: [-75, 70, 0, 90],
  ring: [70, -62, 0, -90], bread: [0, -62, 0, 0], meter: [30, 140, 0, 0], box: [-150, -95, 0, 0], pi5: [300, -70, 0, -10],
  frame: [0, 250, 165, 0],
};
// inside the box (box-local, lid up), the order they fly in
const BOXP = {
  cell: [-17, 28, 2.5, 0], boost: [-17, 28, 20.6, 0], zero: [-20, -22, 5.6, 0], tpl: [37, 31, 2.5, 0], bread: [36, -18, 2.5, 90],
  cam3: [0, -LENS_Y, 42.5, 0], ring: [0, 0, 46.0, 0],
};
const BOX_ORDER = ['cell', 'boost', 'zero', 'tpl', 'bread', 'plate', 'cam3', 'ring'];
// the trap mount: box bottom on the plate behind the card, lid facing the card (+y)
const MOUNT = { pos: [POSE.frame[0], POSE.frame[1] - BOX_BACK, POSE.frame[2]], rx: -90 };

// [id, from part, from point (mm, part-local), to part, to point, colour, radius mm, female-jumper ends 'a'/'b'/'ab', male end at b]
const WIRES = [
  ['bat+', 'cell', [38.0, 4, 6], 'tpl', [...tplPad('VDD'), 1.6], 0xc0201a, 0.7],
  ['bat-', 'cell', [-38.0, 4, 6], 'tpl', [...tplPad('GND'), 1.6], 0x161616, 0.7],
  ['drv', 'tpl', [...tplPad('DRV'), 1.6], 'boost', [...MT_PADS['VIN+'], 1.6], 0xc0201a, 0.6],
  ['gnd1', 'tpl', [...tplPad('GND'), 1.6], 'boost', [...MT_PADS['VIN-'], 1.6], 0x161616, 0.6],
  ['5v', 'boost', [...MT_PADS['VOUT+'], 1.6], 'zero', [...zeroPin(2), DUP_Z], 0xc0201a, 0.65, 'b'],
  ['gnd2', 'boost', [...MT_PADS['VOUT-'], 1.6], 'zero', [...zeroPin(6), DUP_Z], 0x161616, 0.65, 'b'],
  ['gpio17', 'zero', [...zeroPin(11), DUP_Z], 'bread', [...bbHole(5, 'b'), MALE_Z], 0x1f9a3a, 0.65, 'a', true],
  ['gnd3', 'zero', [...zeroPin(9), DUP_Z], 'bread', [...bbHole(10, 'b'), MALE_Z], 0x161616, 0.65, 'a', true],
  ['ring-', 'ring', [...ringPad('-'), 1.6], 'bread', [...bbHole(9, 'b'), MALE_Z], 0x161616, 0.45, '', true],
  ['ring+', 'ring', [...ringPad('+'), 1.6], 'zero', [...zeroPin(4), DUP_Z], 0xc0201a, 0.45, 'b'],
  ['done', 'zero', [...zeroPin(37), DUP_Z], 'tpl', [...tplPad('DONE'), 1.6], 0xe8c21a, 0.65, 'a'],
];
const POWER_WIRES = ['bat+', 'drv', '5v'];

const ease = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));
const clamp01 = (t) => Math.max(0, Math.min(1, t));

async function loadGLB(url) {
  const { gz } = await (await fetch(url)).json();
  const bin = Uint8Array.from(atob(gz), (c) => c.charCodeAt(0));
  const glb = await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  return new GLTFLoader().parseAsync(glb, '');
}

function canvasTex(T, w, h, draw) {
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  draw(cv.getContext('2d'), w, h);
  const tx = new T.CanvasTexture(cv);
  tx.colorSpace = T.SRGBColorSpace;
  tx.anisotropy = 8;
  tx.userData = { cv };
  return tx;
}

export async function build(GH) {
  const T = GH.THREE;
  const V = (x = 0, y = 0, z = 0) => new T.Vector3(x * MM, y * MM, z * MM);
  const root = new T.Group();
  root.name = 'bench';
  root.visible = false;
  const zup = new T.Group();
  zup.rotation.x = -Math.PI / 2;
  root.add(zup);
  GH.scene.add(root);

  // ---------------- the parts (glb) ----------------
  const gltf = await loadGLB('assets/bench_pestcam.glb.json');
  const comps = {};
  gltf.scene.traverse((o) => { if (o.userData?.gh_type === 'component') comps[o.userData.gh_id.replace('bp_', '')] = { root: o, parts: {} }; });
  for (const c of Object.values(comps)) c.root.traverse((o) => { if (o.userData?.part_name) c.parts[o.userData.part_name] = o; });
  gltf.scene.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  const places = {};
  const mount = (key, obj) => {
    const place = new T.Group();
    place.name = 'bench.' + key;
    const wrap = new T.Group();
    wrap.rotation.x = Math.PI / 2;                  // glb is y-up; the bench is z-up
    obj.position.set(0, 0, 0);
    wrap.add(obj);
    place.add(wrap);
    zup.add(place);
    places[key] = place;
    return place;
  };
  for (const k of Object.keys(comps)) mount(k, comps[k].root);
  const P = (k) => comps[k].parts;
  // the meter probes become their own objects
  for (const nm of ['probe_red', 'probe_black']) { const o = P('meter')[nm]; o.parent.remove(o); mount(nm, o); }
  // per-object materials for the things that light up
  const ledMat = P('ring').leds.material.clone();
  P('ring').leds.material = ledMat;
  ledMat.emissive = new T.Color(0xfff3e0);
  ledMat.emissiveIntensity = 0;
  const ringLight = new T.PointLight(0xfff2dc, 0, 0.6, 2);
  places.ring.add(ringLight);
  ringLight.position.set(0, 0, 0.008);
  const latch = P('zero').csi_latch, latch0 = latch.position.x;
  const screw = P('boost').trim_screw;
  const plate = P('box').plate, plateY = plate.position.y;
  const lid = P('box').lid, lidY = lid.position.y;

  // ---------------- table, mat, stand, card ----------------
  const wood = canvasTex(T, 1024, 512, (g, w, h) => {
    g.fillStyle = '#b98a5c'; g.fillRect(0, 0, w, h);
    let s = 7;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 260; i++) {
      const y = rnd() * h, a = 0.05 + 0.12 * rnd();
      g.strokeStyle = rnd() < 0.5 ? `rgba(110,70,35,${a})` : `rgba(230,190,140,${a})`;
      g.lineWidth = 1 + 3 * rnd();
      g.beginPath(); g.moveTo(0, y);
      for (let x = 0; x <= w; x += 64) g.lineTo(x, y + 6 * Math.sin(x * 0.004 + i) + 3 * rnd());
      g.stroke();
    }
  });
  wood.wrapS = wood.wrapT = T.RepeatWrapping;
  const table = new T.Mesh(new T.BoxGeometry(1.9, 1.1, 0.04), new T.MeshStandardMaterial({ map: wood, roughness: 0.62 }));
  table.position.set(0.05, 0.12, -0.023);
  table.receiveShadow = true;
  zup.add(table);
  const MAT = [0.72, 0.56], MATC = [0.02, 0.1];
  const matTex = canvasTex(T, 2048, 1600, (g, w, h) => {
    g.fillStyle = '#1d4a3a'; g.fillRect(0, 0, w, h);
    const pxm = w / (MAT[0] * 1000);
    for (let mm = 0; mm <= MAT[0] * 1000; mm += 10) {
      g.strokeStyle = mm % 50 ? 'rgba(150,200,175,0.13)' : 'rgba(180,220,200,0.24)';
      g.lineWidth = mm % 50 ? 1.0 : 1.8;
      g.beginPath(); g.moveTo(mm * pxm, 0); g.lineTo(mm * pxm, h); g.stroke();
    }
    for (let mm = 0; mm <= MAT[1] * 1000; mm += 10) {
      g.strokeStyle = mm % 50 ? 'rgba(150,200,175,0.13)' : 'rgba(180,220,200,0.24)';
      g.lineWidth = mm % 50 ? 1.0 : 1.8;
      g.beginPath(); g.moveTo(0, h - mm * pxm); g.lineTo(w, h - mm * pxm); g.stroke();
    }
    g.fillStyle = 'rgba(210,240,220,0.55)'; g.font = 'bold 22px Arial';
    for (let mm = 50; mm < MAT[0] * 1000; mm += 50) g.fillText(String(mm / 10), mm * pxm + 4, h - 8);
  });
  const mat = new T.Mesh(new T.BoxGeometry(MAT[0], MAT[1], 0.003), [0, 1, 2, 3].map(() => new T.MeshStandardMaterial({ color: 0x1d4a3a, roughness: 0.85 }))
    .concat([new T.MeshStandardMaterial({ map: matTex, roughness: 0.82 }), new T.MeshStandardMaterial({ color: 0x1d4a3a })]));
  mat.position.set(MATC[0], MATC[1], -0.0015);
  mat.receiveShadow = true;
  zup.add(mat);
  // a lab stand holding the card frame by its hook
  const alu = new T.MeshStandardMaterial({ color: 0xc9cdd2, metalness: 0.85, roughness: 0.3 });
  const steel = new T.MeshStandardMaterial({ color: 0x2b2e31, metalness: 0.5, roughness: 0.45 });
  const stand = new T.Group();
  const F = POSE.frame;
  const hookZ = F[2] + 58 + 12;
  const rodY = F[1] + 85;
  const addCyl = (r, x0, y0, z0, x1, y1, z1, m) => {
    const a = V(x0, y0, z0), b = V(x1, y1, z1);
    const msh = new T.Mesh(new T.CylinderGeometry(r * MM, r * MM, a.distanceTo(b), 20), m);
    msh.position.copy(a).add(b).multiplyScalar(0.5);
    msh.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), b.clone().sub(a).normalize());
    msh.castShadow = msh.receiveShadow = true;
    stand.add(msh);
  };
  const base = new T.Mesh(new T.BoxGeometry(0.16, 0.11, 0.009), steel);
  base.position.copy(V(0, rodY + 10, 4.5));
  base.castShadow = base.receiveShadow = true;
  stand.add(base);
  addCyl(5, 0, rodY, 0, 0, rodY, hookZ + 40, alu);
  addCyl(4, 0, rodY + 6, hookZ + 8, 0, F[1] - 22, hookZ + 8, alu);
  const boss = new T.Mesh(new T.BoxGeometry(0.022, 0.022, 0.03), steel);
  boss.position.copy(V(0, rodY, hookZ + 8));
  stand.add(boss);
  zup.add(stand);

  // the sticky card (front face = -y of the frame), with its insects
  const card = new T.Group();
  places.frame.add(card);
  const cardTex = canvasTex(T, 2000, 800, (g, w, h) => {
    g.fillStyle = '#f4d40a'; g.fillRect(0, 0, w, h);
    g.strokeStyle = 'rgba(40,40,20,0.55)'; g.lineWidth = 3;
    for (let k = 1; k < 10; k++) { g.beginPath(); g.moveTo(k * w / 10, 0); g.lineTo(k * w / 10, h); g.stroke(); }
    for (let k = 1; k < 4; k++) { g.beginPath(); g.moveTo(0, k * h / 4); g.lineTo(w, k * h / 4); g.stroke(); }
    g.lineWidth = 8; g.strokeRect(4, 4, w - 8, h - 8);
  });
  const cardFace = new T.Mesh(new T.PlaneGeometry(0.25, 0.1), new T.MeshPhysicalMaterial({ map: cardTex, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.08, emissive: new T.Color(0xffe23a), emissiveMap: cardTex, emissiveIntensity: 0.32 }));
  cardFace.rotation.x = Math.PI / 2;
  cardFace.position.y = -0.0002;
  cardFace.receiveShadow = true;
  card.add(cardFace);
  const cardBack = new T.Mesh(new T.BoxGeometry(0.25, 0.0004, 0.1), new T.MeshStandardMaterial({ color: 0xf2d20a, roughness: 0.3 }));
  cardBack.position.y = 0.00001;
  card.add(cardBack);
  const CARD_DATA = await (await fetch('assets/bench_card.json')).json();
  const INS = CARD_DATA.insects;
  const insGeo = new T.SphereGeometry(1, 12, 8);
  const KIND = {
    wf: { s: [0.78, 0.22, 0.52], c: 0xf7f7f2, r: 0.55 },
    th: { s: [0.58, 0.1, 0.14], c: 0x3a2814, r: 0.5 },
    mp: { s: [1.7, 0.36, 0.55], c: 0x6aa232, r: 0.45 },
    fl: { s: [0.95, 0.26, 0.3], c: 0x141414, r: 0.4 },
  };
  const insMesh = {};
  for (const [k, d] of Object.entries(KIND)) {
    const list = INS.filter((o) => o.k === k);
    const im = new T.InstancedMesh(insGeo, new T.MeshStandardMaterial({ color: d.c, roughness: d.r }), list.length);
    im.castShadow = true;
    im.frustumCulled = false;
    im.userData = { list, s: d.s };
    card.add(im);
    insMesh[k] = im;
  }
  // gnat wings (translucent) as a second instanced mesh
  const flList = INS.filter((o) => o.k === 'fl');
  const wing = new T.InstancedMesh(insGeo, new T.MeshStandardMaterial({ color: 0xcfd6dc, roughness: 0.2, transparent: true, opacity: 0.45 }), flList.length);
  wing.frustumCulled = false;
  card.add(wing);
  const newOnes = INS.filter((o) => o.new);
  const fly0 = new Map(newOnes.map((o, i) => [o, { du: 40 * Math.sin(i * 2.3), dv: 30 * Math.cos(i * 1.7) + 10, d: 70 + 50 * ((i * 37) % 10) / 10, ph: i * 1.3 }]));
  const m4 = new T.Matrix4(), q = new T.Quaternion(), sv = new T.Vector3(), pv = new T.Vector3(), yAxis = new T.Vector3(0, 1, 0);
  function placeInsects(land) {
    const n = newOnes.length;
    for (const [k, im] of Object.entries(insMesh)) {
      im.userData.list.forEach((o, i) => {
        let u = o.u, v = o.v, y = -0.35, s = 1;
        if (o.new) {
          const j = newOnes.indexOf(o);
          const t = clamp01((land * (n + 6) - j) / 6);
          const f = fly0.get(o), e = 1 - ease(t);
          u += f.du * e + 4 * Math.sin(f.ph + t * 9) * e;
          v += f.dv * e + 3 * Math.cos(f.ph + t * 7) * e;
          y -= f.d * e;
          if (t <= 0) s = 0;
        }
        q.setFromAxisAngle(yAxis, (o.yaw * Math.PI) / 180);
        pv.set(u * MM, y * MM, v * MM);
        sv.set(im.userData.s[0] * MM * s, im.userData.s[1] * MM * s, im.userData.s[2] * MM * s);
        im.setMatrixAt(i, m4.compose(pv, q, sv));
        if (k === 'fl') {
          pv.y -= 0.25 * MM;
          sv.set(1.05 * MM * s, 0.04 * MM * s, 0.62 * MM * s);
          wing.setMatrixAt(i, m4.compose(pv, q, sv));
        }
      });
      im.instanceMatrix.needsUpdate = true;
    }
    wing.instanceMatrix.needsUpdate = true;
  }
  // the camera's view: lens to the corners of what it sees at 20 cm (66 x 41 deg = 260 x 150 mm)
  const fr = [-130, 130].flatMap((x) => [-75, 75].map((z) => V(x, 0, z)));
  const lensP = V(0, -CAM_DIST, 0);
  const fpts = [];
  for (const c of fr) fpts.push(lensP, c);
  const [c00, c01, c10, c11] = fr;
  fpts.push(c00, c01, c01, c11, c11, c10, c10, c00);
  const frustum = new T.LineSegments(new T.BufferGeometry().setFromPoints(fpts), new T.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false }));
  places.frame.add(frustum);

  // ---------------- wires ----------------
  const anchor = (key, p) => {               // a part-local point (mm) -> zup coordinates (m)
    const pl = places[key];
    pl.updateMatrix();
    return V(...p).applyMatrix4(pl.matrix);
  };
  const upOf = (key) => new T.Vector3(0, 0, 1).applyQuaternion(places[key].quaternion);
  const housingGeo = new T.BoxGeometry(2.54 * MM, 2.54 * MM, 14 * MM);
  const housingMat = new T.MeshStandardMaterial({ color: 0x111111, roughness: 0.5 });
  const wires = WIRES.map(([id, ka, pa, kb, pb, col, r, fem = '', male = false]) => {
    const material = new T.MeshStandardMaterial({ color: col, roughness: 0.42, emissive: new T.Color(col), emissiveIntensity: 0 });
    const mesh = new T.Mesh(new T.BufferGeometry(), material);
    mesh.castShadow = true;
    zup.add(mesh);
    const housings = [];
    for (const [end, key, p] of [['a', ka, pa], ['b', kb, pb]]) {
      if (fem.includes(end) || (end === 'b' && male)) {
        const h = new T.Mesh(housingGeo, housingMat);
        h.castShadow = true;
        const z0 = fem.includes(end) ? ZT + 2.5 + 7 : BB_T + 7 - 1.5;
        h.position.copy(V(p[0], p[1], z0));
        h.visible = false;
        places[key].add(h);
        housings.push([end, h]);
      }
    }
    return { id, ka, pa, kb, pb, r, mesh, material, housings, prog: 0, glow: 0, sig: '' };
  });
  function buildWire(w) {
    const a = anchor(w.ka, w.pa), b = anchor(w.kb, w.pb);
    const ua = upOf(w.ka), ub = upOf(w.kb);
    const d = a.distanceTo(b);
    const lift = 0.006 + 0.22 * d;
    const top = Math.max(a.z, b.z);
    const mid = a.clone().lerp(b, 0.5);
    mid.z = top + lift;
    const pts = [a, a.clone().addScaledVector(ua, 0.006), a.clone().lerp(mid, 0.4).setZ(top + lift * 0.8), mid,
      b.clone().lerp(mid, 0.4).setZ(top + lift * 0.8), b.clone().addScaledVector(ub, 0.006), b];
    const curve = new T.CatmullRomCurve3(pts, false, 'centripetal');
    w.mesh.geometry.dispose();
    w.mesh.geometry = new T.TubeGeometry(curve, 72, w.r * MM, 8, false);
    w.total = w.mesh.geometry.index.count;
  }
  // the camera ribbon (Pi Zero adapter: 22-pin 0.5 mm -> 15-pin 1 mm), a flat strip between the two connectors
  const ribbonMat = new T.MeshStandardMaterial({ vertexColors: true, roughness: 0.45, side: T.DoubleSide });
  const ribTop = new T.Mesh(new T.BufferGeometry(), ribbonMat), ribBot = new T.Mesh(new T.BufferGeometry(), ribbonMat);
  ribTop.castShadow = true;
  zup.add(ribTop, ribBot);
  function buildRibbon(slide, flip, vis) {
    ribTop.visible = ribBot.visible = vis > 0;
    if (vis <= 0) return;
    const out = (1 - slide) * 14;
    const a = anchor('zero', [29.6 + out, 0.05, ZT + 0.6 + (1 - slide) * 3]);
    const da = new T.Vector3(1, 0, 0).applyQuaternion(places.zero.quaternion);
    const b = anchor('cam3', [0, -CH / 2 + 2.0, -1.2]);
    const db = new T.Vector3(0, -1, 0).applyQuaternion(places.cam3.quaternion);
    const curve = new T.CatmullRomCurve3([a, a.clone().addScaledVector(da, 0.008), b.clone().addScaledVector(db, 0.008), b], false, 'centripetal');
    const N = 60, L = curve.getLength() / MM;
    const top = [], bot = [], ct = [], cb = [], idx = [];
    const zUp = new T.Vector3(0, 0, 1);
    for (let i = 0; i <= N; i++) {
      const u = i / N, s = u * L;
      const p = curve.getPointAt(u), t = curve.getTangentAt(u);
      let side = new T.Vector3().crossVectors(zUp, t);
      if (side.lengthSq() < 1e-6) side.set(0, 1, 0);
      side.normalize();
      const tw = flip * Math.PI * clamp01(1 - s / 26);
      side.applyAxisAngle(t, tw);
      const nrm = new T.Vector3().crossVectors(t, side).normalize();
      const w = (s < 12 ? 11.7 : s < 20 ? 11.7 + (s - 12) / 8 * 4.3 : 16) / 2 * MM;
      for (const [arr, col, off, contact] of [[top, ct, 0.05, false], [bot, cb, -0.05, true]]) {
        const c = off > 0 ? (s < 9 || s > L - 9 ? [0.06, 0.24, 0.62] : [0.78, 0.78, 0.75]) : ((s < 3.5 || s > L - 3.5) ? [0.7, 0.68, 0.62] : [0.78, 0.78, 0.75]);
        for (const sg of [-1, 1]) {
          const v = p.clone().addScaledVector(side, sg * w).addScaledVector(nrm, off * MM);
          arr.push(v.x, v.y, v.z);
          col.push(...c);
        }
      }
      if (i < N) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
    }
    for (const [mesh, pos, col] of [[ribTop, top, ct], [ribBot, bot, cb]]) {
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
      g.setAttribute('color', new T.Float32BufferAttribute(col, 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      mesh.geometry.dispose();
      mesh.geometry = g;
    }
  }
  // multimeter leads + LCD
  const leadMats = [new T.MeshStandardMaterial({ color: 0xb01818, roughness: 0.5 }), new T.MeshStandardMaterial({ color: 0x151515, roughness: 0.5 })];
  const leads = leadMats.map((m) => { const o = new T.Mesh(new T.BufferGeometry(), m); o.castShadow = true; zup.add(o); return o; });
  const lcdTex = canvasTex(T, 512, 256, () => {});
  const lcd = new T.Mesh(new T.PlaneGeometry(0.048, 0.023), new T.MeshBasicMaterial({ map: lcdTex, toneMapped: false }));
  lcd.position.copy(V(0, 42, 31.1));
  places.meter.add(lcd);
  let lcdShown = '';
  function drawLCD(txt) {
    if (txt === lcdShown) return;
    lcdShown = txt;
    const g = lcdTex.userData.cv.getContext('2d');
    g.fillStyle = '#a9b49b'; g.fillRect(0, 0, 512, 256);
    g.fillStyle = 'rgba(30,35,25,0.08)'; g.font = 'bold 150px "Courier New", monospace'; g.textAlign = 'right'; g.textBaseline = 'middle';
    g.fillText('88.88', 490, 140);
    g.fillStyle = '#1b2016'; g.fillText(txt, 490, 140);
    g.font = 'bold 40px Arial'; g.textAlign = 'left'; g.fillText('DC V', 24, 44);
    lcdTex.needsUpdate = true;
  }

  // ---------------- lights + studio ----------------
  const key = new T.DirectionalLight(0xfff1e2, 2.4);
  key.position.set(-0.55, -0.75, 1.35);
  key.target.position.set(0.0, 0.06, 0);
  key.castShadow = true;
  Object.assign(key.shadow.camera, { left: -0.5, right: 0.5, top: 0.5, bottom: -0.5, near: 0.2, far: 3.5 });
  key.shadow.mapSize.set(4096, 4096);
  key.shadow.bias = -0.00015;
  key.shadow.normalBias = 0.0004;
  key.shadow.radius = 3;
  zup.add(key, key.target);
  const fill = new T.DirectionalLight(0xdfe8ff, 0.7);
  fill.position.set(0.9, -0.3, 0.6);
  zup.add(fill);
  const hemi = new T.HemisphereLight(0xf2f4f8, 0x6b5843, 0.55);
  zup.add(hemi);
  const pmrem = new T.PMREMGenerator(GH.renderer);
  const roomEnv = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  const BG = new T.Color(0xdcd9d2);
  const W = GH.world;

  // ---------------- knobs ----------------
  const K = {
    latch: 0, rib: 0, ribSlide: 1, ribFlip: 0, ring: 0, trim: 0, meter: 0, probe: 0, glow: 0, done: 0, land: 1,
    boxShow: 0, boxIn: 0, plate: 0, lid: 0, mount: 0, frustum: 0, pi5: 0, trap: 1, exposure: 1.0, bloom: 1.0,
  };
  for (const k of ['zero', 'cam3', 'tpl', 'cell', 'ring', 'boost', 'bread']) K['v:' + k] = 1;
  for (const w of wires) K['w:' + w.id] = 1;
  const tweens = new Map();
  let dirty = true;
  const api = {
    group: root, zup, places, comps, wires, K, INS, CARD_DATA, POSE, stand, card,
    set(k, v) { tweens.delete(k); K[k] = v; dirty = true; },
    to(k, v, dur = 0.5, from) { if (from !== undefined) K[k] = from; tweens.set(k, { a: K[k], b: v, t: 0, dur: Math.max(0.001, dur) }); },
    setAll(o) { for (const [k, v] of Object.entries(o)) api.set(k, v); },
  };

  // poses
  const poseM = (p, rz = p[3] || 0, rx = 0) => new T.Matrix4().compose(V(p[0], p[1], p[2]), new T.Quaternion().setFromEuler(new T.Euler(rx * Math.PI / 180, 0, rz * Math.PI / 180)), new T.Vector3(1, 1, 1));
  const benchM = Object.fromEntries(Object.entries(POSE).map(([k, p]) => [k, poseM(p)]));
  const mountM = poseM([...MOUNT.pos, 0], 0, MOUNT.rx);
  const tmpA = { p: new T.Vector3(), q: new T.Quaternion(), s: new T.Vector3() }, tmpB = { p: new T.Vector3(), q: new T.Quaternion(), s: new T.Vector3() };
  const setPlace = (pl, Ma, Mb, t, arc = 0) => {
    Ma.decompose(tmpA.p, tmpA.q, tmpA.s);
    if (t <= 0 || !Mb) { pl.position.copy(tmpA.p); pl.quaternion.copy(tmpA.q); return; }
    Mb.decompose(tmpB.p, tmpB.q, tmpB.s);
    pl.position.lerpVectors(tmpA.p, tmpB.p, t);
    pl.position.z += arc * Math.sin(Math.PI * t);
    pl.quaternion.slerpQuaternions(tmpA.q, tmpB.q, t);
  };

  function apply() {
    // the box: on the bench, or carried to the trap mount
    const box = places.box;
    box.visible = K.boxShow > 0;
    setPlace(box, benchM.box, mountM, ease(K.mount), 0.09);
    box.updateMatrix();
    plate.visible = K.plate > 0;
    plate.position.y = plateY + (1 - ease(K.plate)) * 0.09;
    lid.visible = K.lid > 0;
    lid.position.y = lidY + (1 - ease(K.lid)) * 0.1;
    // parts: bench pose, or flying into the box (staggered)
    const n = BOX_ORDER.length;
    BOX_ORDER.forEach((k, i) => {
      const t = ease(clamp01((K.boxIn * (n + 1.5) - i) / 2.5));
      if (k === 'plate') return;
      const pl = places[k];
      const Mb = BOXP[k] ? box.matrix.clone().multiply(poseM(BOXP[k])) : null;
      setPlace(pl, benchM[k], Mb, t, 0.08);
      const vis = K['v:' + k] ?? 1;
      pl.visible = vis > 0;
      if (vis < 1) pl.position.z += (1 - ease(vis)) * 0.05;
    });
    // meter + probes: slide in from the right; probes onto the boost board's output pads
    const mv = ease(K.meter);
    places.meter.visible = places.probe_red.visible = places.probe_black.visible = K.meter > 0;
    setPlace(places.meter, poseM([POSE.meter[0] + 260, POSE.meter[1] + 40, 0, POSE.meter[3]]), benchM.meter, mv);
    places.meter.updateMatrix();
    const pr = ease(K.probe);
    const mp = places.meter.position;
    for (const [nm, pad, rest, lean, side] of [['probe_red', 'VOUT+', [52, -10], 32, -8], ['probe_black', 'VOUT-', [60, -28], 26, 10]]) {
      const tip = anchor('boost', [...MT_PADS[pad], 1.7]);
      const tilt = new T.Quaternion().setFromEuler(new T.Euler(-lean * Math.PI / 180, side * Math.PI / 180, 0));
      const flat = new T.Quaternion().setFromEuler(new T.Euler(0, Math.PI / 2, 0.35));
      const pl = places[nm];
      pl.quaternion.slerpQuaternions(flat, tilt, pr);
      const axis = new T.Vector3(0, 0, 1).applyQuaternion(tilt);
      const target = tip.clone().addScaledVector(axis, 17 * MM);
      const lying = new T.Vector3(mp.x + rest[0] * MM, mp.y + rest[1] * MM, 5 * MM);
      pl.position.lerpVectors(lying, target, pr);
      if (pr > 0 && pr < 1) pl.position.z += 0.04 * Math.sin(Math.PI * pr);
      pl.updateMatrix();
    }
    // Pi 5: rises into view
    places.pi5.visible = K.pi5 > 0;
    setPlace(places.pi5, poseM([POSE.pi5[0] + 120, POSE.pi5[1], 0, POSE.pi5[3]]), benchM.pi5, ease(K.pi5));
    // the trap stand
    places.frame.visible = stand.visible = K.trap > 0;
    setPlace(places.frame, benchM.frame, null, 0);
    frustum.material.opacity = 0.8 * K.frustum;
    frustum.visible = K.frustum > 0;
    // small moving parts
    latch.position.x = latch0 + 0.0011 * ease(K.latch);
    screw.rotation.y = -K.trim * Math.PI * 2 * 6;
    ledMat.emissiveIntensity = 7 * K.ring;
    ringLight.intensity = 0.06 * K.ring;
    placeInsects(K.land);
    for (const pl of Object.values(places)) pl.updateMatrix();
    // wires
    for (const w of wires) {
      const prog = K['w:' + w.id];
      const show = prog > 0 && (K['v:' + w.ka] ?? 1) > 0 && (K['v:' + w.kb] ?? 1) > 0;
      w.mesh.visible = show;
      for (const [end, h] of w.housings) h.visible = show && (end === 'a' || prog > 0.97);
      if (!show) continue;
      buildWire(w);
      w.mesh.geometry.setDrawRange(0, Math.floor(w.total * clamp01(prog) / 48) * 48);
      const glow = POWER_WIRES.includes(w.id) || ['gnd1', 'gnd2', 'bat-'].includes(w.id) ? K.glow : w.id === 'done' ? K.done : 0;
      w.material.emissiveIntensity = glow * (w.id === 'done' ? 1.6 : 0.9);
    }
    buildRibbon(K.ribSlide, K.ribFlip, K.rib);
    // probe leads
    if (K.meter > 0) {
      [['probe_red', [-22, -50, 32.6]], ['probe_black', [0, -50, 32.6]]].forEach(([nm, jack], i) => {
        const a = V(0, 0, 95).applyMatrix4(places[nm].matrix);
        const b = V(...jack).applyMatrix4(places.meter.matrix);
        const mid = a.clone().lerp(b, 0.5); mid.z = Math.max(a.z, b.z) + 0.03;
        const c = new T.CatmullRomCurve3([a, a.clone().add(V(0, 0, 12)), mid, b.clone().add(V(0, 0, 10)), b], false, 'centripetal');
        leads[i].geometry.dispose();
        leads[i].geometry = new T.TubeGeometry(c, 48, 1.1 * MM, 8, false);
        leads[i].visible = true;
      });
    } else leads.forEach((l) => { l.visible = false; });
    const v = 12.6 + (5.1 - 12.6) * clamp01(K.trim);
    drawLCD(K.meter > 0 ? v.toFixed(2) : '');
    GH.dirtyShadows?.();
  }

  // ---------------- studio on/off ----------------
  const saved = {};
  function studio() {
    GH.scene.background = BG;
    GH.scene.environment = roomEnv;
    GH.scene.environmentIntensity = 0.55;
    GH.scene.backgroundIntensity = 1;
    W.sun.intensity = 0; W.hemi.intensity = 0; if (W.moon) W.moon.intensity = 0;
    GH.renderer.toneMappingExposure = 0.92 * K.exposure;
    const bl = GH.bloom;
    if (bl) { bl.threshold = 2.4; bl.strength = 0.32 * K.bloom; bl.radius = 0.5; }
    const f = GH.scene.fog;
    if (f) { if (f.isFogExp2) f.density = 0; else { f.near = 1e4; f.far = 2e4; } }
  }
  const setTime0 = W.setTime.bind(W);
  W.setTime = (...a) => { const r = setTime0(...a); if (root.visible) studio(); return r; };
  const hidden = [];
  api.show = (on) => {
    if (on === root.visible) return;
    const S = GH.scene, cam = GH.camera, ctl = GH.controls;
    if (on) {
      const bl = GH.bloom;
      if (bl) Object.assign(saved, { blT: bl.threshold, blS: bl.strength, blR: bl.radius });
      Object.assign(saved, { bg: S.background, env: S.environment, envI: S.environmentIntensity, bgI: S.backgroundIntensity, exp: GH.renderer.toneMappingExposure,
        near: cam.near, far: cam.far, minD: ctl.minDistance, maxP: ctl.maxPolarAngle,
        fog: S.fog ? (S.fog.isFogExp2 ? { d: S.fog.density } : { n: S.fog.near, f: S.fog.far }) : null });
      for (const o of S.children) if (o !== root && o.visible && !o.isLight) { hidden.push(o); o.visible = false; }
      cam.near = 0.003; cam.far = 40; cam.updateProjectionMatrix();
      ctl.minDistance = 0; ctl.maxPolarAngle = Math.PI;
      root.visible = true;
      studio();
    } else {
      hidden.splice(0).forEach((o) => { o.visible = true; });
      root.visible = false;
      S.background = saved.bg; S.environment = saved.env; S.environmentIntensity = saved.envI; S.backgroundIntensity = saved.bgI;
      GH.renderer.toneMappingExposure = saved.exp;
      if (GH.bloom && saved.blT !== undefined) Object.assign(GH.bloom, { threshold: saved.blT, strength: saved.blS, radius: saved.blR });
      cam.near = saved.near; cam.far = saved.far; cam.updateProjectionMatrix();
      ctl.minDistance = saved.minD; ctl.maxPolarAngle = saved.maxP;
      if (S.fog && saved.fog) { if (S.fog.isFogExp2) S.fog.density = saved.fog.d; else { S.fog.near = saved.fog.n; S.fog.far = saved.fog.f; } }
      W.setTime(GH.sim.t + 1, 0);
    }
    GH.dirtyShadows?.();
  };

  api.update = (dt) => {
    for (const [k, tw] of tweens) {
      tw.t += dt / tw.dur;
      K[k] = tw.a + (tw.b - tw.a) * ease(Math.min(1, tw.t));
      dirty = true;
      if (tw.t >= 1) tweens.delete(k);
    }
    if (!root.visible) return;
    studio();
    if (dirty) { apply(); dirty = false; }
  };
  { const u = GH.farm4.update.bind(GH.farm4); GH.farm4.update = (dt, ct) => { u(dt, ct); api.update(dt); }; }

  // ---------------- points for the overlay (screen 0..1) ----------------
  const PTS = {
    zero: ['zero', [0, 0, 8]], cam3: ['cam3', [0, LENS_Y, 10]], tpl: ['tpl', [0, 0, 4]], cell: ['cell', [0, 0, 18]], ring: ['ring', [0, 18, 4]],
    boost: ['boost', [0, 0, 6]], bread: ['bread', [0, 0, 10]], meter: ['meter', [0, 42, 32]], pi5: ['pi5', [-14, 3, 4]], hailo: ['pi5', [-40, -1, 20]],
    pin2: ['zero', [...zeroPin(2), 10]], pin6: ['zero', [...zeroPin(6), 10]], pin11: ['zero', [...zeroPin(11), 10]], pin37: ['zero', [...zeroPin(37), 10]],
    pin4: ['zero', [...zeroPin(4), 10]], csi: ['zero', [30.8, 0, 2.5]], soc: ['zero', [-5.2, 0, 2.5]],
    vout: ['boost', [15.6, 0, 2]], vin: ['boost', [-15.6, 0, 2]], screw: ['boost', [-6.6, 5.4, 12]], done: ['tpl', [...tplPad('DONE'), 2]], drv: ['tpl', [...tplPad('DRV'), 2]],
    trimpot: ['tpl', [5.4, 1.2, 4]], gate: ['bread', [...bbHole(8, 'a'), 14]], mosfet: ['bread', [0, 14.5, 20]], r1k: ['bread', [-6.35, 6.35, 11]], box: ['box', [0, 0, 40]], lens: ['box', [0, 0, 62]],
  };
  const vproj = new T.Vector3();
  const proj = (p) => {
    vproj.copy(p);
    zup.localToWorld(vproj);
    vproj.project(GH.camera);
    return [+((vproj.x + 1) / 2).toFixed(4), +((1 - vproj.y) / 2).toFixed(4), +vproj.z.toFixed(4)];
  };
  api.readout = () => {
    if (!root.visible) return null;
    const out = {};
    for (const [k, [part, p]] of Object.entries(PTS)) out[k] = places[part].visible ? proj(anchor(part, p)) : null;
    places.frame.updateMatrixWorld(true);
    const cardPt = (u, v) => { const w = V(u, -0.4, v); card.localToWorld(w); w.project(GH.camera); return [+((w.x + 1) / 2).toFixed(4), +((1 - w.y) / 2).toFixed(4)]; };
    out.card = [cardPt(-125, 50), cardPt(125, 50), cardPt(125, -50), cardPt(-125, -50)];
    out.k = { ring: +K.ring.toFixed(3), trim: +K.trim.toFixed(3), glow: +K.glow.toFixed(3), done: +K.done.toFixed(3), land: +K.land.toFixed(3), frustum: +K.frustum.toFixed(3) };
    return out;
  };
  api.apply = () => { dirty = true; apply(); };
  apply();
  return api;
}
