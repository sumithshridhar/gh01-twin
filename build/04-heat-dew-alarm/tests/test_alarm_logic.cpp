// Laptop tests for the heat-and-dew alarm's decisions (../alarm_logic.h). No hardware needed:
//   bash build/04-heat-dew-alarm/tests/run_test.sh
#include <cstdio>
#include <functional>
#include "../alarm_logic.h"

static int passed = 0, failed = 0;
#define CHECK(name, cond) do { if (cond) { passed++; std::printf("PASS  %s\n", name); } else { failed++; std::printf("FAIL  %s\n", name); } } while (0)
const unsigned long MIN = 60UL * 1000;

struct Run { int dew = 0, heat = 0, bad = 0, dewOver = 0, heatOver = 0; bool dewNow = false, heatNow = false, badNow = false; };
// one reading a minute; the air wobbles by a hundredth of a degree, like a real sensor
Run run(AlarmState& s, int minutes, std::function<void(int, float&, float&)> air, unsigned long t0 = 0, bool wobble = true) {
  AlarmCfg c; Run r;
  for (int m = 0; m < minutes; m++) {
    float t = 25, rh = 60; air(m, t, rh);
    if (wobble) t += (m % 2) * 0.01f;
    AlarmOut o = check(c, s, t, rh, t0 + m * MIN);
    r.dew += o.sendDew; r.heat += o.sendHeat; r.bad += o.sendBad; r.dewOver += o.dewOver; r.heatOver += o.heatOver;
    r.dewNow = o.dew; r.heatNow = o.heat; r.badNow = o.sensorBad;
  }
  return r;
}

int main() {
  CHECK("dew point of 25 C / 60 % is about 16.7 C", fabsf(dewPointC(25, 60) - 16.7f) < 0.3f);
  CHECK("dew point of 20 C / 95 % is about 19.2 C", fabsf(dewPointC(20, 95) - 19.2f) < 0.3f);
  { AlarmState s; Run r = run(s, 24 * 60, [](int, float& t, float& rh) { t = 30; rh = 50; });
    CHECK("a dry warm day: no warnings at all", r.dew + r.heat + r.bad == 0); }
  { AlarmState s; Run r = run(s, 8 * 60, [](int m, float& t, float& rh) { t = 19; rh = m < 30 ? 80 : 94; });
    CHECK("a damp night: the dew warning comes", r.dew >= 1 && r.dewNow);
    CHECK("a damp night of 8 hours: at most 3 messages, not 450", r.dew <= 3); }
  { AlarmState s; Run r = run(s, 6 * 60, [](int, float& t, float& rh) { t = 22; rh = 97; });
    CHECK("97 % humidity all night: it warns (the gap is under 1 C)", r.dew >= 1); }
  { AlarmState s; Run r = run(s, 3 * 60, [](int m, float& t, float& rh) { t = 19; rh = (m >= 60 && m < 66) ? 94 : 75; });
    CHECK("a 6-minute damp spell: no warning", r.dew == 0); }
  { AlarmState s; Run r = run(s, 6 * 60, [](int m, float& t, float& rh) { t = 19; rh = (m % 2) ? 89.0f : 87.5f; });
    CHECK("hovering at the limit: no stream of start/stop messages", r.dew <= 2 && r.dewOver == 0); }
  { AlarmState s; Run r = run(s, 5 * 60, [](int m, float& t, float& rh) { t = 19; rh = m < 120 ? 94 : 60; });
    CHECK("the air dries out: the dew warning ends once", r.dew == 1 && r.dewOver == 1 && !r.dewNow); }
  { AlarmState s; Run r = run(s, 2 * 60, [](int m, float& t, float& rh) { t = m < 20 ? 31 : 36.5f; rh = 40; });
    CHECK("36.5 C for over 10 minutes: the heat warning comes once", r.heat == 1 && r.heatNow); }
  { AlarmState s; Run r = run(s, 6 * 60, [](int, float& t, float& rh) { t = 34.8f; rh = 40; });
    CHECK("34.8 C all afternoon: no heat warning", r.heat == 0); }
  { AlarmState s; Run r = run(s, 4 * 60, [](int m, float& t, float& rh) { t = m < 60 ? 36 : (m < 90 ? 34 : 32); rh = 40; });
    CHECK("heat ends only below 33 C, and only once", r.heat == 1 && r.heatOver == 1 && !r.heatNow); }
  { AlarmState s; Run r = run(s, 6 * 60, [](int, float& t, float& rh) { t = NAN; rh = NAN; });
    CHECK("sensor unplugged (no number): a fault, no dew or heat warning", r.bad >= 1 && r.bad <= 2 && r.dew + r.heat == 0); }
  { AlarmState s; Run r = run(s, 3 * 60, [](int, float& t, float& rh) { t = 125; rh = 0; });
    CHECK("impossible numbers (125 C, 0 %): a fault, nothing else", r.bad == 1 && r.dew + r.heat == 0); }
  { AlarmState s; Run r = run(s, 3 * 60, [](int, float& t, float& rh) { t = 21.37f; rh = 96.0f; }, 0, false);
    CHECK("stuck sensor (same reading for an hour): reported as a fault", r.badNow && r.bad == 1); }
  { AlarmState s; run(s, 60, [](int, float& t, float& rh) { t = NAN; rh = NAN; });
    Run r = run(s, 3 * 60, [](int, float& t, float& rh) { t = 19; rh = 94; }, 60 * MIN);
    CHECK("after the sensor is fixed, warnings work again", !r.badNow && r.dew == 1); }
  std::printf("\n%d/%d PASS\n", passed, passed + failed);
  return failed ? 1 : 0;
}
