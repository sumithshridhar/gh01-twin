// A melon polyhouse bay (14 Oct 2026), for the video on melons and hidden fruit. Not part of GH-01: built on demand.
//
//   const M = await import('./js/melon.js'); GH.melon = M.build(GH); GH.melon.show(true);
//
// Blender-style coordinates (metres, z up). Bed A (y -0.95): muskmelons trained up strings to a crop wire at 2.3 m,
// pruned to one stem, one fruit per vine hanging in a net bag (Crown-melon style). The robot's pipe rails run down the
// aisle (y 0.05). Bed B (y 1.25): watermelons left to crawl on the mulch, some fruit under the leaves. The scout robot
// (a clone of GH-01's) carries a camera boom over bed B with an air nozzle. Knobs drive the demos (like bench.js):
// arm, puff, views, nbv, cloud, newfruit, complete.
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const ease = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));
const clamp01 = (t) => Math.max(0, Math.min(1, t));
export const LAYOUT = { x0: 0, x1: 12, bedA: -0.95, bedB: 1.25, aisle: 0.05, gauge: 0.55, bedTop: 0.25, wireZ: 2.3, robotX: 5.0 };

function rng(seed) { let s = seed; return () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646; }

function canvasTex(T, w, h, draw) {
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  draw(cv.getContext('2d'), w, h);
  const tx = new T.CanvasTexture(cv);
  tx.colorSpace = T.SRGBColorSpace;
  tx.anisotropy = 8;
  return tx;
}

export function build(GH) {
  const T = GH.THREE, L = LAYOUT;
  const V = (x, y, z) => new T.Vector3(x, y, z);
  const root = new T.Group();
  root.name = 'melonhouse';
  root.visible = false;
  const zup = new T.Group();
  zup.rotation.x = -Math.PI / 2;
  root.add(zup);
  GH.scene.add(root);
  const R = rng(20261014);

  // ---------------- materials ----------------
  const M = {
    soil: new T.MeshStandardMaterial({ color: 0x7a5538, roughness: 1 }),
    mulch: new T.MeshStandardMaterial({ color: 0x1b1c1e, roughness: 0.55 }),
    mulchB: new T.MeshStandardMaterial({ color: 0x24262a, roughness: 0.6 }),
    stem: new T.MeshStandardMaterial({ color: 0x5f8f35, roughness: 0.7 }),
    leaf: new T.MeshStandardMaterial({ color: 0xffffff, roughness: 0.72, side: T.DoubleSide }),
    twine: new T.LineBasicMaterial({ color: 0xe8e2d0 }),
    net: new T.LineBasicMaterial({ color: 0xf2efe6, transparent: true, opacity: 0.85 }),
    gi: new T.MeshStandardMaterial({ color: 0xc8ccd0, metalness: 0.8, roughness: 0.35 }),
    film: new T.MeshStandardMaterial({ color: 0xf4f7f8, roughness: 0.2, transparent: true, opacity: 0.1, side: T.DoubleSide, depthWrite: false }),
    pipe: new T.MeshStandardMaterial({ color: 0xc9ced3, metalness: 0.75, roughness: 0.32 }),
    tag: new T.MeshStandardMaterial({ color: 0xf5f5f0, roughness: 0.5 }),
    flower: new T.MeshStandardMaterial({ color: 0xf5c518, roughness: 0.5, side: T.DoubleSide }),
  };
  const melonTex = canvasTex(T, 1024, 512, (g, w, h) => {
    g.fillStyle = '#b9b67a'; g.fillRect(0, 0, w, h);
    const r = rng(5);
    for (let i = 0; i < 1800; i++) {                       // the net: short pale cracks joining up
      const x = r() * w, y = r() * h, a = r() * Math.PI, l = 8 + r() * 22;
      g.strokeStyle = `rgba(240,236,214,${0.55 + 0.4 * r()})`; g.lineWidth = 1.5 + r() * 2;
      g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a) * l * 0.5 + 4 * r(), y + Math.sin(a) * l * 0.5, x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
    }
  });
  const waterTex = canvasTex(T, 1024, 512, (g, w, h) => {
    g.fillStyle = '#9cc46a'; g.fillRect(0, 0, w, h);
    for (let k = 0; k < 16; k++) {
      const x0 = (k / 16) * w;
      g.fillStyle = '#2f5a1e';
      g.beginPath(); g.moveTo(x0, 0);
      for (let y = 0; y <= h; y += 16) g.lineTo(x0 + 10 * Math.sin(y * 0.05 + k) + 6 * Math.sin(y * 0.13), y);
      for (let y = h; y >= 0; y -= 16) g.lineTo(x0 + 26 + 10 * Math.sin(y * 0.05 + k + 1) + 6 * Math.sin(y * 0.11), y);
      g.closePath(); g.fill();
    }
  });
  M.melon = new T.MeshStandardMaterial({ map: melonTex, roughness: 0.65 });
  M.water = new T.MeshPhysicalMaterial({ map: waterTex, roughness: 0.35, clearcoat: 0.4 });

  // ---------------- leaves (one shape, many instances) ----------------
  function leafGeo(deep) {
    const pts = [];
    const N = 90;
    for (let i = 0; i <= N; i++) {
      const th = -Math.PI * 0.93 + (i / N) * Math.PI * 1.86;
      const lob = deep ? 0.5 * (0.55 + 0.45 * Math.pow(Math.abs(Math.cos(2.5 * th)), 0.45)) : 0.5 * (0.84 + 0.16 * Math.cos(5 * th));
      pts.push(new T.Vector2(0.5 + lob * Math.cos(th), lob * Math.sin(th) * 1.05));
    }
    pts.push(new T.Vector2(0.06, 0));
    const g = new T.ShapeGeometry(new T.Shape(pts), 12);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), y = p.getY(i);
      p.setZ(i, 0.12 * y * y - 0.18 * Math.max(0, x - 0.55) ** 2 + 0.02 * Math.sin(9 * x + 7 * y));   // cupped, tip droops
    }
    g.computeVertexNormals();
    return g;
  }
  const leafA = leafGeo(false), leafB = leafGeo(true);
  const leavesA = [], leavesB = [];        // [matrix, colour]
  const m4 = new T.Matrix4(), q = new T.Quaternion(), e = new T.Euler();
  const leafM = (pos, yaw, pitch, roll, size) => new T.Matrix4().compose(pos, q.setFromEuler(e.set(roll, -pitch, yaw, 'ZYX')).clone(), V(size, size, size));
  const leafCol = () => new T.Color().setHSL(0.26 + 0.03 * R(), 0.5 + 0.12 * R(), 0.16 + 0.06 * R());

  // ---------------- bed A: melons up strings ----------------
  const stems = [], petioles = [], twine = [], netPts = [], fruits = [], tagsM = [], flowersM = [];
  const plantsA = [];
  for (const dy of [-0.2, 0.2]) {
    for (let x = 0.6; x < L.x1 - 0.4; x += 0.45) {
      const px = x + (dy > 0 ? 0.22 : 0), py = L.bedA + dy, z0 = L.bedTop;
      const H = 1.75 + 0.35 * R();
      twine.push(V(px, py, z0), V(px, py, L.wireZ));
      const sp = [];
      for (let z = z0; z <= z0 + H; z += 0.1) sp.push(V(px + 0.012 * Math.sin(z * 9), py + 0.012 * Math.cos(z * 9), z));
      stems.push(new T.TubeGeometry(new T.CatmullRomCurve3(sp), 40, 0.0055, 6));
      const plant = { x: px, y: py, H, leaves: [], fruit: null };
      let az = R() * 6.28;
      for (let k = 0, z = z0 + 0.3; z < z0 + H; k++, z += 0.085 + 0.02 * R()) {
        az += 2.4;
        const out = V(Math.cos(az), Math.sin(az) * 0.6 + (dy < 0 ? -0.25 : 0.25), 0).normalize();
        const plen = 0.08 + 0.05 * R();
        const base = V(px, py, z), tip = base.clone().addScaledVector(out, plen).add(V(0, 0, 0.03));
        petioles.push(new T.TubeGeometry(new T.CatmullRomCurve3([base, base.clone().lerp(tip, 0.5).add(V(0, 0, 0.025)), tip]), 6, 0.0025, 4));
        const size = (0.19 + 0.08 * R()) * (z - z0 > H - 0.3 ? 0.6 : 1);
        const mtx = leafM(tip, Math.atan2(out.y, out.x), -0.35 - 0.3 * R(), (R() - 0.5) * 0.6, size);
        leavesA.push([mtx, leafCol()]);
        plant.leaves.push(leavesA.length - 1);
        if (z - z0 > H - 0.25 && R() < 0.5) flowersM.push(new T.Matrix4().compose(tip.clone().add(V(0, 0, 0.02)), new T.Quaternion(), V(0.012, 0.012, 0.012)));
      }
      // one fruit at ~1 m, in a net bag tied to the string
      const fz = z0 + 0.85 + 0.25 * R(), r = 0.068 + 0.012 * R();
      const fdir = dy < 0 ? -1 : 1;
      const fc = V(px + 0.03, py + fdir * 0.11, fz - 0.16);
      fruits.push(new T.Matrix4().compose(fc, new T.Quaternion().setFromEuler(new T.Euler(R(), R(), R())), V(r, r, r * 0.97)));
      plant.fruit = { c: fc, r };
      // net bag: meridians + rings around the fruit, a cord up to the string
      const mer = 8, rings = 5;
      for (let i = 0; i < mer; i++) {
        const a = (i / mer) * Math.PI * 2;
        let prev = null;
        for (let j = 0; j <= 10; j++) {
          const ph = -Math.PI / 2 + (j / 10) * Math.PI * 0.95;
          const p = fc.clone().add(V(Math.cos(a) * Math.cos(ph) * r * 1.03, Math.sin(a) * Math.cos(ph) * r * 1.03, Math.sin(ph) * r * 1.03));
          if (prev) netPts.push(prev, p);
          prev = p;
        }
      }
      for (let j = 1; j < rings; j++) {
        const ph = -Math.PI / 2 + (j / rings) * Math.PI * 0.9;
        let prev = null;
        for (let i = 0; i <= 24; i++) {
          const a = (i / 24) * Math.PI * 2;
          const p = fc.clone().add(V(Math.cos(a) * Math.cos(ph) * r * 1.03, Math.sin(a) * Math.cos(ph) * r * 1.03, Math.sin(ph) * r * 1.03));
          if (prev) netPts.push(prev, p);
          prev = p;
        }
      }
      netPts.push(fc.clone().add(V(0, 0, r)), V(px, py, fz + 0.04));
      tagsM.push(new T.Matrix4().compose(V(px, py + (dy < 0 ? -0.006 : 0.006), z0 + 0.42), new T.Quaternion(), V(0.035, 0.002, 0.02)));
      plantsA.push(plant);
    }
  }
  const add = (o, cast = true) => { o.castShadow = cast; o.receiveShadow = true; zup.add(o); return o; };
  add(new T.Mesh(mergeGeometries(stems), M.stem));
  add(new T.Mesh(mergeGeometries(petioles), M.stem), false);
  zup.add(new T.LineSegments(new T.BufferGeometry().setFromPoints(twine), M.twine));
  const netLines = new T.LineSegments(new T.BufferGeometry().setFromPoints(netPts), M.net);
  zup.add(netLines);
  const sphere = new T.SphereGeometry(1, 36, 24);
  const fruitIM = add(new T.InstancedMesh(sphere, M.melon, fruits.length));
  fruits.forEach((m, i) => fruitIM.setMatrixAt(i, m));
  const tagIM = add(new T.InstancedMesh(new T.BoxGeometry(1, 1, 1), M.tag, tagsM.length), false);
  tagsM.forEach((m, i) => tagIM.setMatrixAt(i, m));
  const flowerIM = add(new T.InstancedMesh(new T.CircleGeometry(1, 5), M.flower, flowersM.length), false);
  flowersM.forEach((m, i) => flowerIM.setMatrixAt(i, m));

  // the demo melon: the one nearest the robot on the aisle side, with a leaf right in front of it
  const target = plantsA.filter((p) => p.y > L.bedA).reduce((a, p) => (Math.abs(p.fruit.c.x - L.robotX - 0.2) < Math.abs(a.fruit.c.x - L.robotX - 0.2) ? p : a));
  const TF = target.fruit;
  const blocker = leafM(TF.c.clone().add(V(-0.03, 0.12, 0.04)), Math.PI / 2 + 0.2, -1.2, 0.1, 0.2);
  leavesA.push([blocker, leafCol()]);

  // ---------------- bed B: watermelons on the ground ----------------
  const runners = [], waterM = [], coverIdx = [];
  const plantsB = [];
  for (let x = 0.8; x < L.x1 - 0.6; x += 0.9) {
    const n = 4 + Math.floor(R() * 2);
    for (let k = 0; k < n; k++) {
      let ang = (k / n) * Math.PI * 2 + R() * 0.6;
      let p = V(x, L.bedB, L.bedTop + 0.01);
      const pts = [p.clone()];
      for (let s = 0; s < 14; s++) {
        ang += (R() - 0.5) * 0.7;
        let d = V(Math.cos(ang), Math.sin(ang) * 0.55, 0);
        p = p.clone().addScaledVector(d, 0.1);
        if (Math.abs(p.y - L.bedB) > 0.55) { ang = -ang; p.y = L.bedB + Math.sign(p.y - L.bedB) * 0.55; }
        pts.push(p.clone());
        if (s % 1 === 0) {
          const side = s % 2 ? 1 : -1;
          const lp = p.clone().add(V(-Math.sin(ang) * 0.04 * side, Math.cos(ang) * 0.04 * side, 0.05 + 0.06 * R()));
          leavesB.push([leafM(lp, ang + side * 1.2, 0.3 + 0.3 * R(), (R() - 0.5) * 0.5, 0.15 + 0.06 * R()), leafCol()]);
        }
      }
      runners.push(new T.TubeGeometry(new T.CatmullRomCurve3(pts), 40, 0.0045, 5));
      if (k < 2 && R() < 0.8) {
        const fp = pts[5 + Math.floor(R() * 6)];
        const a = R() * Math.PI;
        const rr = 0.1 + 0.03 * R();
        waterM.push({ c: V(fp.x, fp.y, L.bedTop + rr * 0.78), a, r: rr });
      }
    }
    plantsB.push({ x });
  }
  add(new T.Mesh(mergeGeometries(runners), M.stem), false);
  // the demo watermelon under three leaves, right below the arm
  const WT = { c: V(L.robotX + 0.05, L.bedB - 0.05, L.bedTop + 0.11 * 0.78), a: 0.3, r: 0.12 };
  waterM.push(WT);
  const cover = [];
  for (let i = 0; i < 3; i++) {
    const a = WT.a + (i - 1) * 1.6;
    const lp = WT.c.clone().add(V(Math.cos(a) * 0.05, Math.sin(a) * 0.05, 0.11));
    cover.push({ pos: lp, yaw: a + Math.PI, size: 0.22 - 0.02 * i, col: leafCol() });
  }
  const waterIM = add(new T.InstancedMesh(sphere, M.water, waterM.length));
  waterM.forEach((w, i) => waterIM.setMatrixAt(i, new T.Matrix4().compose(w.c, new T.Quaternion().setFromEuler(new T.Euler(0, Math.PI / 2, w.a, 'ZYX')), V(w.r * 0.8, w.r * 1.35, w.r * 0.8))));

  const mkLeaves = (geo, list, extra = 0) => {
    const im = new T.InstancedMesh(geo, M.leaf, list.length + extra);
    list.forEach(([m, c], i) => { im.setMatrixAt(i, m); im.setColorAt(i, c); });
    return add(im);
  };
  const leafIMA = mkLeaves(leafA, leavesA);
  const leafIMB = mkLeaves(leafB, leavesB, cover.length);
  const coverBase = leavesB.length;
  cover.forEach((c, i) => leafIMB.setColorAt(coverBase + i, c.col));

  // ---------------- beds, floor, rails, structure ----------------
  const box = (sx, sy, sz, x, y, z, m, cast = false) => { const o = new T.Mesh(new T.BoxGeometry(sx, sy, sz), m); o.position.set(x, y, z); return add(o, cast); };
  const xm = (L.x0 + L.x1) / 2, len = L.x1 - L.x0;
  box(len + 4, 8, 0.02, xm, 0.2, -0.01, M.soil);
  box(len, 0.85, L.bedTop, xm, L.bedA, L.bedTop / 2, M.soil);
  box(len, 0.87, 0.006, xm, L.bedA, L.bedTop + 0.003, M.mulch);
  box(len, 1.2, L.bedTop, xm, L.bedB, L.bedTop / 2, M.soil);
  box(len, 1.22, 0.006, xm, L.bedB, L.bedTop + 0.003, M.mulchB);
  for (const sy of [-1, 1]) {
    const pipe = new T.Mesh(new T.CylinderGeometry(0.0255, 0.0255, len, 14), M.pipe);
    pipe.rotation.z = Math.PI / 2;
    pipe.position.set(xm, L.aisle + sy * L.gauge / 2, 0.1);
    add(pipe);
  }
  for (const y of [L.bedA - 0.2, L.bedA + 0.2]) {                      // crop wires
    const w = new T.Mesh(new T.CylinderGeometry(0.002, 0.002, len, 4), M.gi);
    w.rotation.z = Math.PI / 2; w.position.set(xm, y, L.wireZ); add(w, false);
  }
  // gothic arches every 4 m, purlins, film
  const archPts = (s) => {
    const pts = [];
    for (let i = 0; i <= 24; i++) {
      const t = i / 24, a = t * Math.PI / 2;
      pts.push([s * (3.2 - 3.2 * (1 - Math.cos(a)) * 0.92), 2.4 + 1.6 * Math.sin(a)]);
    }
    return [[s * 3.2, 0], ...pts];
  };
  for (let x = L.x0; x <= L.x1 + 0.01; x += 4) {
    for (const s of [-1, 1]) {
      const c = new T.CatmullRomCurve3(archPts(s).map(([y, z]) => V(x, 0.2 + y, z)));
      add(new T.Mesh(new T.TubeGeometry(c, 30, 0.024, 8), M.gi));
    }
  }
  const prof = [...archPts(-1).reverse(), ...archPts(1)];
  const fp = [], fi = [];
  prof.forEach(([y, z]) => { fp.push(L.x0 - 0.02, 0.2 + y, z, L.x1 + 0.02, 0.2 + y, z); });
  for (let i = 0; i < prof.length - 1; i++) { const k = i * 2; fi.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  const filmG = new T.BufferGeometry();
  filmG.setAttribute('position', new T.Float32BufferAttribute(fp, 3));
  filmG.setIndex(fi); filmG.computeVertexNormals();
  const film = new T.Mesh(filmG, M.film);
  zup.add(film);

  // ---------------- the robot + camera boom + air nozzle ----------------
  let robot = null;
  const src = GH.A.comps.get('scout_robot')?.root;
  const robotG = new T.Group();
  zup.add(robotG);
  if (src) {
    robot = src.clone(true);
    const railPiece = GH.A.comps.get('scout_robot').parts.find((p) => p.name === 'pipe_rails')?.obj;
    if (railPiece) { const o = robot.getObjectByName(railPiece.name); if (o) o.visible = false; }
    robot.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    robot.position.set(0, 0, 0);
    const w = new T.Group(); w.rotation.x = Math.PI / 2; w.add(robot);
    robotG.add(w);
  }
  robotG.position.set(L.robotX, L.aisle, 0.1 + 0.0255);
  const boom = new T.Group();
  robotG.add(boom);
  const alu = new T.MeshStandardMaterial({ color: 0xd4d8dc, metalness: 0.8, roughness: 0.3 });
  const post = new T.Mesh(new T.BoxGeometry(0.03, 0.03, 0.9), alu); post.position.set(0, 0.0, 0.85 + 0.45); boom.add(post);
  const armLen = L.bedB - L.aisle;
  const arm = new T.Mesh(new T.BoxGeometry(0.03, 1, 0.03), alu); boom.add(arm);
  const head = new T.Group(); boom.add(head);
  const camBox = new T.Mesh(new T.BoxGeometry(0.07, 0.05, 0.06), new T.MeshStandardMaterial({ color: 0x1d2024, roughness: 0.5 }));
  head.add(camBox);
  const lens = new T.Mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 20), new T.MeshStandardMaterial({ color: 0x050505, roughness: 0.1, metalness: 0.5 }));
  lens.rotation.x = Math.PI / 2; lens.position.z = -0.035; head.add(lens);
  const nozzle = new T.Mesh(new T.CylinderGeometry(0.006, 0.01, 0.06, 12), new T.MeshStandardMaterial({ color: 0xe23b2e, roughness: 0.4 }));
  nozzle.rotation.x = Math.PI / 2; nozzle.position.set(0.06, 0, -0.03); head.add(nozzle);
  for (const o of [post, arm, camBox, nozzle]) o.castShadow = true;
  // air puff particles
  const NP = 220;
  const puffG = new T.BufferGeometry();
  puffG.setAttribute('position', new T.Float32BufferAttribute(new Float32Array(NP * 3), 3));
  const puffPts = new T.Points(puffG, new T.PointsMaterial({ color: 0xffffff, size: 0.012, transparent: true, opacity: 0.0, depthWrite: false }));
  zup.add(puffPts);
  const puffSeed = Array.from({ length: NP }, () => [R(), R(), R()]);

  // thick lines (WebGL lines are 1 px): every segment pair becomes a thin cylinder, merged
  const tubeLines = (pts, r) => {
    const gs = [];
    for (let i = 0; i < pts.length; i += 2) {
      const a = pts[i], b = pts[i + 1], d = b.clone().sub(a), l = d.length();
      if (l < 1e-6) continue;
      const g = new T.CylinderGeometry(r, r, l, 5, 1, true);
      g.applyMatrix4(new T.Matrix4().compose(a.clone().add(b).multiplyScalar(0.5), new T.Quaternion().setFromUnitVectors(V(0, 1, 0), d.normalize()), V(1, 1, 1)));
      gs.push(g);
    }
    return mergeGeometries(gs);
  };
  // ---------------- the views: 5 heights x 2 sides, and the next-best view ----------------
  const views = new T.Group(); zup.add(views);
  const frust = (eye, look, col, fovH = 0.5, fovV = 0.32, d = 0.55) => {
    const f = look.clone().sub(eye).normalize();
    const up = Math.abs(f.z) > 0.9 ? V(1, 0, 0) : V(0, 0, 1);
    const r = new T.Vector3().crossVectors(f, up).normalize(), u = new T.Vector3().crossVectors(r, f).normalize();
    const c = (sx, sy) => eye.clone().addScaledVector(f, d).addScaledVector(r, sx * Math.tan(fovH) * d).addScaledVector(u, sy * Math.tan(fovV) * d);
    const k = [c(-1, -1), c(1, -1), c(1, 1), c(-1, 1)];
    const pts = [eye, k[0], eye, k[1], eye, k[2], eye, k[3], k[0], k[1], k[1], k[2], k[2], k[3], k[3], k[0]];
    return new T.Mesh(tubeLines(pts, 0.0035), new T.MeshBasicMaterial({ color: col, transparent: true, opacity: 0, toneMapped: false }));
  };
  const VZ = [0.45, 0.75, 1.05, 1.35, 1.65];
  const viewList = [];
  VZ.forEach((z, i) => {
    const eye = V(L.robotX, L.aisle - 0.22, z);
    const fr = frust(eye, V(L.robotX, L.bedA, z), 0x45c6e6);
    views.add(fr); viewList.push(fr);
  });
  const fz = TF.c.z;
  const nbvA = V(L.robotX, L.aisle - 0.22, fz + 0.05), nbvB = V(TF.c.x + 0.32, L.aisle - 0.26, fz + 0.18);
  let nbvFr = null;

  // ---------------- 3D point cloud of the plants near the robot ----------------
  const cloudPts = [], cloudCol = [], newPts = [];
  const leafPos = leafA.attributes.position;
  const tmp = new T.Vector3();
  leavesA.forEach(([m]) => {
    tmp.setFromMatrixPosition(m);
    if (Math.abs(tmp.x - L.robotX) > 1.6) return;
    for (let i = 0; i < leafPos.count; i += 3) {
      tmp.fromBufferAttribute(leafPos, i).applyMatrix4(m);
      cloudPts.push(tmp.x, tmp.y, tmp.z); cloudCol.push(0.35, 0.85, 0.45);
    }
  });
  plantsA.forEach((p) => {
    if (Math.abs(p.x - L.robotX) > 1.6) return;
    for (let i = 0; i < 160; i++) {
      const u = R() * Math.PI * 2, v = Math.acos(2 * R() - 1);
      const s = V(Math.sin(v) * Math.cos(u), Math.sin(v) * Math.sin(u), Math.cos(v)).multiplyScalar(p.fruit.r).add(p.fruit.c);
      cloudPts.push(s.x, s.y, s.z); cloudCol.push(1.0, 0.75, 0.3);
    }
    for (let z = L.bedTop; z < L.bedTop + p.H; z += 0.02) { cloudPts.push(p.x, p.y, z); cloudCol.push(0.5, 0.95, 0.4); }
  });
  // "today": a new fruit set on the plant next to the target (a small one), shown only in the new scan
  const NF = plantsA.find((p) => p !== target && Math.abs(p.x - target.x) < 0.5 && p.y === target.y) || plantsA[0];
  const nfc = V(NF.x + 0.04, NF.y + 0.05, L.bedTop + 1.35), nfr = 0.025;
  for (let i = 0; i < 90; i++) {
    const u = R() * Math.PI * 2, v = Math.acos(2 * R() - 1);
    const s = V(Math.sin(v) * Math.cos(u), Math.sin(v) * Math.sin(u), Math.cos(v)).multiplyScalar(nfr).add(nfc);
    newPts.push(s.x, s.y, s.z);
  }
  const cloudG = new T.BufferGeometry();
  cloudG.setAttribute('position', new T.Float32BufferAttribute(cloudPts, 3));
  cloudG.setAttribute('color', new T.Float32BufferAttribute(cloudCol, 3));
  const cloud = new T.Points(cloudG, new T.PointsMaterial({ size: 0.013, vertexColors: true, transparent: true, opacity: 0, depthWrite: false, toneMapped: false }));
  zup.add(cloud);
  const newCloud = new T.Points(new T.BufferGeometry().setAttribute('position', new T.Float32BufferAttribute(newPts, 3)),
    new T.PointsMaterial({ size: 0.02, color: 0xff3b2f, transparent: true, opacity: 0, depthWrite: false, toneMapped: false }));
  zup.add(newCloud);
  // the real new fruit (small, green) on that plant
  const newFruit = add(new T.Mesh(sphere, new T.MeshStandardMaterial({ color: 0x6f9a3c, roughness: 0.6 })));
  newFruit.position.copy(nfc); newFruit.scale.setScalar(nfr);

  // ---------------- shape completion: a dashed sphere round the half-hidden melon ----------------
  const ring = (axis, n = 64) => { const p = []; for (let i = 0; i < n; i++) { if (i % 2) continue; const a0 = (i / n) * Math.PI * 2, a1 = ((i + 1) / n) * Math.PI * 2; const pt = (a) => axis === 'z' ? V(Math.cos(a), Math.sin(a), 0) : axis === 'x' ? V(0, Math.cos(a), Math.sin(a)) : V(Math.cos(a), 0, Math.sin(a)); p.push(pt(a0), pt(a1)); } return p; };
  const compPts = [...ring('z'), ...ring('x'), ...ring('y')];
  const comp = new T.Mesh(tubeLines(compPts, 0.022), new T.MeshBasicMaterial({ color: 0xffc34d, transparent: true, opacity: 0, toneMapped: false }));
  comp.position.copy(TF.c);
  zup.add(comp);

  // ---------------- knobs ----------------
  const K = { arm: 0, puff: 0, views: 0, nbv: 0, cloud: 0, newfruit: 0, complete: 0, plants: 1 };
  const tweens = new Map();
  let dirty = true, puffT = 0;
  const api = { group: root, zup, K, LAYOUT: L, target: TF, water: WT, robotG, head, nbvA, nbvB, plantsA,
    set(k, v) { tweens.delete(k); K[k] = v; dirty = true; },
    to(k, v, dur = 0.5, from) { if (from !== undefined) K[k] = from; tweens.set(k, { a: K[k], b: v, t: 0, dur: Math.max(0.001, dur) }); },
    setAll(o) { for (const [k, v] of Object.entries(o)) api.set(k, v); } };

  function apply(dt) {
    // boom: rises and reaches over bed B
    const a = ease(K.arm);
    boom.visible = K.arm > 0;
    const reach = armLen * a;
    arm.scale.y = Math.max(0.001, reach + 0.02);
    arm.position.set(0, reach / 2, 1.3);
    head.position.set(0, reach, 1.24 - 0.35 * a);
    // cover leaves lift with the puff
    const p = ease(K.puff);
    cover.forEach((c, i) => {
      const lift = p * (0.9 + 0.25 * i);
      const pos = c.pos.clone().add(V(Math.cos(c.yaw) * -0.03 * p, Math.sin(c.yaw) * -0.03 * p, 0.05 * p));
      leafIMB.setMatrixAt(coverBase + i, leafM(pos, c.yaw, 0.15 + lift, 0.0, c.size));
    });
    leafIMB.instanceMatrix.needsUpdate = true;
    // puff particles: from the nozzle down to the fruit
    puffPts.material.opacity = 0.55 * Math.min(1, K.puff * 3) * (K.puff < 0.98 ? 1 : 0.4);
    if (K.puff > 0) {
      puffT += dt;
      const n0 = V(L.robotX + 0.06, L.aisle + reach, 1.24 - 0.35 * a - 0.06 + 0.1255);
      const arr = puffG.attributes.position.array;
      puffSeed.forEach(([s0, s1, s2], i) => {
        const u = (s0 + puffT * 1.6) % 1;
        const tgt = WT.c.clone().add(V((s1 - 0.5) * 0.25 * u, (s2 - 0.5) * 0.25 * u, 0.12));
        const pt = n0.clone().lerp(tgt, u);
        arr[i * 3] = pt.x; arr[i * 3 + 1] = pt.y; arr[i * 3 + 2] = pt.z;
      });
      puffG.attributes.position.needsUpdate = true;
    }
    // the 10 views
    viewList.forEach((v, i) => { v.material.opacity = 0.9 * clamp01(K.views * 6 - i * 1.0); });
    if (K.nbv > 0 && !nbvFr) { nbvFr = frust(nbvA, TF.c, 0x3ddc84, 0.3, 0.2, 0.4); views.add(nbvFr); }
    if (nbvFr) {
      const t = ease(K.nbv);
      const eye = nbvA.clone().lerp(nbvB, t);
      views.remove(nbvFr); nbvFr.geometry.dispose();
      nbvFr = frust(eye, TF.c, t > 0.95 ? 0x3ddc84 : 0xffc34d, 0.3, 0.2, eye.distanceTo(TF.c) * 0.95);
      nbvFr.material.opacity = Math.min(1, K.nbv * 4);
      views.add(nbvFr);
    }
    // point cloud
    cloud.material.opacity = 0.95 * K.cloud;
    newCloud.material.opacity = K.newfruit;
    newFruit.visible = K.newfruit > 0;
    const plantsOp = 1 - 0.9 * K.cloud;
    for (const m of [M.leaf, M.stem, M.melon]) { m.transparent = plantsOp < 1; m.opacity = plantsOp; m.depthWrite = plantsOp > 0.5; }
    netLines.material.opacity = 0.85 * plantsOp;
    // completion
    comp.material.opacity = K.complete;
    comp.scale.setScalar(TF.r * (0.6 + 0.4 * ease(K.complete)) * 1.02);
    GH.dirtyShadows?.();
  }

  const hidden = [];
  const world = GH.world;
  const shadow0 = { ...world.sun.shadow.camera };
  api.show = (on) => {
    if (on === root.visible) return;
    if (on) {
      const keep = new Set([root, world.sky, world.sun, world.sun.target, world.hemi, world.moon, world.backdrop]);
      for (const o of GH.scene.children) if (!keep.has(o) && o.visible && !o.isLight) { hidden.push(o); o.visible = false; }
      const sc = world.sun.shadow.camera;
      Object.assign(sc, { left: -9, right: 9, top: 9, bottom: -9, far: 120 });
      sc.updateProjectionMatrix();
      world.sun.target.position.copy(GH.B(6, 0, 0));
    } else {
      hidden.splice(0).forEach((o) => { o.visible = true; });
      const sc = world.sun.shadow.camera;
      Object.assign(sc, { left: shadow0.left, right: shadow0.right, top: shadow0.top, bottom: shadow0.bottom, far: shadow0.far });
      sc.updateProjectionMatrix();
      world.sun.target.position.set(4.5, 0, 0);
    }
    root.visible = on;
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
    if (dirty || K.puff > 0) { apply(dt); dirty = false; }
  };
  { const u = GH.farm4.update.bind(GH.farm4); GH.farm4.update = (dt, ct) => { u(dt, ct); api.update(dt); }; }
  const vp = new T.Vector3();
  const proj = (p) => { vp.copy(p); zup.localToWorld(vp); vp.project(GH.camera); return [+((vp.x + 1) / 2).toFixed(4), +((1 - vp.y) / 2).toFixed(4), +vp.z.toFixed(4)]; };
  api.readout = () => root.visible ? {
    target: proj(TF.c), water: proj(WT.c), head: proj(V(L.robotX, L.aisle + armLen * ease(K.arm), 1.2)), robot: proj(V(L.robotX, L.aisle, 0.9)),
    tag: proj(V(target.x, target.y + 0.006, L.bedTop + 0.42)), newfruit: proj(nfc), bag: proj(plantsA[3].fruit.c),
    r: +TF.r.toFixed(4), k: { puff: +K.puff.toFixed(3), views: +K.views.toFixed(3), nbv: +K.nbv.toFixed(3), cloud: +K.cloud.toFixed(3), complete: +K.complete.toFixed(3) } } : null;
  apply(0);
  return api;
}
