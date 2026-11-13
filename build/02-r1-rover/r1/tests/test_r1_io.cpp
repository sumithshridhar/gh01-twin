// Software-in-the-loop test of the REAL rover firmware (r1_io.ino) on a laptop, no Arduino needed.
// 18 Oct 2026: first version (14 checks). 13 Nov 2026: firmware v2, with the rover's safety circuit in the loop too.
//
// The sketch is compiled as-is against a fake Arduino (Arduino.h in this folder). The test plays two parts:
//   - the Pi: it sends command lines;
//   - the hardware around the board: the e-stop chain (e-stop + both bumpers), the green RESET button and the latch
//     relay it starts, the battery voltage and the tank float.
// It moves the clock 1 ms at a time and checks the pins the sketch drives.
//
//   bash run_test.sh   (builds the test in a temp folder, runs it, deletes it: a fresh unsigned .exe makes antivirus
//                       tools like Avast pause it for a scan, 18 Oct 2026)
#include <cstdio>
#include <string>
#include "Arduino.h"
#include "../firmware/r1_io/r1_io.ino"

static int fails = 0, checks = 0;
static void check(bool ok, const char* what, const std::string& detail = "") {
  checks++;
  std::printf("  %s  %s %s\n", ok ? "PASS" : "FAIL", what, detail.c_str());
  if (!ok) fails++;
}

// ---- the hardware around the board
static bool chainClosed = true;    // e-stop + front bumper + rear bumper (all normally closed, in series)
static bool resetPressed = false;  // the green RESET push button (normally open)
static bool latchHeld = false;     // latch relay K2: RESET starts it, its own contact holds it while the chain is closed
static double battV = 25.6;        // 8S LiFePO4
static int adcOf(double v) { return (int)(v * 10.0 / 66.0 / 5.0 * 1023.0 + 0.5); }   // 56 k / 10 k divider, 5 V ADC
static void hardware() {
  if (!chainClosed) latchHeld = false;
  else if (resetPressed) latchHeld = true;
  g_adc[ESTOP_SENSE] = chainClosed ? adcOf(battV) : 0;
  g_adc[LATCH_SENSE] = latchHeld ? adcOf(battV) : 0;
  g_adc[BATT_SENSE] = adcOf(battV);
}
static void run(unsigned long ms) { for (unsigned long i = 0; i < ms; i++) { hardware(); g_ms++; loop(); } }
static void pressReset() { resetPressed = true; run(20); resetPressed = false; run(20); }
static unsigned long lastSend = 0;                                                  // when the Pi last sent a command
static void every(unsigned long period, unsigned long total, const char* line) {   // the Pi resending a command
  for (unsigned long t = 0; t < total; t += period) { Serial.send(line); lastSend = g_ms; run(period); }
}

// ---- reading the board back
static int pwm(int i) { return g_pwm[PWM_PIN[i]]; }
static bool wheelsStopped() { for (int i = 0; i < 4; i++) if (pwm(i) != 0) return false; return true; }
static bool relayOn(int pin) { return g_pin[pin] == (RELAY_ACTIVE_LOW ? LOW : HIGH); }
static bool valveOpen(int n) { return relayOn(VALVE_PIN[n]); }
static bool anyValveOpen() { for (int n = 0; n < 6; n++) if (valveOpen(n)) return true; return false; }
static bool pumpOn() { return relayOn(PUMP_PIN); }
static bool brakeOn() { return g_pin[BRAKE_PIN] == (BRAKE_ACTIVE_HIGH ? HIGH : LOW); }
static std::string fmt(const char* f, long a, long b = 0, long c = 0, long d = 0) {
  char s[160]; std::snprintf(s, sizeof s, f, a, b, c, d); return s;
}
static std::string pwms() { return fmt("(PWM %ld %ld %ld %ld)", pwm(0), pwm(1), pwm(2), pwm(3)); }
static std::string lastStatus() {
  size_t a = Serial.out.rfind("S ");
  if (a == std::string::npos) return "";
  size_t e = Serial.out.find('\n', a);
  return e == std::string::npos ? "" : Serial.out.substr(a, e - a);
}
static int nFields() { std::string s = lastStatus(); if (s.empty()) return 0; int n = 1; for (char c : s) n += (c == ' '); return n; }
static long field(int k) {                     // field k of the last status line ("S" is field 0)
  std::string s = lastStatus(); size_t p = 0;
  for (int i = 0; i < k; i++) { p = s.find(' ', p); if (p == std::string::npos) return -999; p++; }
  return std::strtol(s.c_str() + p, nullptr, 10);
}
static long flags() { run(60); return field(9); }
static void enableAndCentre() { Serial.send("E 1"); run(20); every(100, 300, "D 0 0"); }

int main() {
  hardware();                                   // the battery and the chain are there before the board boots
  g_pin[TANK_SENSE] = LOW;                      // water in the tank
  setup();
  std::printf("R1 firmware test (r1_io.ino v2 on a fake Arduino Mega, with the safety circuit)\n");

  std::printf("1. boot\n");
  check(wheelsStopped() && brakeOn(), "wheels stopped, brake on");
  check(!anyValveOpen() && !pumpOn(), "all valves closed, pump off");
  run(60);
  check(nFields() == 10, "status line has 10 fields", "(\"" + lastStatus() + "\")");
  check(field(8) == 256, "it reads the battery: 25.6 V", fmt("(%ld)", field(8)));

  std::printf("2. it won't drive until a person has pressed RESET and the Pi enables it\n");
  every(100, 500, "D 50 50");
  check(wheelsStopped(), "D 50 50 without E 1 -> wheels stay still");
  enableAndCentre();
  every(100, 500, "D 50 50");
  check(wheelsStopped(), "E 1 before anyone pressed RESET -> refused, wheels stay still");

  std::printf("3. RESET, enable, centre the stick, drive\n");
  pressReset();
  Serial.send("E 1"); run(20);
  every(100, 500, "D 50 50");
  check(wheelsStopped(), "D 50 50 straight after E 1 -> refused until a neutral D 0 0");
  Serial.send("D 0 0"); run(20);
  Serial.send("D 50 50"); run(50);
  check(pwm(0) > 0 && pwm(0) < 100, "smooth start: the speed ramps up", fmt("(PWM %ld after 50 ms, not a jump to 100)", pwm(0)));
  every(100, 600, "D 50 50");
  check(pwm(0) == 100 && pwm(1) == 100 && pwm(2) == 100 && pwm(3) == 100, "all 4 wheels at speed", pwms());
  check(g_pin[DIR_PIN[0]] != g_pin[DIR_PIN[1]], "right side mirrored (motors face the other way)");

  std::printf("4. the Pi goes silent: the watchdog must stop the wheels\n");
  unsigned long stopped = 0;
  for (int i = 0; i < 1000 && !stopped; i++) { run(1); if (wheelsStopped()) stopped = g_ms - lastSend; }
  check(stopped >= 300 && stopped <= 320, "wheels stop ~300 ms after the Pi goes quiet", fmt("(%ld ms after the last command)", stopped));
  check(brakeOn(), "brake on after the watchdog");
  every(100, 600, "D 50 50");
  check(wheelsStopped(), "the Pi comes back still sending D 50 50 -> stays stopped until a neutral D 0 0", pwms());
  every(100, 200, "D 0 0"); every(100, 800, "D 50 50");
  check(pwm(0) == 100, "after D 0 0 it drives again", pwms());

  std::printf("5. a bumper hits something while driving\n");
  chainClosed = false;
  unsigned long t0 = g_ms; stopped = 0;
  for (int i = 0; i < 100 && !stopped; i++) { Serial.send("D 50 50"); run(1); if (wheelsStopped()) stopped = g_ms - t0; }
  check(stopped > 0 && stopped <= 2, "wheels stop at once, even while the Pi keeps sending", fmt("(after %ld ms)", stopped));
  check(relayOn(LIGHT_R), "tower light red");
  check(!relayOn(ENABLE_PIN), "drive-enable relay opened, so the contactor drops too");

  std::printf("6. the obstacle walks away and the bumper springs back; the Pi still sends D 50 50\n");
  chainClosed = true;
  every(100, 5000, "D 50 50");
  check(wheelsStopped(), "stays stopped for 5 s (v1 drove off again by itself)", pwms());
  enableAndCentre(); every(100, 500, "D 50 50");
  check(wheelsStopped(), "E 1 from the Pi alone is refused: nobody pressed RESET on the rover");
  pressReset(); enableAndCentre(); every(100, 800, "D 50 50");
  check(pwm(0) == 100, "RESET pressed + E 1 + D 0 0 -> it can drive again", pwms());

  std::printf("7. e-stop pressed, then twisted out again\n");
  chainClosed = false; every(100, 300, "D 50 50");
  chainClosed = true; every(100, 2000, "D 50 50");
  check(wheelsStopped() && (flags() & 1), "still stopped, status says 'tripped: press RESET'", fmt("(flags %ld)", field(9)));

  std::printf("8. spraying: a valve only opens when spraying is armed\n");
  pressReset(); enableAndCentre();
  Serial.send("V 2 1"); run(20);
  check(!valveOpen(2), "V 2 1 while NOT armed -> refused");
  Serial.send("A 1"); Serial.send("V 2 1"); run(20);
  check(valveOpen(2) && pumpOn(), "armed -> valve 2 opens, pump runs");
  run(400);
  check(!valveOpen(2) && !pumpOn(), "Pi silent -> watchdog closes the valve and stops the pump");

  std::printf("9. a valve never stays open more than 4 s\n");
  every(100, 200, "D 0 0");
  Serial.send("A 1"); Serial.send("V 3 1"); run(1);
  unsigned long opened = g_ms - 1, closedAt = 0;
  for (int t = 0; t < 10000 && !closedAt; t += 10) { Serial.send("P"); run(10); if (!valveOpen(3)) closedAt = g_ms - opened; }
  check(closedAt >= 3990 && closedAt <= 4020, "it closes by itself after 4 s, though the Pi keeps pinging",
        fmt("(closed after %ld ms; v1 was still open after 60 s)", closedAt));
  check(!pumpOn(), "the pump stops with it");
  check(flags() & 32, "status flag 32: a valve hit its 4 s limit");

  std::printf("10. broken command lines do nothing\n");
  Serial.send("A 1"); run(10);
  const char* bad[] = {"V 1", "V 9 1", "V 1 1x", "V11", "V 1  1", "v 1 1", "V -1 1"};
  bool none = true;
  for (const char* b : bad) { Serial.send(b); run(5); if (anyValveOpen()) none = false; }
  check(none, "7 broken valve lines (\"V 1\", \"V 9 1\", \"V11\" ...) -> no valve opens (v1: \"V 1\" opened valve 1)");
  every(100, 200, "D 0 0"); every(100, 800, "D 50 50");
  stopped = 0;
  for (int i = 0; i < 1000 && !stopped; i++) { if (i % 50 == 0) Serial.send("D 50"); run(1); if (wheelsStopped()) stopped = g_ms - lastSend; }
  check(stopped >= 300 && stopped <= 320, "broken lines don't feed the watchdog: the wheels still stop",
        fmt("(%ld ms after the last valid command)", stopped));

  std::printf("11. the tank runs dry while spraying\n");
  every(100, 200, "D 0 0");
  Serial.send("A 1"); Serial.send("V 4 1"); run(10);
  bool wasOpen = valveOpen(4);
  g_pin[TANK_SENSE] = HIGH;
  t0 = g_ms; unsigned long closed = 0;
  for (int i = 0; i < 1000 && !closed; i++) { if (i % 100 == 0) Serial.send("P"); run(1); if (!valveOpen(4) && !pumpOn()) closed = g_ms - t0; }
  check(wasOpen && closed >= 295 && closed <= 320, "valve and pump off ~0.3 s after the float reads dry (sloshing filtered)",
        fmt("(after %ld ms)", closed));
  Serial.send("A 1"); run(60);
  check(field(7) == 0, "A 1 is refused while the tank is dry");
  g_pin[TANK_SENSE] = LOW;

  std::printf("12. the battery\n");
  every(100, 200, "D 0 0"); every(100, 800, "D 80 80");
  battV = 20.5; every(100, 500, "D 80 80");
  battV = 25.6; every(100, 3000, "D 80 80");
  check(pwm(0) == 160 && !(flags() & 12), "a 0.5 s dip to 20.5 V (motors starting) -> no alarm, still driving", pwms());
  battV = 23.6; every(100, 12000, "D 80 80");
  check(flags() & 4, "23.6 V for 12 s -> battery LOW", fmt("(flags %ld)", field(9)));
  check(pwm(0) == 100, "battery low -> speed capped at half", pwms());
  Serial.send("A 1"); run(60);
  check(field(7) == 0, "battery low -> spraying can't be armed");
  battV = 22.0; every(100, 5000, "D 80 80");
  check(wheelsStopped() && (flags() & 8), "22.0 V for 5 s -> battery FLAT: the wheels stop while the Pi still has power to report",
        fmt("(flags %ld)", field(9)));
  every(100, 2000, "D 80 80");
  check(wheelsStopped(), "and they stay stopped while it is flat");
  battV = 27.0; every(100, 7000, "D 0 0"); every(100, 800, "D 80 80");
  check(!(flags() & 12) && pwm(0) == 160, "charger connected (27 V for 7 s) -> back to normal", pwms());
  check(field(8) >= 268 && field(8) <= 272, "status reports the battery in tenths of a volt", fmt("(%ld = 27.0 V)", field(8)));

  if (fails) std::printf("\n%d of %d checks FAILED\n", fails, checks);
  else std::printf("\nALL PASSED: %d of %d checks\n", checks, checks);
  return fails ? 1 : 0;
}
