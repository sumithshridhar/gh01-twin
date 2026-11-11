// The same 16 checks as build/03-auto-watering/tests/test_water_logic.cpp, run against the browser port
// (js/water_logic.js), so the "Try to break it" page provably uses the box's rules.   node tools/test_water_logic_js.mjs
import { CFG, WATER, SENSOR_BAD, DAY_CAP, LOCKED, newState, decide, watered } from '../js/water_logic.js';

let passed = 0, failed = 0;
const CHECK = (name, cond) => { if (cond) { passed++; console.log('PASS ', name); } else { failed++; console.log('FAIL ', name); } };
const MIN = 60e3, HOUR = 60 * MIN;

class Farm {
  constructor() {
    this.c = { ...CFG };
    this.s = newState();
    this.total = 0; this.boot = 0; this.soil = 1800; this.dryPerMin = 0.6; this.waterArrives = true;
    this.waterings = 0; this.bad = 0; this.capped = 0; this.lockedReads = 0; this.openMs = 0; this.lastWaterAt = [];
    this.sensor = (f) => Math.trunc(f.soil);
  }
  powerCut() {                               // the sketch keeps these in flash; everything else is forgotten
    const k = newState(), s = this.s;
    k.waterings = s.waterings.slice(); k.nWater = s.nWater; k.nextSlot = s.nextSlot; k.noEffect = s.noEffect; k.locked = s.locked;
    this.s = k;
    this.boot = this.total;
  }
  pass(ms) { this.total += ms; this.soil = Math.min(this.c.dry, this.soil + this.dryPerMin * (ms / MIN)); }
  run(forMs) {
    const end = this.total + forMs;
    while (this.total < end) {
      const raw = this.sensor(this);
      const d = decide(this.c, this.s, raw, this.total, this.total - this.boot);
      if (d.act === SENSOR_BAD) this.bad++;
      if (d.act === DAY_CAP) this.capped++;
      if (d.act === LOCKED) this.lockedReads++;
      if (d.act === WATER) {
        this.openMs += this.c.waterMs;
        this.total += this.c.waterMs;
        if (this.waterings < 64) this.lastWaterAt[this.waterings] = this.total;
        this.waterings++;
        watered(this.c, this.s, raw, this.total);
        if (this.waterArrives) this.soil -= 320;
        if (this.soil < this.c.wet) this.soil = this.c.wet;
      }
      this.pass(d.waitMs);
    }
  }
  mostIn24h() {
    let best = 0;
    const n = Math.min(this.waterings, 64), t = this.lastWaterAt;
    for (let i = 0; i < n; i++) { let k = 0; for (let j = i; j < n && t[j] - t[i] < 24 * HOUR; j++) k++; if (k > best) best = k; }
    return best;
  }
}

{ const f = new Farm(); f.run(7 * 24 * HOUR);
  CHECK('normal week: it waters', f.waterings > 0);
  CHECK('normal week: soil never reaches bone dry', f.soil < f.c.dry - 300);
  CHECK('normal week: daily limit kept', f.mostIn24h() <= f.c.maxPerDay);
  CHECK('normal week: no lock, no sensor alarm', !f.s.locked && f.bad === 0); }
{ const f = new Farm(); f.soil = 2500; f.sensor = () => 4095; f.run(3 * 24 * HOUR);
  CHECK('cable out (4095): no watering in 3 days', f.waterings === 0 && f.bad > 0); }
{ const f = new Farm(); f.soil = 2500; f.sensor = () => 0; f.run(3 * 24 * HOUR);
  CHECK('sensor shorted (0): no watering in 3 days', f.waterings === 0 && f.bad > 0); }
{ const f = new Farm(); f.soil = 1500; f.dryPerMin = 0; let n = 0;
  f.sensor = (x) => (++n % 10 === 0) ? 2700 : Math.trunc(x.soil);
  f.run(24 * HOUR);
  CHECK('single dry glitches: no watering', f.waterings === 0); }
{ const f = new Farm(); f.soil = 2500; f.waterArrives = false; f.run(5 * 24 * HOUR);
  CHECK('empty tank: exactly 2 tries, then locked', f.waterings === 2 && f.s.locked);
  CHECK('empty tank: valve open 2 minutes in 5 days', f.openMs === 2 * f.c.waterMs); }
{ const f = new Farm(); f.soil = 2500; f.waterArrives = false; f.run(6 * HOUR);
  for (let i = 0; i < 20; i++) { f.powerCut(); f.run(3 * HOUR); }
  CHECK('empty tank + 20 power cuts: still only 2 tries', f.waterings === 2 && f.s.locked); }
{ const f = new Farm(); f.soil = 2500; f.waterArrives = false; f.run(6 * HOUR);
  f.waterArrives = true; f.soil = 1500; f.run(2 * HOUR);
  const cleared = !f.s.locked;
  f.run(4 * 24 * HOUR);
  CHECK('lock clears when the soil reads wet again', cleared);
  CHECK('after the fix it waters again', f.waterings > 2); }
{ const f = new Farm(); f.soil = 2500;
  for (let i = 0; i < 144; i++) { f.powerCut(); f.run(10 * MIN); }
  CHECK('flickering power for 24 h: no watering', f.waterings === 0); }
{ const f = new Farm(); f.soil = 2800; f.dryPerMin = 12; f.c.minChange = 60;
  for (let i = 0; i < 24; i++) { f.powerCut(); f.run(3 * HOUR); }
  CHECK('3-hour power windows, thirsty corner: daily limit kept', f.mostIn24h() <= f.c.maxPerDay && f.waterings > 0); }
{ const f = new Farm(); f.soil = 2600; f.run(29 * MIN);
  const early = f.waterings; f.run(10 * MIN);
  CHECK('no watering in the first 30 min after power-up', early === 0 && f.waterings === 1); }
{ const f = new Farm(); f.soil = 2850; f.dryPerMin = 8; f.run(7 * 24 * HOUR);
  CHECK('worst case: valve open at most 6 minutes in any 24 h', f.mostIn24h() <= f.c.maxPerDay && f.capped > 0); }

console.log(`\n${passed}/${passed + failed} PASS`);
process.exit(failed ? 1 : 0);
