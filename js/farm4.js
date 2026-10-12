// GH-01 farm v4 (11 Oct 2026), the parts of the scale-up that live in the browser: GH-02's ~2,500 tomato plants (light
// instanced proxies, so the page stays fast), the inspection drone's flight, rain and gusts, the windbreak swaying, and
// the drain-recycling UV lamp. The houses, skid, mast, dock and drone themselves are modelled in Blender (gh_farm.glb).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { B } from './world.js';

// GH-02 layout (Blender coords, see blender/components/scaleup.py)
const GH2 = { x0: 13, x1: 45, y0: -16, spans: 4, span: 8, pitch: 1.6, gutter: 4.5 };
const DOCK = [10.2, 14.2];

function leafTexture() {
  const c = document.createElement('canvas');
  c.width = 128; c.height = 512;
  const g = c.getContext('2d');
  const rnd = (i) => { const x = Math.sin(i * 12.9898) * 43758.5453; return x - Math.floor(x); };
  g.strokeStyle = '#3d5a1f'; g.lineWidth = 3;
  g.beginPath(); g.moveTo(64, 512); g.lineTo(64, 0); g.stroke();
  for (let i = 0; i < 260; i++) {                         // compound tomato leaves: many small leaflets
    const y = rnd(i) * 470 + 20, x = 64 + (rnd(i + 7) - 0.5) * 110;
    const s = 9 + rnd(i + 3) * 10, a = (rnd(i + 5) - 0.5) * 2.2;
    const l = 26 + rnd(i + 11) * 22;
    g.fillStyle = `hsl(${92 + rnd(i + 13) * 22}, ${42 + rnd(i + 17) * 20}%, ${20 + rnd(i + 19) * 16}%)`;
    g.save(); g.translate(x, y); g.rotate(a); g.beginPath(); g.ellipse(0, 0, s, s * 0.55, 0, 0, Math.PI * 2); g.fill(); g.restore();
    if (i % 3 === 0) { g.fillStyle = `hsl(100, 45%, ${l}%)`; g.beginPath(); g.ellipse(x + 3, y - 2, s * 0.5, s * 0.28, a, 0, Math.PI * 2); g.fill(); }
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

export class Farm4 {
  constructor(scene, A) {
    this.scene = scene;
    this.A = A;
    this.t = 0;
    this.ready = false;
  }

  setup(sim) {
    this.sim = sim;
    this.buildCrop();
    this.buildRain();
    const A = this.A;
    this.drone = A.comps.get('drone')?.root || null;
    if (this.drone) { this.drone.userData.p0 = this.drone.position.clone(); this.drone.userData.q0 = this.drone.quaternion.clone(); }
    this.belt = [];
    const wb = A.comps.get('windbreak');
    wb?.root.traverse((m) => { if (m.isMesh) this.belt.push(m); });
    this.swayU = { uTime: { value: 0 }, uAmp: { value: 0 } };
    const sway = this.swayU;
    this.belt.forEach((m) => {
      m.material = m.material.clone();
      m.material.onBeforeCompile = (sh) => {
        sh.uniforms.uTime = sway.uTime; sh.uniforms.uAmp = sway.uAmp;
        sh.vertexShader = 'uniform float uTime; uniform float uAmp;\n' + sh.vertexShader.replace('#include <begin_vertex>',
          `#include <begin_vertex>
          vec4 wp = modelMatrix * vec4(transformed, 1.0);
          float h = max(0.0, wp.y - 1.0);
          float w = sin(uTime * 2.1 + wp.x * 0.35 + wp.z * 0.21) * 0.6 + sin(uTime * 3.7 + wp.x) * 0.25;
          transformed.z += uAmp * h * h * 0.012 * (1.0 + w);
          transformed.x += uAmp * h * h * 0.004 * w;`);
      };
      m.material.needsUpdate = true;
    });
    this.uv = [];
    A.comps.get('drain_recycle')?.root.traverse((m) => {
      if (!m.isMesh) return;
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      mats.forEach((mm, i) => { if (/purple|led_blue/.test(mm.name)) { const c = mm.clone(); c.emissive = new THREE.Color(0x9b5cff); if (Array.isArray(m.material)) m.material[i] = c; else m.material = c; this.uv.push(c); } });
    });
    // the lamp-on indicator: a violet glow on the UV unit and its light on the skid (UV-C itself is invisible)
    const uvPart = A.comps.get('drain_recycle')?.parts.find((p) => p.name === 'uv_steriliser')?.obj;
    if (uvPart) {
      const wp = uvPart.getWorldPosition(new THREE.Vector3());
      this.uvLight = new THREE.PointLight(0x9b6bff, 0, 3.2, 1.6);
      this.uvLight.position.copy(wp).add(new THREE.Vector3(0, 0.12, 0));
      this.uvOrb = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 10), new THREE.MeshBasicMaterial({ color: 0xb48cff, transparent: true, opacity: 0 }));
      this.uvOrb.position.copy(wp).add(new THREE.Vector3(0, 0.07, 0));
      this.uvOrb.userData.fx = true;
      this.scene.add(this.uvLight, this.uvOrb);
    }
    // 12 Oct 2026: the mast's beacon (flashes for critical alarms while offline) and the router's status light
    const mast = A.comps.get('comms_mast');
    const bPart = mast?.parts.find((p) => p.name === 'beacon_siren')?.obj;
    if (bPart) {
      const bp = new THREE.Vector3();
      const box = new THREE.Box3().setFromObject(bPart); box.getCenter(bp);
      this.beaconLight = new THREE.PointLight(0xffa020, 0, 9, 1.4);
      this.beaconLight.position.copy(bp).add(new THREE.Vector3(0, 0.08, 0));
      this.beaconGlow = new THREE.Mesh(new THREE.SphereGeometry(0.075, 16, 10), new THREE.MeshBasicMaterial({ color: 0xffb030, transparent: true, opacity: 0 }));
      this.beaconGlow.position.copy(bp).add(new THREE.Vector3(0, 0.03, 0));
      this.beaconGlow.userData.fx = true;
      this.scene.add(this.beaconLight, this.beaconGlow);
    }
    this.routerLed = [];
    mast?.parts.find((p) => p.name === 'mast')?.obj.traverse((m) => {
      if (!m.isMesh) return;
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      mats.forEach((mm, i) => { if (/led_green/.test(mm.name)) { const c = mm.clone(); if (Array.isArray(m.material)) m.material[i] = c; else m.material = c; this.routerLed.push(c); } });
    });
    this.ready = true;
  }

  // ── GH-02 crop: double rows of high-wire tomatoes on every row, about 2,560 plants ──
  buildCrop() {
    const tex = leafTexture();
    const mat = new THREE.MeshStandardMaterial({ map: tex, alphaTest: 0.45, side: THREE.DoubleSide, roughness: 0.75 });
    const H = 2.35, Wd = 0.62;
    const planes = [0, Math.PI / 3, (2 * Math.PI) / 3].map((a) => { const p = new THREE.PlaneGeometry(Wd, H); p.translate(0, H / 2, 0); p.rotateY(a); return p; });
    const plant = mergeGeometries(planes);
    const truss = mergeGeometries([[0, 0, 0], [0.06, 0.03, 0.02], [-0.05, 0.02, 0.04], [0.01, -0.05, 0.03], [0.04, -0.04, -0.04]]
      .map(([x, y, z]) => { const s = new THREE.IcosahedronGeometry(0.048, 1); s.translate(x, y, z); return s; }));
    const fruitMat = new THREE.MeshStandardMaterial({ roughness: 0.32, color: 0xffffff });
    const pos = [];
    for (let s = 0; s < GH2.spans; s++) {
      const y0 = GH2.y0 + GH2.span * s;
      for (let r = 0; r < 5; r++) {
        const y = y0 + 0.8 + GH2.pitch * r;
        for (const dy of [-0.17, 0.17]) for (let x = GH2.x0 + 1.6 + (dy > 0 ? 0.22 : 0); x < GH2.x1 - 1.3; x += 0.45) pos.push([x, y + dy]);
      }
    }
    const n = pos.length;
    const pI = new THREE.InstancedMesh(plant, mat, n);
    const fI = new THREE.InstancedMesh(truss, fruitMat, n * 3);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), c = new THREE.Color();
    const rnd = (i) => { const x = Math.sin(i * 78.233) * 43758.5453; return x - Math.floor(x); };
    pos.forEach(([x, y], i) => {
      const sc = 0.9 + rnd(i) * 0.2;
      q.setFromEuler(e.set(0, rnd(i + 1) * Math.PI, 0));
      m.compose(B(x, y, 0.56), q, new THREE.Vector3(sc, 0.92 + rnd(i + 2) * 0.16, sc));
      pI.setMatrixAt(i, m);
      for (let k = 0; k < 3; k++) {                         // 3 trusses on the aisle side of the canopy, lowest ripest
        const z = 0.7 + k * 0.38 + rnd(i * 3 + k) * 0.1;
        const side = rnd(i + 31) > 0.5 ? 0.2 : -0.2;
        m.compose(B(x + (rnd(i + k) - 0.5) * 0.25, y + side, z), q, new THREE.Vector3(1, 1, 1));
        fI.setMatrixAt(i * 3 + k, m);
        const ripe = rnd(i * 7 + k) * (1 - 0.3 * k);
        fI.setColorAt(i * 3 + k, c.setHSL(ripe > 0.42 ? 0.005 : ripe > 0.25 ? 0.06 : 0.2, 0.9, ripe > 0.42 ? 0.4 : 0.38));
      }
    });
    pI.castShadow = false; pI.receiveShadow = true;
    fI.castShadow = false;
    pI.userData.fx = fI.userData.fx = true;
    this.scene.add(pI, fI);
    this.crop = { pI, fI, n };
  }

  // ── rain: streaks in a box that follows the camera target ──
  buildRain() {
    const N = 9000, g = new THREE.BufferGeometry();
    const p = new Float32Array(N * 6);
    this.rainSeed = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) { this.rainSeed[i * 3] = Math.random() * 90 - 45; this.rainSeed[i * 3 + 1] = Math.random() * 30; this.rainSeed[i * 3 + 2] = Math.random() * 90 - 45; }
    g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    this.rain = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0xf4f9ff, transparent: true, opacity: 0, depthWrite: false }));
    this.rain.frustumCulled = false;
    this.rain.userData.fx = true;
    this.scene.add(this.rain);
  }

  // ── drone path: take off, lawn-mower passes over GH-02's 4 spans, a pass over GH-01, land ──
  dronePath() {
    if (this._path) return this._path;
    const z = 16.5, [dx, dy] = DOCK;
    const P = [[dx, dy, 0.75], [dx, dy, z]];
    for (let s = 0; s < GH2.spans; s++) {
      const y = GH2.y0 + GH2.span * (s + 0.5);
      const a = s % 2 ? GH2.x1 + 1 : GH2.x0 - 1, b = s % 2 ? GH2.x0 - 1 : GH2.x1 + 1;
      P.push([a, y, z], [b, y, z]);
    }
    P.push([4.5, 0, 13.5], [-1, 0, 13.5], [dx, dy, z], [dx, dy, 0.75]);
    const pts = P.map(([x, y, zz]) => B(x, y, zz));
    const len = [0];
    for (let i = 1; i < pts.length; i++) len.push(len[i - 1] + pts[i].distanceTo(pts[i - 1]));
    this._path = { pts, len, total: len[len.length - 1] };
    return this._path;
  }

  update(dt, camTarget) {
    if (!this.ready) return;
    const sim = this.sim, o = sim.out || {};
    this.t += dt;
    // rain
    const rate = o.rain || 0, R = this.rain;
    R.material.opacity += ((rate > 0 ? Math.min(0.8, 0.25 + rate / 110) : 0) - R.material.opacity) * Math.min(1, dt * 2);
    R.visible = R.material.opacity > 0.01;
    const fog = this.scene.fog, k = R.material.opacity / 0.55;           // heavy rain closes in the horizon
    if (fog && !this.A.selected) { fog.near = 90 - 20 * k; fog.far = 520 - 160 * k; }
    if (R.visible) {
      const p = R.geometry.attributes.position.array, sd = this.rainSeed, N = sd.length / 3;
      const wind = (o.wind || 0) * 0.08, fall = 26 * dt, len = 0.95;
      const cx = camTarget.x, cy = camTarget.y, cz = camTarget.z;
      for (let i = 0; i < N; i++) {
        sd[i * 3 + 1] -= fall;
        if (sd[i * 3 + 1] < -2) sd[i * 3 + 1] += 30;
        const x = cx + sd[i * 3], y = cy + sd[i * 3 + 1] - 6, z = cz + sd[i * 3 + 2];
        p[i * 6] = x; p[i * 6 + 1] = y; p[i * 6 + 2] = z;
        p[i * 6 + 3] = x - wind * len; p[i * 6 + 4] = y + len; p[i * 6 + 5] = z;
      }
      R.geometry.attributes.position.needsUpdate = true;
    }
    // windbreak sway with the wind outside
    this.swayU.uTime.value = this.t;
    this.swayU.uAmp.value += (Math.min(1.6, (o.wind || 0) / 9) - this.swayU.uAmp.value) * Math.min(1, dt * 1.5);
    // UV lamp glows while drain water is being recycled
    const uvOn = sim.recycleOK?.() && (sim.w.uvI ?? 100) >= 60 ? 1 : 0;      // the lamp's own glow: off when it is dead
    this.uv.forEach((m) => { m.emissiveIntensity = uvOn * (2.4 + 0.3 * Math.sin(this.t * 9)); });
    this.uvK = (this.uvK ?? uvOn) + (uvOn - (this.uvK ?? uvOn)) * Math.min(1, dt * 8);
    if (this.uvLight) { this.uvLight.intensity = this.uvK * (2.2 + 0.25 * Math.sin(this.t * 11)); this.uvOrb.material.opacity = this.uvK * 0.9; }
    // comms: beacon flashes (2 Hz) while a critical alarm is out by SMS; router light red while offline
    const c = sim.comms;
    if (this.beaconLight && c) {
      const on = c.beacon ? (Math.sin(this.t * Math.PI * 4) > 0 ? 1 : 0.15) : 0;
      this.beaconLight.intensity = on * 6; this.beaconGlow.material.opacity = on * 0.95;
    }
    this.routerLed.forEach((m) => { if (m.emissive) { m.emissive.set(c && !c.ok ? 0xff2a1a : 0x2aff6a); m.emissiveIntensity = 3; } m.color?.set(c && !c.ok ? 0xff2a1a : 0x2aff6a); });
    // drone
    const d = sim.drone, D = this.drone;
    if (D && d) {
      if (d.phase === 'flying') {
        const u = Math.min(1, Math.max(0, (sim.t - d.t0) / d.dur));
        const P = this.dronePath(), sL = u * P.total;
        let i = 1;
        while (i < P.len.length - 1 && P.len[i] < sL) i++;
        const k = (sL - P.len[i - 1]) / Math.max(1e-6, P.len[i] - P.len[i - 1]);
        const pos = new THREE.Vector3().lerpVectors(P.pts[i - 1], P.pts[i], k);
        pos.y += Math.sin(this.t * 3.1) * 0.05;
        D.position.copy(D.parent ? D.parent.worldToLocal(pos.clone()) : pos);
        const dir = new THREE.Vector3().subVectors(P.pts[i], P.pts[i - 1]); dir.y = 0;
        if (dir.lengthSq() > 1e-4) { const yaw = Math.atan2(-dir.z, dir.x); D.quaternion.setFromEuler(new THREE.Euler(0, yaw, 0)); }
        this.onDrone?.(pos, dir);                                            // e.g. a chase camera (video recorder)
      } else if (D.userData.p0) { D.position.copy(D.userData.p0); D.quaternion.copy(D.userData.q0); }
    }
  }
}
