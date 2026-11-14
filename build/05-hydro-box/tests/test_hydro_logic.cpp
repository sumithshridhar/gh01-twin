// Laptop tests for the hydro box's decisions (../hydro_box/hydro_logic.h). No hardware needed:
//   bash build/05-hydro-box/tests/run_test.sh
// A small tank model stands in for a real NFT system: the plants slowly use nutrients (EC falls) and push the pH up,
// the reservoir loses a little water, a nutrient dose raises the EC and a pH-down dose lowers the pH. Each test breaks
// one thing a real tank breaks and checks the box stays safe.
#include <cstdio>
#include <functional>
#include "../hydro_box/hydro_logic.h"

static int passed = 0, failed = 0;
#define CHECK(name, cond) do { if (cond) { passed++; std::printf("PASS  %s\n", name); } else { failed++; std::printf("FAIL  %s\n", name); } } while (0)

const unsigned long MIN = 60UL * 1000, HOUR = 60 * MIN, DAY = 24 * HOUR;

struct Tank {
  HydroCfg c;
  HydroState s;
  unsigned long total = 0, boot = 0;            // powered-on ms across power cuts / `total` at the last power-up
  double ph = 6.0, ec = 1.6, litres = 100;      // the true tank
  double phDrift = 0.0003, ecDrift = 0.0003;    // per minute: pH creeps up, EC falls (about 0.4 a day each)
  double phPerDose = -0.12, ecPerDose = 0.15;   // what one dose really does to this tank
  double lowMark = 40;                          // the float switch drops below this
  bool pumpWorks = true, nutrientLeft = true;
  int ecDoses = 0, phDoses = 0, pumpMinNoFlow = 0, pumpMin = 0, inBand = 0, minutes = 0;
  int sent[H_NWARN] = {0};
  unsigned long ecAt[256], phAt[256];
  int dosedSoonAfterBoot = 0;
  std::function<float(Tank&)> phProbe = [](Tank& t) { return (float)t.ph + ((t.minutes & 1) ? 0.004f : 0.0f); };
  std::function<float(Tank&)> ecProbe = [](Tank& t) { return (float)t.ec + ((t.minutes & 1) ? 0.002f : 0.0f); };

  void powerCut() { s = afterPowerCut(s); boot = total; }
  void run(unsigned long forMs) {
    unsigned long end = total + forMs;
    while (total < end) {
      HydroIn in{phProbe(*this), ecProbe(*this), litres < lowMark, 0.0f, total, total - boot};
      bool flowNow = pumpWorks && litres >= lowMark;
      in.flow = s.pumpWasOn || true ? (flowNow ? 4.0f : 0.0f) : 0.0f;
      HydroOut o = step(c, s, in);
      if (o.pump) { pumpMin++; if (!flowNow) pumpMinNoFlow++; }
      if (o.doseEcMs) {
        if (ecDoses < 256) ecAt[ecDoses] = total;
        ecDoses++;
        if (nutrientLeft) ec += ecPerDose;
        if (total - boot < c.bootWaitMs) dosedSoonAfterBoot++;
      }
      if (o.dosePhMs) {
        if (phDoses < 256) phAt[phDoses] = total;
        phDoses++;
        ph += phPerDose;
        if (total - boot < c.bootWaitMs) dosedSoonAfterBoot++;
      }
      for (int w = 0; w < H_NWARN; w++) sent[w] += o.send[w];
      ph += phDrift; ec -= ecDrift; if (ec < 0.1) ec = 0.1;
      litres -= 0.004;                           // about 6 L a day
      if (ph >= c.phLow && ph <= c.phHigh && ec >= c.ecLow && ec <= c.ecHigh) inBand++;
      minutes++;
      total += MIN;
    }
  }
  int mostIn24h(unsigned long* at, int n) {
    int best = 0; n = n < 256 ? n : 256;
    for (int i = 0; i < n; i++) { int k = 0; for (int j = i; j < n && at[j] - at[i] < DAY; j++) k++; if (k > best) best = k; }
    return best;
  }
};

int main() {
  { Tank t; t.run(7 * DAY);
    CHECK("normal week: pH and EC inside their bands 90 % of the time (it waits 10 min before a dose)", t.inBand >= 0.90 * t.minutes);
    CHECK("normal week: it doses both, and no warnings at all", t.ecDoses > 0 && t.phDoses > 0 &&
          t.sent[H_EC_LOCK] + t.sent[H_PH_LOCK] + t.sent[H_PROBE_BAD] + t.sent[H_NO_FLOW] + t.sent[H_LOW_WATER] == 0); }
  { Tank t; t.phDrift = 0.003; t.ecDrift = 0.002; t.run(3 * DAY);
    CHECK("fast drift: never more than 6 doses a channel in any 24 h", t.mostIn24h(t.ecAt, t.ecDoses) <= 6 && t.mostIn24h(t.phAt, t.phDoses) <= 6); }
  { Tank t; t.phDrift = 0; t.ecDrift = 0; t.run(2 * HOUR);
    t.phProbe = [](Tank& x) { return (float)((x.minutes % 60) < 6 ? 6.9 : x.ph) + ((x.minutes & 1) ? 0.004f : 0.0f); };
    t.run(3 * HOUR);
    CHECK("a 6-minute pH spike: no dose", t.phDoses == 0); }
  { Tank t; t.litres = 41; t.run(12 * HOUR);
    CHECK("reservoir runs low: the pump never runs below the float", t.pumpMinNoFlow == 0);
    CHECK("reservoir runs low: one warning, repeated at most every 30 minutes", t.sent[H_LOW_WATER] >= 1 && t.sent[H_LOW_WATER] <= 12 * 2 + 1); }
  { Tank t; t.run(HOUR); t.pumpWorks = false; t.run(6 * HOUR);
    CHECK("dead pump: warned at once, then it only tries again every 30 min (at most 3 min a try)",
          t.sent[H_NO_FLOW] >= 1 && t.pumpMinNoFlow <= 3 * 13);
    t.pumpWorks = true; t.run(2 * HOUR);
    CHECK("pump fixed: running again by the next try", t.pumpMin > 60 + 60); }
  { Tank t; t.nutrientLeft = false; t.ecDrift = 0.0006; t.run(2 * DAY);
    CHECK("empty nutrient bottle: exactly 2 doses, then it stops and warns", t.ecDoses == 2 && t.s.ec.locked && t.sent[H_EC_LOCK] >= 1); }
  { Tank t; t.phProbe = [](Tank& x) { return 7.0f + ((x.minutes & 1) ? 0.004f : 0.0f); }; t.run(2 * DAY);
    CHECK("drifted pH probe stuck high: 2 doses of pH-down, not 30", t.phDoses == 2 && t.s.ph.locked); }
  { Tank t; t.ph = 6.6; t.phPerDose = +0.12; t.run(DAY);
    CHECK("wrong bottle (pH goes up after pH-down): stops after 1 dose", t.phDoses == 1 && t.s.ph.locked); }
  { Tank t; t.ec = 1.0; t.phProbe = [](Tank&) { return NAN; }; t.run(DAY);
    CHECK("pH probe unplugged: no dosing at all, and a probe warning", t.ecDoses + t.phDoses == 0 && t.sent[H_PROBE_BAD] >= 1); }
  { Tank t; t.ec = 1.0; t.phProbe = [](Tank&) { return 14.5f; }; t.ecProbe = [](Tank&) { return 0.0f; }; t.run(DAY);
    CHECK("impossible numbers (pH 14.5, EC 0): no dosing", t.ecDoses + t.phDoses == 0); }
  { Tank t; t.run(HOUR); t.phProbe = [](Tank&) { return 6.80f; }; int before = t.phDoses; t.run(2 * HOUR); int at2h = t.phDoses; t.run(DAY);
    CHECK("stuck pH probe (the exact same reading for an hour): reported, and no dosing after that",
          t.sent[H_PROBE_BAD] >= 1 && t.phDoses == at2h && at2h - before <= 2); }
  { Tank t; t.ecDrift = 0.002; for (int i = 0; i < 20; i++) { t.run(70 * MIN); t.powerCut(); } t.run(DAY);
    CHECK("20 power cuts: never a dose in the first 30 min after power-up", t.dosedSoonAfterBoot == 0);
    CHECK("20 power cuts: the daily limit still holds", t.mostIn24h(t.ecAt, t.ecDoses) <= 6); }
  { Tank t; t.ec = 2.6; t.ecDrift = 0; t.run(DAY);
    CHECK("EC too high: no nutrient dose, an add-water warning", t.ecDoses == 0 && t.sent[H_EC_HIGH] >= 1); }
  { Tank t; t.litres = 39; t.ec = 1.0; t.ecDrift = 0; t.run(DAY);
    CHECK("pump off (reservoir low): no dosing, a dose can't mix", t.ecDoses == 0); }
  { Tank t; t.nutrientLeft = false; t.ecDrift = 0.0006; t.run(DAY); bool lockedThen = t.s.ec.locked;
    t.nutrientLeft = true; t.ec = 1.6; t.run(HOUR);
    bool cleared = !t.s.ec.locked; int dosesBefore = t.ecDoses; t.run(2 * DAY);
    CHECK("bottle refilled and topped up by hand: the lock clears and dosing works again", lockedThen && cleared && t.ecDoses > dosesBefore); }
  std::printf("\n%d/%d PASS\n", passed, passed + failed);
  return failed ? 1 : 0;
}
