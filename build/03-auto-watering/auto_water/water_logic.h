// GH-01 Build Part 3: the watering box's decisions, kept apart from the hardware so they can be tested on a laptop
// (../tests/test_water_logic.cpp). Nothing in here touches a pin: auto_water.ino reads the sensor, asks decide() what
// to do, and moves the valve.
//
// The rule behind every line: when something is wrong, the valve stays shut and a person is told.
//   - a reading that is impossible (cable out, sensor broken)          -> never water
//   - one dry reading (a loose wire, a hand on the sensor)             -> not enough, it needs several in a row
//   - power just came back                                             -> wait first, so flickering power can't flood
//   - watered, but the soil did not get wetter, twice in a row         -> lock: the water is not arriving (empty tank,
//                                                                         blocked line, sensor out of the soil)
//   - too many waterings in 24 powered-on hours                        -> stop for the day (counted across power cuts)
// A lock clears by itself once the soil reads wet again (someone fixed it or watered by hand).
#pragma once

struct WaterCfg {
  int dry = 2900;                          // sensor reading in dry air (higher number = drier)
  int wet = 1250;                          // sensor reading in water
  int thirsty = 2075;                      // water when the reading is above this
  int slack = 400;                         // readings beyond dry+slack or wet-slack are impossible
  int needDryReads = 3;                    // dry readings in a row before watering
  int minChange = 60;                      // after a watering the reading must drop by at least this
  int maxNoEffect = 2;                     // waterings in a row that changed nothing -> lock
  int maxPerDay = 6;
  unsigned long waterMs = 60UL * 1000;             // valve open time
  unsigned long soakMs = 30UL * 60 * 1000;         // wait after watering: the water needs time to reach the sensor
  unsigned long checkMs = 60UL * 1000;             // normal time between readings
  unsigned long bootWaitMs = 30UL * 60 * 1000;     // no watering this soon after power-up
  unsigned long badWaitMs = 10UL * 60 * 1000;      // wait after an impossible reading
};

struct WaterState {
  unsigned long waterings[12] = {0};       // when the last waterings happened (powered-on ms); kept across power cuts
  int nWater = 0, nextSlot = 0;            // kept across power cuts
  int dryReads = 0;
  bool checkEffect = false;                // a watering is waiting to be judged by the next reading
  int rawBefore = 0;
  int noEffect = 0;                        // kept across power cuts by the sketch
  bool locked = false;                     // kept across power cuts by the sketch
};

enum WaterAct { W_WAIT, W_WATER, W_SENSOR_BAD, W_DAY_CAP, W_LOCKED };

struct WaterDecision {
  WaterAct act;
  unsigned long waitMs;                    // how long to wait before the next reading (after watering: the soak)
  bool changed;                            // noEffect or locked changed: the sketch should save them
};

inline int wateredInLastDay(const WaterState& s, unsigned long now) {
  int n = 0;
  for (int i = 0; i < s.nWater; i++)
    if (now - s.waterings[i] < 24UL * 3600 * 1000) n++;
  return n;
}

inline bool sensorPossible(const WaterCfg& c, int raw) {
  return raw <= c.dry + c.slack && raw >= c.wet - c.slack;
}

// Call once per reading.
//   now       = powered-on time in ms, counted across power cuts (the sketch saves it), so the daily limit survives a cut
//   sinceBoot = ms since this power-up
inline WaterDecision decide(const WaterCfg& c, WaterState& s, int raw, unsigned long now, unsigned long sinceBoot) {
  bool changed = false;
  if (!sensorPossible(c, raw)) {
    s.dryReads = 0;
    s.checkEffect = false;                 // can't judge the last watering with a broken reading
    return {W_SENSOR_BAD, c.badWaitMs, false};
  }
  if (s.checkEffect) {                     // did the last watering reach the sensor?
    s.checkEffect = false;
    int before = s.noEffect;
    s.noEffect = (s.rawBefore - raw >= c.minChange) ? 0 : s.noEffect + 1;
    if (s.noEffect >= c.maxNoEffect && !s.locked) s.locked = true;
    changed = (s.noEffect != before) || s.locked;
  }
  if (raw <= c.thirsty) {                  // wet enough: nothing to do, and any lock is over
    s.dryReads = 0;
    if (s.locked || s.noEffect) { s.locked = false; s.noEffect = 0; changed = true; }
    return {W_WAIT, c.checkMs, changed};
  }
  if (s.locked) return {W_LOCKED, c.checkMs, changed};
  if (s.dryReads < c.needDryReads) s.dryReads++;
  if (sinceBoot < c.bootWaitMs || s.dryReads < c.needDryReads) return {W_WAIT, c.checkMs, changed};
  if (wateredInLastDay(s, now) >= c.maxPerDay) return {W_DAY_CAP, c.checkMs, changed};
  return {W_WATER, c.soakMs, changed};
}

// Call right after the valve has closed again.
inline void watered(const WaterCfg& c, WaterState& s, int rawBefore, unsigned long now) {
  int slots = c.maxPerDay < 12 ? c.maxPerDay : 12;
  s.waterings[s.nextSlot] = now;
  s.nextSlot = (s.nextSlot + 1) % slots;
  if (s.nWater < slots) s.nWater++;
  s.rawBefore = rawBefore;
  s.checkEffect = true;
  s.dryReads = 0;
}
