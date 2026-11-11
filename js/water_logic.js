// The watering box's decisions, for the browser: a line-for-line port of build/03-auto-watering/auto_water/water_logic.h.
// No DOM in here, so the same 16 checks that test the C++ run against it: node tools/test_water_logic_js.mjs
//
// The rule behind every line: when something is wrong, the valve stays shut and a person is told.
export const CFG = { dry: 2900, wet: 1250, thirsty: 2075, slack: 400, needDryReads: 3, minChange: 60, maxNoEffect: 2, maxPerDay: 6,
  waterMs: 60e3, soakMs: 30 * 60e3, checkMs: 60e3, bootWaitMs: 30 * 60e3, badWaitMs: 10 * 60e3 };
export const WAIT = 0, WATER = 1, SENSOR_BAD = 2, DAY_CAP = 3, LOCKED = 4;
export const newState = () => ({ waterings: new Array(12).fill(0), nWater: 0, nextSlot: 0, dryReads: 0, checkEffect: false, rawBefore: 0, noEffect: 0, locked: false });

export function wateredInLastDay(s, now) {
  let n = 0;
  for (let i = 0; i < s.nWater; i++) if (now - s.waterings[i] < 24 * 3600e3) n++;
  return n;
}
export const sensorPossible = (c, raw) => raw <= c.dry + c.slack && raw >= c.wet - c.slack;

// Call once per reading. now = powered-on ms counted across power cuts; sinceBoot = ms since this power-up.
export function decide(c, s, raw, now, sinceBoot) {
  let changed = false;
  if (!sensorPossible(c, raw)) {
    s.dryReads = 0;
    s.checkEffect = false;                 // can't judge the last watering with a broken reading
    return { act: SENSOR_BAD, waitMs: c.badWaitMs, changed: false };
  }
  if (s.checkEffect) {                     // did the last watering reach the sensor?
    s.checkEffect = false;
    const before = s.noEffect;
    s.noEffect = (s.rawBefore - raw >= c.minChange) ? 0 : s.noEffect + 1;
    if (s.noEffect >= c.maxNoEffect && !s.locked) s.locked = true;
    changed = (s.noEffect !== before) || s.locked;
  }
  if (raw <= c.thirsty) {                  // wet enough: nothing to do, and any lock is over
    s.dryReads = 0;
    if (s.locked || s.noEffect) { s.locked = false; s.noEffect = 0; changed = true; }
    return { act: WAIT, waitMs: c.checkMs, changed };
  }
  if (s.locked) return { act: LOCKED, waitMs: c.checkMs, changed };
  if (s.dryReads < c.needDryReads) s.dryReads++;
  if (sinceBoot < c.bootWaitMs || s.dryReads < c.needDryReads) return { act: WAIT, waitMs: c.checkMs, changed };
  if (wateredInLastDay(s, now) >= c.maxPerDay) return { act: DAY_CAP, waitMs: c.checkMs, changed };
  return { act: WATER, waitMs: c.soakMs, changed };
}

// Call right after the valve has closed again.
export function watered(c, s, rawBefore, now) {
  const slots = Math.min(c.maxPerDay, 12);
  s.waterings[s.nextSlot] = now;
  s.nextSlot = (s.nextSlot + 1) % slots;
  if (s.nWater < slots) s.nWater++;
  s.rawBefore = rawBefore;
  s.checkEffect = true;
  s.dryReads = 0;
}
