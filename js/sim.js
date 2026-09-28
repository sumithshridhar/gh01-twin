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
    this.act = { vent: 35, fans: 0, pad: false, fog: false, haf: true, led: false, pump: false, valve: [false, false, false],
      dosing: [false, false, false], mixer: false };
    this.w = { tank: 72, mix: 58, ec: 3.02, ph: 5.84, flow: 0, pressure: 0, todayL: 212, dosedML: 780, supply: true,
      targetEC: 3.0, targetPH: 5.8 };
    this.zones = [0, 1, 2].map((i) => ({ wc: 64 + i, shots: 7 + i % 2, drain: 18 + i * 2, lastML: 180 }));
    this.radSum = 62;
    this.irrHold = 0;
    this.dli = 14.2;
    this.faults = { pump: false, sensor: false, water: false, robot: false, disease: false, filter: false };
    this.flags = { box1Stuck: null, box1Fault: false, sensorWarned: false, hardThermo: false, tankLow: false, tankLowLow: false,
      irrBlocked: false, diseaseFound: false, robotAlarm: false };
    this.irr = { phase: 'idle', zone: 0, t0: 0, dur: 5.4, vol: 180, confirmed: false, startReal: 0, retry: 0 };
    this.mixing = { phase: 'idle', t0: 0 };
    this.fogCycle = 0;
    this.lastClimateLog = '';
    this.robot = { x: 4.6, y: -0.8, lift: 1.1, wp: 3, route: this.makeRoute(), phase: 'move', timer: 0, scanning: false,
      battery: 76, scanned: 31, pollinated: 118, stuck: false, override: null, puff: 0 };
    this.traps = [{ wf: 23, th: 4, tu: 1 }, { wf: 17, th: 6, tu: 0 }, { wf: 9, th: 2, tu: 1 }];
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
    const box1 = this.flags.box1Stuck ?? T - 0.1;
    const box2 = T + this.box2off;
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
    if (this.t >= 1440) { this.t -= 1440; this.day++; this.dli = 0; }
    const o = this.out = this.weather(this.t);
    const a = this.act, i = this.inn;
    // ── climate physics (exponential integration → stable at any speed)
    const fansOn = a.fans;
    const ach = 1.5 + (a.vent / 100) * 25 + fansOn * 55;                          // air changes per hour
    const k = ach / 60;
    const padOn = a.pad && fansOn > 0;
    const Tsup = padOn ? o.T - 0.8 * (o.T - wetBulb(o.T, o.RH)) : o.T;
    const eOut = (o.RH / 100) * es(o.T);
    const eSup = padOn ? Math.min(es(Tsup) * 0.9, eOut + 1.4) : eOut;
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
    // ── roots: transpiration dries the slabs
    for (const z of this.zones) z.wc = clamp(z.wc - dt * (0.045 * sun * (0.6 + vpd) + 0.002), 35, 90);
    // ── water
    if (this.w.supply && this.w.tank < 90) this.w.tank = Math.min(90, this.w.tank + 0.35 * dt);
    if (!this.w.supply) this.w.tank = Math.max(0, this.w.tank - 0.9 * dt);
    this.climateControl(dt);
    this.irrigationTick(dt);
    this.mixTick(dt);
    this.faultChecks(dt);
    this.traps.forEach((tr) => { if (Math.random() < dt * 0.004) tr.wf++; });
    if (Math.floor(this.t) % 5 === 0 && this.lastHist !== Math.floor(this.t)) {
      this.lastHist = Math.floor(this.t);
      const r = this.readings;
      this.hist.push({ t: this.t, T: r.T, RH: r.RH, vpd: r.vpd, solar: o.solar, Tout: o.T, tank: this.w.tank, mix: this.w.mix,
        w: this.slabWeight, ec: this.w.ec, ph: this.w.ph, flow: this.w.flow, co2: r.CO2 });
      if (this.hist.length > 400) this.hist.shift();
    }
  }

  get slabWeight() { return 15.6 + this.zones[2].wc * 0.095; }

  // ── climate: AI proposes, PLC checks ───────────────────────
  climateControl(dt) {
    const r = this.readings, o = this.out, a = this.act;
    const Tctl = this.flags.box1Fault ? r.box2 : (r.box1 + r.box2) / 2;
    const day = o.solar > 40;
    const target = day ? 24 : 18.5;
    const fut = this.weather(this.t + 60).T;
    const p = { vent: a.vent, fans: 0, pad: false, fog: false, fogMode: false, led: false, why: '' };
    if (day) {
      p.vent = clamp(18 + (Tctl - target) * 28, 5, 100);
      // staged fan control with hysteresis (on at the upper threshold, off only 1–1.2 °C lower)
      const pre = fut > 32 && Tctl > 25.5;
      let fans = a.fans;
      if (fans === 0 && (Tctl > 26.8 || pre)) fans = 1;
      if (fans >= 1 && Tctl > 28.2) fans = 2;
      if (fans === 2 && Tctl < 27.0) fans = 1;
      if (fans >= 1 && Tctl < 25.6 && !pre) fans = 0;
      p.fans = fans;
      p.pad = fans === 2 ? r.RH < 82 : a.pad && fans >= 1 && Tctl > 26.4 && r.RH < 85;
      if (fans !== a.fans || p.pad !== a.pad) {
        p.why = fans === 2 ? `air ${Tctl.toFixed(1)} °C > 28.2 → both fans + wet pad`
          : fans === 1 ? (pre && Tctl <= 26.8 ? `forecast ${fut.toFixed(0)} °C in 1 h → pre-cool` : `air ${Tctl.toFixed(1)} °C (stage 1 band 25.6–28.2)`)
          : `air ${Tctl.toFixed(1)} °C < 25.6 → natural ventilation`;
      }
      if (p.fans > 0) p.vent = 0;                                       // fan-pad mode needs a closed house
      const fogWant = a.fogMode ? r.vpd > 1.2 && Tctl > 25 && r.RH < 76 : r.vpd > 1.45 && Tctl > 25.5 && r.RH < 70;
      if (fogWant) { p.fogMode = true; this.fogCycle += dt; p.fog = this.fogCycle % 8 < 2; if (!p.why || p.fans === 0) p.why = `VPD ${r.vpd.toFixed(2)} kPa too dry → fog pulses (2 min of every 8)`; }
      p.led = this.cloud > 0.55;
    } else {
      p.vent = r.RH > 88 ? 12 : 4;
      if (r.RH > 88 && !p.why) p.why = `night RH ${r.RH.toFixed(0)} % → crack vents (disease risk)`;
    }
    if (this.flags.diseaseFound && r.vpd < 0.55) { p.vent = Math.max(p.vent, 20); p.why = p.why || 'disease plan: keep VPD ≥ 0.55 kPa'; }
    // PLC limits
    let plcNote = '';
    if (o.wind > 10) { p.vent = Math.min(p.vent, 10); plcNote = 'wind > 10 m/s → vent limited to 10 %'; }
    if (p.pad && p.fans === 0) { p.pad = false; plcNote = 'pad needs fans'; }
    if (p.fog && r.RH > 85) { p.fog = false; p.fogMode = false; plcNote = 'fog blocked: RH > 85 %'; }
    // hard-wired thermostat (independent of AI + PLC program)
    if (Tctl >= 35) {
      p.fans = 2; p.pad = true; p.vent = 0;
      if (!this.flags.hardThermo) {
        this.flags.hardThermo = true;
        this.app.log('ALARM', `HARD-WIRED thermostat: ${Tctl.toFixed(1)} °C ≥ 35 °C → both fans + pad forced ON`);
        this.app.alarm('High temperature · hard-wired cooling ON');
        this.app.sound.alarm();
      }
    } else if (this.flags.hardThermo && Tctl < 33) { this.flags.hardThermo = false; this.app.alarm(null); }
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
  }

  // ── irrigation ─────────────────────────────────────────────
  startIrrigation(forced = false) {
    if (this.irr.phase !== 'idle') return;
    const r = this.readings;
    const drain = this.zones.reduce((s, z) => s + z.drain, 0) / 3;
    const vol = Math.round((150 + 60 * clamp(r.vpd - 0.8, 0, 1) + (drain < 20 ? 20 : 0)) / 10) * 10;
    this.irr = { ...this.irr, phase: 'deciding', vol, zone: 0, retry: this.irr.retry || 0 };
    const A = this.app;
    const id = (this.irrCycle = (this.irrCycle || 0) + 1);   // steps of an older request must not act on this one
    const later = (s, fn) => this.later(s, () => { if (this.irrCycle === id) fn(); });
    A.chain('SENSE');
    A.log('SENSE', `${forced ? 'Manual request · ' : ''}radiation sum ${this.radSum.toFixed(0)} J/cm² · slab 3 weight ${this.slabWeight.toFixed(2)} kg · VPD ${r.vpd.toFixed(2)}`);
    ['par_sensor', 'slab_scale', 'weather_station', 'substrate_sensor', 'drain_meter'].forEach((s) => A.pulse(s, 'control_cabinet', 'sense'));
    later(1.0, () => A.chain('DATA'));
    later(1.6, () => { A.chain('AI'); A.log('AI', `Irrigate zones 1→3: ${vol} mL per plant (VPD ${r.vpd.toFixed(2)} kPa, drain ${drain.toFixed(0)} % → target 25 %)`); });
    later(2.4, () => A.chain('DECIDE'));
    later(3.0, () => {
      A.chain('PLC');
      const w = this.w;
      if (this.flags.tankLowLow || w.tank < 8) { this.block('LOW-LOW float open (hard-wired) — pump cannot start'); return; }
      if (this.flags.irrBlocked) { this.block('irrigation blocked until the pump fault is cleared'); return; }
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
    if (irr.phase === 'idle' && this.radSum >= 100 && h > 7.5 && h < 17.5 && !this.flags.irrBlocked && !this.flags.tankLowLow &&
      this.realT > (this.irrHold || 0)) this.startIrrigation();
    if (irr.phase !== 'running') { a.pump = false; a.valve = [false, false, false]; w.flow = 0; w.pressure = Math.max(0, w.pressure - dt * 3); return; }
    const z = irr.zone;
    a.pump = true;
    a.valve = [z === 0, z === 1, z === 2];
    const pumpOK = !this.faults.pump && !this.flags.tankLowLow;
    w.flow = pumpOK ? 0.6 * (1 - (this.faults.filter ? 0.5 : 0)) : 0;           // L/min at the meter (18 drippers × 2 L/h)
    w.pressure = pumpOK ? 2.1 : 0;
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
    zz.wc = Math.min(90, zz.wc + dt * 0.75);
    if (zz.wc > 70) zz.drain = Math.min(40, zz.drain + dt * 0.3);
    if (this.t - irr.t0 >= irr.dur) {
      zz.shots++; zz.lastML = irr.vol;
      if (z < 2) {
        irr.zone++; irr.t0 = this.t; irr.confirmed = false; irr.startReal = this.realT;
        this.app.log('ACT', `Zone ${z + 1} done (${irr.vol} mL/plant) → valve ${z + 2} OPEN`);
        this.app.pulse('control_cabinet', `zone_valve_${z + 2}`, 'cmd');
      } else {
        irr.phase = 'idle'; this.radSum = 0; irr.retry = 0;
        this.app.log('OK', `Cycle complete · 54 plants × ${irr.vol} mL · slab 3 now ${this.slabWeight.toFixed(2)} kg · next by radiation sum`);
        this.app.chain(null);
        this.app.sound.chime();
      }
    }
  }

  pumpFailed() {
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
    if (this.faults.sensor && !f.box1Fault) {
      f.box1Stuck = f.box1Stuck ?? this.readings.box1;
      const r = this.readings;
      if (!f.sensorWarned && Math.abs(r.box1 - r.box2) > 1.2) {
        f.box1Fault = true; f.sensorWarned = true;
        this.app.chain('ALARM');
        this.app.log('SENSE', `Climate box 1 reads ${r.box1.toFixed(1)} °C unchanged for 20 min; box 2 reads ${r.box2.toFixed(1)} °C`);
        this.app.log('PLC', 'Plausibility check failed (stuck value + disagreement > 1.2 °C) → box 1 marked BAD, control uses box 2');
        this.app.flagComponent('climate_box_1', 'fault');
        this.app.alarm('Sensor fault · climate box 1');
        this.app.toast('Telegram → farmer', 'GH-01: climate sensor 1 is stuck. Running on sensor 2. Check its fan / cable.');
        this.app.log('FARMER', 'Alert sent: sensor fault (control continues on box 2)');
        this.app.sound.alarm();
        this.app.focusOn?.('climate_box_1');
      }
    }
    if (w.tank < 20 && !f.tankLow) {
      f.tankLow = true;
      this.app.log('SENSE', `Ultrasonic level ${w.tank.toFixed(0)} % (LOW)`);
      this.app.log('AI', 'Ration mode: shorter shots, skip one cycle until refilled');
      this.app.toast('Telegram → farmer', `GH-01: fresh-water tank at ${w.tank.toFixed(0)} %. Supply looks off.`);
      this.app.pulse('level_water_tank', 'control_cabinet', 'sense');
    }
    if (w.tank < 8 && !f.tankLowLow) {
      f.tankLowLow = true;
      this.app.chain('ALARM');
      this.app.log('ALARM', 'LOW-LOW float switch OPEN → pump contactor coil cut in hardware (no software involved)');
      this.app.alarm('Water shortage · pumps locked out');
      this.app.flagComponent('water_tank', 'fault');
      this.app.sound.alarm();
      this.app.focusOn?.('water_tank');
    }
    if (w.tank > 25 && f.tankLowLow) { f.tankLowLow = false; f.tankLow = false; this.app.alarm(null); this.app.flagComponent('water_tank', null); this.app.log('OK', 'Tank refilled → float closed, pumps released'); }
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
      case 'sensor':
        this.faults.sensor = true;
        this.flags.box1Stuck = this.readings.box1 - 2.5;
        A.log('OK', 'Scenario: climate box 1 stops updating (stuck value)');
        A.toast('Scenario', 'Climate sensor 1 froze. The PLC cross-checks it against sensor 2.');
        break;
      case 'water':
        this.w.supply = false; this.w.tank = Math.min(this.w.tank, 26);
        this.faults.water = true;
        A.log('OK', 'Scenario: borewell supply cut — tank is draining');
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
      const bad = id.endsWith('1') && this.flags.box1Fault;
      return L([['Air temp', `${(id.endsWith('1') ? r.box1 : r.box2).toFixed(1)} °C`], ['Humidity', `${r.RH.toFixed(0)} %`],
        ['VPD', `${r.vpd.toFixed(2)} kPa`], ['CO₂', `${r.CO2.toFixed(0)} ppm`], ['Fan', bad ? '— (stuck)' : '4 200 rpm'], ['Status', bad ? 'BAD · ignored' : 'OK']], 'T', 'Air temperature °C');
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
    if (id.startsWith('zone_valve') || id.startsWith('row_')) { const n = +id.slice(-1) - 1; return L([['Valve', on(a.valve[n])], ['Slab water', `${z(n).wc.toFixed(0)} %`], ['Shots today', z(n).shots], ['Last shot', `${z(n).lastML} mL/plant`], ['Drain', `${z(n).drain.toFixed(0)} %`]]); }
    if (id === 'drain_meter') return L([['Drain today', `${(this.zones.reduce((s, q) => s + q.drain, 0) / 3).toFixed(0)} %`], ['Drain EC', `${(w.ec + 0.9).toFixed(1)} mS/cm`], ['Target', '20–30 %']]);
    if (id === 'slab_scale') return L([['Weight', `${this.slabWeight.toFixed(2)} kg`], ['Uptake', `${(o.solar / 1000 * 9).toFixed(1)} mL/min`], ['Water content', `${z(2).wc.toFixed(0)} %`]], 'w', 'Slab kg');
    if (id === 'substrate_sensor') return L([['Water content', `${z(2).wc.toFixed(0)} %`], ['Pore EC', `${(w.ec + 1.1).toFixed(1)} mS/cm`], ['Root temp', `${(r.T - 2.5).toFixed(1)} °C`]]);
    if (id.startsWith('exhaust_fan')) return L([['Stage', a.fans >= +id.slice(-1) ? 'ON' : 'OFF'], ['Speed', a.fans >= +id.slice(-1) ? '620 rpm' : '0'], ['Air changes', `${(1.5 + a.vent / 4 + a.fans * 55).toFixed(0)} /h`]], 'T', 'Air °C');
    if (id === 'cooling_pad') return L([['Pad pump', on(a.pad)], ['Air cooled by', a.pad ? `${(0.8 * (o.T - wetBulb(o.T, o.RH))).toFixed(1)} °C` : '—'], ['Outside RH', `${o.RH.toFixed(0)} %`]], 'T', 'Air °C');
    if (id.startsWith('haf_fan')) return L([['Running', on(a.haf)], ['Air speed', '0.5 m/s']]);
    if (id === 'vent_drive' || id === 'greenhouse_structure') return L([['Vent', `${a.vent.toFixed(0)} %`], ['Inside', `${r.T.toFixed(1)} °C`], ['Outside', `${o.T.toFixed(1)} °C`], ['Wind', `${o.wind.toFixed(1)} m/s`]], 'T', 'Air °C');
    if (id === 'fog_pump' || id === 'fog_line') return L([['Fog', on(a.fog)], ['Line pressure', a.fog ? '70 bar' : '0 bar'], ['VPD', `${r.vpd.toFixed(2)} kPa`]], 'vpd', 'VPD kPa');
    if (id.startsWith('led_')) return L([['Lights', on(a.led)], ['Power', a.led ? '600 W' : '0 W'], ['DLI today', `${this.dli.toFixed(1)} mol`]], 'solar', 'Solar W/m²');
    if (id.startsWith('canopy_camera')) return L([['Canopy cover', '82 %'], ['Wilting index', (0.05 + r.vpd * 0.03).toFixed(2)], ['Last image', fmtT(this.t - (this.t % 15))]]);
    if (id.startsWith('sticky_trap')) { const tr = this.traps[+id.slice(-1) - 1]; return L([['Whitefly', tr.wf], ['Thrips', tr.th], ['Tuta moth', tr.tu], ['Card age', '9 days']]); }
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
