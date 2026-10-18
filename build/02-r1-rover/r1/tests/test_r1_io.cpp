// Software-in-the-loop test of the REAL rover firmware (r1_io.ino) on a laptop, no Arduino needed (18 Oct 2026).
// The sketch is compiled as-is against a fake Arduino (Arduino.h in this folder); the test plays the Pi: it sends command
// lines, moves the clock 1 ms at a time, and checks the pins the sketch drives.
//
//   bash run_test.sh   (builds the test in a temp folder, runs it, deletes it: a fresh unsigned .exe makes antivirus
//                       tools like Avast pause it for a scan, 18 Oct 2026)
#include <cstdio>
#include "Arduino.h"
#include "../firmware/r1_io/r1_io.ino"

static int fails = 0;
static void check(bool ok, const char* what, const char* detail = "") {
  std::printf("  %s  %s %s\n", ok ? "PASS" : "FAIL", what, detail);
  if (!ok) fails++;
}
static void run(unsigned long ms) { for (unsigned long i = 0; i < ms; i++) { g_ms++; loop(); } }
static unsigned long lastSend = 0;                                                  // when the Pi last sent anything
static void every(unsigned long period, unsigned long total, const char* line) {   // the Pi resending a command
  for (unsigned long t = 0; t < total; t += period) { Serial.send(line); lastSend = g_ms; run(period); }
}
static int pwm(int i) { return g_pwm[PWM_PIN[i]]; }
static bool wheelsStopped() { for (int i = 0; i < 4; i++) if (pwm(i) != 0) return false; return true; }
static bool valveOpen(int n) { return g_pin[VALVE_PIN[n]] == (RELAY_ACTIVE_LOW ? LOW : HIGH); }
static bool pumpOn() { return g_pin[PUMP_PIN] == (RELAY_ACTIVE_LOW ? LOW : HIGH); }
static bool brakeOn() { return g_pin[BRAKE_PIN] == (BRAKE_ACTIVE_HIGH ? HIGH : LOW); }

int main() {
  g_adc[ESTOP_SENSE] = 900;                     // e-stop loop closed (reads ~4.4 V)
  g_pin[TANK_SENSE] = LOW;                      // water in the tank
  setup();
  std::printf("R1 firmware test (r1_io.ino on a fake Arduino Mega)\n");

  std::printf("1. boot\n");
  check(wheelsStopped() && brakeOn(), "wheels stopped, brake on");
  check(!valveOpen(0) && !pumpOn(), "all valves closed, pump off");

  std::printf("2. drive is refused until the Pi enables it\n");
  every(100, 500, "D 50 50");
  check(wheelsStopped(), "D 50 50 without E 1 -> wheels stay still");

  std::printf("3. enable + drive at 50 %%\n");
  Serial.send("E 1");
  Serial.send("D 50 50"); run(50);
  char r[80];
  std::snprintf(r, sizeof r, "(PWM %d after 50 ms, not a jump to 100)", pwm(0));
  check(pwm(0) > 0 && pwm(0) < 100, "smooth start: the speed ramps up", r);
  every(100, 600, "D 50 50");
  char d[80];
  std::snprintf(d, sizeof d, "(PWM %d %d %d %d, target 100)", pwm(0), pwm(1), pwm(2), pwm(3));
  check(pwm(0) == 100 && pwm(1) == 100 && pwm(2) == 100 && pwm(3) == 100, "all 4 wheels at speed", d);
  check(g_pin[DIR_PIN[0]] != g_pin[DIR_PIN[1]], "right side mirrored (motors face the other way)");

  std::printf("4. the Pi goes silent: the watchdog must stop the wheels\n");
  unsigned long t0 = lastSend, stopped = 0;
  for (int i = 0; i < 1000 && !stopped; i++) { g_ms++; loop(); if (wheelsStopped()) stopped = g_ms - t0; }
  std::snprintf(d, sizeof d, "(stopped %lu ms after the last command)", stopped);
  check(stopped >= 300 && stopped <= 320, "wheels stop ~300 ms after the Pi goes quiet", d);
  check(brakeOn(), "brake on after the watchdog");

  std::printf("5. e-stop pressed while driving\n");
  every(100, 600, "D 60 60");
  g_adc[ESTOP_SENSE] = 100;                     // loop opened (button or bumper)
  t0 = g_ms; stopped = 0;
  for (int i = 0; i < 100 && !stopped; i++) { g_ms++; Serial.send("D 60 60"); loop(); if (wheelsStopped()) stopped = g_ms - t0; }
  std::snprintf(d, sizeof d, "(stopped after %lu ms)", stopped);
  check(stopped > 0 && stopped <= 2, "wheels stop at once, even while the Pi keeps sending", d);
  check(g_pin[LIGHT_R] == (RELAY_ACTIVE_LOW ? LOW : HIGH), "tower light red");
  g_adc[ESTOP_SENSE] = 900;

  std::printf("6. spraying: a valve only opens when spraying is armed\n");
  Serial.send("V 2 1"); run(20);
  check(!valveOpen(2), "V 2 1 while NOT armed -> refused");
  Serial.send("A 1"); Serial.send("V 2 1"); run(20);
  check(valveOpen(2) && pumpOn(), "armed -> valve 2 opens, pump runs");
  run(400);
  check(!valveOpen(2) && !pumpOn(), "Pi silent -> watchdog closes the valve and stops the pump");

  std::printf("7. the status line the Pi reads\n");
  Serial.out.clear(); Serial.send("P"); run(60);
  size_t a = Serial.out.rfind("S ");
  std::string last = a == std::string::npos ? "" : Serial.out.substr(a, Serial.out.find('\n', a) - a);
  int n = 0; for (char c : last) n += (c == ' ');
  check(n == 7, "S line has 8 fields", ("(\"" + last + "\")").c_str());

  std::printf(fails ? "\n%d FAILED\n" : "\nALL PASSED\n", fails);
  return fails ? 1 : 0;
}
