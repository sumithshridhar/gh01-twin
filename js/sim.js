// Greenhouse simulation: weather → climate model → AI advisor → safety PLC → actuators, irrigation/fertigation,
// robot patrol and failure scenarios. Physics is deliberately simple but moves in the right direction and magnitude.
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const es = (T) => 0.6108 * Math.exp((17.27 * T) / (T + 237.3));            // saturation vapour pressure, kPa
const wetBulb = (T, RH) => T * Math.atan(0.151977 * Math.sqrt(RH + 8.313659)) + Math.atan(T + RH) - Math.atan(RH - 1.676331)
  + 0.00391838 * RH ** 1.5 * Math.atan(0.023101 * RH) - 4.686035;          // Stull 2011
const fmtT = (m) => { const h = Math.floor(m / 60) % 24, mi = Math.floor(m % 60); return `${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`; };

export class Sim {
  constructor(app, data) {
    this.app = app;
    this.data = data;
    this.speed = 60;
    this.running = true;
    this.hist = [];
    this.queue = [];
    this.realT = 0;
    this.reset(true);
    this.out = this.weather(this.t);
  }

  reset(first = false) {
    this.t = this.t ?? 690;
    this.day = 86;
    this.heat = false;
    this.cloud = 0.1;
    this.out = {};
    this.inn = { T: 24.4, e: 2.15, CO2: 432 };
    this.box2off = 0.3;
    this.act = { vent: 35, fans: 0, pad: false, padPump: false, padWet: 0, fog: false, haf: true, led: false, pump: false, valve: [false, false, false],
      dosing: [false, false, false], mixer: false };
    this.w = { tank: 72, mix: 58, ec: 3.02, ph: 5.84, flow: 0, pressure: 0, todayL: 49, dosedML: 780, supply: true,
      targetEC: 3.0, targetPH: 5.8, pond: 33, source: 'none', refill: false };      // pond: % of 84 m³ (1.8 m deep)
    // 6 Oct 2026: the farm's power. 3.24 kWp solar + 5.12 kWh LiFePO4 behind a hybrid inverter; the grid is the backup
    this.power = { grid: true, solar: true, soc: 0.86, pv: 0, load: 0, battKW: 0, gridKW: 0, level: 'full', cutUntil: null,
      todayKWh: 9.8, mode: 'solar + grid' };
    // 8 Oct 2026: each zone's slab keeps a real water + salt balance (per plant: 1/3 of a 100 × 20 × 10 cm coco slab = 6.7 L).
    // Before, "drain" was a counter that only ever went up (stuck at 40 %) and "shots today" never reset.
    this.zones = [0, 1, 2].map((i) => ({ wc: 64 + i, ec: 3.6, shots: 5, givenL: 0.9, drainL: 0.2, drainSalt: 0.2 * 3.8, drain: 22, lastML: 180 }));
    this.radSum = 62;
    this.shotJ = 100;                 // J/cm² of sunlight per shot; the AI steers it to keep the drain at 20–30 %
    this.drainSteer = true;
    this.irrHold = 0;
    this.dli = 14.2;
    this.faults = { pump: false, sensor: false, water: false, robot: false, disease: false, filter: false };
    this.flags = { boxStuck: [null, null], boxBad: [false, false], disagree: false, disagreeSince: null, hardThermo: false, pondLow: false, tankLow: false, tankLowLow: false, refillFail: false, plantsDry: false,
      irrBlocked: false, diseaseFound: false, robotAlarm: false };
    this.irr = { phase: 'idle', zone: 0, t0: 0, dur: 5.4, vol: 180, confirmed: false, startReal: 0, retry: 0 };
    // 9 Oct 2026: leaf wetness. wetMin = unbroken minutes of wet leaves, dryMin = minutes since they were last wet,
    // warned = advisory sent, cycle = the 10-min night vent opening is running, cycleAt = when it was last asked for
    this.leaf = { wet: false, wetMin: 0, dryMin: 0, leafT: 24, dew: 15, warned: false, cycle: false, cycleAt: null };
    this.mixing = { phase: 'idle', t0: 0 };
    this.fogCycle = 0;
    this.stageSince = -1e9;
    this.noise = [0, 0];
    this.sens = [{ v: null, since: this.t }, { v: null, since: this.t }];   // last value of each climate box + when it last changed
    this.lastClimateLog = '';
    this.robot = { x: 4.6, y: -0.8, lift: 1.1, wp: 3, route: this.makeRoute(), phase: 'move', timer: 0, scanning: false,
      battery: 76, scanned: 31, pollinated: 118, stuck: false, override: null, puff: 0 };
    this.traps = [{ wf: 23, th: 4, tu: 1 }, { wf: 17, th: 6, tu: 0 }, { wf: 9, th: 2, tu: 1 }];
    this.tankHist = [];
    this.refillDueSince = null;
    this.queue = [];
    this.app.alarm(null);
    this.app.clearMarkers?.();
    if (!first) this.app.log('OK', 'System reset · all faults cleared · AUTO mode');
  }

  makeRoute() {
    const R = [];
    const stops = this.data.robot.stops.filter((_, i) => i % 3 === 1);    // one stop per slab (middle plant)
    for (const y of this.data.robot.aisles_y) {
      R.push({ x: 1.75, y, stop: false });
      for (const x of stops) R.push({ x, y, stop: true });
      R.push({ x: 2.1, y, stop: false });
      R.push({ x: 1.75, y, stop: false });
    }
    return R;
  }

  later(sec, fn) { this.queue.push({ at: this.realT + sec, fn }); }

  // ── weather ────────────────────────────────────────────────
  weather(t) {
    const h = (t / 60) % 24;
    const cloud = this.heat ? 0 : this.cloud;
    const solar = 960 * Math.max(0, Math.sin(Math.PI * (h - 6.1) / 12.1)) ** 1.25 * (1 - 0.65 * cloud);
    let T = 23 + 7.5 * Math.sin((2 * Math.PI * (h - 9.5)) / 24);
    let RH = clamp(72 - 28 * Math.sin((2 * Math.PI * (h - 9.5)) / 24), 25, 96);
    if (this.heat) { T += 9; RH = clamp(RH - 22, 12, 90); }
    const wind = 2.2 + 1.6 * Math.sin(h / 3.1) + (this.heat ? 1.5 : 0);
    return { T, RH, solar, wind, cloud, rain: false };
  }

  get readings() {
    const i = this.inn, T = i.T;
    const RH = clamp((i.e / es(T)) * 100, 5, 100);
    const vpd = Math.max(0, es(T) - i.e);
    const [s1, s2] = this.flags.boxStuck;                                 // a frozen box repeats one number exactly
    const box1 = s1 ?? T - 0.1 + this.noise[0];
    const box2 = s2 ?? T + this.box2off + this.noise[1];
    return { T, RH, vpd, CO2: i.CO2, box1, box2, ppfd: this.out.solar * 2.02 * 0.72, solar: this.out.solar };
  }

  // ── main tick (dt real seconds) ────────────────────────────
  tick(dtReal) {
    this.realT += dtReal;
    for (let k = this.queue.length - 1; k >= 0; k--) if (this.queue[k].at <= this.realT) { const q = this.queue.splice(k, 1)[0]; q.fn(); }
    this.robotTick(dtReal);
    if (!this.running) return;
    let dt = (dtReal * this.speed) / 60;           // sim minutes this frame
    while (dt > 0) { const step = Math.min(dt, 1); this.step(step); dt -= step; }
  }

  step(dt) {
    this.t += dt;
    this.noise = this.noise.map(() => (Math.random() - 0.5) * 0.08);     // live sensors flicker by a few hundredths
    if (this.t >= 1440) {                         // midnight: the "today" counters start again
      this.t -= 1440; this.day++; this.dli = 0;
      for (const z of this.zones) Object.assign(z, { shots: 0, givenL: 0, drainL: 0, drainSalt: 0, drain: 0 });
      this.w.todayL = 0; this.w.dosedML = 0; this.power.todayKWh = 0;
    }
    const o = this.out = this.weather(this.t);
    const a = this.act, i = this.inn;
    // ── climate physics (exponential integration → stable at any speed)
    const fansOn = a.fans;
    const ach = 1.5 + (a.vent / 100) * 25 + fansOn * 55;                          // air changes per hour
    const k = ach / 60;
    // the pad soaks in ~3 min when its pump runs and dries in ~8 min when it stops, so cycling the pump gives part-cooling
    a.padWet = a.padPump ? a.padWet + (1 - a.padWet) * (1 - Math.exp(-dt / 3)) : a.padWet * Math.exp(-dt / 8);
    const pw = fansOn > 0 ? a.padWet : 0;
    const TsupFull = o.T - 0.8 * (o.T - wetBulb(o.T, o.RH));
    const Tsup = o.T - pw * (o.T - TsupFull);
    const eOut = (o.RH / 100) * es(o.T);
    const eSup = eOut + pw * (Math.min(es(TsupFull) * 0.9, eOut + 1.4) - eOut);
    const vpd = Math.max(0, es(i.T) - i.e);
    const sun = o.solar / 1000;
    const gain = sun * 0.8 - sun * 0.3 * (0.4 + vpd) * 0.6 - (a.fog ? 0.12 : 0) + (a.led ? 0.03 : 0);
    const Teq = Tsup + gain / k;
    i.T = Teq + (i.T - Teq) * Math.exp(-k * dt);
    const transp = sun * 0.1 * (0.3 + vpd) + 0.004;
    const eEq = eSup + (transp + (a.fog ? 0.05 : 0)) / k;
    i.e = Math.min(es(i.T) * 0.99, eEq + (i.e - eEq) * Math.exp(-k * dt));
    const co2Eq = 425 - (sun * 1.6) / k;
    i.CO2 = co2Eq + (i.CO2 - co2Eq) * Math.exp(-k * dt);
    this.dli += (o.solar * 2.02 * 0.72 * 60 * dt) / 1e6;
    this.radSum += (o.solar * 60 * dt) / 1e4;                                     // J/cm²
    // ── roots: transpiration dries the slabs. The roots take up water with fewer salts than the feed (≈ 0.8 × feed EC),
    // so what they leave behind concentrates in the slab; only drain water carries it out.
    for (const z of this.zones) {
      const up = Math.min(dt * (0.045 * sun * (0.6 + vpd) + 0.002), z.wc - 35);        // % of the slab volume
      const salt = z.ec * z.wc - up * Math.min(z.ec, 0.8 * this.w.ec);
      z.wc -= up;
      z.ec = salt / z.wc;
    }
    // ── water
    this.waterTick(dt);
    if (Math.floor(this.t) !== this.tankMin) {                     // the tank level once a minute, last 10 minutes
      this.tankMin = Math.floor(this.t);
      this.tankHist = [...(this.tankHist || []), this.w.tank].slice(-11);
    }
    this.leafTick(dt);
    this.climateControl(dt);
    this.irrigationTick(dt);
    this.powerTick(dt);
    this.mixTick(dt);
    this.faultChecks(dt);
    this.traps.forEach((tr) => { if (Math.random() < dt * 0.004) tr.wf++; });
    if (Math.floor(this.t) % 5 === 0 && this.lastHist !== Math.floor(this.t)) {
      this.lastHist = Math.floor(this.t);
      const r = this.readings;
      this.hist.push({ t: this.t, T: r.T, RH: r.RH, vpd: r.vpd, solar: o.solar, Tout: o.T, tank: this.w.tank, mix: this.w.mix,
        soc: this.power.soc * 100, pv: this.power.pv, pond: this.w.pond,
        w: this.slabWeight, ec: this.w.ec, ph: this.w.ph, flow: this.w.flow, co2: r.CO2 });
      if (this.hist.length > 400) this.hist.shift();
    }
  }

  get slabWeight() { return 15.6 + this.zones[2].wc * 0.095; }

  // ── water sources: farm pond first, borewell as backup (6 Oct 2026) ──────────────
  // The tank's float switch starts a refill below 60 % and stops it at 92 %. The pond pump (Kirloskar Chhotu, ~25 L/min)
  // fills it while the pond is above its 20 % reserve; below that the PLC switches to the borewell.
  waterTick(dt) {
    const w = this.w, a = this.act;
    if (!w.supply) {                                  // both sources cut (scenario): the tank only drains
      w.refill = false; w.source = 'none'; a.pondPump = a.borePump = false;
      w.tank = Math.max(0, w.tank - 0.9 * dt);
      return;
    }
    if (w.tank < 60) w.refill = true;
    if (w.tank >= 92) w.refill = false;
    const powered = this.power.level !== 'off' && this.power.level !== 'critical';
    w.source = !w.refill || !powered ? 'none' : (w.pond > 20 && !this.flags.pondLow ? 'pond' : 'borewell');
    a.pondPump = w.source === 'pond';
    a.borePump = w.source === 'borewell';
    if (w.source !== 'none') {
      const q = Math.min(dt * 5, 92 - w.tank);         // %/min of the 500 L tank (25 L/min)
      w.tank += q;
      if (w.source === 'pond') w.pond = Math.max(0, w.pond - (q * 5) / 840);   // 1 % of the pond = 840 L
    }
  }

  pondLitres() { return (this.w.pond / 100) * 84000; }
  pondLevelM() { return Math.cbrt(1 + 0.75 * (this.w.pond / 100) * 84) - 1; }   // 8 × 8 m top, 2 × 2 m bottom, 3 m deep

  // ── power (6 Oct 2026): solar first, battery second, grid last; load shedding when the battery runs low ───────
  powerTick(dt) {
    const P = this.power, a = this.act, A = this.app;
    if (P.cutUntil !== null && this.t >= P.cutUntil && !P.grid) {
      P.grid = true; P.cutUntil = null;
      A.chain('OK');
      A.log('OK', `Grid power back · battery at ${(P.soc * 100).toFixed(0)} % · all loads restored, the battery recharges from the panels`);
      A.alarm(null);
      A.flagComponent('hybrid_inverter', null);
    }
    P.pv = P.solar ? 3.24 * (this.out.solar / 1000) * 0.8 : 0;   // kW after inverter, dust and heat losses
    P.load = 0.08 + 0.42 * a.fans + (a.padPump ? 0.37 : 0) + (a.haf ? 0.16 : 0) + (a.pump ? 0.55 : 0) + (a.mixer ? 0.05 : 0) +
      (a.pondPump ? 0.37 : 0) + (a.borePump ? 1.1 : 0) + (a.fog ? 0.0 : 0);
    const net = P.pv - P.load;
    if (net >= 0) { P.battKW = P.soc < 0.999 ? Math.min(net, 2.5) : 0; P.gridKW = 0; }
    else if (P.grid) { P.battKW = 0; P.gridKW = -net; }
    else if (P.solar && P.soc > 0.12) { P.battKW = net; P.gridKW = 0; }
    else { P.battKW = 0; P.gridKW = 0; }
    P.soc = clamp(P.soc + (P.battKW * dt) / 60 / 5.12, 0, 1);
    P.todayKWh += (P.pv * dt) / 60;
    const prev = P.level;
    P.level = P.grid ? 'full' : !P.solar ? 'off' : P.pv >= P.load || P.soc > 0.3 ? 'full' : P.soc > 0.12 ? 'reserve' : 'critical';
    P.mode = P.grid ? (P.pv > 0.05 ? 'solar + grid' : 'grid') : !P.solar ? 'NO POWER' : P.pv >= P.load ? 'solar only' : 'solar + battery';
    a.haf = P.level === 'full';
    if (prev !== P.level) {
      if (P.level === 'reserve') {
        A.chain('PLC');
        A.log('PLC', `Battery at ${(P.soc * 100).toFixed(0)} % → reserve mode: circulation fans, fogging and robot charging OFF, cooling capped at one fan`);
        A.toast('Telegram → farmer', `GH-01: still no grid power. Battery ${(P.soc * 100).toFixed(0)} %. Running reduced cooling to keep the reserve.`);
      } else if (P.level === 'critical') {
        A.chain('ALARM');
        A.log('ALARM', 'Battery at 12 % → only the controller, alarms and 4G stay on. Fans and pad OFF.');
        A.alarm('Battery critical · cooling off');
        A.sound.alarm();
      } else if (P.level === 'off') {
        A.chain('ALARM');
        A.log('ALARM', 'No grid and no solar/battery: fans, pad, vents and pumps stop. Only the controller (DC UPS) is alive.');
      } else if (prev === 'reserve' || prev === 'critical') A.log('OK', 'Power sufficient again → full operation');
    }
  }

  // ── climate: AI proposes, PLC checks ───────────────────────
  climateControl(dt) {
    const r = this.readings, o = this.out, a = this.act;
    const f = this.flags;
    const Tctl = f.boxBad[0] ? r.box2 : f.boxBad[1] ? r.box1 : f.disagree ? Math.max(r.box1, r.box2) : (r.box1 + r.box2) / 2;
    const day = o.solar > 40;
    const target = day ? 24 : 18.5;
    const fut = this.weather(this.t + 60).T;
    const p = { vent: a.vent, fans: 0, pad: false, fog: false, fogMode: false, led: false, why: '' };
    // Cooling follows the air temperature, not the sun. Before 7 Oct 2026 sunset meant "night mode": on a heat-wave
    // evening (37 °C outside) the fans and pad switched off at 17:54 and the house climbed to 35 °C.
    const cooling = day || a.fans > 0 || Tctl > 26.8;
    if (cooling) {
      p.vent = clamp(18 + (Tctl - target) * 28, 5, 100);
      // staged cooling: 0 = vents only, 1 = one fan, 2 = both fans, 3 = both fans + wet pad. One stage up above its
      // threshold, one stage down below a lower one, and each stage is held ≥ 5 min (pad: 10 min) so nothing
      // short-cycles, except a step up at ≥ 30 °C. Before 4 Oct 2026 the stages jumped and chattered: in a heat wave the pad switched 145× in 90 min.
      const pre = fut > 32 && Tctl > 25.5;
      const NAMES = ['vents only', 'one fan', 'both fans', 'both fans + wet pad'];
      const UP = [26.8, 28.2, 28.2], DOWN = [25.6, 27.0, 26.0];
      const now = a.pad ? 3 : a.fans;
      // the pad stays on while the outside air is too hot to do without it (what the house would reach on both fans
      // alone); before 7 Oct 2026 it went off as soon as the pad had cooled the house, so it flipped every 10 min
      const noPadT = o.T + (o.solar / 1000) * 0.8 / ((1.5 + 110) / 60);
      let stage = now;
      if (stage < 3 && (Tctl > UP[stage] || (stage === 0 && pre)) && (stage < 2 || r.RH < 88)) stage++;
      else if (stage > 0 && ((Tctl < DOWN[stage - 1] && (stage < 3 || noPadT < UP[2] - 0.5)) || (stage === 3 && r.RH > 92)) && !(stage === 1 && pre)) stage--;
      const minHold = stage === 3 || now === 3 ? 10 : 5;                  // the pad pump gets a longer minimum run
      if (stage !== now && this.t - this.stageSince < minHold && !(stage > now && Tctl >= 30)) stage = now;
      if (stage !== now) this.stageSince = this.t;
      p.fans = Math.min(stage, 2);
      p.pad = stage === 3;
      if (stage !== now) {
        p.why = stage > now ? (stage === 1 && pre && Tctl <= UP[0] ? `forecast ${fut.toFixed(0)} °C in 1 h → pre-cool: one fan`
          : `air ${Tctl.toFixed(1)} °C > ${UP[now]} → ${NAMES[stage]}`)
          : `air ${Tctl.toFixed(1)} °C${stage === 2 && r.RH > 92 ? `, RH ${r.RH.toFixed(0)} %` : ''} → step down to ${NAMES[stage]}`;
      }
      if (p.fans > 0) p.vent = 0;                                       // fan-pad mode needs a closed house
      else if (!day) p.vent = r.RH > 88 ? 12 : 4;                         // after dark, back to the night vent setting
      const fogWant = a.fogMode ? r.vpd > 1.2 && Tctl > 25 && r.RH < 76 : r.vpd > 1.45 && Tctl > 25.5 && r.RH < 70;
      if (fogWant) { p.fogMode = true; this.fogCycle += dt; p.fog = this.fogCycle % 8 < 2; if (!p.why || p.fans === 0) p.why = `VPD ${r.vpd.toFixed(2)} kPa too dry → fog pulses (2 min of every 8)`; }
      p.led = false;                                                     // LED toplights removed from GH-01 on 6 Oct 2026
    } else {
      p.vent = r.RH > 88 ? 12 : 4;
      if (r.RH > 88 && !p.why) p.why = `night RH ${r.RH.toFixed(0)} % → crack vents (disease risk)`;
      if (this.leaf.cycle) { p.vent = 30; p.why = `leaves wet ${(this.leaf.wetMin / 60).toFixed(1)} h → 10-min vent cycle`; }   // leafTick() asked, the PLC limits below still apply
    }
    if (this.flags.diseaseFound && r.vpd < 0.55) { p.vent = Math.max(p.vent, 20); p.why = p.why || 'disease plan: keep VPD ≥ 0.55 kPa'; }
    // PLC limits
    let plcNote = '';
    if (o.wind > 10) { p.vent = Math.min(p.vent, 10); plcNote = 'wind > 10 m/s → vent limited to 10 %'; }
    if (p.pad && p.fans === 0) { p.pad = false; plcNote = 'pad needs fans'; }
    if (p.fog && r.RH > 85) { p.fog = false; p.fogMode = false; plcNote = 'fog blocked: RH > 85 %'; }
    // hard-wired thermostat (independent of AI + PLC program, with its own bulb, so a bad climate box can't blind it)
    if (r.T >= 35 || (this.flags.hardThermo && r.T >= 30)) {             // latched: stays on until the air is below 30 °C
      p.fans = 2; p.pad = true; p.vent = 0;
      if (!this.flags.hardThermo) {
        this.flags.hardThermo = true;
        const dead = this.power.level === 'off' || this.power.level === 'critical';
        this.app.log('ALARM', dead ? `HARD-WIRED thermostat tripped at ${r.T.toFixed(1)} °C, but there is NO POWER: the fans cannot start`
          : `HARD-WIRED thermostat: ${r.T.toFixed(1)} °C ≥ 35 °C → both fans + pad forced ON`);
        this.app.alarm(dead ? 'High temperature · no power for cooling' : 'High temperature · hard-wired cooling ON');
        this.app.sound.alarm();
      }
    } else if (this.flags.hardThermo) { this.flags.hardThermo = false; this.app.alarm(null); }
    const lvl = this.power.level;
    // reserve: one fan + the wet pad (0.79 kW) cools far more per watt than two dry fans (0.84 kW). Before 7 Oct 2026
    // reserve mode dropped the pad and the house cycled up to 35 °C every few minutes.
    if (lvl === 'reserve') { if (p.fans >= 2) p.pad = true; p.fans = Math.min(p.fans, 1); p.fog = false; p.fogMode = false; }
    if (lvl === 'critical' || lvl === 'off') { p.fans = 0; p.pad = false; p.fog = false; p.fogMode = false; }
    if (lvl === 'off') p.vent = a.vent;                                   // the vent motor has no power either
    const changed = p.fans !== a.fans || p.pad !== a.pad || Math.abs(p.vent - a.vent) > 12 || p.led !== a.led || p.fogMode !== !!a.fogMode;
    const sig = `${p.fans}|${p.pad}|${Math.round(p.vent / 12)}|${p.led}|${p.fogMode}`;
    if (changed && sig !== this.lastClimateLog) {
      this.lastClimateLog = sig;
      const acts = [];
      if (p.fans !== a.fans) acts.push(`fans ${a.fans}→${p.fans}`);
      if (p.pad !== a.pad) acts.push(`pad ${p.pad ? 'ON' : 'OFF'}`);
      if (Math.abs(p.vent - a.vent) > 12) acts.push(`vent ${Math.round(a.vent)}→${Math.round(p.vent)} %`);
      if (p.fogMode !== !!a.fogMode) acts.push(`fog ${p.fogMode ? 'pulses ON' : 'OFF'}`);
      if (p.led !== a.led) acts.push(`LEDs ${p.led ? 'ON' : 'OFF'}`);
      if (acts.length) {
        this.app.log('SENSE', `Air ${Tctl.toFixed(1)} °C · RH ${r.RH.toFixed(0)} % · VPD ${r.vpd.toFixed(2)} · out ${o.T.toFixed(1)} °C`);
        this.app.log('AI', `${acts.join(', ')}${p.why ? ' — ' + p.why : ''}`);
        this.app.log('PLC', plcNote ? `✓ with limit: ${plcNote}` : '✓ inside limits → executing');
        ['climate_box_1', 'climate_box_2', 'weather_station'].forEach((s) => this.app.pulse(s, 'control_cabinet', 'sense'));
        this.later(0.8, () => {
          if (p.fans !== a.fans) ['exhaust_fan_1', 'exhaust_fan_2'].forEach((f) => this.app.pulse('control_cabinet', f, 'cmd'));
          if (p.pad !== a.pad) this.app.pulse('control_cabinet', 'cooling_pad', 'cmd');
          this.app.pulse('control_cabinet', 'vent_drive', 'cmd');
        });
      }
    }
    Object.assign(a, { vent: p.vent, fans: p.fans, pad: p.pad, fog: p.fog, fogMode: p.fogMode, led: p.led });
    // pad mode cycles the pad pump to hold the air near 85 % RH: a pad left running all afternoon held 90 % RH and a VPD
    // of 0.3 kPa (7 Oct 2026), too damp for tomatoes. Air above 27.5 °C (or the hard-wired thermostat) keeps it running.
    if (!a.pad || a.fans === 0) a.padPump = false;
    else if (this.flags.hardThermo || Tctl > 26 || r.RH < 83) a.padPump = true;
    else if (r.RH > 86) a.padPump = false;
  }

  // ── leaf wetness and disease risk (9 Oct 2026) ─────────────────────────────────────────────────────────────
  // Before 9 Oct 2026 the house sat at 95-99 % RH for about 6 h every night and nothing said so. On a clear night a leaf
  // radiates heat to the sky and sits ~1 °C below the air; once it is within 0.5 °C of the dew point (RH ≳ 92 %) it films
  // with water. Grey mould, leaf mould and early blight need hours of that to infect, so the twin counts unbroken wet
  // hours (a dry spell of 30 min starts the count again) and warns at 4 h, a usual grower's warning level.
  // The AI only advises: a 10-min vent opening once an hour while it lasts. The PLC's own limits still decide it:
  // wind and no-power limits in climateControl(), and here the crop's night minimum, since cold air in would chill the plants.
  leafTick(dt) {
    const L = this.leaf, A = this.app, r = this.readings, o = this.out;
    const x = Math.log(this.inn.e / 0.6108), dew = (237.3 * x) / (17.27 - x);       // dew point, °C
    const leafT = r.T - (o.solar > 40 ? 0 : 1.0);
    const wet = r.RH > 90 && leafT - dew < 0.5;
    Object.assign(L, { wet, leafT, dew });
    if (wet) { L.wetMin += dt; L.dryMin = 0; }
    else if ((L.dryMin += dt) >= 30 && L.wetMin > 0) {
      if (L.warned) A.log('OK', `Leaves dry again after ${(L.wetMin / 60).toFixed(1)} h of wetness · RH ${r.RH.toFixed(0)} %`);
      Object.assign(L, { wetMin: 0, warned: false, cycle: false, cycleAt: null });
    }
    if (L.wetMin >= 240 && !L.warned) {
      L.warned = true;
      const h = L.wetMin / 60;
      A.chain('AI');
      A.log('SENSE', `Leaves wet ${h.toFixed(1)} h in a row: air ${r.T.toFixed(1)} °C, RH ${r.RH.toFixed(0)} %, dew point ${dew.toFixed(1)} °C, leaf ≈ ${leafT.toFixed(1)} °C`);
      A.log('AI', 'Disease risk up (grey mould, leaf mould, early blight). Plan: ask the PLC for vents at 30 % for 10 min every hour while it lasts; ask the farmer to check the lower leaves at first light');
      A.toast('Telegram → farmer', `GH-01: the leaves have been wet for ${h.toFixed(0)} h (humidity ${r.RH.toFixed(0)} %). That raises the risk of grey mould and leaf mould. Nothing is broken. The controller opens the vents for 10 min every hour when it is safe to. Please check the lower leaves at first light.`);
      A.log('FARMER', 'Advisory sent: leaf wetness / disease risk (Telegram)');
      ['climate_box_1', 'climate_box_2'].forEach((s) => A.pulse(s, 'control_cabinet', 'sense'));
    }
    const since = (t0) => (this.t - t0 + 1440) % 1440;
    if (L.warned && wet && !L.cycle && (L.cycleAt === null || since(L.cycleAt) >= 60)) {
      L.cycleAt = this.t;                                 // asked at most once an hour, whatever the PLC answers
      if (o.T < 15) {
        A.log('AI', 'Vent cycle proposed: 30 % for 10 min to swap the damp air');
        A.log('PLC', `✗ declined: outside ${o.T.toFixed(1)} °C is below the crop's 15 °C night minimum → vents stay as they are`);
      } else L.cycle = true;                              // climateControl() carries it out and logs it
    }
    if (L.cycle && since(L.cycleAt) >= 10) L.cycle = false;
  }

  // ── irrigation ─────────────────────────────────────────────
  startIrrigation(forced = false) {
    if (this.irr.phase !== 'idle') return;
    const r = this.readings;
    const drain = this.drainToday();
    const vol = Math.round(((150 + 60 * clamp(r.vpd - 0.8, 0, 1)) * (this.flags.tankLow ? 0.6 : 1)) / 10) * 10;   // ration: 60 % shots
    // valve time per zone = the shot: 18 drippers × 2 L/h = 0.6 L/min, so 150 mL per plant takes 4.5 min
    this.irr = { ...this.irr, phase: 'deciding', vol, dur: (vol * 18) / 600, zone: 0, retry: this.irr.retry || 0 };
    const A = this.app;
    const id = (this.irrCycle = (this.irrCycle || 0) + 1);   // steps of an older request must not act on this one
    const later = (s, fn) => this.later(s, () => { if (this.irrCycle === id) fn(); });
    A.chain('SENSE');
    A.log('SENSE', `${forced ? 'Manual request · ' : ''}radiation sum ${this.radSum.toFixed(0)} J/cm² · slab 3 weight ${this.slabWeight.toFixed(2)} kg · VPD ${r.vpd.toFixed(2)}`);
    ['par_sensor', 'slab_scale', 'weather_station', 'substrate_sensor', 'drain_meter'].forEach((s) => A.pulse(s, 'control_cabinet', 'sense'));
    later(1.0, () => A.chain('DATA'));
    later(1.6, () => { A.chain('AI'); A.log('AI', `Irrigate zones 1→3: ${vol} mL per plant (VPD ${r.vpd.toFixed(2)} kPa) · drain today ${drain.toFixed(0)} %, target 20–30 % · a shot every ${this.shotJ} J/cm²`); });
    later(2.4, () => A.chain('DECIDE'));
    later(3.0, () => {
      A.chain('PLC');
      const w = this.w;
      if (this.flags.tankLowLow || w.tank < 8) { this.block('LOW-LOW float open (hard-wired) — pump cannot start'); return; }
      if (this.flags.irrBlocked) { this.block('irrigation blocked until the pump fault is cleared'); return; }
      if (this.power.level === 'off' || this.power.level === 'critical') { this.block('no power for the pump (grid off, battery reserve)'); return; }
      if (w.mix < 6) { this.block('mix tank empty — waiting for batch'); return; }
      A.log('PLC', `✓ tank ${w.tank.toFixed(0)} % · mix ${w.mix.toFixed(0)} % · EC ${w.ec.toFixed(2)} · pH ${w.ph.toFixed(2)} · pump OK · max 10 min/zone`);
    });
    later(3.8, () => {
      if (this.irr.phase !== 'deciding') return;
      A.chain('ACT');
      A.log('ACT', `Pump ON · zone valve 1 OPEN`);
      A.pulse('control_cabinet', 'irrigation_pump', 'cmd');
      A.pulse('control_cabinet', 'zone_valve_1', 'cmd');
      this.irr.phase = 'running'; this.irr.zone = 0; this.irr.t0 = this.t; this.irr.confirmed = false; this.irr.startReal = this.realT;
    });
  }

  block(why) {
    this.irr.phase = 'idle';
    this.irrHold = this.realT + 45;   // no automatic re-request right after a refusal
    this.app.chain('ALARM');
    this.app.log('ALARM', `PLC refused: ${why}`);
    this.app.sound.alarm();
  }

  irrigationTick(dt) {
    const irr = this.irr, a = this.act, w = this.w;
    const h = (this.t / 60) % 24;
    if (irr.phase === 'idle' && this.radSum >= this.shotJ && h > 7.5 && h < 17.5 && !this.flags.irrBlocked && !this.flags.tankLowLow &&
      this.realT > (this.irrHold || 0)) this.startIrrigation();
    if (irr.phase === 'running' && (this.power.level === 'off' || this.power.level === 'critical')) {
      irr.phase = 'idle'; this.irrHold = this.realT + 45;
      this.app.log('ACT', 'No power → pump stopped mid-shot; the cycle resumes when power is back');
    }
    if (irr.phase === 'running' && this.flags.tankLowLow) this.stopForNoWater();
    if (irr.phase !== 'running') { a.pump = false; a.valve = [false, false, false]; w.flow = 0; w.pressure = Math.max(0, w.pressure - dt * 3); return; }
    const z = irr.zone;
    a.pump = true;
    a.valve = [z === 0, z === 1, z === 2];
    const pumpOK = !this.faults.pump && !this.flags.tankLowLow;
    w.flow = pumpOK ? 0.6 * (1 - (this.faults.filter ? 0.5 : 0)) : 0;           // L/min at the meter (18 drippers × 2 L/h)
    w.pressure = pumpOK ? 2.1 : 0;
    if (w.flow > 0) this.waterSlab(this.zones[z], (w.flow / 18) * dt);
    const realSince = this.realT - irr.startReal;
    if (!irr.confirmed && realSince > 2.2) {
      if (w.flow > 0) {
        irr.confirmed = true;
        this.app.chain('OK');
        this.app.log('OK', `Flow meter ${(w.flow).toFixed(2)} L/min · pressure ${w.pressure.toFixed(1)} bar → zone ${z + 1} confirmed`);
        this.app.pulse('flow_meter', 'control_cabinet', 'sense');
        this.app.pulse('pressure_tx', 'control_cabinet', 'sense');
      } else {
        this.pumpFailed();
        return;
      }
    }
    if (!irr.confirmed) return;
    // the PLC keeps watching the flow meter for the whole shot, not just at start: a pump that dies mid-run is caught too
    if (w.flow <= 0) {
      if (irr.noFlowSince == null) irr.noFlowSince = this.realT;
      if (this.realT - irr.noFlowSince > 2.0) { irr.noFlowSince = null; this.pumpFailed(); return; }
    } else irr.noFlowSince = null;
    w.mix = Math.max(0, w.mix - (w.flow * dt) / 2.0);
    w.todayL += w.flow * dt;
    const zz = this.zones[z];
    if (this.t - irr.t0 >= irr.dur) {
      zz.shots++; zz.lastML = irr.vol;
      if (z < 2) {
        irr.zone++; irr.t0 = this.t; irr.confirmed = false; irr.startReal = this.realT;
        this.app.log('ACT', `Zone ${z + 1} done (${irr.vol} mL/plant) → valve ${z + 2} OPEN`);
        this.app.pulse('control_cabinet', `zone_valve_${z + 2}`, 'cmd');
      } else {
        irr.phase = 'idle'; this.radSum = 0; irr.retry = 0;
        this.app.log('OK', `Cycle complete · 54 plants × ${irr.vol} mL · drain today ${this.drainToday().toFixed(0)} % · slab EC ${this.slabEC().toFixed(1)}`);
        this.steerDrain();
        this.app.chain(null);
        this.app.sound.chime();
      }
    }
  }

  // one minute of drippers on a zone's slab: a little runs straight through (channeling), the rest wets the coco up to
  // container capacity, and anything above that drains, carrying the slab's salts with it
  waterSlab(z, litres) {
    const SLAB_L = 6.67, FC = 72, BYPASS = 0.05;
    const pct = (litres / SLAB_L) * 100;
    const inPct = pct * (1 - BYPASS);
    const wc = z.wc + inPct, salt = z.ec * z.wc + inPct * this.w.ec;
    const over = Math.max(0, wc - FC);
    z.ec = salt / wc;
    z.wc = wc - over;
    const drainL = ((over + pct * BYPASS) / 100) * SLAB_L;
    z.givenL += litres;
    z.drainL += drainL;
    z.drainSalt += (over / 100) * SLAB_L * z.ec + litres * BYPASS * this.w.ec;
    z.drain = (100 * z.drainL) / z.givenL;
  }

  drainToday() { const g = this.zones.reduce((s, z) => s + z.givenL, 0); return g > 0 ? (100 * this.zones.reduce((s, z) => s + z.drainL, 0)) / g : 0; }
  drainEC() { const d = this.zones.reduce((s, z) => s + z.drainL, 0); return d > 0 ? this.zones.reduce((s, z) => s + z.drainSalt, 0) / d : this.w.ec; }
  slabEC() { return this.zones.reduce((s, z) => s + z.ec, 0) / 3; }

  // the growers' rule: drain below 20 % means salts are building up around the roots → water more often; above 30 % is
  // waste → less often. Steered by the sunlight per shot, after the first 3 shots of the day (a dry morning slab drains nothing).
  steerDrain() {
    if (!this.drainSteer || this.zones[0].givenL < 0.45) return;
    const d = this.drainToday(), ec = this.slabEC(), [lo, hi] = ec > 5 ? [25, 35] : [20, 30];   // salty slab: wash it a bit more
    const old = this.shotJ;
    if (d < lo) this.shotJ = Math.max(60, this.shotJ - 10);
    else if (d > hi) this.shotJ = Math.min(160, this.shotJ + 10);
    if (this.shotJ !== old) {
      this.app.chain('AI');
      this.app.log('AI', `Drain today ${d.toFixed(0)} % (target ${lo}–${hi} %), slab EC ${ec.toFixed(1)} → a shot every ${this.shotJ} J/cm² (was ${old})`);
    }
  }

  pumpFailed() {
    if (this.flags.tankLowLow) { this.stopForNoWater(); return; }    // no flow because there's no water: not the pump
    const irr = this.irr;
    irr.phase = 'idle';
    this.irrHold = this.realT + 45;   // only the one explicit retry below, no automatic re-request
    this.act.pump = false;
    this.act.valve = [false, false, false];
    this.app.chain('ALARM');
    this.app.log('ALARM', 'No flow for 2 s with the pump on (0.0 L/min, 0.0 bar) → pump + valve OFF');
    this.app.flagComponent('irrigation_pump', 'fault');
    this.app.sound.alarm();
    if ((irr.retry || 0) < 1) {
      irr.retry = 1;
      this.app.log('PLC', 'Retry once in 3 s (rule: one automatic retry)');
      this.later(3.2, () => this.startIrrigationDirect());
    } else {
      this.flags.irrBlocked = true;
      this.app.log('ALARM', 'Second attempt failed → irrigation BLOCKED · fallback: none until repaired');
      this.app.alarm('Pump fault · irrigation blocked');
      this.app.toast('Telegram → farmer', 'GH-01: irrigation pump has no flow (checked twice). Irrigation blocked. Check pump / power / priming.');
      this.app.log('FARMER', 'Alert sent: pump fault (Telegram + SMS)');
      this.app.focusOn?.('irrigation_pump');
    }
  }

  startIrrigationDirect() {
    this.irrCycle = (this.irrCycle || 0) + 1;
    this.irr.phase = 'running'; this.irr.zone = 0; this.irr.t0 = this.t; this.irr.confirmed = false; this.irr.startReal = this.realT;
    this.app.log('ACT', 'Retry: pump ON · valve 1 OPEN');
    this.app.pulse('control_cabinet', 'irrigation_pump', 'cmd');
  }

  // ── fertigation batch ──────────────────────────────────────
  mixTick(dt) {
    const w = this.w, m = this.mixing, a = this.act;
    if (m.phase === 'idle' && w.mix < 30 && !this.flags.tankLowLow && this.irr.phase === 'idle') {
      m.phase = 'fill'; m.t0 = this.t;
      this.app.log('AI', `Mix tank ${w.mix.toFixed(0)} % → new batch, recipe fruiting-v3 (EC ${w.targetEC}, pH ${w.targetPH})`);
      this.app.log('PLC', '✓ fill 100 L from fresh-water tank, dose max 1.2 L stock per batch');
    }
    if (m.phase === 'fill') {
      const q = Math.min(dt * 12, 60 - w.mix);
      w.mix += q; w.tank = Math.max(0, w.tank - q * 0.4); w.ec = w.ec * 0.97 + 0.3 * 0.03;
      if (w.mix >= 59) { m.phase = 'dose'; m.t0 = this.t; this.app.log('ACT', 'Dosing pumps A + B + acid ON · mixer ON'); ['dosing_pump_A', 'dosing_pump_B', 'dosing_pump_acid'].forEach((d) => this.app.pulse('control_cabinet', d, 'cmd')); }
    }
    a.dosing = [m.phase === 'dose', m.phase === 'dose', m.phase === 'dose' && w.ph > w.targetPH];
    a.mixer = m.phase === 'dose' || m.phase === 'mix';
    if (m.phase === 'dose') {
      w.ec += (w.targetEC + 0.02 - w.ec) * Math.min(1, dt * 0.25);
      w.ph += (w.targetPH - w.ph) * Math.min(1, dt * 0.25);
      w.dosedML += dt * 40;
      if (Math.abs(w.ec - w.targetEC) < 0.05) { m.phase = 'mix'; m.t0 = this.t; }
    }
    if (m.phase === 'mix' && this.t - m.t0 > 4) {
      m.phase = 'idle';
      this.app.log('OK', `Batch ready: EC ${w.ec.toFixed(2)} · pH ${w.ph.toFixed(2)} (flow-cell confirmed)`);
      this.app.pulse('sensor_flow_cell', 'control_cabinet', 'sense');
    }
  }

  // ── fault detection ────────────────────────────────────────
  faultChecks(dt) {
    const f = this.flags, w = this.w;
    // Climate boxes: a live sensor flickers; a frozen one repeats the same number. Before 6 Oct 2026 the twin only ever
    // checked box 1 (by disagreement), so a frozen box 2 went unnoticed all day and dragged the average down.
    const r = this.readings, vals = [r.box1, r.box2];
    const age = (i) => (this.t - this.sens[i].since + 1440) % 1440;
    vals.forEach((v, i) => { if (this.sens[i].v === null || Math.abs(v - this.sens[i].v) > 1e-6) { this.sens[i].v = v; this.sens[i].since = this.t; } });
    for (const i of [0, 1]) {
      const j = 1 - i;
      if (f.boxBad[0] || f.boxBad[1] || age(i) < 20 || age(j) > 2) continue;
      f.boxBad[i] = true; f.disagree = false;
      const id = `climate_box_${i + 1}`;
      this.app.chain('ALARM');
      this.app.log('SENSE', `Climate box ${i + 1} has read exactly ${vals[i].toFixed(2)} °C for 20 min; box ${j + 1} keeps moving (${vals[j].toFixed(2)} °C)`);
      this.app.log('PLC', `Flat-line check failed → box ${i + 1} marked BAD, control uses box ${j + 1}`);
      this.app.flagComponent(id, 'fault');
      this.app.alarm(`Sensor fault · climate box ${i + 1}`);
      this.app.toast('Telegram → farmer', `GH-01: climate sensor ${i + 1} is frozen. Running on sensor ${j + 1}. Check its fan / cable.`);
      this.app.log('FARMER', `Alert sent: sensor fault (control continues on box ${j + 1})`);
      this.app.sound.alarm();
      this.app.focusOn?.(id);
    }
    // both still moving but far apart: we can't tell which is right, so cool on the warmer one (the safe side)
    const gap = Math.abs(r.box1 - r.box2);
    if (!f.boxBad[0] && !f.boxBad[1]) {
      if (gap > 1.5) f.disagreeSince ??= this.t; else f.disagreeSince = null;
      if (!f.disagree && f.disagreeSince !== null && (this.t - f.disagreeSince + 1440) % 1440 >= 10) {
        f.disagree = true;
        this.app.log('PLC', `Climate boxes disagree by ${gap.toFixed(1)} °C for 10 min and both are live → control uses the warmer one`);
        this.app.alarm('Climate sensors disagree');
        this.app.toast('Telegram → farmer', `GH-01: climate sensors 1 and 2 differ by ${gap.toFixed(1)} °C. Cooling on the warmer one. Please check both.`);
      }
      if (f.disagree && gap < 0.8) { f.disagree = false; this.app.alarm(null); this.app.log('OK', 'Climate boxes agree again'); }
    }
    if (w.pond < 20 && !f.pondLow) {
      f.pondLow = true;
      const days = Math.max(0, (this.pondLitres() - 0.05 * 84000) / 350);
      this.app.chain('PLC');
      this.app.log('SENSE', `Pond level ${this.pondLevelM().toFixed(2)} m (${w.pond.toFixed(1)} %, ${Math.round(this.pondLitres()).toLocaleString('en-IN')} L)`);
      this.app.log('PLC', 'Pond below its 20 % reserve → pond pump OFF, tank refill switched to the borewell');
      this.app.log('AI', `The reserve covers ≈ ${days.toFixed(0)} days at 350 L/day (drip + wet pad) if the borewell fails too`);
      this.app.toast('Telegram → farmer', `GH-01: farm pond at 20 %. Using the borewell now; the pond is kept as a ${days.toFixed(0)}-day reserve.`);
      this.app.log('FARMER', 'Alert sent: pond at reserve level');
      this.app.pulse('level_pond', 'control_cabinet', 'sense');
      this.app.focusOn?.('farm_pond');
    }
    if (w.pond > 25 && f.pondLow) { f.pondLow = false; this.app.log('OK', 'Pond back above 25 % → refills from the pond again'); }
    // Water: say what is actually wrong, and how long the plants have. Before 9 Oct 2026 an empty tank came out as either
    // "check pump / power / priming" (the no-flow check fired after the float switch had cut the pump) or as no message at
    // all for the rest of the day, while the slabs dried out. "Ration mode" was logged but never applied.
    const fall = this.tankFall();                                   // %/min the tank has dropped over the last 10 min
    if (w.tank < 60) this.refillDueSince ??= this.t; else this.refillDueSince = null;
    const due = this.refillDueSince !== null ? (this.t - this.refillDueSince + 1440) % 1440 : 0;
    if (due >= 8 && fall > 0.3 && !f.refillFail) {                  // a refill has been due for 8 min, yet the level keeps dropping
      f.refillFail = true;
      const left = w.tank / fall;
      this.app.chain('ALARM');
      this.app.log('SENSE', `Tank ${w.tank.toFixed(0)} % and falling ${fall.toFixed(1)} %/min although a refill is due`);
      this.app.log('AI', `Refill not reaching the tank: pond pump and borewell are not delivering. ≈ ${Math.round(left)} min of water left`);
      this.app.toast('Telegram → farmer', `GH-01: the water tank is emptying (${w.tank.toFixed(0)} %) and the refill isn't working. Check the pond pump, the borewell and their power. About ${Math.round(left)} min of water left.`);
      this.app.log('FARMER', 'Alert sent: water supply not delivering');
      this.app.pulse('level_water_tank', 'control_cabinet', 'sense');
    }
    if (w.tank < 20 && !f.tankLow) {
      f.tankLow = true;
      this.app.log('SENSE', `Ultrasonic level ${w.tank.toFixed(0)} % (LOW)`);
      this.app.log('AI', 'Ration mode: shots cut to 60 % until the tank refills');
      this.app.pulse('level_water_tank', 'control_cabinet', 'sense');
    }
    if (w.tank < 8 && !f.tankLowLow) {
      f.tankLowLow = true;
      if (this.irr.phase === 'running') this.stopForNoWater();
      this.app.chain('ALARM');
      this.app.log('ALARM', 'LOW-LOW float switch OPEN → pump contactor coil cut in hardware (no software involved)');
      this.app.alarm('Water shortage · pumps locked out');
      this.app.flagComponent('water_tank', 'fault');
      const h = this.hoursToStress();
      this.app.toast('Telegram → farmer', `GH-01: water tank EMPTY. Irrigation stopped: the pump is fine, there is no water. The slabs hold about ${h.toFixed(1)} h of water at this sun.`);
      this.app.log('FARMER', 'Alert sent: tank empty (not a pump fault)');
      this.app.sound.alarm();
      this.app.focusOn?.('water_tank');
    }
    const wc = this.zones.reduce((s, z) => s + z.wc, 0) / 3;
    if (f.tankLowLow && wc < 55 && !f.plantsDry) {
      f.plantsDry = true;
      this.app.chain('ALARM');
      this.app.log('ALARM', `Slabs at ${wc.toFixed(0)} % water (normal 65–72 %) and no water to give`);
      this.app.toast('Telegram → farmer', `GH-01: plants are drying. Slab water ${wc.toFixed(0)} % (normal 65–72 %). Wilting in about ${this.hoursToStress(45).toFixed(1)} h unless water is restored.`);
      this.app.log('FARMER', 'Alert sent: plants drying');
    }
    if (w.tank > 25 && f.tankLowLow) {
      Object.assign(f, { tankLowLow: false, tankLow: false, refillFail: false, plantsDry: false });
      this.app.alarm(null); this.app.flagComponent('water_tank', null); this.app.log('OK', 'Tank refilled → float closed, pumps released');
    }
  }

  // the tank's drop over the last 10 minutes, in % per minute (positive = falling)
  tankFall() {
    const h = this.tankHist;
    return h && h.length > 5 ? (h[0] - h[h.length - 1]) / (h.length - 1) : 0;
  }

  // hours until the slabs dry to `to` % at the current uptake (sunlight × dryness of the air), for the farmer's message
  hoursToStress(to = 50) {
    const r = this.readings, sun = this.out.solar / 1000;
    const rate = Math.max(0.01, 0.045 * sun * (0.6 + r.vpd) + 0.002);       // % of the slab per minute
    const wc = this.zones.reduce((s, z) => s + z.wc, 0) / 3;
    return Math.max(0, wc - to) / rate / 60;
  }

  // the float switch cut the pump mid-shot: stop the cycle as a water shortage (not a pump fault) and don't count it as watered
  stopForNoWater() {
    const irr = this.irr;
    this.app.log('ACT', `Float switch cut the pump in zone ${irr.zone + 1}: cycle stopped${irr.zone < 2 ? `, zone${irr.zone < 1 ? 's 2–3' : ' 3'} not watered` : ''}`);
    irr.phase = 'idle';
    irr.noFlowSince = null;
    this.irrHold = this.realT + 45;
    this.act.pump = false;
    this.act.valve = [false, false, false];
  }

  // ── robot patrol (real time) ───────────────────────────────
  robotTick(dt) {
    const R = this.robot;
    if (R.stuck) return;
    if (R.phase === 'scan') {
      R.timer += dt;
      const t = R.timer;
      R.lift = t < 1.4 ? 0.35 + (t / 1.4) * 1.95 : t < 2.8 ? 2.3 - ((t - 1.4) / 1.4) * 1.2 : 1.1;
      R.scanning = t < 2.8;
      if (t > 1.0 && t < 1.05 + dt) { R.puff = 1; R.pollinated += 2; }
      if (R.override === 'disease' && t > 2.0 && !this.flags.diseaseFound) this.diseaseDetected();
      if (t > 3.0) {
        R.phase = 'move'; R.scanned += 2;
        R.wp = (R.wp + 1) % R.route.length;
        if (R.override === 'disease') R.override = null;
      }
      return;
    }
    let target = R.route[R.wp];
    if (R.override === 'disease' && R.overrideTarget) target = R.overrideTarget;
    const dx = target.x - R.x, dy = target.y - R.y;
    const d = Math.hypot(dx, dy);
    const v = (R.override ? 1.1 : 0.45) * dt;
    if (d <= v) {
      R.x = target.x; R.y = target.y;
      if (target === R.overrideTarget || target.stop) { R.phase = 'scan'; R.timer = 0; if (target === R.overrideTarget) R.overrideTarget = null; }
      else R.wp = (R.wp + 1) % R.route.length;
    } else {
      // move along x first when changing aisles (stay on the concrete path)
      if (Math.abs(dy) > 0.01 && R.x > 1.8) { R.x -= Math.min(v, R.x - 1.75); }
      else if (Math.abs(dy) > 0.01) { R.y += Math.sign(dy) * Math.min(v, Math.abs(dy)); }
      else R.x += Math.sign(dx) * Math.min(v, Math.abs(dx));
    }
  }

  diseaseDetected() {
    this.flags.diseaseFound = true;
    const A = this.app;
    A.chain('SENSE');
    A.log('ROBOT', 'Scan of #042 (row 3, slab 2): 5 heights, 2 stereo images');
    A.log('AI', 'Vision: brown concentric leaf spots on 2 lower leaves → early blight suspected (confidence 0.87)');
    this.later(0.8, () => {
      A.chain('AI');
      A.log('AI', 'Plan: keep night VPD ≥ 0.55 kPa (less leaf wetness), HAF fans on, flag #042 + neighbours for rescans');
      A.log('PLC', '✓ climate targets inside limits');
      A.markPlant('plant_042');
      A.toast('Telegram → farmer', 'GH-01: plant #042 shows possible early blight on 2 lower leaves. Photo attached. Please inspect and remove those leaves.');
      A.log('FARMER', 'Photo + location sent · task "Inspect #042" created');
      A.sound.alarm();
      A.focusOn?.('plant_042');
    });
  }

  // ── scenarios ──────────────────────────────────────────────
  scenario(name) {
    const A = this.app;
    switch (name) {
      case 'irrigate':
        if ((this.t / 60) % 24 < 7 || (this.t / 60) % 24 > 18) { this.t = 11 * 60; A.log('OK', 'Clock moved to 11:00 for the irrigation demo'); }
        this.radSum = Math.max(this.radSum, 101);
        this.startIrrigation(true);
        break;
      case 'heat':
        this.heat = true; if ((this.t / 60) % 24 < 10 || (this.t / 60) % 24 > 16) { this.t = 12.5 * 60; }
        A.log('SENSE', 'Weather station: heat wave — outside 38 °C, RH 25 %, full sun');
        A.toast('Scenario', 'Heat wave. Watch the AI step up: vents → fans → wet pad → fog, and the hard-wired thermostat behind it.');
        break;
      case 'pump':
        this.faults.pump = true;
        A.log('OK', 'Scenario: pump fails silently (motor runs dry / seized)');
        this.scenario('irrigate');
        break;
      case 'sensor': {
        const n = Math.random() < 0.5 ? 0 : 1, v = n ? this.readings.box2 : this.readings.box1;
        this.faults.sensor = true;
        this.flags.boxStuck[n] = v;
        A.log('OK', `Scenario: climate box ${n + 1} freezes at ${v.toFixed(2)} °C (stuck value)`);
        A.toast('Scenario', `Climate sensor ${n + 1} froze. Live sensors flicker; a frozen one repeats the same number. Watch the PLC find it.`);
        break;
      }
      case 'water':
        this.w.supply = false; this.w.tank = Math.min(this.w.tank, 26); this.tankHist = [];   // the demo's jump isn't a trend
        this.faults.water = true;
        A.log('OK', 'Scenario: both water sources cut (pond pump and borewell) — tank is draining');
        A.toast('Scenario', 'Water supply cut. Watch the level sensor, then the hard-wired float switch.');
        this.later(4, () => this.scenario('irrigate'));
        break;
      case 'disease': {
        const p = this.data.plants.find((q) => q.id === 'plant_042');
        this.robot.override = 'disease';
        this.robot.stuck = false;
        this.robot.overrideTarget = { x: p.pos[0], y: this.data.robot.aisles_y[1], stop: true };
        this.robot.phase = 'move';
        A.log('ROBOT', 'Scouting plan changed: next scan row 3 (plant #042)');
        A.toast('Scenario', 'The robot drives to plant #042 and scans it.');
        break;
      }
      case 'robot':
        this.robot.stuck = true; this.faults.robot = true;
        A.chain('ALARM');
        A.log('ROBOT', `Bumper contact at aisle ${this.robot.y < 0 ? 1 : 2}, x = ${this.robot.x.toFixed(1)} m → motor power cut (hardware)`);
        A.log('ALARM', 'Robot heartbeat lost for 10 s → robot marked OFFLINE. Greenhouse control continues normally.');
        A.alarm('Robot stopped · bumper');
        A.flagComponent('scout_robot', 'fault');
        A.toast('Telegram → farmer', 'GH-01: scout robot stopped in the aisle (bumper). Climate + irrigation unaffected.');
        A.sound.alarm();
        A.focusOn?.('scout_robot');
        break;
      case 'power': {
        const h = (this.t / 60) % 24;
        const P = this.power;
        if (h < 14 || h > 17) {                    // after a sunny day the panels have filled the battery by 4 PM
          this.t = Math.floor(this.t / 1440) * 1440 + 16 * 60; P.soc = 1;
          A.log('OK', 'Clock moved to 16:00 for the power-cut demo (battery full after a sunny day)');
        }
        P.grid = false; P.cutUntil = this.t + 240;
        A.chain('ALARM');
        A.log('SENSE', 'Grid 0 V on all three phases: the farm feeder is off (4 hours)');
        if (P.solar) A.log('ACT', `Hybrid inverter → solar + battery in 20 ms. Nothing stopped. PV ${P.pv.toFixed(1)} kW · load ${P.load.toFixed(1)} kW · battery ${(P.soc * 100).toFixed(0)} %`);
        A.log('PLC', 'Load-shedding plan armed: below 30 % battery → reduced cooling; below 12 % → controller and alarms only');
        A.alarm(P.solar ? 'Grid power cut · running on solar + battery' : 'Grid power cut · NO POWER');
        A.flagComponent('hybrid_inverter', 'fault');
        A.toast('Scenario', 'Power cut for 4 hours, through sunset: the panels fade and the battery takes over. Watch the battery and the cooling.');
        A.toast('Telegram → farmer', P.solar ? `GH-01: grid power cut. Running on solar + battery (${(P.soc * 100).toFixed(0)} %). Cooling continues.`
          : 'GH-01: grid power cut. No backup power: fans and pad are OFF.');
        A.log('FARMER', 'Alert sent: grid power cut');
        A.sound.alarm();
        break;
      }
      case 'pond':
        this.w.pond = 20.3; this.w.tank = Math.min(this.w.tank, 32); this.w.refill = true; this.flags.pondLow = false;
        A.log('OK', 'Scenario: dry season, 7 weeks without rain — the farm pond is down to 20 %');
        A.toast('Scenario', 'April, no rain for 7 weeks: the pond is at 20 %. Watch the twin keep the last 20 % as a reserve and switch the tank to the borewell.');
        break;
      case 'reset':
        this.reset();
        A.flagComponent(null, null);
        break;
    }
  }

  // ── live data for the panel ────────────────────────────────
  live(id) {
    const r = this.readings, o = this.out, a = this.act, w = this.w;
    const on = (b) => (b ? 'ON' : 'OFF');
    const L = (rows, key, label) => ({ rows, spark: key ? { key, label } : null });
    const z = (n) => this.zones[n];
    if (id.startsWith('climate_box')) {
      const bad = this.flags.boxBad[+id.slice(-1) - 1];
      return L([['Air temp', `${(id.endsWith('1') ? r.box1 : r.box2).toFixed(1)} °C`], ['Humidity', `${r.RH.toFixed(0)} %`],
        ['VPD', `${r.vpd.toFixed(2)} kPa`], ['CO₂', `${r.CO2.toFixed(0)} ppm`], ['Leaves', this.leaf.wet ? `WET · ${(this.leaf.wetMin / 60).toFixed(1)} h in a row` : 'dry'],
        ['Fan', bad ? '— (stuck)' : '4 200 rpm'], ['Status', bad ? 'BAD · ignored' : 'OK']], 'T', 'Air temperature °C');
    }
    if (id === 'par_sensor') return L([['PPFD', `${r.ppfd.toFixed(0)} µmol/m²/s`], ['DLI today', `${this.dli.toFixed(1)} mol`], ['Target', '20–30 mol']], 'solar', 'Solar W/m²');
    if (id === 'weather_station') return L([['Outside', `${o.T.toFixed(1)} °C`], ['RH', `${o.RH.toFixed(0)} %`], ['Sun', `${o.solar.toFixed(0)} W/m²`], ['Wind', `${o.wind.toFixed(1)} m/s`], ['Rain', 'no']], 'Tout', 'Outside °C');
    if (id.includes('water_tank')) return L([['Level', `${w.tank.toFixed(0)} %`], ['Volume', `${(w.tank * 5).toFixed(0)} L`], ['Supply', w.supply ? 'ON (float valve)' : 'CUT'], ['LOW-LOW float', this.flags.tankLowLow ? 'OPEN → pumps locked' : 'closed']], 'tank', 'Tank %');
    if (id.includes('mix_tank')) return L([['Level', `${w.mix.toFixed(0)} %`], ['EC', `${w.ec.toFixed(2)} mS/cm`], ['pH', w.ph.toFixed(2)], ['Mixer', on(a.mixer)], ['Batch', this.mixing.phase]], 'mix', 'Mix tank %');
    if (id.startsWith('stock')) return L([['Level', id.endsWith('acid') ? '71 %' : '64 %'], ['Dosed today', `${Math.round(w.dosedML / 3)} mL`]]);
    if (id.startsWith('dosing_pump')) { const k = ['A', 'B', 'acid'].indexOf(id.split('_').pop()); return L([['Running', on(a.dosing[k])], ['Dosed today', `${Math.round(w.dosedML / 3)} mL`], ['Calibration', '1.60 mL/rev']]); }
    if (id === 'ph_probe') return L([['pH', w.ph.toFixed(2)], ['Target', '5.5–6.0'], ['Last calibration', '2026-09-01']], 'ph', 'pH');
    if (id === 'ec_probe' || id === 'sensor_flow_cell') return L([['EC', `${w.ec.toFixed(2)} mS/cm`], ['pH', w.ph.toFixed(2)], ['Temp', '23.4 °C']], 'ec', 'EC mS/cm');
    if (id === 'irrigation_pump') return L([['Running', on(a.pump)], ['Pressure', `${w.pressure.toFixed(1)} bar`], ['Current', a.pump ? (this.faults.pump ? '0.3 A (dry)' : '3.6 A') : '0 A'], ['Status', this.flags.irrBlocked ? 'FAULT · blocked' : this.faults.pump ? 'fault (hidden)' : 'OK']], 'flow', 'Flow L/min');
    if (id === 'flow_meter') return L([['Flow', `${w.flow.toFixed(2)} L/min`], ['Today', `${w.todayL.toFixed(0)} L`], ['Pulses/L', '450']], 'flow', 'Flow L/min');
    if (id === 'pressure_tx' || id === 'pressure_gauge') return L([['Pressure', `${w.pressure.toFixed(1)} bar`], ['Range', '0–10 bar']], 'flow', 'Flow L/min');
    if (id === 'disc_filter') return L([['Δp', `${(0.15 + (a.pump ? 0.05 : 0)).toFixed(2)} bar`], ['Clean in', '9 days']]);
    if (id.startsWith('zone_valve') || id.startsWith('row_')) { const n = +id.slice(-1) - 1; return L([['Valve', on(a.valve[n])], ['Slab water', `${z(n).wc.toFixed(0)} %`], ['Shots today', z(n).shots], ['Last shot', `${z(n).lastML} mL/plant`], ['Drain today', `${z(n).drain.toFixed(0)} %`], ['Slab EC', `${z(n).ec.toFixed(1)} mS/cm`]]); }
    if (id === 'drain_meter') return L([['Drain today', `${this.drainToday().toFixed(0)} %`], ['Drain EC', `${this.drainEC().toFixed(1)} mS/cm`], ['Target', '20–30 %'], ['A shot every', `${this.shotJ} J/cm² of sun`]]);
    if (id === 'slab_scale') return L([['Weight', `${this.slabWeight.toFixed(2)} kg`], ['Uptake', `${(o.solar / 1000 * 9).toFixed(1)} mL/min`], ['Water content', `${z(2).wc.toFixed(0)} %`]], 'w', 'Slab kg');
    if (id === 'substrate_sensor') return L([['Water content', `${z(2).wc.toFixed(0)} %`], ['Pore EC', `${z(2).ec.toFixed(1)} mS/cm`], ['Root temp', `${(r.T - 2.5).toFixed(1)} °C`]]);
    if (id.startsWith('exhaust_fan')) return L([['Stage', a.fans >= +id.slice(-1) ? 'ON' : 'OFF'], ['Speed', a.fans >= +id.slice(-1) ? '620 rpm' : '0'], ['Air changes', `${(1.5 + a.vent / 4 + a.fans * 55).toFixed(0)} /h`]], 'T', 'Air °C');
    if (id === 'cooling_pad') return L([['Pad mode', on(a.pad)], ['Pad pump', on(a.padPump)], ['Pad wet', `${(a.padWet * 100).toFixed(0)} %`], ['Air cooled by', a.padWet > 0.05 && a.fans ? `${(0.8 * a.padWet * (o.T - wetBulb(o.T, o.RH))).toFixed(1)} °C` : '—'], ['Inside RH', `${this.readings.RH.toFixed(0)} %`]], 'T', 'Air °C');
    if (id.startsWith('haf_fan')) return L([['Running', on(a.haf)], ['Air speed', '0.5 m/s']]);
    if (id === 'vent_drive' || id === 'greenhouse_structure') return L([['Vent', `${a.vent.toFixed(0)} %`], ['Inside', `${r.T.toFixed(1)} °C`], ['Outside', `${o.T.toFixed(1)} °C`], ['Wind', `${o.wind.toFixed(1)} m/s`]], 'T', 'Air °C');
    if (id === 'fog_pump' || id === 'fog_line') return L([['Fog', on(a.fog)], ['Line pressure', a.fog ? '70 bar' : '0 bar'], ['VPD', `${r.vpd.toFixed(2)} kPa`]], 'vpd', 'VPD kPa');
    if (id.startsWith('led_')) return L([['Lights', on(a.led)], ['Power', a.led ? '600 W' : '0 W'], ['DLI today', `${this.dli.toFixed(1)} mol`]], 'solar', 'Solar W/m²');
    if (id.startsWith('canopy_camera')) return L([['Canopy cover', '82 %'], ['Wilting index', (0.05 + r.vpd * 0.03).toFixed(2)], ['Last image', fmtT(this.t - (this.t % 15))]]);
    if (id.startsWith('sticky_trap')) { const tr = this.traps[+id.slice(-1) - 1]; return L([['Whitefly', tr.wf], ['Thrips', tr.th], ['Tuta moth', tr.tu], ['Card age', '9 days']]); }
    const P = this.power;
    const kw = (x) => `${(x * 1000).toFixed(0)} W`;
    if (id === 'solar_array') return L([['PV now', kw(P.pv)], ['Today', `${P.todayKWh.toFixed(1)} kWh`], ['Panels', '6 × 540 W (3.24 kWp)'], ['Facing', 'south, 13°']], 'pv', 'PV kW');
    if (id === 'hybrid_inverter') return L([['Mode', P.mode], ['Grid', P.grid ? 'ON' : `OFF · back at ${P.cutUntil !== null ? fmtT(P.cutUntil) : '—'}`], ['Load', kw(P.load)], ['PV', kw(P.pv)], ['Battery', P.battKW >= 0 ? `charging ${kw(P.battKW)}` : `supplying ${kw(-P.battKW)}`], ['Grid draw', kw(P.gridKW)]], 'soc', 'Battery %');
    if (id === 'battery_bank') {
      const left = P.battKW < 0 ? ((P.soc - 0.12) * 5.12) / -P.battKW : null;
      return L([['Charge', `${(P.soc * 100).toFixed(0)} %`], ['Energy', `${(P.soc * 5.12).toFixed(2)} kWh of 5.12`], ['Time left', left !== null ? `${Math.floor(left)} h ${Math.round((left % 1) * 60)} min at this load` : '— (not discharging)'], ['Mode', P.level], ['Reserve', '30 % kept for safety loads']], 'soc', 'Battery %');
    }
    if (id === 'power_panel') return L([['Grid', P.grid ? '230 V · ON' : 'OFF'], ['Load', kw(P.load)], ['Surge arresters', 'OK']]);
    if (id === 'farm_pond') return L([['Level', `${this.pondLevelM().toFixed(2)} m of 3.0`], ['Stored', `${(w.pond).toFixed(1)} % · ${Math.round(this.pondLitres()).toLocaleString('en-IN')} L`], ['Reserve', '20 % (kept for emergencies)'], ['Tank refills from', w.source === 'none' ? (this.flags.pondLow ? 'borewell (when needed)' : 'pond (when needed)') : w.source], ['Days of water', `${Math.max(0, (this.pondLitres() - 0.05 * 84000) / 350).toFixed(0)} at 350 L/day`]], 'pond', 'Pond %');
    if (id === 'level_pond') return L([['Distance to water', `${(1.2 + 3 - this.pondLevelM()).toFixed(2)} m`], ['Level', `${this.pondLevelM().toFixed(2)} m`], ['Node power', 'own solar panel']], 'pond', 'Pond %');
    if (id === 'pond_pump') return L([['Running', on(a.pondPump)], ['Flow', a.pondPump ? '≈ 25 L/min' : '0'], ['Pond', `${w.pond.toFixed(1)} %`], ['Rule', 'only above the 20 % reserve']], 'pond', 'Pond %');
    if (id === 'borewell') return L([['Running', on(a.borePump)], ['Role', 'backup source'], ['Tank refill', w.refill ? 'in progress' : 'idle']], 'tank', 'Tank %');
    if (id === 'source_valves') return L([['Pond valve', on(a.pondPump)], ['Borewell valve', on(a.borePump)]]);
    if (id === 'control_cabinet') return L([['Mode', 'AUTO'], ['Safety PLC', 'OK · 10 ms cycle'], ['Edge computer', 'OK · AI advising'], ['Alarms', this.app.alarmText || 'none'], ['UPS', '100 %']]);
    if (id.startsWith('esp32')) return L([['Wi-Fi', '−61 dBm'], ['Last message', '4 s ago'], ['Uptime', '312 h']]);
    if (id === 'farmer_tablet') return L([['Screen', 'Overview'], ['Alerts', this.app.alarmText ? 1 : 0]]);
    if (id === 'scout_robot') { const R = this.robot; return L([['Mode', R.stuck ? 'STOPPED' : R.phase === 'scan' ? 'scanning' : 'driving'], ['Aisle', R.y < 0 ? 1 : 2], ['Position', `x ${R.x.toFixed(1)} m`], ['Camera head', `${R.lift.toFixed(2)} m`], ['Battery', `${R.battery} %`], ['Plants today', R.scanned], ['Flowers pollinated', R.pollinated]]); }
    if (id === 'robot_dock') return L([['Robot docked', 'no'], ['Charger', 'standby']]);
    if (id.startsWith('plant_')) {
      const p = this.data.plants.find((q) => q.id === id);
      const sick = id === 'plant_042' && this.flags.diseaseFound;
      return L([['Plant', p ? p.tag : id], ['Place', p ? `row ${p.row} · slab ${p.slab} · slot ${p.slot}` : '—'], ['Stage', 'production · week 13'],
        ['Height', '1.85 m'], ['Growth', '24.5 cm/week'], ['Trusses', '7 (1 flowering)'], ['Fruit', '10 red · 5 turning · 11 green'],
        ['Water', `slab ${z(p ? p.row - 1 : 0).wc.toFixed(0)} % · uptake normal`], ['Health', sick ? 'EARLY BLIGHT SUSPECTED' : 'healthy'],
        ['Expected harvest', '0.9 kg · 2 Oct']]);
    }
    return L([]);
  }

  clock() { return `Day ${this.day} · ${fmtT(this.t)}`; }
}
