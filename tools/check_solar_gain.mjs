#!/usr/bin/env node
// Solar heat gain check for the GH-01 twin's climate model (js/sim.js). No dependencies: plain Node 18+.
//
//   node tools/check_solar_gain.mjs                    stage table: inside minus supply air at a clear noon
//   node tools/check_solar_gain.mjs --scenarios        also run every scenario button and print its key events
//   node tools/check_solar_gain.mjs --sim old/sim.js   check another copy of the model (e.g. `git show main:js/sim.js`)
//
// It loads the Sim class headless: sim.js has no imports and only talks to the page through the `app` object it is
// given, so a stub that swallows (or records) those calls is enough. No DOM, no three.js.
//
// 4 Nov 2026: written to reproduce a bug: in fan mode the sun barely warmed the house (rise ~10× too small).
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const argv = process.argv.slice(2);
const simFile = argv.includes('--sim') ? path.resolve(argv[argv.indexOf('--sim') + 1]) : path.join(ROOT, 'js/sim.js');
const { Sim } = await import(pathToFileURL(simFile).href);
const DATA = JSON.parse(readFileSync(path.join(ROOT, 'assets/sim.json'), 'utf8'));

// the page's `app` object, stubbed: log lines and toasts are recorded, everything else (3D pulses, sounds…) is a no-op
function stubApp(log = [], clock = () => '') {
  const noop = () => {};
  const sound = new Proxy({}, { get: () => noop });
  return new Proxy({}, {
    get(_, k) {
      if (k === 'log') return (lvl, msg) => log.push({ at: clock(), lvl, msg });
      if (k === 'toast') return (title, msg) => log.push({ at: clock(), lvl: 'TOAST', msg: `${title}: ${msg}` });
      if (k === 'alarm') return (msg) => { if (msg) log.push({ at: clock(), lvl: 'ALARMBAR', msg }); };
      if (k === 'sound') return sound;
      if (k === 'then') return undefined;
      return noop;
    },
  });
}

// ── 1. the model: hold each cooling stage at a clear noon until the air settles ─────────────────────────────────
const SOLAR = 900;                                         // W/m² outside, clear noon (outside air: the twin's noon, 27.6 °C)
const STAGES = [
  { name: 'vents only (100 %)', act: { vent: 100, fans: 0, pad: false, padPump: false } },
  { name: 'one fan', act: { vent: 0, fans: 1, pad: false, padPump: false } },
  { name: 'both fans', act: { vent: 0, fans: 2, pad: false, padPump: false } },
  { name: 'both fans + wet pad', act: { vent: 0, fans: 2, pad: true, padPump: true } },
];

function settle(stage, solar) {
  const sim = new Sim(stubApp(), DATA);
  sim.t = 720;
  const noon = { ...sim.weather(720), solar, cloud: 0, rain: 0 };
  sim.weather = () => ({ ...noon });                       // the weather stands still at noon
  const hold = () => Object.assign(sim.act, stage.act, { fog: false, fogMode: false, led: false });
  sim.climateControl = hold;                               // the controller is bypassed: the stage is held
  sim.irrigationTick = () => {};
  hold();
  for (let m = 0; m < 180; m++) sim.step(1);
  return { T: sim.inn.T, out: noon, vpd: sim.readings.vpd };
}

// ── 2. what it should be: a plain sensible-heat balance on the twin's own house ───────────────────────────────
// Rise = sun absorbed over the floor × (1 − share used for transpiration) ÷ (ρ·cp·airflow): the summer ventilation
// balance of ANSI/ASABE EP406 ("Heating, Ventilating and Cooling Greenhouses"). It leaves out the heat lost through the
// cover, so it is an upper bound, most of all for the vents-only stage (lowest airflow).
const H = DATA.house;                                      // 9.0 × 5.0 m, 3.0 m to the gutter, 4.2 m to the ridge
const AREA = H.L * H.W;                                    // 45 m² of floor
const VOL = H.L * H.W * H.GH + 0.5 * H.L * H.W * (H.RH - H.GH);   // 162 m³ (box + gable roof)
const RHO_CP = 1.2 * 1006;                                 // J/(m³·K), air
const TAU_ALPHA = 0.8;                                     // share of outside sun absorbed inside (the twin's own figure)
const E_CROP = 0.5;                                        // share of it the crop spends on transpiration: a fixed design
                                                           // value (0.5 and 1.0 are the two used in "Estimated viability of
                                                           // greenhouse cooling technologies for growing a tomato crop under
                                                           // various climates", Int. J. Agric. & Biol. Eng.). The twin's own
                                                           // share moves with VPD, so the two columns differ a little.
const achOf = (a) => 1.5 + (a.vent / 100) * 25 + a.fans * 55;     // air changes per hour, as in js/sim.js
const expected = (a, solar) => (solar * TAU_ALPHA * (1 - E_CROP) * AREA) / (RHO_CP * (achOf(a) * VOL / 3600));
// Fan-pad design guides: 8 cfm per ft² of floor (≈ 146 m³/h per m²) gives about 7–8 °F (≈ 4 °C) from pad to fans.
// Bucklin, Leary, McConnell & Wilkerson, "Fan and Pad Greenhouse Evaporative Cooling Systems", UF/IFAS EDIS CIR1135.
const GUIDE_FLOW = 8 * 0.3048 ** 3 * 60 / 0.3048 ** 2;     // 8 cfm/ft² → m³/h per m² (146.3)

console.log(`GH-01 solar gain check · ${path.relative(ROOT, simFile) || simFile}`);
console.log(`house ${H.L} × ${H.W} m = ${AREA} m² floor, ${VOL.toFixed(0)} m³ · clear noon ${SOLAR} W/m² outside\n`);
console.log('stage                  ACH/h  m³/h·m²  outside  supply  inside   rise (model)  rise (energy balance)');
for (const s of STAGES) {
  const lit = settle(s, SOLAR), dark = settle(s, 0);       // with no sun the house settles at the supply air
  const rise = lit.T - dark.T, ach = achOf(s.act);
  console.log(`${s.name.padEnd(22)} ${ach.toFixed(1).padStart(5)}  ${(ach * VOL / 3600 * 3600 / AREA).toFixed(0).padStart(7)}  `
    + `${lit.out.T.toFixed(1).padStart(7)}  ${dark.T.toFixed(1).padStart(6)}  ${lit.T.toFixed(1).padStart(6)}  `
    + `${rise.toFixed(2).padStart(10)} °C  ${expected(s.act, SOLAR).toFixed(2).padStart(8)} °C`);
}
console.log(`\nguide check: ${GUIDE_FLOW.toFixed(0)} m³/h per m² of floor → about 4 °C pad-to-fan rise (UF/IFAS CIR1135)`);

// ── 3. optional: play every scenario button and print what the farmer would see ─────────────────────────────
if (argv.includes('--scenarios')) {
  const NAMES = ['heat', 'irrigate', 'pump', 'sensor', 'water', 'disease', 'robot', 'power', 'pond', 'filter', 'stockA', 'bore',
    'storm', 'uv', 'net'];
  const KEY = /ALARM|PLC|FARMER|AI|TOAST|ALARMBAR/;
  const fmt = (m) => { m = ((m % 1440) + 1440) % 1440; return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(Math.floor(m % 60)).padStart(2, '0')}`; };
  for (const name of NAMES) {
    let seed = 42;                                         // same random draws every run (sensor noise, which box freezes…)
    Math.random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const log = [];
    let sim = null;
    sim = new Sim(stubApp(log, () => (sim ? fmt(sim.t) + ' ' : '')), DATA);
    sim.t = 690;
    for (let m = 0; m < 30; m++) sim.step(1);              // settle into the day first
    log.length = 0;
    const t0 = sim.t;
    sim.scenario(name);
    let maxT = -99, maxAt = 0;
    for (let s = 0; s < 6 * 60 * 4; s++) {                 // 6 sim-hours in 15-s ticks (the page runs 60× real time)
      sim.tick(0.25);
      if (sim.inn.T > maxT) { maxT = sim.inn.T; maxAt = sim.t; }
    }
    console.log(`\n── ${name} (from ${fmt(t0)}) · inside max ${maxT.toFixed(1)} °C at ${fmt(maxAt)}`);
    for (const l of log.filter((x) => KEY.test(x.lvl)).slice(0, 40)) console.log(`   ${l.at}${l.lvl.padEnd(8)} ${l.msg.slice(0, 150)}`);
  }
}
