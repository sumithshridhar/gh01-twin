// A one-hectare Dutch-style glasshouse with pipe rails, for explaining how pipe-rail robots work at scale (14 Oct 2026).
// Not part of GH-01: a stand-in for "a big commercial greenhouse", built on demand for videos and hidden otherwise.
//
//   const BF = await import('./js/bigfarm.js'); GH.bigFarm = BF.build(GH); GH.bigFarm.show(true);
//
// Layout (Blender coordinates, metres): the concrete main path runs along y at x -3…0; 76 aisles every 1.6 m (y -60…60),
// each with two 51 mm heating pipes 0.55 m apart from x 0.2 to 100; a high-wire tomato row between neighbouring aisles;
// a Venlo roof (gutters every 8 m at 6 m, a ridge every 4 m) on columns every 4.5 m. Numbers follow common Dutch practice:
// 51 mm pipes, 42-60 cm c-c, supports every 1-2 m, ~70-80 rails per hectare.
import { foliageMaterial } from './world.js';

export const LAYOUT = { pathX: [-3, 0], railX: [0.2, 100], aisleY0: -60, pitch: 1.6, aisles: 76, gauge: 0.55, pipeR: 0.0255, railZ: 0.1,
  gutterZ: 6.0, ridgeZ: 6.8, span: 8.0, bay: 4.5 };

export function build(GH) {
  const T = GH.THREE, B = GH.B, L = LAYOUT;
  const g = new T.Group();
  g.name = 'bigfarm';
  g.visible = false;
  const V3 = T.Vector3, M4 = T.Matrix4, Q = T.Quaternion;
  const aisleY = (k) => L.aisleY0 + L.pitch * k;
  const mat = {
    pipe: new T.MeshStandardMaterial({ color: 0xc9ced3, metalness: 0.75, roughness: 0.32 }),
    hot: new T.MeshStandardMaterial({ color: 0xff7a2a, emissive: 0xff5a10, emissiveIntensity: 0.0, metalness: 0.5, roughness: 0.4 }),
    support: new T.MeshStandardMaterial({ color: 0x8d949a, metalness: 0.6, roughness: 0.5 }),
    concrete: new T.MeshStandardMaterial({ color: 0x8e8a83, roughness: 1.0 }),
    cover: new T.MeshStandardMaterial({ color: 0xd9dcd6, roughness: 0.95 }),
    gutter: new T.MeshStandardMaterial({ color: 0xe8ebee, metalness: 0.4, roughness: 0.45 }),
    steel: new T.MeshStandardMaterial({ color: 0xdfe3e6, metalness: 0.7, roughness: 0.35 }),
    glass: new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, metalness: 0, transmission: 0, transparent: true, opacity: 0.12, side: T.DoubleSide, depthWrite: false }),
    slab: new T.MeshStandardMaterial({ color: 0xf4f4f0, roughness: 0.8 }),
    leaf: foliageMaterial(0x6aa64d, { sparse: 0.55, lump: 0.25, scale: 1.8, holes: 0.26 }),
  };
  // a box in Blender coords: centre (x, y, z), size (sx, sy, sz)
  const boxMat = (x, y, z, sx, sy, sz) => new M4().compose(B(x, y, z), new Q(), new V3(sx, sz, sy));
  const inst = (geo, m, mats, cast = true, recv = true) => {
    const im = new T.InstancedMesh(geo, m, mats.length);
    mats.forEach((mm, i) => im.setMatrixAt(i, mm));
    im.castShadow = cast; im.receiveShadow = recv;
    im.frustumCulled = false;
    g.add(im);
    return im;
  };
  const unitBox = new T.BoxGeometry(1, 1, 1);
  const len = L.railX[1] - L.railX[0], xm = (L.railX[0] + L.railX[1]) / 2;
  // floors: white ground cover in the house, concrete main path
  inst(unitBox, mat.cover, [boxMat(xm, 0, -0.005, len + 0.6, 124, 0.01)], false);
  inst(unitBox, mat.concrete, [boxMat(-1.5, 0, 0.02, 3.0, 124, 0.04)], false);
  // pipe rails: two pipes per aisle; at the path end each pipe turns down into the floor (to the header under the path)
  const pipeGeo = new T.CylinderGeometry(L.pipeR, L.pipeR, 1, 14, 1);
  const pipeM = [], riseM = [], supM = [];
  const rotX = new Q().setFromAxisAngle(new V3(0, 0, 1), Math.PI / 2);      // cylinder (three Y) -> along Blender x
  for (let k = 0; k < L.aisles; k++) {
    const ay = aisleY(k);
    for (const sy of [-1, 1]) {
      const y = ay + sy * L.gauge / 2;
      pipeM.push(new M4().compose(B(xm, y, L.railZ), rotX, new V3(1, len, 1)));
      riseM.push(new M4().compose(B(L.railX[0], y, L.railZ / 2), new Q(), new V3(1, L.railZ, 1)));
      for (let x = L.railX[0] + 1.2; x < L.railX[1]; x += 1.5) supM.push(boxMat(x, y, L.railZ / 2 - 0.01, 0.05, 0.07, L.railZ - 0.02));
    }
  }
  const pipes = inst(pipeGeo, mat.pipe, pipeM);
  const risers = inst(pipeGeo, mat.pipe, riseM);
  inst(unitBox, mat.support, supM, false);
  // crop rows between aisles: hanging gutter + slab line, then the plants (a leafy wall, real plant models near the path)
  const rowY = (k) => aisleY(k) + L.pitch / 2;
  const gutM = [], slabM = [], hedgeM = [];
  const NEAR = 7.0;                                  // real plant models for the first 7 m of every row
  for (let k = -1; k < L.aisles; k++) {
    const y = rowY(k);
    gutM.push(boxMat(xm, y, 0.72, len - 0.4, 0.22, 0.08));
    slabM.push(boxMat(xm, y, 0.8, len - 0.6, 0.18, 0.08));
    hedgeM.push(boxMat((L.railX[0] + NEAR + L.railX[1]) / 2, y, 2.3, len - NEAR - 0.6, 0.55, 3.0));
  }
  inst(unitBox, mat.gutter, gutM);
  inst(unitBox, mat.slab, slabM);
  const hedge = inst(new T.BoxGeometry(1, 1, 1, 60, 8, 2), mat.leaf, hedgeM);
  // real plant models near the path: cloned from the twin's plants #001-#006 (their instanced pieces, re-placed)
  const tmpl = ['plant_001', 'plant_002', 'plant_004', 'plant_005', 'plant_007', 'plant_008']
    .map((id) => GH.plantSlots?.get(id)).filter(Boolean);
  if (tmpl.length) {
    const byIm = new Map();
    const spots = [];
    // a double row per gutter (high-wire tomato), staggered
    for (let k = -1; k < L.aisles; k++) for (let x = L.railX[0] + 0.45; x < L.railX[0] + NEAR + 0.3; x += 0.33) { spots.push([x, rowY(k) - 0.11]); spots.push([x + 0.165, rowY(k) + 0.11]); }
    spots.forEach(([x, y], n) => {
      const slots = tmpl[n % tmpl.length];
      const yaw = ((n * 47) % 360) * Math.PI / 180;
      const place = new M4().compose(B(x, y, 0.78), new Q().setFromAxisAngle(new V3(0, 1, 0), yaw), new V3(1, 1.25, 1));
      for (const s of slots) {
        const rel = new M4().makeTranslation(-s.pivot.x, -s.pivot.y, -s.pivot.z).multiply(s.mat);
        const key = s.im.uuid;
        if (!byIm.has(key)) byIm.set(key, { im: s.im, mats: [] });
        byIm.get(key).mats.push(place.clone().multiply(rel));
      }
    });
    for (const { im, mats } of byIm.values()) inst(im.geometry, im.material, mats);
  }
  // Venlo roof: gutters every 8 m (y) on columns every 4.5 m (x), a ridge every 4 m, glass panes, trusses
  const ys = [];
  for (let y = -62; y <= 62.01; y += L.span) ys.push(y);
  const colM = [], gutterM = [], trussM = [], ridgeM = [];
  for (const y of ys) {
    gutterM.push(boxMat(xm - 1.5, y, L.gutterZ, len + 3.6, 0.22, 0.16));
    for (let x = -2.5; x <= L.railX[1] + 0.1; x += L.bay) colM.push(boxMat(x, y, L.gutterZ / 2, 0.1, 0.1, L.gutterZ));
  }
  for (let x = -2.5; x <= L.railX[1] + 0.1; x += L.bay) trussM.push(boxMat(x, 0, L.gutterZ - 0.35, 0.06, 124, 0.5));
  const paneM = [];
  for (let y = -62; y < 62; y += L.span / 2) {
    ridgeM.push(boxMat(xm - 1.5, y + L.span / 4, L.ridgeZ, len + 3.6, 0.06, 0.06));
    const run = L.span / 4, rise = L.ridgeZ - L.gutterZ, a = Math.atan2(rise, run), w = Math.hypot(run, rise);
    for (const sgn of [1, -1]) {
      const cy = y + L.span / 4 - sgn * run / 2;
      paneM.push(new M4().compose(B(xm - 1.5, cy, (L.gutterZ + L.ridgeZ) / 2),
        new Q().setFromAxisAngle(new V3(1, 0, 0), sgn * a), new V3(len + 3.6, 0.01, w)));
    }
  }
  inst(unitBox, mat.steel, colM);
  inst(unitBox, mat.gutter, gutterM);
  inst(unitBox, mat.steel, trussM);
  inst(unitBox, mat.steel, ridgeM, false);
  const panes = inst(unitBox, mat.glass, paneM, false, false);
  // the front wall (glass) behind the main path
  inst(unitBox, mat.glass, [boxMat(-3.05, 0, L.gutterZ / 2, 0.02, 124, L.gutterZ)], false, false);

  // a pipe-rail robot: a copy of GH-01's scout robot, on the pipes of one aisle
  let robot = null;
  const src = GH.A.comps.get('scout_robot')?.root;
  if (src) {
    robot = src.clone(true);
    const railPiece = GH.A.comps.get('scout_robot').parts.find((p) => p.name === 'pipe_rails')?.obj;  // its display rail
    if (railPiece) { const o = robot.getObjectByName(railPiece.name); if (o) o.visible = false; }
    robot.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    robot.visible = true;
    g.add(robot);
  }

  GH.scene.add(g);
  const hidden = [];
  const world = GH.world;
  const shadow0 = { ...world.sun.shadow.camera };
  const api = {
    group: g, layout: L, pipes, risers, robot, hedge, panes, aisleY, rowY,
    roof(on) { panes.visible = on; },
    /** put the robot at x along aisle k (heading +x) */
    placeRobot(k, x, z = L.railZ + L.pipeR) {
      if (!robot) return;
      robot.position.copy(B(x, aisleY(k), z));
    },
    /** hot-water view: the pipes glow (a thermal-camera style hint that they are the heating) */
    hot(on, k = 1) { pipes.material = risers.material = on ? mat.hot : mat.pipe; mat.hot.emissiveIntensity = on ? 1.6 * k : 0; },
    show(on) {
      if (on === g.visible) return;
      if (on) {
        const keep = new Set([g, world.sky, world.sun, world.sun.target, world.hemi, world.moon, world.backdrop]);
        for (const o of GH.scene.children) if (!keep.has(o) && o.visible && !o.isLight) { hidden.push(o); o.visible = false; }
        const sc = world.sun.shadow.camera;
        Object.assign(sc, { left: -70, right: 70, top: 70, bottom: -70, far: 260 });
        sc.updateProjectionMatrix();
        world.sun.target.position.copy(B(20, 0, 0));
      } else {
        hidden.splice(0).forEach((o) => { o.visible = true; });
        const sc = world.sun.shadow.camera;
        Object.assign(sc, { left: shadow0.left, right: shadow0.right, top: shadow0.top, bottom: shadow0.bottom, far: shadow0.far });
        sc.updateProjectionMatrix();
        world.sun.target.position.set(4.5, 0, 0);
      }
      g.visible = on;
      GH.dirtyShadows?.();
    },
  };
  return api;
}
