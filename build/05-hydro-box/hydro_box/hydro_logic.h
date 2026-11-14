// GH-01 Build Part 5: the hydro box's decisions (14 Nov 2026), kept apart from the hardware so they can be tested on a
// laptop (../tests/test_hydro_logic.cpp). Nothing in here touches a pin: a sketch reads the probes, the float switch and
// the flow sensor once a minute, asks step() what to do, and switches the pump and the dosing pumps.
//
// For a recirculating system (NFT channels, a reservoir, one pump). The same rule as the watering box: after every
// action, check that it worked; if it did nothing twice, stop and tell a person.
//   - reservoir below the float switch                    -> pump off at once (never run it dry), warn
//   - pump on but no water moving                         -> warn at once, pump off, try again every 30 minutes
//   - EC (nutrient strength) low for 10 minutes           -> a small dose of nutrient A + B, wait 15 minutes to mix
//   - pH high for 10 minutes                              -> a small dose of pH-down, wait 15 minutes to mix
//   - a dose did not move the reading, twice in a row     -> stop dosing that channel and warn: bottle empty, tube
//                                                            blocked, or the probe has drifted
//   - a dose moved the reading the wrong way              -> stop at once: wrong bottle or a broken probe
//   - a probe reads impossible numbers, or the exact same -> no dosing at all (a pump never acts on a broken probe)
//     number for an hour
//   - EC too high, or pH too low                          -> it cannot fix these by dosing: it warns (add water)
//   - power just came back                                -> no dosing for 30 minutes; the daily dose limit survives cuts
// A dosing lock clears by itself once that reading is back inside its band (someone refilled the bottle or fixed it).
// The limits are starting points. Set them for the crop, and tune them on a real tank.
#pragma once
#include <math.h>

struct HydroCfg {
  float phLow = 5.5f, phHigh = 6.5f;              // the pH band
  float ecLow = 1.2f, ecHigh = 2.2f;              // the EC band, mS/cm
  float phMove = 0.05f, ecMove = 0.03f;           // a dose that works moves the reading at least this much
  int maxNoEffect = 2;                            // doses in a row that changed nothing -> lock that channel
  int maxDosesPerDay = 6;                         // per channel, counted across power cuts
  unsigned long holdMs = 10UL * 60 * 1000;        // out of band this long before a dose (one odd reading never doses)
  unsigned long mixMs = 15UL * 60 * 1000;         // after a dose: let the pump mix the tank before judging it
  unsigned long doseMs = 4UL * 1000;              // one dose = the dosing pump on for this long
  unsigned long bootWaitMs = 30UL * 60 * 1000;    // no dosing this soon after power-up
  unsigned long flatMs = 60UL * 60 * 1000;        // the exact same probe reading this long = stuck probe
  unsigned long flowGraceMs = 2UL * 60 * 1000;    // the pump may take this long to fill the line
  unsigned long retryMs = 30UL * 60 * 1000;       // a pump with no flow is tried again after this
  unsigned long warnEveryMs = 30UL * 60 * 1000;   // the same warning again no sooner than this
};

struct Channel {                                  // one dosing channel (nutrient, or pH-down)
  unsigned long outSince = 0; bool out = false;   // how long the reading has been out of band (on the dosing side)
  bool judging = false; float before = 0; unsigned long dosedAt = 0;
  int noEffect = 0; bool locked = false;          // kept across power cuts by the sketch
  unsigned long doses[8] = {0}; int nDoses = 0, next = 0;   // when the last doses happened; kept across power cuts
};

struct Probe { bool have = false; float last = 0; unsigned long sameSince = 0; };

struct HydroState {
  Channel ec, ph;
  Probe pPh, pEc;
  bool pumpLocked = false; unsigned long lockedAt = 0; // no flow: pump off until the retry
  bool pumpWasOn = false; unsigned long pumpOnSince = 0;
  unsigned long warned[8] = {0};                  // last time each warning was sent (0 = never)
};

enum HydroWarn { H_LOW_WATER, H_NO_FLOW, H_PROBE_BAD, H_EC_LOCK, H_PH_LOCK, H_EC_HIGH, H_PH_LOW, H_NWARN };

struct HydroIn {
  float ph, ec;                                   // probe readings (NAN when the probe does not answer)
  bool lowWater;                                  // the float switch: true = below the low mark
  float flow;                                     // litres a minute in the pump line (0 = nothing moving)
  unsigned long now;                              // powered-on ms, counted across power cuts (the sketch saves it)
  unsigned long sinceBoot;                        // ms since this power-up
};

struct HydroOut {
  bool pump = false;
  unsigned long doseEcMs = 0, dosePhMs = 0;       // run the nutrient A + B pumps / the pH-down pump this long now
  bool send[H_NWARN] = {false};                   // send this warning now
  bool probeBad = false;
};

inline int dosesInLastDay(const Channel& ch, unsigned long now) {
  int n = 0;
  for (int i = 0; i < ch.nDoses; i++) if (now - ch.doses[i] < 24UL * 3600 * 1000) n++;
  return n;
}

inline bool probeOk(Probe& p, float v, float lo, float hi, unsigned long now, const HydroCfg& c) {
  if (!isfinite(v) || v < lo || v > hi) { p.have = false; return false; }
  if (!p.have || v != p.last) { p.have = true; p.last = v; p.sameSince = now; }
  return now - p.sameSince < c.flatMs;            // real water always moves the last digit a little
}

inline void warn(HydroState& s, HydroOut& o, HydroWarn w, unsigned long now, const HydroCfg& c) {
  if (s.warned[w] == 0 || now - s.warned[w] >= c.warnEveryMs) { s.warned[w] = now ? now : 1; o.send[w] = true; }
}

// One dosing channel. dir = +1: dose when the reading is too low (EC), -1: when it is too high (pH-down).
// Returns the dose length to run now (0 = none).
inline unsigned long channel(Channel& ch, float v, float lo, float hi, float move, int dir, bool canDose, unsigned long now,
                             const HydroCfg& c, HydroState& s, HydroOut& o, HydroWarn lockWarn) {
  if (ch.judging && now - ch.dosedAt >= c.mixMs) {          // did the last dose do anything?
    ch.judging = false;
    float moved = (v - ch.before) * dir;                     // > 0: towards the band
    if (moved <= -2 * move) { ch.locked = true; ch.noEffect = c.maxNoEffect; }   // clearly the wrong way: stop at once
    else if (moved < move) { if (++ch.noEffect >= c.maxNoEffect) ch.locked = true; }
    else ch.noEffect = 0;
  }
  bool inBand = v >= lo && v <= hi;
  if (inBand && (ch.locked || ch.noEffect)) { ch.locked = false; ch.noEffect = 0; }   // fixed, or recovered by itself
  if (ch.locked) { warn(s, o, lockWarn, now, c); return 0; }
  bool needs = dir > 0 ? v < lo : v > hi;
  if (!needs) { ch.out = false; return 0; }
  if (!ch.out) { ch.out = true; ch.outSince = now; }
  if (!canDose || ch.judging) return 0;
  if (now - ch.outSince < c.holdMs) return 0;
  if (dosesInLastDay(ch, now) >= c.maxDosesPerDay) return 0;
  ch.doses[ch.next] = now; ch.next = (ch.next + 1) % 8; if (ch.nDoses < 8) ch.nDoses++;
  ch.judging = true; ch.before = v; ch.dosedAt = now;
  return c.doseMs;
}

// Call once a minute.
inline HydroOut step(const HydroCfg& c, HydroState& s, const HydroIn& in) {
  HydroOut o;
  unsigned long now = in.now;
  // ── the pump ──
  bool want = !in.lowWater;
  if (in.lowWater) warn(s, o, H_LOW_WATER, now, c);
  if (s.pumpLocked && now - s.lockedAt >= c.retryMs) { s.pumpLocked = false; s.pumpWasOn = false; }   // try again
  if (s.pumpLocked) want = false;
  if (want) {
    if (!s.pumpWasOn) { s.pumpWasOn = true; s.pumpOnSince = now; }
    if (in.flow <= 0.0f && now - s.pumpOnSince >= c.flowGraceMs) {      // dead pump, blocked line or an air lock
      s.pumpLocked = true; s.lockedAt = now; s.pumpWasOn = false; want = false;
      warn(s, o, H_NO_FLOW, now, c);
    }
  } else if (!s.pumpLocked) s.pumpWasOn = false;
  o.pump = want;
  bool flowing = want && in.flow > 0.0f;
  // ── the probes ──
  bool phOk = probeOk(s.pPh, in.ph, 2.0f, 12.0f, now, c);
  bool ecOk = probeOk(s.pEc, in.ec, 0.05f, 6.0f, now, c);
  if (!phOk || !ecOk) {
    o.probeBad = true;
    warn(s, o, H_PROBE_BAD, now, c);
    s.ec.judging = s.ph.judging = false;          // a broken reading can't judge a dose
    s.ec.out = s.ph.out = false;
    return o;
  }
  // ── dosing: only with water moving (it mixes the dose), never right after power-up, one channel at a time ──
  if (!flowing) {                                 // no water moving = no mixing: a dose waiting to be judged waits too
    if (s.ec.judging) s.ec.dosedAt = now;
    if (s.ph.judging) s.ph.dosedAt = now;
  }
  bool canDose = flowing && in.sinceBoot >= c.bootWaitMs;
  bool mixing = s.ec.judging || s.ph.judging;
  o.doseEcMs = channel(s.ec, in.ec, c.ecLow, c.ecHigh, c.ecMove, +1, canDose && !mixing, now, c, s, o, H_EC_LOCK);
  mixing = mixing || o.doseEcMs > 0;              // nutrients first: they shift the pH, so pH waits for the next round
  o.dosePhMs = channel(s.ph, in.ph, c.phLow, c.phHigh, c.phMove, -1, canDose && !mixing, now, c, s, o, H_PH_LOCK);
  if (in.ec > c.ecHigh) warn(s, o, H_EC_HIGH, now, c);      // can't take nutrients out: add plain water
  if (in.ph < c.phLow) warn(s, o, H_PH_LOW, now, c);        // this box only carries pH-down
  return o;
}

// What the sketch keeps in flash across a power cut (everything else starts fresh).
inline HydroState afterPowerCut(const HydroState& s) {
  HydroState k;
  const Channel* from[2] = {&s.ec, &s.ph};
  Channel* to[2] = {&k.ec, &k.ph};
  for (int j = 0; j < 2; j++) {
    for (int i = 0; i < 8; i++) to[j]->doses[i] = from[j]->doses[i];
    to[j]->nDoses = from[j]->nDoses; to[j]->next = from[j]->next;
    to[j]->noEffect = from[j]->noEffect; to[j]->locked = from[j]->locked;
  }
  return k;
}
