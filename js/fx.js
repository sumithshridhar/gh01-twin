// Visual effects: explode burst, water flow in pipes, data links + pulses, fog, drips, airflow, scan cone, markers.
import * as THREE from 'three';
import { Bv } from './world.js';

const add = (s, o) => { s.add(o); return o; };

function dotTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const DOT = dotTexture();

// particle pool rendered as additive points
class Particles {
  constructor(scene, max, size, color, blending = THREE.AdditiveBlending) {
    this.max = max;
    this.pos = new Float32Array(max * 3);
    this.vel = new Float32Array(max * 3);
    this.life = new Float32Array(max);
    this.ttl = new Float32Array(max);
    this.col = new Float32Array(max * 3);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(this.col, 3));
    this.mat = new THREE.PointsMaterial({ size, map: DOT, vertexColors: true, transparent: true, depthWrite: false,
      blending, sizeAttenuation: true, opacity: 1 });
    this.pts = new THREE.Points(g, this.mat);
    this.pts.frustumCulled = false;
    this.pts.renderOrder = 5;
    scene.add(this.pts);
    this.i = 0;
    this.base = new THREE.Color(color);
    this.gravity = 0;
    this.drag = 0;
  }
  emit(p, v, ttl, color) {
    const i = this.i = (this.i + 1) % this.max;
    this.pos.set([p.x, p.y, p.z], i * 3);
    this.vel.set([v.x, v.y, v.z], i * 3);
    this.life[i] = ttl; this.ttl[i] = ttl;
    const c = color || this.base;
    this.col.set([c.r, c.g, c.b], i * 3);
  }
  update(dt) {
    for (let i = 0; i < this.max; i++) {
      if (this.life[i] <= 0) { this.pos[i * 3 + 1] = -999; continue; }
      this.life[i] -= dt;
      const k = i * 3;
      this.vel[k + 1] -= this.gravity * dt;
      const d = Math.exp(-this.drag * dt);
      this.vel[k] *= d; this.vel[k + 1] *= d; this.vel[k + 2] *= d;
      this.pos[k] += this.vel[k] * dt; this.pos[k + 1] += this.vel[k + 1] * dt; this.pos[k + 2] += this.vel[k + 2] * dt;
      const f = Math.max(0, this.life[i] / this.ttl[i]);
      this.col[k] *= 0.985 + 0.015 * f; this.col[k + 1] *= 0.985 + 0.015 * f; this.col[k + 2] *= 0.985 + 0.015 * f;
    }
    this.pts.geometry.attributes.position.needsUpdate = true;
    this.pts.geometry.attributes.color.needsUpdate = true;
  }
}

// a tube along a path with moving stripes (water / data)
function flowMaterial(color, speed, stripes) {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uOn: { value: 0 }, uColor: { value: new THREE.Color(color) },
      uSpeed: { value: speed }, uStripes: { value: stripes } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `uniform float uTime, uOn, uSpeed, uStripes; uniform vec3 uColor; varying vec2 vUv;
      void main(){ float s = fract(vUv.x * uStripes - uTime * uSpeed); float band = smoothstep(0.0,0.15,s) * (1.0 - smoothstep(0.45,0.7,s));
        float a = uOn * (0.18 + 0.82 * band); gl_FragColor = vec4(uColor * (0.6 + band), a); }`,
  });
}

export class FX {
  constructor(app) {
    this.app = app;
    const s = this.scene = app.scene;
    this.sparks = new Particles(s, 900, 0.07, 0xffe08a);
    this.sparks.drag = 2.2;
    this.fog = new Particles(s, 900, 0.35, 0xdfefff, THREE.NormalBlending);
    this.fog.mat.opacity = 0.35; this.fog.drag = 0.8;
    this.drops = new Particles(s, 600, 0.028, 0x9fe8ff);
    this.drops.gravity = 5;
    this.air = new Particles(s, 700, 0.09, 0xcfe8ff);
    this.air.mat.opacity = 0.5;
    this.puffs = new Particles(s, 300, 0.12, 0xfff3c0);
    this.puffs.drag = 3;
    this.flows = [];
    this.links = new Map();
    this.pulses = [];
    this.rings = [];
    this.markers = new Map();
    this.t = 0;
    this.netVisible = false;
    this.airOn = false;
    this.linkMatSense = new THREE.MeshBasicMaterial({ color: 0x45c6e6, transparent: true, opacity: 0.22, depthWrite: false, blending: THREE.AdditiveBlending });
    this.linkMatCmd = new THREE.MeshBasicMaterial({ color: 0xf2c230, transparent: true, opacity: 0.22, depthWrite: false, blending: THREE.AdditiveBlending });
    this.pulseGeo = new THREE.SphereGeometry(0.035, 12, 8);
    // robot scan cone
    const cone = new THREE.ConeGeometry(0.55, 1.2, 24, 1, true);
    cone.translate(0, -0.6, 0);
    cone.rotateZ(Math.PI / 2);
    this.scanMat = new THREE.MeshBasicMaterial({ color: 0x9fd7ff, transparent: true, opacity: 0.0, depthWrite: false,
      blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    this.scanL = new THREE.Mesh(cone, this.scanMat);
    this.scanR = new THREE.Mesh(cone, this.scanMat);
    this.scanL.rotation.y = Math.PI / 2; this.scanR.rotation.y = -Math.PI / 2;
    this.scanL.renderOrder = this.scanR.renderOrder = 4;
  }

  // ── explode burst ────────────────────────────────────────────
  burst(center, radius) {
    const c1 = new THREE.Color(0xffe08a), c2 = new THREE.Color(0x7fe0ff);
    for (let i = 0; i < 220; i++) {
      const v = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.3, Math.random() - 0.5).normalize()
        .multiplyScalar((1.2 + Math.random() * 2.8) * Math.max(0.35, radius));
      this.sparks.emit(center, v, 0.5 + Math.random() * 0.6, Math.random() < 0.6 ? c1 : c2);
    }
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.9, 1.0, 64),
      new THREE.MeshBasicMaterial({ color: 0xffd766, transparent: true, opacity: 0.9, side: THREE.DoubleSide,
        depthWrite: false, blending: THREE.AdditiveBlending }));
    ring.position.copy(center);
    ring.lookAt(this.app.camera.position);
    ring.userData = { t: 0, r: Math.max(0.25, radius) };
    this.scene.add(ring);
    this.rings.push(ring);
    const flash = new THREE.PointLight(0xffe2a0, 25 * Math.max(0.4, radius), 6 * Math.max(0.4, radius), 2);
    flash.position.copy(center);
    flash.userData = { t: 0 };
    this.scene.add(flash);
    this.rings.push(flash);
  }

  // ── water flow tubes ─────────────────────────────────────────
  flowTube(points, radius = 0.021, color = 0x45c6e6, speed = 1.2) {
    const pts = points.map(Bv);
    const curve = new THREE.CurvePath();
    for (let i = 0; i < pts.length - 1; i++) curve.add(new THREE.LineCurve3(pts[i], pts[i + 1]));
    let len = 0; for (let i = 0; i < pts.length - 1; i++) len += pts[i].distanceTo(pts[i + 1]);
    const geo = new THREE.TubeGeometry(curve, Math.max(8, Math.round(len * 12)), radius, 10, false);
    const mat = flowMaterial(color, speed, Math.max(2, len * 3));
    const m = new THREE.Mesh(geo, mat);
    m.renderOrder = 3;
    m.visible = false;
    this.scene.add(m);
    const f = { mesh: m, mat, target: 0 };
    this.flows.push(f);
    return f;
  }
  setFlow(f, on) { if (f) { f.target = on ? 1 : 0; if (on) f.mesh.visible = true; } }

  // ── data network ─────────────────────────────────────────────
  link(key, from, to, kind) {
    if (this.links.has(key)) return this.links.get(key);
    const mid = from.clone().lerp(to, 0.5);
    mid.y = Math.max(from.y, to.y) + 1.2 + from.distanceTo(to) * 0.12;
    const curve = new THREE.QuadraticBezierCurve3(from.clone(), mid, to.clone());
    const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 40, 0.006, 6, false), kind === 'cmd' ? this.linkMatCmd : this.linkMatSense);
    tube.visible = this.netVisible;
    tube.renderOrder = 3;
    this.scene.add(tube);
    const L = { curve, tube, kind };
    this.links.set(key, L);
    return L;
  }
  showNetwork(on) { this.netVisible = on; for (const L of this.links.values()) L.tube.visible = on; }
  pulse(L, color, dur = 1.1, reverse = false) {
    if (!L) return;
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 1, blending: THREE.AdditiveBlending, depthWrite: false });
    const m = new THREE.Mesh(this.pulseGeo, mat);
    m.renderOrder = 6;
    this.scene.add(m);
    L.tube.visible = true;
    this.pulses.push({ L, m, t: 0, dur, reverse, trail: 0 });
  }

  // ── markers (alarm / disease) ────────────────────────────────
  marker(key, pos, color = 0xff5a3c, label = '!') {
    this.clearMarker(key);
    const g = new THREE.Group();
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const x = c.getContext('2d');
    x.fillStyle = '#' + new THREE.Color(color).getHexString(); x.beginPath(); x.arc(64, 64, 54, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#fff'; x.font = 'bold 76px Arial'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(label, 64, 70);
    const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    sp.scale.set(0.16, 0.16, 1);
    sp.renderOrder = 10;
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.14, 0.165, 48), new THREE.MeshBasicMaterial({ color, transparent: true,
      opacity: 0.9, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }));
    ring.rotation.x = -Math.PI / 2;
    g.add(sp, ring);
    g.position.copy(pos);
    g.userData = { sp, ring, base: pos.clone() };
    this.scene.add(g);
    this.markers.set(key, g);
    return g;
  }
  clearMarker(key) { const g = this.markers.get(key); if (g) { this.scene.remove(g); this.markers.delete(key); } }

  // ── ambient emitters ─────────────────────────────────────────
  fogAt(nozzles) {
    for (const n of nozzles) {
      if (Math.random() < 0.55) continue;
      const p = n.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.05, -0.04, (Math.random() - 0.5) * 0.05));
      const v = new THREE.Vector3((Math.random() - 0.5) * 0.9, -0.3 - Math.random() * 0.4, (Math.random() - 0.5) * 0.9);
      this.fog.emit(p, v, 2.2 + Math.random() * 1.5);
    }
  }
  dripAt(points) {
    for (const p of points) if (Math.random() < 0.18) this.drops.emit(p, new THREE.Vector3(0, -0.05, 0), 0.35);
  }
  puff(p, dir) {
    for (let i = 0; i < 26; i++) {
      const v = dir.clone().multiplyScalar(1.2 + Math.random()).add(new THREE.Vector3((Math.random() - .5) * .6, (Math.random() - .5) * .6, (Math.random() - .5) * .6));
      this.puffs.emit(p, v, 0.5 + Math.random() * 0.4);
    }
  }
  airflow(fromX, toX, yRange, zRange, strength) {
    const n = Math.round(6 * strength);
    for (let i = 0; i < n; i++) {
      const p = new THREE.Vector3(fromX, yRange[0] + Math.random() * (yRange[1] - yRange[0]), zRange[0] + Math.random() * (zRange[1] - zRange[0]));
      this.air.emit(p, new THREE.Vector3(-(1.6 + Math.random()) * strength, 0, 0), (fromX - toX) / (1.9 * strength));
    }
  }

  update(dt) {
    this.t += dt;
    for (const P of [this.sparks, this.fog, this.drops, this.air, this.puffs]) P.update(dt);
    for (const f of this.flows) {
      f.mat.uniforms.uTime.value = this.t;
      const u = f.mat.uniforms.uOn;
      u.value += (f.target - u.value) * Math.min(1, dt * 3);
      if (f.target === 0 && u.value < 0.01) f.mesh.visible = false;
    }
    for (let i = this.pulses.length - 1; i >= 0; i--) {
      const p = this.pulses[i];
      p.t += dt / p.dur;
      const k = Math.min(1, p.t);
      p.m.position.copy(p.L.curve.getPoint(p.reverse ? 1 - k : k));
      p.m.scale.setScalar(1 + Math.sin(k * Math.PI) * 0.6);
      if (p.t >= 1.15) {
        this.scene.remove(p.m); p.m.material.dispose();
        if (!this.netVisible && !this.pulses.some((q) => q !== p && q.L === p.L)) p.L.tube.visible = false;
        this.pulses.splice(i, 1);
      }
    }
    for (let i = this.rings.length - 1; i >= 0; i--) {
      const r = this.rings[i];
      r.userData.t += dt;
      const t = r.userData.t;
      if (r.isPointLight) {
        r.intensity *= Math.exp(-dt * 7);
        if (t > 0.8) { this.scene.remove(r); this.rings.splice(i, 1); }
      } else {
        const s = r.userData.r * (0.3 + t * 5.5);
        r.scale.set(s, s, s);
        r.material.opacity = Math.max(0, 0.9 - t * 1.6);
        if (t > 0.6) { this.scene.remove(r); r.geometry.dispose(); r.material.dispose(); this.rings.splice(i, 1); }
      }
    }
    for (const g of this.markers.values()) {
      const { sp, ring, base } = g.userData;
      sp.position.y = 0.25 + Math.sin(this.t * 3) * 0.05;
      const s = 1 + ((this.t * 0.9) % 1) * 1.6;
      ring.scale.set(s, s, s);
      ring.material.opacity = 0.9 * (1 - ((this.t * 0.9) % 1));
      g.position.copy(base);
    }
  }
}
