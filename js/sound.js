// Tiny synthesized sound effects (no audio files). Starts after the first user click.
export class Sound {
  constructor() { this.on = true; this.ctx = null; }
  ensure() {
    if (!this.ctx) { try { this.ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { this.on = false; } }
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
    return this.ctx;
  }
  noise(dur) {
    const c = this.ctx, b = c.createBuffer(1, Math.ceil(c.sampleRate * dur), c.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length) ** 2;
    const s = c.createBufferSource(); s.buffer = b; return s;
  }
  env(g, t, a, d, peak) { g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(0.0001, t + a + d); }
  explode() {
    if (!this.on || !this.ensure()) return;
    const c = this.ctx, t = c.currentTime;
    const n = this.noise(0.6), f = c.createBiquadFilter(), g = c.createGain();
    f.type = 'bandpass'; f.frequency.setValueAtTime(3000, t); f.frequency.exponentialRampToValueAtTime(300, t + 0.5); f.Q.value = 0.8;
    this.env(g, t, 0.01, 0.55, 0.35);
    n.connect(f).connect(g).connect(c.destination); n.start(t);
    const o = c.createOscillator(), g2 = c.createGain();
    o.type = 'sine'; o.frequency.setValueAtTime(90, t); o.frequency.exponentialRampToValueAtTime(40, t + 0.35);
    this.env(g2, t, 0.005, 0.35, 0.5);
    o.connect(g2).connect(c.destination); o.start(t); o.stop(t + 0.45);
    const o2 = c.createOscillator(), g3 = c.createGain();
    o2.type = 'triangle'; o2.frequency.setValueAtTime(420, t + 0.05); o2.frequency.exponentialRampToValueAtTime(1300, t + 0.4);
    this.env(g3, t + 0.05, 0.02, 0.4, 0.06);
    o2.connect(g3).connect(c.destination); o2.start(t + 0.05); o2.stop(t + 0.5);
  }
  implode() {
    if (!this.on || !this.ensure()) return;
    const c = this.ctx, t = c.currentTime, o = c.createOscillator(), g = c.createGain();
    o.type = 'triangle'; o.frequency.setValueAtTime(900, t); o.frequency.exponentialRampToValueAtTime(220, t + 0.3);
    this.env(g, t, 0.01, 0.3, 0.07);
    o.connect(g).connect(c.destination); o.start(t); o.stop(t + 0.35);
  }
  tick() {
    if (!this.on || !this.ensure()) return;
    const c = this.ctx, t = c.currentTime, o = c.createOscillator(), g = c.createGain();
    o.type = 'square'; o.frequency.value = 1800; this.env(g, t, 0.002, 0.04, 0.03);
    o.connect(g).connect(c.destination); o.start(t); o.stop(t + 0.06);
  }
  alarm() {
    if (!this.on || !this.ensure()) return;
    const c = this.ctx, t = c.currentTime;
    for (let i = 0; i < 3; i++) {
      const o = c.createOscillator(), g = c.createGain();
      o.type = 'sawtooth'; o.frequency.value = i % 2 ? 660 : 880;
      this.env(g, t + i * 0.22, 0.01, 0.18, 0.06);
      o.connect(g).connect(c.destination); o.start(t + i * 0.22); o.stop(t + i * 0.22 + 0.22);
    }
  }
  chime() {
    if (!this.on || !this.ensure()) return;
    const c = this.ctx, t = c.currentTime;
    [660, 990].forEach((f, i) => {
      const o = c.createOscillator(), g = c.createGain();
      o.type = 'sine'; o.frequency.value = f; this.env(g, t + i * 0.09, 0.01, 0.35, 0.05);
      o.connect(g).connect(c.destination); o.start(t + i * 0.09); o.stop(t + i * 0.09 + 0.4);
    });
  }
}
