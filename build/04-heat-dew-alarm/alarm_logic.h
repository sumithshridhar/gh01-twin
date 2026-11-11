// GH-01 Build Part 4: the heat-and-dew alarm's decisions, kept apart from the hardware so they can be tested on a
// laptop (tests/test_alarm_logic.cpp). The box only warns. A person opens the vents or switches on the foggers.
//
//   - dew: fungus starts when water forms on the leaves. That happens when the air cools to its dew point, so the
//     alarm watches the gap between air temperature and dew point, not plain humidity (which reads 95-99 % every night)
//   - heat: the air stays above the limit for 10 minutes
//   - a warning must last 10 minutes before it is sent, repeats at most every 3 hours, and ends only when the reading
//     is clearly back to normal, so the phone does not fill up and get ignored
//   - a reading that is impossible, or that has not moved at all for an hour, is reported as a sensor fault, and
//     no dew or heat warning is trusted while it lasts
// The limits are starting points. Tune them on a real crop.
#pragma once
#include <math.h>

struct AlarmCfg {
  float dewGapOn = 2.0f, dewGapOff = 3.0f;          // degrees C between air and dew point
  float heatOn = 35.0f, heatOff = 33.0f;            // degrees C
  unsigned long holdMs = 10UL * 60 * 1000;          // a condition must last this long
  unsigned long repeatMs = 3UL * 3600 * 1000;       // the same warning again no sooner than this
  unsigned long flatMs = 60UL * 60 * 1000;          // identical readings for this long = stuck sensor
};

struct Watch {                                      // one warning (dew, heat or sensor fault)
  bool in = false, active = false, sent = false;
  unsigned long since = 0, lastSent = 0;
};

struct AlarmState {
  Watch dew, heat, bad;
  bool haveLast = false;
  float lastT = 0, lastRH = 0;
  unsigned long sameSince = 0;
};

struct AlarmOut {
  bool sensorBad = false, dew = false, heat = false;            // what is true now
  bool sendBad = false, sendDew = false, sendHeat = false;      // send a message now
  bool dewOver = false, heatOver = false;                       // it just ended
  float dewPoint = NAN, gap = NAN;
};

// Magnus formula, good to about 0.2 C between 0 and 50 C
inline float dewPointC(float t, float rh) {
  float g = logf(rh / 100.0f) + 17.62f * t / (243.12f + t);
  return 243.12f * g / (17.62f - g);
}

inline bool tick(Watch& w, bool on, bool off, unsigned long now, const AlarmCfg& c, bool& over) {
  over = false;
  if (off) {
    if (w.active) over = true;
    w = Watch();
    return false;
  }
  if (on && !w.in) { w.in = true; w.since = now; }
  if (!on && !w.active) w.in = false;                  // dipped in and came straight back out: start again
  if (w.in && on && now - w.since >= c.holdMs) w.active = true;
  if (w.active && (!w.sent || now - w.lastSent >= c.repeatMs)) { w.sent = true; w.lastSent = now; return true; }
  return false;
}

// Call once a minute with the air temperature (C) and relative humidity (%).
inline AlarmOut check(const AlarmCfg& c, AlarmState& s, float t, float rh, unsigned long now) {
  AlarmOut o;
  bool possible = isfinite(t) && isfinite(rh) && t > -5.0f && t < 60.0f && rh >= 1.0f && rh <= 100.0f;
  if (possible) {
    if (!s.haveLast || t != s.lastT || rh != s.lastRH) { s.haveLast = true; s.lastT = t; s.lastRH = rh; s.sameSince = now; }
    if (now - s.sameSince >= c.flatMs) possible = false;       // real air always moves a little
  }
  bool over;
  if (!possible) {
    o.sensorBad = true;
    if (!s.bad.sent || now - s.bad.lastSent >= c.repeatMs) { s.bad.sent = true; s.bad.lastSent = now; o.sendBad = true; }
    s.dew = Watch(); s.heat = Watch();                       // nothing from a broken sensor is trusted
    return o;
  }
  s.bad = Watch();
  o.dewPoint = dewPointC(t, rh);
  o.gap = t - o.dewPoint;
  o.sendDew = tick(s.dew, o.gap <= c.dewGapOn, o.gap >= c.dewGapOff, now, c, over); o.dewOver = over;
  o.sendHeat = tick(s.heat, t >= c.heatOn, t <= c.heatOff, now, c, over); o.heatOver = over;
  o.dew = s.dew.active; o.heat = s.heat.active;
  return o;
}
