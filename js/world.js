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

  addBackdrop() {
    this.backdrop = new THREE.Group();
    this.scene.add(this.backdrop);
    const s = this.backdrop;
    // tree line + field strips around the site
    const trunk = new THREE.CylinderGeometry(0.12, 0.18, 2.2, 6);
    const crown = new THREE.IcosahedronGeometry(1.6, 1);
    const tMat = new THREE.MeshStandardMaterial({ color: 0x5b4632, roughness: 1 });
    const cMat = new THREE.MeshStandardMaterial({ color: 0x3f6b35, roughness: 0.9, flatShading: true });
    const N = 90;
    const tI = new THREE.InstancedMesh(trunk, tMat, N);
    const cI = new THREE.InstancedMesh(crown, cMat, N);
    const m = new THREE.Matrix4();
    let k = 0;
    const rnd = (i) => { const x = Math.sin(i * 91.7) * 1e4; return x - Math.floor(x); };
    for (let i = 0; i < N; i++) {
      const a = (i / N) * Math.PI * 2 + rnd(i) * 0.05;
      const r = 42 + rnd(i + 3) * 26;
      const x = 4.5 + Math.cos(a) * r, z = Math.sin(a) * r;
      const sc = 0.8 + rnd(i + 7) * 1.1;
      m.compose(new THREE.Vector3(x, 1.1 * sc, z), new THREE.Quaternion(), new THREE.Vector3(sc, sc, sc));
      tI.setMatrixAt(k, m);
      m.compose(new THREE.Vector3(x, 2.9 * sc, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, rnd(i) * 3, 0)),
        new THREE.Vector3(sc, sc * (0.9 + rnd(i + 9) * 0.5), sc));
      cI.setMatrixAt(k, m);
      k++;
    }
    tI.castShadow = cI.castShadow = false;
    s.add(tI, cI);
    // crop field strips (neighbouring farmland)
    const strip = new THREE.PlaneGeometry(26, 4);
    const fMats = [0x6e8a3a, 0x8a7a45, 0x5f7d33].map((c) => new THREE.MeshStandardMaterial({ color: c, roughness: 1 }));
    for (let i = 0; i < 6; i++) {
      const p = new THREE.Mesh(strip, fMats[i % 3]);
      p.rotation.x = -Math.PI / 2;
      p.position.set(-30 + (i % 2) * 70, 0.02, -24 + Math.floor(i / 2) * 22);
      s.add(p);
    }
    // distant hills
    const hillMat = new THREE.MeshStandardMaterial({ color: 0x6f8a67, roughness: 1, flatShading: true });
    for (let i = 0; i < 9; i++) {
      const h = new THREE.Mesh(new THREE.SphereGeometry(40 + rnd(i) * 30, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2), hillMat);
      const a = (i / 9) * Math.PI * 2;
      h.position.set(4.5 + Math.cos(a) * 190, -18, Math.sin(a) * 190);
      h.scale.y = 0.35 + rnd(i + 2) * 0.25;
      s.add(h);
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
