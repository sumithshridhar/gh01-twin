// Laptop tests for the watering box's decisions (auto_water/water_logic.h). No ESP32 needed:
//   bash build/03-auto-watering/tests/run_test.sh
// A small soil model stands in for the pot: it dries a little every minute, and a watering that really arrives makes
// it wetter about 20 minutes later. Each test breaks one thing a real farm breaks and checks the valve stays safe.
#include <cstdio>
#include <functional>
#include "../auto_water/water_logic.h"

static int passed = 0, failed = 0;
#define CHECK(name, cond) do { if (cond) { passed++; std::printf("PASS  %s\n", name); } else { failed++; std::printf("FAIL  %s\n", name); } } while (0)

const unsigned long MIN = 60UL * 1000, HOUR = 60 * MIN;

struct Farm {
  WaterCfg c;
  WaterState s;
  unsigned long total = 0;                 // powered-on ms across power cuts
  unsigned long boot = 0;                  // `total` at the last power-up
  double soil = 1800;                      // the true reading of the soil (higher = drier)
  double dryPerMin = 0.6;                  // how fast it dries: about 3 waterings' worth a day
  bool waterArrives = true;                // false: empty tank / blocked line / sensor out of the soil
  int waterings = 0, bad = 0, capped = 0, lockedReads = 0;
  unsigned long openMs = 0;
  unsigned long lastWaterAt[64];
  std::function<int(Farm&)> sensor = [](Farm& f) { return (int)f.soil; };

  void powerCut() {                        // the sketch keeps these in flash; everything else is forgotten
    WaterState k;
    for (int i = 0; i < 12; i++) k.waterings[i] = s.waterings[i];
    k.nWater = s.nWater; k.nextSlot = s.nextSlot; k.noEffect = s.noEffect; k.locked = s.locked;
    s = k;
    boot = total;
  }
  void pass(unsigned long ms) {            // time goes by with the valve shut
    total += ms;
    soil += dryPerMin * (ms / (double)MIN);
    if (soil > c.dry) soil = c.dry;
  }
  void run(unsigned long forMs) {
    unsigned long end = total + forMs;
    while (total < end) {
      int raw = sensor(*this);
      WaterDecision d = decide(c, s, raw, total, total - boot);
      if (d.act == W_SENSOR_BAD) bad++;
      if (d.act == W_DAY_CAP) capped++;
      if (d.act == W_LOCKED) lockedReads++;
      if (d.act == W_WATER) {
        openMs += c.waterMs;
        total += c.waterMs;
        if (waterings < 64) lastWaterAt[waterings] = total;
        waterings++;
        watered(c, s, raw, total);
        if (waterArrives) soil -= 320;     // wetter by the time the soak is over
        if (soil < c.wet) soil = c.wet;
      }
      pass(d.waitMs);
    }
  }
  int mostIn24h() {                        // the largest number of waterings inside any 24 powered-on hours
    int best = 0, n = waterings < 64 ? waterings : 64;
    for (int i = 0; i < n; i++) {
      int k = 0;
      for (int j = i; j < n && lastWaterAt[j] - lastWaterAt[i] < 24 * HOUR; j++) k++;
      if (k > best) best = k;
    }
    return best;
  }
};

int main() {
  { // 1. a normal week: it waters, the soil stays healthy, and it never passes the daily limit
    Farm f; f.run(7 * 24 * HOUR);
    CHECK("normal week: it waters", f.waterings > 0);
    CHECK("normal week: soil never reaches bone dry", f.soil < f.c.dry - 300);
    CHECK("normal week: daily limit kept", f.mostIn24h() <= f.c.maxPerDay);
    CHECK("normal week: no lock, no sensor alarm", !f.s.locked && f.bad == 0);
  }
  { // 2. the sensor cable falls out (reads the top of the scale): never water
    Farm f; f.soil = 2500; f.sensor = [](Farm&) { return 4095; }; f.run(3 * 24 * HOUR);
    CHECK("cable out (4095): no watering in 3 days", f.waterings == 0 && f.bad > 0);
  }
  { // 3. the sensor shorts (reads zero): never water
    Farm f; f.soil = 2500; f.sensor = [](Farm&) { return 0; }; f.run(3 * 24 * HOUR);
    CHECK("sensor shorted (0): no watering in 3 days", f.waterings == 0 && f.bad > 0);
  }
  { // 4. one wrong dry reading in wet soil (a knocked wire): not enough to open the valve
    Farm f; f.soil = 1500; f.dryPerMin = 0; int n = 0;
    f.sensor = [&n](Farm& x) { return (++n % 10 == 0) ? 2700 : (int)x.soil; };
    f.run(24 * HOUR);
    CHECK("single dry glitches: no watering", f.waterings == 0);
  }
  { // 5. the tank is empty: it tries twice, sees no change, locks and stays locked
    Farm f; f.soil = 2500; f.waterArrives = false; f.run(5 * 24 * HOUR);
    CHECK("empty tank: exactly 2 tries, then locked", f.waterings == 2 && f.s.locked);
    CHECK("empty tank: valve open 2 minutes in 5 days", f.openMs == 2 * f.c.waterMs);
  }
  { // 6. ...and a power cut does not clear that lock
    Farm f; f.soil = 2500; f.waterArrives = false; f.run(6 * HOUR);
    for (int i = 0; i < 20; i++) { f.powerCut(); f.run(3 * HOUR); }
    CHECK("empty tank + 20 power cuts: still only 2 tries", f.waterings == 2 && f.s.locked);
  }
  { // 7. someone refills the tank and waters by hand: the lock clears and it works again
    Farm f; f.soil = 2500; f.waterArrives = false; f.run(6 * HOUR);
    f.waterArrives = true; f.soil = 1500; f.run(2 * HOUR);
    bool cleared = !f.s.locked;
    f.run(4 * 24 * HOUR);
    CHECK("lock clears when the soil reads wet again", cleared);
    CHECK("after the fix it waters again", f.waterings > 2);
  }
  { // 8. power flickers every 10 minutes with dry soil: the valve never opens (dry is safer than a flood)
    Farm f; f.soil = 2500;
    for (int i = 0; i < 144; i++) { f.powerCut(); f.run(10 * MIN); }
    CHECK("flickering power for 24 h: no watering", f.waterings == 0);
  }
  { // 9. farm power comes 3 hours at a time and the sensor sits in a dry corner that barely responds:
    //    the daily limit still holds, because waterings are counted across the cuts
    Farm f; f.soil = 2800; f.dryPerMin = 12; f.c.minChange = 60;
    for (int i = 0; i < 24; i++) { f.powerCut(); f.run(3 * HOUR); }
    CHECK("3-hour power windows, thirsty corner: daily limit kept", f.mostIn24h() <= f.c.maxPerDay && f.waterings > 0);
  }
  { // 10. the first watering never comes sooner than 30 minutes after power-up
    Farm f; f.soil = 2600; f.run(29 * MIN);
    int early = f.waterings; f.run(10 * MIN);
    CHECK("no watering in the first 30 min after power-up", early == 0 && f.waterings == 1);
  }
  { // 11. very hot week, soil dries 13x faster than normal: it hits the daily limit and stops there
    Farm f; f.soil = 2850; f.dryPerMin = 8; f.run(7 * 24 * HOUR);
    CHECK("worst case: valve open at most 6 minutes in any 24 h", f.mostIn24h() <= f.c.maxPerDay && f.capped > 0);
  }
  std::printf("\n%d/%d PASS\n", passed, passed + failed);
  return failed ? 1 : 0;
}
