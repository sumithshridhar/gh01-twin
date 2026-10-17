// The soil-bed polyhouse scene (17 Oct 2026): an 8 m x 12 m strawberry polyhouse with raised beds under silver mulch and
// drip lines, the R1 rover driving up and down a path, the wheel bath and mist arch at the door, and the Build Part 3
// watering kit on zone 1 (valve on the zone feed, box on the corner column, sensor in the bed). Built in Blender
// (blender/build_rover_web.py) -> assets/rover_house.glb.json + sb_plant.glb.json + rover_house.json. Not part of GH-01:
// built on demand from the scene menu (js/scenes.js).
//
//   const RV = await import('./js/rover.js'); GH.rover = await RV.build(GH); GH.rover.show(true);
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

async function loadGLB(url) {
  const { gz } = await (await fetch(url)).json();
  const bin = Uint8Array.from(atob(gz), (c) => c.charCodeAt(0));
  const glb = await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  return new GLTFLoader().parseAsync(glb, '');
}

export async function build(GH) {
  const T = GH.THREE, B = GH.B, world = GH.world;
  const [house, plant, meta] = await Promise.all([loadGLB('assets/rover_house.glb.json'), loadGLB('assets/sb_plant.glb.json'),
    fetch('assets/rover_house.json').then((r) => r.json())]);
  const root = new T.Group();
  root.name = 'roverhouse';
  root.visible = false;
  root.add(house.scene);                         // the glb is already y-up in the twin's (Blender -> three) frame
  house.scene.traverse((o) => {
    if (!o.isMesh) return;
    const film = /uv_film|net/.test(o.material?.name || '');
    o.castShadow = !film;
    o.receiveShadow = true;
    if (film) { o.material.transparent = true; o.material.depthWrite = false; o.material.side = T.DoubleSide; }
    if (/mulch_silver/.test(o.material?.name || '')) { o.material.metalness = 0.25; o.material.roughness = 0.5; }   // no bloom streaks on the bed shoulders
  });
  // strawberry plants: one instanced mesh per part of the plant, on every planting hole
  plant.scene.updateMatrixWorld(true);
  const holes = meta.holes;
  const m = new T.Matrix4(), q = new T.Quaternion(), s = new T.Vector3(), up = new T.Vector3(0, 1, 0);
  plant.scene.traverse((o) => {
    if (!o.isMesh) return;
    const im = new T.InstancedMesh(o.geometry, o.material, holes.length);
    holes.forEach(([x, y, z, rz, sc], i) => {
      q.setFromAxisAngle(up, rz);
      s.setScalar(sc);
      m.compose(B(x, y, z), q, s).multiply(o.matrixWorld);
      im.setMatrixAt(i, m);
    });
    im.castShadow = true;
    im.receiveShadow = true;
    root.add(im);
  });
  GH.scene.add(root);
  // the rover: its own root, driven along one path
  let rover = null;
  house.scene.traverse((o) => { if (o.userData?.gh_id === meta.rover) rover = o; });
  const pathY = meta.paths[1];
  const xa = meta.x0 + 0.6, xb = meta.x1 - 0.8;
  const drive = { x: xa, dir: 1, wait: 0 };
  const api = { root, meta, rover, paused: false };
  api.update = (dt) => {
    if (!root.visible || !rover || api.paused) return;
    if (drive.wait > 0) { drive.wait -= dt; return; }
    drive.x += drive.dir * 0.25 * dt;                 // 0.25 m/s: a photo of every plant, both sides
    if (drive.x > xb || drive.x < xa) { drive.x = Math.min(xb, Math.max(xa, drive.x)); drive.dir *= -1; drive.wait = 2.0; }
    rover.position.copy(B(drive.x, pathY, 0));
  };
  const shadow0 = { ...world.sun.shadow.camera };
  const hidden = [];
  api.show = (on) => {
    if (on === root.visible) return;
    if (on) {
      const keep = new Set([root, world.sky, world.sun, world.sun.target, world.hemi, world.moon, world.backdrop]);
      for (const o of GH.scene.children) if (!keep.has(o) && o.visible && !o.isLight) { hidden.push(o); o.visible = false; }
      const sc = world.sun.shadow.camera;
      Object.assign(sc, { left: -10, right: 10, top: 10, bottom: -10, far: 140 });
      sc.updateProjectionMatrix();
      world.sun.target.position.copy(B(6, 0, 0));
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
  { const u = GH.farm4.update.bind(GH.farm4); GH.farm4.update = (dt, ct) => { u(dt, ct); api.update(dt); }; }
  return api;
}
