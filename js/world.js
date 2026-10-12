// Sky, sun, day/night lighting, ground and a simple farm backdrop.
import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';

// Blender (x, y, z-up) → three.js (x, y-up, z)
export const B = (x, y, z) => new THREE.Vector3(x, z, -y);
export const Bv = (a) => B(a[0], a[1], a[2]);

function noiseTexture(size, base, spread, grain, repeat) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const img = g.createImageData(size, size);
  const rnd = (i) => { const x = Math.sin(i * 12.9898) * 43758.5453; return x - Math.floor(x); };
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const i = (y * size + x) * 4;
    const n = rnd(x * 7.1 + y * 131.7) * grain + rnd(Math.floor(x / 6) * 3.3 + Math.floor(y / 6) * 17.9) * (1 - grain);
    for (let k = 0; k < 3; k++) img.data[i + k] = Math.max(0, Math.min(255, base[k] + (n - 0.5) * spread[k]));
    img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat, repeat);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

export class World {
  constructor(renderer, scene) {
    this.renderer = renderer;
    this.scene = scene;
    this.pmrem = new THREE.PMREMGenerator(renderer);
    // sky dome
    this.sky = new Sky();
    this.sky.scale.setScalar(4000);
    const u = this.sky.material.uniforms;
    u.turbidity.value = 6; u.rayleigh.value = 1.6; u.mieCoefficient.value = 0.004; u.mieDirectionalG.value = 0.82;
    scene.add(this.sky);
    this.skyScene = new THREE.Scene();
    this.skyForEnv = new Sky();
    this.skyForEnv.scale.setScalar(4000);
    this.skyScene.add(this.skyForEnv);
    // lights
    this.sun = new THREE.DirectionalLight(0xfff2e0, 3.0);
    this.sun.castShadow = true;
    const sc = this.sun.shadow.camera;
    sc.left = -11; sc.right = 11; sc.top = 11; sc.bottom = -11; sc.near = 1; sc.far = 80;
    const mobile = matchMedia('(max-width: 820px)').matches;
    this.sun.shadow.mapSize.set(mobile ? 2048 : 4096, mobile ? 2048 : 4096);
    this.sun.shadow.bias = -0.0002;
    this.sun.shadow.normalBias = 0.025;
    this.sun.target.position.set(4.5, 0, 0);
    scene.add(this.sun, this.sun.target);
    this.hemi = new THREE.HemisphereLight(0xcfe6ff, 0x5a5040, 0.6);
    scene.add(this.hemi);
    this.moon = new THREE.DirectionalLight(0x8fb0ff, 0.0);
    this.moon.position.set(-20, 30, -10);
    scene.add(this.moon);
    // ground + backdrop
    this.grass = noiseTexture(256, [86, 104, 58], [60, 70, 40], 0.55, 90);
    scene.fog = new THREE.Fog(0xbfd4e6, 90, 520);
    this.addBackdrop();
    this.envTime = -999;
  }

  groundMaterial() {
    return new THREE.MeshStandardMaterial({ map: this.grass, roughness: 0.95, metalness: 0, color: 0xffffff });
  }

  // 11 Oct 2026 (farm v4): the land round the farm, as it looks in Kolar / Chikkaballapur: a mulberry garden for silkworms
  // next door (Chikkaballapur is Karnataka's no. 2 silk district), a ragi field, a mango orchard, eucalyptus along the
  // village road, the 11 kV farm feeder on cement poles, granite boulders, a small village and rocky hills. Low-poly and
  // instanced so it costs little; nothing here casts shadows. Positions in Blender coords (x north, y west), see B().
  addBackdrop() {
    this.backdrop = new THREE.Group();
    this.scene.add(this.backdrop);
    const s = this.backdrop;
    const P = (x, y, z = 0) => new THREE.Vector3(x, z, -y);
    const rnd = (i) => { const x = Math.sin(i * 91.7) * 1e4; return x - Math.floor(x); };
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), v = new THREE.Vector3();
    const inst = (geo, mat, list) => {            // list of [pos Vector3, scale Vector3, yaw]
      const im = new THREE.InstancedMesh(geo, mat, list.length);
      list.forEach(([p, sc, yaw], i) => { q.setFromEuler(e.set(0, yaw || 0, 0)); m4.compose(p, q, sc); im.setMatrixAt(i, m4); });
      im.castShadow = false; im.receiveShadow = false;
      s.add(im);
      return im;
    };
    const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.95, flatShading: true, ...o });
    // ground patches: ragi field (south-east), mulberry soil (west), orchard floor (north), the village road + driveway
    const plane = (x0, x1, y0, y1, m, h = 0.03) => {
      const p = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, y1 - y0), m);
      p.rotation.x = -Math.PI / 2; p.position.copy(P((x0 + x1) / 2, (y0 + y1) / 2, h)); p.receiveShadow = false; s.add(p); return p;
    };
    const stripes = (a, b, n) => {
      const c = document.createElement('canvas'); c.width = 64; c.height = 512; const g = c.getContext('2d');
      for (let i = 0; i < n; i++) { g.fillStyle = i % 2 ? a : b; g.fillRect(0, (i * 512) / n, 64, 512 / n + 1); }
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
    };
    const ragiT = stripes('#9a8f45', '#7f8a3a', 32); ragiT.repeat.set(1, 6);
    plane(-12, 60, -95, -32, new THREE.MeshStandardMaterial({ map: ragiT, roughness: 1 }), 0.04);
    plane(-12, 60, 30, 75, mat(0x7a4a2c), 0.035);                       // mulberry garden soil (red)
    plane(-17, -12, -160, 160, mat(0x4a4744, { roughness: 0.9 }), 0.06);  // village road (tarmac), along y
    plane(-12, -3.6, 1.2, 3.4, mat(0x9a6a48), 0.05);                     // murram driveway to the farm gate
    // mulberry: rows of low bushes, 1.5 m apart (V1 mulberry, pruned to ~1.5 m)
    const mul = [];
    for (let y = 32; y <= 73; y += 1.5) for (let x = -10; x <= 58; x += 0.9) {
      const i = x * 13 + y * 7;
      mul.push([P(x + (rnd(i) - 0.5) * 0.2, y, 0.75), new THREE.Vector3(0.7 + rnd(i + 1) * 0.25, 0.75 + rnd(i + 2) * 0.3, 0.7), rnd(i + 3) * 3]);
    }
    inst(new THREE.IcosahedronGeometry(1, 0), mat(0x5d8f2e), mul);
    // ragi: a few darker clumps for texture
    const rg = [];
    for (let k = 0; k < 500; k++) rg.push([P(-10 + rnd(k) * 68, -34 - rnd(k + 9) * 60, 0.25), new THREE.Vector3(0.6, 0.35, 0.6), 0]);
    inst(new THREE.IcosahedronGeometry(1, 0), mat(0x8c8a3e), rg);
    // mango orchard north of the windbreak: 10 m grid, big dark domes
    const mt = [], mc = [];
    for (let x = 62; x <= 122; x += 10) for (let y = -38; y <= 42; y += 10) {
      const i = x * 3 + y, sc = 0.85 + rnd(i) * 0.35;
      mt.push([P(x + rnd(i + 1) * 2, y + rnd(i + 2) * 2, 1.0 * sc), new THREE.Vector3(sc, sc, sc), 0]);
      mc.push([P(x + rnd(i + 1) * 2, y + rnd(i + 2) * 2, 4.0 * sc), new THREE.Vector3(4.2 * sc, 3.2 * sc, 4.2 * sc), rnd(i) * 3]);
    }
    inst(new THREE.CylinderGeometry(0.25, 0.35, 2, 6), mat(0x4e3b2a), mt);
    inst(new THREE.IcosahedronGeometry(1, 1), mat(0x2f5a26), mc);
    // eucalyptus along the far side of the road: tall pale trunks, narrow sparse crowns
    const et = [], ec = [];
    for (let y = -150; y <= 150; y += 7) {
      const i = y + 400, h = 13 + rnd(i) * 7;
      et.push([P(-19.5 + rnd(i + 1), y, h / 2), new THREE.Vector3(1, h / 2, 1), 0]);
      ec.push([P(-19.5 + rnd(i + 1), y, h * 0.85), new THREE.Vector3(1.6, h * 0.22, 1.6), rnd(i + 2) * 3]);
    }
    inst(new THREE.CylinderGeometry(0.12, 0.2, 2, 6), mat(0xd9d2c4), et);
    inst(new THREE.IcosahedronGeometry(1, 0), mat(0x7d8f5a), ec);
    // 11 kV feeder on cement poles along the road, a DP transformer near the gate, and the service drop to the packhouse
    const poles = [];
    for (let y = -150; y <= 150; y += 40) poles.push(y);
    const pm = mat(0xb8b4ab), wm = new THREE.LineBasicMaterial({ color: 0x2b2b2b });
    poles.forEach((y) => {
      const p = new THREE.Mesh(new THREE.BoxGeometry(0.22, 9, 0.22), pm); p.position.copy(P(-11.5, y, 4.5)); s.add(p);
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, 1.8), mat(0x6b6b6b)); arm.position.copy(P(-11.5, y, 8.6)); s.add(arm);
    });
    for (const off of [-0.8, 0, 0.8]) {                       // 3 conductors with a little sag
      const pts = [];
      for (let k = 0; k < poles.length - 1; k++) for (let j = 0; j <= 8; j++) {
        const u = j / 8, y = poles[k] + (poles[k + 1] - poles[k]) * u;
        pts.push(P(-11.5 + off * 0.0, y, 8.75 - 0.7 * Math.sin(Math.PI * u)).add(new THREE.Vector3(0, 0, off)));
      }
      s.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), wm));
    }
    const tr = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.3, 0.8), mat(0x6f7d6a)); tr.position.copy(P(-11.0, 6, 4.2)); s.add(tr);
    for (const dy of [5, 7]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.2, 8, 0.2), pm); p.position.copy(P(-11.5, dy, 4)); s.add(p); }
    s.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([P(-11.0, 6, 5.5), P(-4, 7.5, 4.6), P(1.5, 8.5, 3.0)]), wm));
    // granite boulders: clusters in the fields and on the hills (Kolar's landscape is full of them)
    const bl = [];
    const cluster = (cx, cy, n, r, big) => { for (let k = 0; k < n; k++) { const i = cx * 7 + cy * 3 + k; const sc = big * (0.4 + rnd(i) * 0.9); bl.push([P(cx + (rnd(i + 1) - 0.5) * r, cy + (rnd(i + 2) - 0.5) * r, sc * 0.35), new THREE.Vector3(sc * (1 + rnd(i + 3) * 0.5), sc * 0.75, sc), rnd(i + 4) * 6]); } };
    cluster(-30, -60, 9, 10, 2.2); cluster(70, -70, 12, 14, 3.0); cluster(30, 95, 8, 10, 2.5); cluster(-45, 70, 10, 12, 2.0);
    cluster(130, 10, 14, 20, 4.0); cluster(-80, -20, 7, 10, 2.4); cluster(85, 60, 6, 8, 2.0);
    inst(new THREE.IcosahedronGeometry(1, 1), mat(0x9a948a), bl);
    // the village across the road: pastel walls, flat RCC roofs, a few tiled roofs, the overhead water tank
    const hw = [], hr = [], tiles = [];
    for (let k = 0; k < 22; k++) {
      const x = -32 - rnd(k) * 45, y = 25 + rnd(k + 5) * 70, wx = 5 + rnd(k + 2) * 4, wy = 6 + rnd(k + 3) * 4, h = 3 + rnd(k + 4) * 3.2;
      hw.push([P(x, y, h / 2), new THREE.Vector3(wx, h, wy), 0]);
      (k % 3 === 0 ? tiles : hr).push([P(x, y, h + 0.15), new THREE.Vector3(wx + 0.4, 0.3, wy + 0.4), 0]);
    }
    const walls = inst(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9 }), hw);
    const pal = [0xe9d8a6, 0xa8d5ba, 0xf2b5a0, 0xd8d8e8, 0xf5e6c8, 0x9fc5e8];
    hw.forEach((_, i) => walls.setColorAt(i, new THREE.Color(pal[i % pal.length])));
    inst(new THREE.BoxGeometry(1, 1, 1), mat(0xbdb7ad), hr);
    inst(new THREE.BoxGeometry(1, 1, 1), mat(0xa4532f), tiles);
    const tank = new THREE.Group();
    const col = new THREE.CylinderGeometry(0.25, 0.25, 12, 6);
    for (let k = 0; k < 4; k++) { const c = new THREE.Mesh(col, pm); c.position.set(Math.cos(k * 1.57) * 2.2, 6, Math.sin(k * 1.57) * 2.2); tank.add(c); }
    const tb = new THREE.Mesh(new THREE.CylinderGeometry(3.4, 2.4, 3.2, 10), mat(0xd7d0c2)); tb.position.y = 13.6; tank.add(tb);
    tank.position.copy(P(-62, 60)); s.add(tank);
    // a few neem / tamarind trees scattered beyond everything
    const tt = [], tc = [];
    for (let i = 0; i < 46; i++) {
      const a = (i / 46) * Math.PI * 2 + rnd(i) * 0.08, r = 105 + rnd(i + 3) * 40;
      const x = 20 + Math.cos(a) * r, y = Math.sin(a) * r, sc = 1.1 + rnd(i + 7) * 1.3;
      tt.push([P(x, y, 1.6 * sc), new THREE.Vector3(sc, sc * 1.6, sc), 0]);
      tc.push([P(x, y, 4.4 * sc), new THREE.Vector3(2.4 * sc, 1.9 * sc, 2.4 * sc), rnd(i) * 3]);
    }
    inst(new THREE.CylinderGeometry(0.15, 0.22, 2, 6), mat(0x5b4632), tt);
    inst(new THREE.IcosahedronGeometry(1, 1), mat(0x3f6b35), tc);
    // rocky hills on the horizon: granite domes with scrub, the Kolar skyline
    const rock = mat(0x8c8678), scrub = mat(0x6f7a52);
    for (let i = 0; i < 11; i++) {
      const a = (i / 11) * Math.PI * 2 + 0.3, R = 230 + rnd(i) * 70;
      const h = new THREE.Mesh(new THREE.SphereGeometry(45 + rnd(i) * 40, 14, 7, 0, Math.PI * 2, 0, Math.PI / 2), i % 3 ? scrub : rock);
      h.position.set(20 + Math.cos(a) * R, -14, Math.sin(a) * R);
      h.scale.y = 0.38 + rnd(i + 2) * 0.35;
      s.add(h);
      const top = -14 + h.geometry.parameters.radius * h.scale.y;     // boulder piles sit on the dome's crown
      for (let k = 0; k < 4; k++) {
        const r = 7 + rnd(i * 5 + k) * 8;
        const b = new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), rock);
        b.position.set(h.position.x + (rnd(i + k) - 0.5) * 30, top - r * 0.35, h.position.z + (rnd(i * 3 + k) - 0.5) * 30);
        b.scale.y = 0.7; s.add(b);
      }
    }
  }

  // minutes since midnight → sun direction. Site ~13°N (Bengaluru), late September.
  sunDir(minutes) {
    const h = minutes / 60;
    const dayFrac = (h - 6.1) / 12.1;
    const el = 76 * Math.sin(Math.PI * dayFrac) * (Math.PI / 180);
    const az = (90 + 180 * dayFrac) * (Math.PI / 180);   // from north (+x) toward east (+z)
    return new THREE.Vector3(Math.cos(el) * Math.cos(az), Math.sin(el), Math.cos(el) * Math.sin(az)).normalize();
  }

  setTime(minutes, cloud = 0) {
    const d = this.sunDir(minutes);
    const el = Math.asin(d.y);
    const day = THREE.MathUtils.clamp((el + 0.08) / 0.3, 0, 1);         // 0 night → 1 day
    const u = this.sky.material.uniforms;
    u.sunPosition.value.copy(d);
    u.rayleigh.value = 1.2 + (1 - day) * 1.5;
    u.turbidity.value = 5 + cloud * 8;
    this.sun.position.copy(this.sun.target.position).addScaledVector(d, 40);
    this.sun.intensity = Math.max(0, Math.sin(Math.max(el, 0))) ** 0.6 * 3.2 * (1 - 0.55 * cloud) * day;
    this.sun.color.setHSL(0.09, 0.6, 0.55 + 0.4 * Math.min(1, Math.max(el, 0) * 2));
    this.hemi.intensity = 0.12 + 0.6 * day;
    this.moon.intensity = (1 - day) * 0.35;
    this.renderer.toneMappingExposure = 0.42 + 0.18 * day + (1 - day) * 0.35;
    const fogC = new THREE.Color().setHSL(0.58, 0.35, 0.08 + 0.72 * day);
    this.scene.fog.color.copy(fogC);
    this.dayFactor = day;
    // refresh reflections every ~20 sim minutes
    if (Math.abs(minutes - this.envTime) > 20) {
      this.envTime = minutes;
      this.skyForEnv.material.uniforms.sunPosition.value.copy(d);
      this.skyForEnv.material.uniforms.rayleigh.value = u.rayleigh.value;
      this.skyForEnv.material.uniforms.turbidity.value = u.turbidity.value;
      if (this.envRT) this.envRT.dispose();
      this.envRT = this.pmrem.fromScene(this.skyScene, 0, 1, 5000);
      this.scene.environment = this.envRT.texture;
      this.scene.environmentIntensity = 0.25 + 0.75 * day;
    }
    return day;
  }
}
