// Blueprint sheet generated from the real mesh: feature + silhouette edges in 3 orthographic views (third-angle),
// overall dimensions in mm, numbered callouts, title block. Lines "draw themselves" with a CSS dash animation.
import * as THREE from 'three';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

const NS = 'http://www.w3.org/2000/svg';
const SHEET = { w: 1000, h: 640 };
const COS_FEATURE = Math.cos(THREE.MathUtils.degToRad(38));
const el = (tag, attrs = {}, parent) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
};
const niceScale = (r) => {
  const opts = [1, 2, 2.5, 5, 10, 15, 20, 25, 50, 75, 100, 150, 200];
  return opts.find((o) => o >= r) || Math.round(r);
};

function meshEdges(mesh, toRoot) {
  const src = mesh.geometry;
  if (!src.index && src.attributes.position.count > 60000) return null;
  let g = new THREE.BufferGeometry();
  g.setAttribute('position', src.attributes.position);
  if (src.index) g.setIndex(src.index);
  g = mergeVertices(g, 1e-4);
  const pa = g.attributes.position;
  const idx = g.index.array;
  const M = new THREE.Matrix4().multiplyMatrices(toRoot, mesh.matrixWorld);
  const P = new Float32Array(pa.count * 3);
  const v = new THREE.Vector3();
  for (let i = 0; i < pa.count; i++) { v.fromBufferAttribute(pa, i).applyMatrix4(M); P[i * 3] = v.x; P[i * 3 + 1] = v.y; P[i * 3 + 2] = v.z; }
  const nt = idx.length / 3;
  const N = new Float32Array(nt * 3);
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  const edges = new Map();
  for (let t = 0; t < nt; t++) {
    const i0 = idx[t * 3], i1 = idx[t * 3 + 1], i2 = idx[t * 3 + 2];
    a.set(P[i0 * 3], P[i0 * 3 + 1], P[i0 * 3 + 2]);
    b.set(P[i1 * 3], P[i1 * 3 + 1], P[i1 * 3 + 2]);
    c.set(P[i2 * 3], P[i2 * 3 + 1], P[i2 * 3 + 2]);
    const n = b.sub(a).cross(c.sub(a)).normalize();
    N[t * 3] = n.x; N[t * 3 + 1] = n.y; N[t * 3 + 2] = n.z;
    for (const [p, q] of [[i0, i1], [i1, i2], [i2, i0]]) {
      const k = p < q ? p * 1048576 + q : q * 1048576 + p;
      const e = edges.get(k);
      if (e) e[3] = t; else edges.set(k, [Math.min(p, q), Math.max(p, q), t, -1]);
    }
  }
  g.dispose();
  return { P, N, edges };
}

export class Blueprint {
  constructor(svg) { this.svg = svg; }

  draw(comp) {
    const svg = this.svg;
    svg.innerHTML = '';
    const root = comp.root;
    root.updateWorldMatrix(true, true);
    const toRoot = new THREE.Matrix4().copy(root.matrixWorld).invert();
    // gather edge data per top-level part
    const data = [];
    const bb = new THREE.Box3();
    comp.parts.forEach((p, pi) => {
      p.obj.traverse((o) => {
        if (!o.isMesh || o.userData.fx) return;
        const e = meshEdges(o, toRoot);
        if (!e) return;
        data.push({ pi, ...e });
        for (let i = 0; i < e.P.length; i += 3) bb.expandByPoint(new THREE.Vector3(e.P[i], e.P[i + 1], e.P[i + 2]));
      });
    });
    if (bb.isEmpty()) return;
    const size = bb.getSize(new THREE.Vector3());
    const W = Math.max(size.x, 1e-3), H = Math.max(size.y, 1e-3), D = Math.max(size.z, 1e-3);
    // layout: top view above front view, right-side view to the right of front
    const R = { x: 70, y: 40, w: 870, h: 470 };
    const gap = 64;
    const s = Math.min((R.w - gap) / (W + D), (R.h - gap) / (D + H));
    const ox = R.x + (R.w - gap - (W + D) * s) / 2;
    const oyTop = R.y + (R.h - gap - (D + H) * s) / 2;
    const front = { x: ox, y: oyTop + D * s + gap, w: W * s, h: H * s };
    const top = { x: ox, y: oyTop, w: W * s, h: D * s };
    const side = { x: ox + W * s + gap, y: front.y, w: D * s, h: H * s };
    const views = [
      { box: front, dir: new THREE.Vector3(0, 0, 1), u: (x, y, z) => front.x + (x - bb.min.x) * s, v: (x, y, z) => front.y + (bb.max.y - y) * s, name: 'FRONT' },
      { box: side, dir: new THREE.Vector3(1, 0, 0), u: (x, y, z) => side.x + (bb.max.z - z) * s, v: (x, y, z) => side.y + (bb.max.y - y) * s, name: 'RIGHT SIDE' },
      { box: top, dir: new THREE.Vector3(0, 1, 0), u: (x, y, z) => top.x + (x - bb.min.x) * s, v: (x, y, z) => top.y + (z - bb.min.z) * s, name: 'TOP' },
    ];
    // background grid + frame
    const gGrid = el('g', {}, svg);
    for (let x = 0; x <= SHEET.w; x += 20) el('line', { x1: x, y1: 0, x2: x, y2: SHEET.h, class: x % 100 ? 'grid-min' : 'grid-maj' }, gGrid);
    for (let y = 0; y <= SHEET.h; y += 20) el('line', { x1: 0, y1: y, x2: SHEET.w, y2: y, class: y % 100 ? 'grid-min' : 'grid-maj' }, gGrid);
    el('rect', { x: 12, y: 12, width: 976, height: 616, class: 'frame' }, svg);
    el('rect', { x: 18, y: 18, width: 964, height: 604, class: 'frame', 'stroke-width': 0.5 }, svg);
    // edges → one path per part (all views)
    const paths = new Map();
    let segs = 0;
    for (const d of data) {
      let str = paths.get(d.pi) || '';
      for (const vw of views) {
        const dx = vw.dir.x, dy = vw.dir.y, dz = vw.dir.z;
        for (const e of d.edges.values()) {
          const [p, q, f1, f2] = e;
          let draw = false;
          if (f2 < 0) draw = true;
          else {
            const n1x = d.N[f1 * 3], n1y = d.N[f1 * 3 + 1], n1z = d.N[f1 * 3 + 2];
            const n2x = d.N[f2 * 3], n2y = d.N[f2 * 3 + 1], n2z = d.N[f2 * 3 + 2];
            if (n1x * n2x + n1y * n2y + n1z * n2z < COS_FEATURE) draw = true;
            else if ((n1x * dx + n1y * dy + n1z * dz) * (n2x * dx + n2y * dy + n2z * dz) < 0) draw = true;
          }
          if (!draw) continue;
          const P = d.P;
          const x1 = vw.u(P[p * 3], P[p * 3 + 1], P[p * 3 + 2]), y1 = vw.v(P[p * 3], P[p * 3 + 1], P[p * 3 + 2]);
          const x2 = vw.u(P[q * 3], P[q * 3 + 1], P[q * 3 + 2]), y2 = vw.v(P[q * 3], P[q * 3 + 1], P[q * 3 + 2]);
          if (Math.abs(x1 - x2) < 0.15 && Math.abs(y1 - y2) < 0.15) continue;
          str += `M${x1.toFixed(1)} ${y1.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}`;
          segs++;
        }
      }
      paths.set(d.pi, str);
    }
    const gEdges = el('g', {}, svg);
    this.pathEls = new Map();
    [...paths.entries()].sort((a, b) => a[0] - b[0]).forEach(([pi, str], k) => {
      const pth = el('path', { d: str, class: 'edge', pathLength: 1, 'data-part': pi }, gEdges);
      pth.style.animationDelay = `${Math.min(k * 70, 900)}ms`;
      this.pathEls.set(pi, pth);
    });
    // view names + dimensions
    const gDim = el('g', { class: 'fade' }, svg);
    for (const vw of views) {
      const t = el('text', { x: vw.box.x, y: vw.box.y + vw.box.h + 42, 'font-size': 10, 'letter-spacing': 1.5 }, gDim);
      t.textContent = vw.name;
    }
    const dim = (x1, y1, x2, y2, label, vertical) => {
      el('line', { x1, y1, x2, y2, class: 'dim' }, gDim);
      const ah = 6;
      if (!vertical) {
        el('path', { d: `M${x1} ${y1}l${ah} -3v6z M${x2} ${y2}l${-ah} -3v6z`, fill: '#9fd0ff' }, gDim);
        el('line', { x1, y1: y1 - 8, x2: x1, y2: y1 + 4, class: 'dim' }, gDim);
        el('line', { x1: x2, y1: y2 - 8, x2, y2: y2 + 4, class: 'dim' }, gDim);
        const t = el('text', { x: (x1 + x2) / 2, y: y1 - 5, 'font-size': 11, 'text-anchor': 'middle' }, gDim);
        t.textContent = label;
      } else {
        el('path', { d: `M${x1} ${y1}l-3 ${ah}h6z M${x2} ${y2}l-3 ${-ah}h6z`, fill: '#9fd0ff' }, gDim);
        el('line', { x1: x1 - 4, y1, x2: x1 + 8, y2: y1, class: 'dim' }, gDim);
        el('line', { x1: x2 - 4, y1: y2, x2: x2 + 8, y2, class: 'dim' }, gDim);
        const t = el('text', { x: x1 - 6, y: (y1 + y2) / 2, 'font-size': 11, 'text-anchor': 'middle',
          transform: `rotate(-90 ${x1 - 6} ${(y1 + y2) / 2})` }, gDim);
        t.textContent = label;
      }
    };
    const mm = (m) => `${Math.round(m * 1000).toLocaleString('en-IN')}`;
    dim(front.x, front.y + front.h + 20, front.x + front.w, front.y + front.h + 20, `${mm(W)}`, false);
    dim(front.x - 20, front.y + front.h, front.x - 20, front.y, `${mm(H)}`, true);
    dim(side.x, side.y + side.h + 20, side.x + side.w, side.y + side.h + 20, `${mm(D)}`, false);
    // callouts around the front view
    const centers = comp.parts.map((p, pi) => {
      const pb = new THREE.Box3();
      for (const d of data) if (d.pi === pi) for (let i = 0; i < d.P.length; i += 3) pb.expandByPoint(new THREE.Vector3(d.P[i], d.P[i + 1], d.P[i + 2]));
      if (pb.isEmpty()) return null;
      const c = pb.getCenter(new THREE.Vector3());
      return { pi, x: views[0].u(c.x, c.y, c.z), y: views[0].v(c.x, c.y, c.z) };
    }).filter(Boolean);
    const fc = { x: front.x + front.w / 2, y: front.y + front.h / 2 };
    const rx = front.w / 2 + 34, ry = front.h / 2 + 30;
    centers.forEach((c) => { c.a = Math.atan2(c.y - fc.y, c.x - fc.x); });
    centers.sort((p, q) => p.a - q.a);
    const minSep = Math.min(0.55, (Math.PI * 2) / Math.max(centers.length, 1));
    for (let it = 0; it < 30; it++) for (let i = 0; i < centers.length; i++) {
      const p = centers[i], q = centers[(i + 1) % centers.length];
      let d = q.a - p.a; if (i === centers.length - 1) d += Math.PI * 2;
      if (centers.length > 1 && d < minSep) { const push = (minSep - d) / 2; p.a -= push; q.a += push; }
    }
    this.callouts = new Map();
    const gCl = el('g', { class: 'fade' }, svg);
    const rad = centers.length > 14 ? 8 : 10;
    for (const c of centers) {
      let bx = fc.x + Math.cos(c.a) * rx, by = fc.y + Math.sin(c.a) * ry;
      bx = Math.min(Math.max(bx, 32), 968); by = Math.min(Math.max(by, 32), 518);
      const g = el('g', { class: 'cl', 'data-part': c.pi }, gCl);
      el('line', { x1: bx, y1: by, x2: c.x, y2: c.y }, g);
      el('circle', { cx: c.x, cy: c.y, r: 1.8, fill: '#d8ecff' }, g);
      el('circle', { cx: bx, cy: by, r: rad }, g);
      const t = el('text', { x: bx, y: by + 3.8, 'font-size': rad + 1, 'text-anchor': 'middle', 'font-weight': 700 }, g);
      t.textContent = c.pi + 1;
      this.callouts.set(c.pi, g);
    }
    // title block
    const tb = el('g', { class: 'fade' }, svg);
    const X = 640, Y = 532, TW = 340, TH = 88;
    el('rect', { x: X, y: Y, width: TW, height: TH, class: 'frame' }, tb);
    for (const yy of [Y + 26, Y + 50, Y + 69]) el('line', { x1: X, y1: yy, x2: X + TW, y2: yy, class: 'dim' }, tb);
    el('line', { x1: X + 170, y1: Y + 50, x2: X + 170, y2: Y + TH, class: 'dim' }, tb);
    const txt = (x, y, str, size, w = 400) => { const t = el('text', { x, y, 'font-size': size, 'font-weight': w }, tb); t.textContent = str; return t; };
    const ratio = niceScale(1000 / (0.42 * s));
    const code = (comp.meta.category || 'GEN').replace(/[^A-Z]/gi, '').slice(0, 3).toUpperCase();
    const num = String([...comp.id].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) % 997, 7)).padStart(3, '0');
    txt(X + 8, Y + 18, 'GH-01 DIGITAL TWIN · AUTONOMOUS GREENHOUSE', 10, 700);
    const title = (comp.meta.title || comp.id).toUpperCase();
    txt(X + 8, Y + 42, title.length > 44 ? title.slice(0, 43) + '…' : title, 11.5, 700);
    txt(X + 8, Y + 63, `DWG No. ${code}-${num}   REV A`, 10);
    txt(X + 178, Y + 63, `SCALE 1:${ratio}   UNITS mm`, 10);
    txt(X + 8, Y + 82, `PARTS ${comp.parts.length}   SHEET 1/1`, 10);
    txt(X + 178, Y + 82, `DRAWN AUTO · ${new Date().toISOString().slice(0, 10)}`, 10);
    const note = el('text', { x: 30, y: 560, 'font-size': 9.5, class: 'fade' }, svg);
    note.textContent = 'THIRD-ANGLE PROJECTION · VISIBLE + HIDDEN EDGES (X-RAY) · GENERATED FROM THE 3D MODEL';
    const n2 = el('text', { x: 30, y: 576, 'font-size': 9.5, class: 'fade' }, svg);
    n2.textContent = `OVERALL ${mm(W)} × ${mm(H)} × ${mm(D)} mm · ${segs.toLocaleString()} EDGES`;
    return { scale: ratio, size: [W, H, D] };
  }

  highlight(pi) {
    if (!this.pathEls) return;
    for (const [k, p] of this.pathEls) p.classList.toggle('hl', k === pi);
    for (const [k, g] of this.callouts || []) g.classList.toggle('hl', k === pi);
  }
}
