// The hydro box scene (14 Nov 2026): a home NFT rack on a concrete roof, made to run itself (Build Part 5).
// Built in Blender (blender/components/hydro_kit.py, blender/build_hydro_web.py) -> assets/hydro_kit.glb.json + hydro_kit.json.
// Four clickable components (rack, reservoir cut open, the box, the dosing pumps) open into their parts like GH-01's.
// Water visibly moves: drops fall from the return pipe into the tank. Built on demand from the scene menu (js/scenes.js).
//
//   const HY = await import('./js/hydro.js'); GH.hydro = await HY.build(GH); GH.hydro.show(true);
import { loadGLB } from './rover.js';

export async function build(GH) {
  const T = GH.THREE, B = GH.B, world = GH.world;
  const [kit, meta] = await Promise.all([loadGLB('assets/hydro_kit.glb.json'), fetch('assets/hydro_kit.json').then((r) => r.json())]);
  const root = new T.Group();
  root.name = 'hydro';
  root.visible = false;
  root.add(kit.scene);                             // already y-up in the twin's frame
  kit.scene.traverse((o) => {
    if (!o.isMesh) return;
    const nm = o.material?.name || '';
    o.castShadow = !/hydro_water|glass|silicone_clear/.test(nm);
    o.receiveShadow = true;
    if (/hydro_water|glass|silicone_clear/.test(nm)) { o.material.transparent = true; o.material.depthWrite = false; }
    if (o.name === 'hydro_roof' && GH.realMat) {   // the same photographed concrete as GH-01's yard
      GH.boxUV(o.geometry, 2.5);
      o.material = GH.realMat('concrete');
    }
  });
  GH.scene.add(root);
  GH.adopt?.(kit.scene, (c) => /^hydro_/.test(c.id || ''));

  // the return flow: a short stream of drops from the header into the tank
  const [ox, oy] = meta.origin;
  const drops = [];
  const dg = new T.SphereGeometry(0.008, 8, 6);
  const dm = new T.MeshStandardMaterial({ color: 0x9fd8ec, transparent: true, opacity: 0.85, roughness: 0.1 });
  for (let i = 0; i < 18; i++) {
    const d = new T.Mesh(dg, dm);
    d.userData.ph = i / 18;
    root.add(d);
    drops.push(d);
  }
  const top = 0.49, bot = 0.33;                    // pipe mouth -> water surface (m, Blender z)
  const api = { root, meta };
  api.update = (dt) => {
    if (!root.visible) return;
    const f = !!GH.sel;
    for (const d of drops) {
      d.visible = !f;
      d.userData.ph = (d.userData.ph + dt * 1.4) % 1;
      const u = d.userData.ph;
      d.position.copy(B(ox + 2.30 + 0.004 * Math.sin(u * 40), oy + 0.0, top - (top - bot) * u * u));
    }
  };
  const shadow0 = { ...world.sun.shadow.camera };
  const hidden = [];
  const keep = new Set([root, world.sky, world.sun, world.sun.target, world.hemi, world.moon]);   // no backdrop: a slice of roof, floating
  const hideRest = () => { for (const o of GH.scene.children) if (!keep.has(o) && o.visible && !o.isLight) { hidden.push(o); o.visible = false; } };
  // wow.js puts the village back for every scene but GH-01's; this one is a roof floating in the sky, so hide it again
  addEventListener('gh-scene', (e) => { if (e.detail === 'hydro' && root.visible) setTimeout(() => { hideRest(); GH.dirtyShadows?.(); }, 0); });
  api.show = (on) => {
    if (on === root.visible) return;
    if (on) {
      hideRest();
      const sc = world.sun.shadow.camera;
      Object.assign(sc, { left: -5, right: 5, top: 5, bottom: -5, far: 140 });
      sc.updateProjectionMatrix();
      world.sun.target.position.copy(B(ox + 1.5, oy, 0));
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
