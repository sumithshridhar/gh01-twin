// "Try to break it" (11 Nov 2026): the watering box's own rules, run in the browser, on a cut-open bed.
//
// decide() and watered() come from js/water_logic.js, a line-for-line port of the box's own water_logic.h; the same 16
// checks pass against both (tools/test_water_logic_js.mjs). The visitor breaks things (pulls the sensor cable, knocks a wire, flickers the power,
// empties the tank, hangs the program, sticks the valve) and sees what the box decides. Dark soil = real water.
// Red stripes = what a box WITHOUT that rule would have done. The one thing code can't fix (a valve stuck open) is
// shown as real water, stopped only by the hand tap.
import { CFG, WATER, SENSOR_BAD, DAY_CAP, LOCKED, newState, decide, watered } from './water_logic.js';

// ---------------------------------------------------------------- the panel
const el = document.createElement('aside');
el.className = 'hud';
el.id = 'breakit';
el.hidden = true;
el.innerHTML = `
  <h3>Try to break it<small>One box waters one bed. Break something and watch what it decides.</small></h3>
  <svg viewBox="0 0 332 196" role="img" aria-label="A bed cut open: the soil, the sensor, the drip lines and the water">
    <defs>
      <linearGradient id="bk-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8fc0e6"/><stop offset="1" stop-color="#d4e7f3"/></linearGradient>
      <pattern id="bk-stripe" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="12" height="12" fill="#ff3b1f" fill-opacity=".34"/><rect width="6" height="12" fill="#ff3b1f" fill-opacity=".9"/></pattern>
      <clipPath id="bk-soil"><path d="M0 110H98L108 62H224L234 110H332V196H0Z"/></clipPath>
    </defs>
    <rect width="332" height="196" fill="url(#bk-sky)"/>
    <path d="M0 110H98L108 62H224L234 110H332V196H0Z" fill="#7d3d24"/>
    <g clip-path="url(#bk-soil)">
      <g fill="#a35a3a" opacity=".5"><circle cx="40" cy="150" r="2"/><circle cx="92" cy="176" r="1.6"/><circle cx="150" cy="128" r="1.8"/><circle cx="210" cy="164" r="2"/><circle cx="270" cy="134" r="1.6"/><circle cx="300" cy="180" r="2"/><circle cx="182" cy="94" r="1.5"/></g>
      <ellipse id="bk-w1" cx="130" cy="66" rx="10" ry="12" fill="#2e130b" opacity=".78"/>
      <ellipse id="bk-w2" cx="202" cy="66" rx="10" ry="12" fill="#2e130b" opacity=".78"/>
      <rect id="bk-flood" x="0" y="196" width="332" height="0" fill="#2f78b3" opacity=".8"/>
      <circle id="bk-g1" cx="130" cy="64" r="0" fill="url(#bk-stripe)"/>
      <circle id="bk-g2" cx="202" cy="64" r="0" fill="url(#bk-stripe)"/>
    </g>
    <path d="M98 110L108 62H224L234 110" fill="none" stroke="#dfe3e8" stroke-width="3.5" stroke-linejoin="round"/>
    <path d="M0 110H98M234 110H332" stroke="#5e2c19" stroke-width="2"/>
    <g fill="#2f8f3f"><ellipse cx="118" cy="50" rx="13" ry="7"/><ellipse cx="140" cy="46" rx="12" ry="7"/><ellipse cx="130" cy="40" rx="10" ry="6"/>
      <ellipse cx="192" cy="46" rx="12" ry="7"/><ellipse cx="214" cy="50" rx="13" ry="7"/><ellipse cx="203" cy="40" rx="10" ry="6"/></g>
    <g fill="#e23a2e"><circle cx="112" cy="58" r="3.4"/><circle cx="146" cy="56" r="3"/><circle cx="220" cy="58" r="3.4"/><circle cx="188" cy="56" r="3"/></g>
    <circle cx="130" cy="61" r="3.6" fill="#15171a"/><circle cx="202" cy="61" r="3.6" fill="#15171a"/>
    <path d="M161 50H171V92L166 100L161 92Z" fill="#16181c"/><rect x="162.5" y="44" width="7" height="7" fill="#f2f2f0"/>
    <path id="bk-cable" d="M166 44C166 22 120 30 84 24C60 20 40 26 30 20" fill="none" stroke="#16181c" stroke-width="2.2" stroke-linecap="round"/>
    <g font-family="system-ui,sans-serif" font-size="9.5" fill="#0f2233"><rect x="8" y="6" width="34" height="24" rx="4" fill="#e9edf0" stroke="#55606a"/><text x="13" y="21">BOX</text></g>
    <path d="M0 132H98" stroke="#b9bfc6" stroke-width="5"/>
    <rect id="bk-valve" x="50" y="122" width="20" height="20" rx="3" fill="#6fd08c" stroke="#10151a"/>
    <g id="bk-tap" transform="rotate(0 24 132)"><rect x="19" y="127" width="10" height="10" fill="#c9a24a" stroke="#10151a"/><rect x="12" y="120" width="24" height="5" rx="2" fill="#e0392b"/></g>
    <g font-family="system-ui,sans-serif" font-size="9" fill="#f3e9e2"><text x="10" y="156">hand tap</text><text x="50" y="156">valve</text><text x="176" y="84">sensor</text></g>
  </svg>
  <div id="bk-key"><span><i style="background:#2e130b"></i>water in the soil</span><span><i style="background:#ff3b1f"></i>a box without this rule</span></div>
  <div id="bk-stat"><div><i>Soil reading</i><b id="bk-soilv">–</b></div><div><i>Valve</i><b id="bk-valvev" class="shut">SHUT</b></div><div><i>Box clock</i><b id="bk-clock">0:00</b></div></div>
  <div id="bk-say"><b>Normal day</b>The box reads the soil once a minute.</div>
  <div id="bk-btns">
    <button data-b="cable" aria-pressed="false">🔌 Pull the sensor cable</button>
    <button data-b="knock">👋 Knock a wire (1 wrong reading)</button>
    <button data-b="power">⚡ Flicker the power</button>
    <button data-b="tank" aria-pressed="false">🪣 Empty the tank</button>
    <button data-b="hang">🧊 Hang the program</button>
    <button data-b="stuck" aria-pressed="false">🔧 Stick the valve open</button>
    <button data-b="tap" class="fix" hidden>✋ Turn the hand tap shut</button>
    <button data-b="reset" class="fix">↺ Reset</button>
  </div>
  <div id="bk-foot">These are the box's real rules (<a href="https://github.com/sumithshridhar/gh01-twin/blob/main/build/03-auto-watering/auto_water/water_logic.h" target="_blank" rel="noopener">water_logic.h</a>) running in your browser. They pass 16 checks on a laptop. They have not run on a real board yet.</div>`;
document.getElementById('app').appendChild(el);
const $ = (q) => el.querySelector(q);

// ---------------------------------------------------------------- a small world for the rules to run in
let W, C;
function reset() {
  holdUntil = ghostHold = 0;
  W = { t: 0, soil: 1980, tank: true, cable: true, knock: false, stuck: false, tapShut: false, hungUntil: 0, flood: 0, ghost: 0, ghostWant: 0, lastRaw: 1980 };
  C = { st: newState(), bootAt: -CFG.bootWaitMs, nextRead: 2000, valveOpen: false, valveUntil: 0, rawBefore: 0 };
  el.querySelectorAll('[aria-pressed]').forEach((b) => b.setAttribute('aria-pressed', 'false'));
  $('[data-b=tap]').hidden = true;
  say('Normal day', 'The box reads the soil once a minute. Water only goes on after three dry readings in a row.');
}
let holdUntil = 0, ghostHold = 0;                       // an important message (and its red ghost) stays up for a few real seconds
function say(title, text, tone = '', hold = 0) {
  if (!hold && performance.now() < holdUntil) return;
  holdUntil = hold ? performance.now() + hold * 1000 : 0;
  const s = $('#bk-say');
  s.className = tone;
  s.innerHTML = `<b>${title}</b>${text}`;
}
const mins = (ms) => Math.max(1, Math.round(ms / 60e3));
const reading = () => { if (!W.cable) return 4095; if (W.knock) { W.knock = false; return 3150; } return Math.round(W.soil); };

function reboot(why, hold = 0) {
  C.valveOpen = false;                                  // a restart always starts with the valve shut
  C.bootAt = W.t;
  C.st.dryReads = 0;
  C.st.checkEffect = false;
  C.nextRead = W.t + 5000;
  say(why, 'A restart always begins with the valve shut. Then no watering for 30 minutes, so flickering power can never flood the bed.', 'warn', hold);
}

function control() {
  if (W.hungUntil) {                                    // the program is frozen: only the watchdog can act
    if (W.t >= W.hungUntil) { W.hungUntil = 0; W.ghostWant = 0; reboot('Watchdog restarted the board', 5); }
    return;
  }
  if (C.valveOpen && W.t >= C.valveUntil) {
    C.valveOpen = false;
    watered(CFG, C.st, C.rawBefore, W.t);
    C.nextRead = W.t + CFG.soakMs;
    say('Watered for 60 seconds', 'Now it waits 30 minutes for the water to reach the sensor, then checks that the soil really got wetter.');
    return;
  }
  if (C.valveOpen || W.t < C.nextRead) return;
  const raw = reading(), sinceBoot = W.t - C.bootAt, wasLocked = C.st.locked;
  W.lastRaw = raw;
  const d = decide(CFG, C.st, raw, W.t, sinceBoot);
  C.nextRead = W.t + d.waitMs;
  if (performance.now() > ghostHold) W.ghostWant = 0;
  if (d.act === SENSOR_BAD) {
    W.ghostWant = 1;
    say('Impossible reading: valve stays shut', `The sensor says ${raw}, which no soil can give. The cable is out or the sensor is broken. It never waters on that, and checks again in ${mins(d.waitMs)} minutes.`, 'bad');
  } else if (d.act === WATER) {
    C.valveOpen = true;
    C.valveUntil = W.t + CFG.waterMs;
    C.rawBefore = raw;
    say('Three dry readings in a row', 'The soil is really dry. The valve opens for 60 seconds.');
  } else if (d.act === LOCKED) {
    if (!wasLocked) say('Stopped, and it tells you', 'It watered twice and the soil did not get wetter. The water is not arriving: empty tank, blocked line, or the sensor is out of the soil. It stops and sends you a message. It starts again once the soil reads wet.', 'bad');
  } else if (d.act === DAY_CAP) {
    say('Enough for today', `It has watered ${CFG.maxPerDay} times in 24 hours. It stops for the day and tells you.`, 'warn');
  } else if (raw <= CFG.thirsty) {
    say(wasLocked ? 'Soil is wet again: back to work' : 'Soil is wet enough', 'Nothing to do. It reads again in a minute.');
  } else if (sinceBoot < CFG.bootWaitMs) {
    W.ghostWant = 0.7;
    say('Power just came back: it waits', `The soil reads dry, but the power came back ${mins(sinceBoot)} minutes ago. No watering for the first 30 minutes after power-up.`, 'warn');
  } else {
    if (raw > CFG.dry) {                                // a knocked wire: one wild reading
      W.ghostWant = 0.4;
      ghostHold = performance.now() + 2200;
      say('One wrong reading: ignored', `The sensor jumped to ${raw} for one reading. A box without this rule would open the valve now. This one counts "dry 1 of 3", and the next good reading sets the count back to zero.`, 'warn', 5);
    } else say(`Dry reading ${C.st.dryReads} of 3`, 'One dry reading is not enough: it could be a loose wire or a hand on the sensor. It needs three in a row.', 'warn');
  }
}

function step(ds) {                                      // ds = simulated ms
  W.t += ds;
  const m = ds / 60e3;
  const flowing = (C.valveOpen || W.stuck) && W.tank && !W.tapShut;
  if (flowing) W.soil = Math.max(CFG.wet, W.soil - 430 * m); else W.soil = Math.min(CFG.dry, W.soil + 9 * m);
  if (W.stuck && flowing && W.soil <= CFG.wet + 30) W.flood = Math.min(1, W.flood + 0.035 * m);
  else if (!flowing) W.flood = Math.max(0, W.flood - 0.004 * m);
  control();
}

function press(b) {
  const k = b.dataset.b;
  if (k === 'reset') return reset();
  if (k === 'cable') {
    W.cable = !W.cable;
    b.setAttribute('aria-pressed', String(!W.cable));
    if (W.cable) { W.ghostWant = 0; say('Cable back in', 'Real readings again. It carries on.'); }
  } else if (k === 'knock') {
    W.knock = true;
    W.soil = Math.min(W.soil, 1950);                    // the bed itself is fine: only the reading is wrong
  } else if (k === 'power') {
    W.soil = Math.max(W.soil, 2400);                    // the worst moment: the bed is dry when the power comes back
    reboot('Power flickered');
  } else if (k === 'tank') {
    W.tank = !W.tank;
    b.setAttribute('aria-pressed', String(!W.tank));
    if (!W.tank) { W.soil = Math.max(W.soil, 2300); say('Tank is empty', 'The bed is getting dry and no water will come. Watch what it does after two tries.', 'warn', 3); }
    else say('Tank refilled', C.st.locked ? 'It stays stopped until the soil reads wet again: water the bed by hand once, or wait for the next good reading.' : 'Water is back.');
  } else if (k === 'hang') {
    C.valveOpen = true;                                 // the worst case: it freezes with the valve open
    C.valveUntil = Infinity;
    W.hungUntil = W.t + 30e3;
    W.ghostWant = 1;
    say('Program frozen, valve open', 'Nothing in the program can close it now. A separate watchdog timer is counting: 30 seconds without a sign of life and it restarts the board.', 'bad');
  } else if (k === 'stuck') {
    W.stuck = !W.stuck;
    W.tapShut = false;
    b.setAttribute('aria-pressed', String(W.stuck));
    $('[data-b=tap]').hidden = !W.stuck;
    if (W.stuck) say('Valve stuck open: code cannot fix this', 'The box says "shut" and the water keeps running. No program can close a jammed valve. That is why the hand tap stays on the line. (Still unsolved: a flow meter that notices.)', 'bad', 600);
    else say('Valve freed', 'The valve answers the box again.', '', 3);
  } else if (k === 'tap') {
    W.tapShut = true;
    b.hidden = true;
    say('Hand tap shut', 'A person stopped the water. The box could not. Every part of GH-01 has to leave a person able to take over.', 'warn', 9);
  }
  if (k !== 'hang') C.nextRead = Math.min(C.nextRead, W.t + 4000);
}
el.addEventListener('click', (e) => { const b = e.target.closest('#bk-btns button'); if (b) press(b); });

// ---------------------------------------------------------------- draw
let last = 0;
function draw(now) {
  requestAnimationFrame(draw);
  if (el.hidden) { last = 0; return; }
  const dt = Math.min(0.1, last ? (now - last) / 1000 : 0);
  last = now;
  // one simulated minute every quarter second; slowed right down while water is moving or the program is frozen
  const speed = W.hungUntil ? 9 : (C.valveOpen ? 24 : 240);
  let left = dt * speed * 1000;
  while (left > 0) { const ds = Math.min(left, 5000); step(ds); left -= ds; }
  W.ghost += (W.ghostWant - W.ghost) * Math.min(1, dt * (W.ghostWant > W.ghost ? 1.6 : 5));
  const wet = Math.max(0, Math.min(1, (CFG.dry - W.soil) / (CFG.dry - CFG.wet)));
  const r = 8 + 50 * wet;
  for (const id of ['#bk-w1', '#bk-w2']) { $(id).setAttribute('rx', r.toFixed(1)); $(id).setAttribute('ry', (r * 1.15).toFixed(1)); }
  const g = W.ghost * 150;
  $('#bk-g1').setAttribute('r', g.toFixed(1));
  $('#bk-g2').setAttribute('r', g.toFixed(1));
  const fh = W.flood * 140;
  $('#bk-flood').setAttribute('y', (196 - fh).toFixed(1));
  $('#bk-flood').setAttribute('height', fh.toFixed(1));
  const open = C.valveOpen || W.stuck;
  $('#bk-valve').setAttribute('fill', W.stuck ? '#ff5a3c' : (open ? '#45c6e6' : '#6fd08c'));
  $('#bk-tap').setAttribute('transform', `rotate(${W.tapShut ? 90 : 0} 24 132)`);
  $('#bk-cable').setAttribute('d', W.cable ? 'M166 44C166 22 120 30 84 24C60 20 40 26 30 20' : 'M186 56C176 30 126 34 84 24C60 20 40 26 30 20');
  const sv = $('#bk-soilv'), raw = W.cable ? Math.round(W.soil) : 4095;
  sv.textContent = W.cable ? `${raw} · ${raw > CFG.thirsty ? 'dry' : 'ok'}` : '4095 · no signal';
  sv.className = !W.cable ? 'bad' : '';
  const vv = $('#bk-valvev');
  vv.textContent = W.stuck ? (W.tapShut ? 'STUCK · TAP SHUT' : 'STUCK OPEN') : (C.valveOpen ? 'OPEN' : 'SHUT');
  vv.className = W.stuck ? 'bad' : (C.valveOpen ? 'open' : 'shut');
  const tm = Math.floor(W.t / 60e3);
  $('#bk-clock').textContent = `${Math.floor(tm / 60)}:${String(tm % 60).padStart(2, '0')}`;
}
reset();
requestAnimationFrame(draw);
addEventListener('gh-scene', (e) => {
  const on = e.detail === 'water';
  if (on && el.hidden) reset();
  el.hidden = !on;
});
