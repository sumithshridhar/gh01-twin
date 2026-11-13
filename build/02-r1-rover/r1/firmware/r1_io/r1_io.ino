// R1 rover I/O board (Arduino Mega 2560). Starter code, untested on hardware: run it with the wheels off the ground.
//
// v2 (13 Nov 2026). Fixes for the defects the laptop tests found (build/02-r1-rover/ISSUES.md, E1-E4):
//   - A bumper or e-stop press LATCHES. Releasing it never restarts the wheels. A person presses the green RESET on the
//     rover (hardware latch, read on A3), the Pi sends E 1, then a neutral D 0 0, and only then can it move again.
//   - Every valve closes by itself after 4 s, even if the Pi keeps the link alive.
//   - Commands are parsed strictly. A broken line ("V 1") does nothing and does not feed the watchdog.
//   - The battery is watched on A2. Low = no spraying and half speed. Flat = the wheels stop while the Pi still has
//     power to say where the rover is, instead of the battery's BMS cutting everything in the middle of a row.
//   - If the tank runs dry while spraying, the valves close and the pump stops.
//
// The Pi talks to this board over USB serial (115200 baud), one command per line:
//   D <left> <right>   wheel speeds, -100..100 (% of max). Left = FL+RL, right = FR+RR (skid steer).
//   V <n> <0|1>        valve n (0..5 = L1 R1 L2 R2 L3 R3) closed/open. Refused unless spraying is armed. 4 s max.
//   A <0|1>            arm spraying (the Pi only sends A 1 after every spray lock has passed).
//   L <g|a|r|o>        tower light: green, amber, red, off.
//   F <0|1>            camera LED rings off/on.
//   E <0|1>            drive enable (relay 12). Refused while the e-stop chain is open or nobody has pressed RESET.
//   P                  ping (the Pi sends a command at least every 200 ms; nothing valid for 300 ms = stop).
// Every 50 ms the board reports:
//   S <fl> <fr> <rl> <rr> <estop_ok> <tank_ok> <armed> <battery_dV> <flags>
//   wheel pulse counts since start, e-stop chain closed (1 = ok), water in the tank, spraying armed, battery in tenths
//   of a volt (256 = 25.6 V), and flags: 1 tripped (needs RESET + E 1), 2 RESET latch held, 4 battery low,
//   8 battery flat, 16 waiting for a neutral D 0 0, 32 a valve hit its 4 s limit, 64 the tank ran dry mid-spray.
//
// Safety does not depend on this code: the e-stop and bumpers drop the latch relay and the contactor in hardware, and
// the pump and valves are fed from after the contactor. This code is the second layer.

const uint8_t PWM_PIN[4] = {4, 5, 6, 7};        // FL FR RL RR -> driver speed input
const uint8_t DIR_PIN[4] = {22, 24, 26, 28};    // driver direction input
const uint8_t BRAKE_PIN = 30;                   // all four drivers' brake input
const uint8_t PULSE_PIN[4] = {18, 19, 20, 21};  // driver speed-pulse output (interrupt pins)
const uint8_t VALVE_PIN[6] = {38, 39, 40, 41, 42, 43};
const uint8_t PUMP_PIN = 44, LIGHT_G = 45, LIGHT_A = 46, LIGHT_R = 47, RINGS_PIN = 48, ENABLE_PIN = 49;
const uint8_t ESTOP_SENSE = A0, TANK_SENSE = A1, BATT_SENSE = A2, LATCH_SENSE = A3;

// Wiring choices that vary by board / build: change them here, not with wires.
const bool RELAY_ACTIVE_LOW = true;             // most opto relay modules switch ON when the input is LOW
const bool BRAKE_ACTIVE_HIGH = true;            // some ZS-X11H versions brake on LOW: set false
const bool MIRROR[4] = {false, true, false, true};  // right-side motors face the other way
const int SENSE_OK_ADC = 600;                   // A0 / A3 through 56 k / 10 k: ~19.4 V. Closed reads 24-29 V
const int MAX_PWM = 200;                        // cap at ~80 % while testing
const int RAMP_PER_TICK = 6;                    // smooth starts: PWM change per 10 ms
const unsigned long WATCHDOG_MS = 300;          // nothing valid from the Pi for this long = stop
const unsigned long VALVE_MAX_MS = 4000;        // a valve never stays open longer, whatever the Pi says
const unsigned long DRY_MS = 300;               // tank float must read dry this long (sloshing) before we act
const int BATT_LOW_DV = 240, BATT_FLAT_DV = 224, BATT_OK_DV = 260;   // 8S LiFePO4: 3.0 / 2.8 / 3.25 V a cell
const unsigned long BATT_LOW_MS = 10000, BATT_FLAT_MS = 3000, BATT_OK_MS = 5000;

volatile long pulses[4] = {0, 0, 0, 0};
int target[4] = {0, 0, 0, 0};                   // -MAX_PWM..MAX_PWM
int current[4] = {0, 0, 0, 0};
bool armed = false, enabled = false, tripped = false, needNeutral = true;
bool battLow = false, battFlat = false, valveTimedOut = false, tankDryStop = false;
bool valveOn[6] = {false, false, false, false, false, false};
unsigned long valveSince[6] = {0, 0, 0, 0, 0, 0};
unsigned long lastCmd = 0, lastReport = 0, lastTick = 0;
bool lowCounting = false, flatCounting = false, okCounting = false, dryCounting = false;
unsigned long lowSince = 0, flatSince = 0, okSince = 0, drySince = 0;
float battDV = 0;                               // filtered battery voltage, tenths of a volt
String line;

void pulse0() { pulses[0] += (current[0] >= 0) ? 1 : -1; }
void pulse1() { pulses[1] += (current[1] >= 0) ? 1 : -1; }
void pulse2() { pulses[2] += (current[2] >= 0) ? 1 : -1; }
void pulse3() { pulses[3] += (current[3] >= 0) ? 1 : -1; }

void relay(uint8_t pin, bool on) { digitalWrite(pin, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW); }
bool chainOk() { return analogRead(ESTOP_SENSE) > SENSE_OK_ADC; }   // e-stop + both bumpers closed
bool latchOk() { return analogRead(LATCH_SENSE) > SENSE_OK_ADC; }   // a person pressed RESET since the last trip
bool tankOk() { return digitalRead(TANK_SENSE) == LOW; }
float readBattDV() { return analogRead(BATT_SENSE) * 330.0f / 1023.0f; }   // 5 V ADC x 6.6 divider, in 0.1 V

bool anyValve() {
  for (uint8_t i = 0; i < 6; i++) if (valveOn[i]) return true;
  return false;
}

void setValve(uint8_t n, bool on) {
  if (on && !valveOn[n]) valveSince[n] = millis();
  valveOn[n] = on;
  relay(VALVE_PIN[n], on);
  relay(PUMP_PIN, anyValve());                  // the pump only runs while a valve is open
}

void allValvesClosed() {
  for (uint8_t i = 0; i < 6; i++) setValve(i, false);
}

void brake(bool on) { digitalWrite(BRAKE_PIN, (on == BRAKE_ACTIVE_HIGH) ? HIGH : LOW); }

void stopAll() {
  for (uint8_t i = 0; i < 4; i++) { target[i] = 0; current[i] = 0; analogWrite(PWM_PIN[i], 0); }
  brake(true);
  allValvesClosed();
  armed = false;
}

void setLight(char c) {
  relay(LIGHT_G, c == 'g');
  relay(LIGHT_A, c == 'a');
  relay(LIGHT_R, c == 'r');
}

void trip() {                                   // bumper or e-stop: stop, drop drive power, wait for a person
  tripped = true;
  enabled = false;
  relay(ENABLE_PIN, false);
  needNeutral = true;
  stopAll();
  setLight('r');
}

void applyWheel(uint8_t i) {
  int v = current[i];
  bool fwd = (v >= 0) ^ MIRROR[i];
  digitalWrite(DIR_PIN[i], fwd ? HIGH : LOW);
  analogWrite(PWM_PIN[i], abs(v));
}

bool driveAllowed() { return enabled && !tripped && chainOk() && latchOk() && !battFlat; }

void drive(long l, long r) {
  l = constrain(l, -100L, 100L);
  r = constrain(r, -100L, 100L);
  bool ok = driveAllowed();
  if (!ok) { l = 0; r = 0; }
  if (needNeutral) {                            // after enable, a watchdog stop or a trip: stick at centre first
    if (ok && l == 0 && r == 0) needNeutral = false;
    else { l = 0; r = 0; }
  }
  if (battLow) { l = constrain(l, -50L, 50L); r = constrain(r, -50L, 50L); }
  int pl = (int)(l * MAX_PWM / 100), pr = (int)(r * MAX_PWM / 100);
  target[0] = pl; target[2] = pl; target[1] = pr; target[3] = pr;
  brake(l == 0 && r == 0);
}

bool isInt(const String& t) {                   // -100..100 style: optional minus, 1-4 digits, nothing else
  unsigned int n = t.length(), i = 0;
  if (n == 0 || n > 5) return false;
  if (t.charAt(0) == '-') { i = 1; if (n == 1) return false; }
  for (; i < n; i++) if (t.charAt(i) < '0' || t.charAt(i) > '9') return false;
  return true;
}

// Returns true only for a complete, valid command. Only valid commands feed the watchdog.
bool handle(String s) {
  s.trim();
  unsigned int n = s.length();
  if (n == 0) return false;
  char c = s.charAt(0);
  if (c == 'P') return n == 1;
  if (n < 3 || s.charAt(1) != ' ') return false;
  if (c == 'D') {
    int sp = s.indexOf(' ', 2);
    if (sp < 0) return false;
    String a = s.substring(2, sp), b = s.substring(sp + 1);
    if (!isInt(a) || !isInt(b)) return false;
    drive(a.toInt(), b.toInt());
    return true;
  }
  if (c == 'V') {
    if (n != 5 || s.charAt(3) != ' ') return false;
    char k = s.charAt(2), v = s.charAt(4);
    if (k < '0' || k > '5' || (v != '0' && v != '1')) return false;
    uint8_t valve = k - '0';
    if (v == '0') { setValve(valve, false); return true; }
    if (armed && chainOk() && !tripped && tankOk() && !battLow && !battFlat) setValve(valve, true);   // else refused
    return true;
  }
  if (n != 3) return false;
  char v = s.charAt(2);
  if (c == 'L') {
    if (v != 'g' && v != 'a' && v != 'r' && v != 'o') return false;
    setLight(v);
    return true;
  }
  if (v != '0' && v != '1') return false;
  if (c == 'A') {
    armed = v == '1' && driveAllowed() && tankOk() && !battLow;
    if (armed) { valveTimedOut = false; tankDryStop = false; }
    else allValvesClosed();
    return true;
  }
  if (c == 'F') { relay(RINGS_PIN, v == '1'); return true; }
  if (c == 'E') {
    if (v == '1') {
      if (!(chainOk() && latchOk())) return true;   // refused: chain still open, or nobody pressed RESET
      tripped = false;
      enabled = true;
      relay(ENABLE_PIN, true);
      needNeutral = true;
    } else {
      enabled = false;
      relay(ENABLE_PIN, false);
      stopAll();
    }
    return true;
  }
  return false;
}

void batteryTick(unsigned long now) {           // every 10 ms
  battDV += (readBattDV() - battDV) * 0.02f;    // ~0.5 s smoothing
  bool below = battDV < BATT_LOW_DV;
  if (below && !lowCounting) { lowCounting = true; lowSince = now; }
  if (!below) lowCounting = false;
  if (lowCounting && now - lowSince >= BATT_LOW_MS && !battLow) { battLow = true; armed = false; allValvesClosed(); }

  bool flat = battDV < BATT_FLAT_DV;
  if (flat && !flatCounting) { flatCounting = true; flatSince = now; }
  if (!flat) flatCounting = false;
  if (flatCounting && now - flatSince >= BATT_FLAT_MS && !battFlat) { battFlat = true; stopAll(); needNeutral = true; }

  bool charged = battDV > BATT_OK_DV;           // the charger is on: clear both
  if (charged && !okCounting) { okCounting = true; okSince = now; }
  if (!charged) okCounting = false;
  if (okCounting && now - okSince >= BATT_OK_MS) { battLow = false; battFlat = false; }
}

void sprayTick(unsigned long now) {
  for (uint8_t i = 0; i < 6; i++) {
    if (valveOn[i] && now - valveSince[i] >= VALVE_MAX_MS) { setValve(i, false); valveTimedOut = true; }
  }
  bool dry = anyValve() && !tankOk();
  if (dry && !dryCounting) { dryCounting = true; drySince = now; }
  if (!dry) dryCounting = false;
  if (dryCounting && now - drySince >= DRY_MS) { allValvesClosed(); armed = false; tankDryStop = true; dryCounting = false; }
}

void setup() {
  Serial.begin(115200);
  for (uint8_t i = 0; i < 4; i++) {
    pinMode(PWM_PIN[i], OUTPUT);
    pinMode(DIR_PIN[i], OUTPUT);
    pinMode(PULSE_PIN[i], INPUT_PULLUP);
  }
  pinMode(BRAKE_PIN, OUTPUT);
  uint8_t outs[] = {38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49};
  for (uint8_t i = 0; i < sizeof(outs); i++) { pinMode(outs[i], OUTPUT); relay(outs[i], false); }
  pinMode(TANK_SENSE, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PULSE_PIN[0]), pulse0, RISING);
  attachInterrupt(digitalPinToInterrupt(PULSE_PIN[1]), pulse1, RISING);
  attachInterrupt(digitalPinToInterrupt(PULSE_PIN[2]), pulse2, RISING);
  attachInterrupt(digitalPinToInterrupt(PULSE_PIN[3]), pulse3, RISING);
  battDV = readBattDV();
  stopAll();
  setLight('r');
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n') { if (handle(line)) lastCmd = millis(); line = ""; }
    else if (line.length() < 40) line += ch;
  }
  unsigned long now = millis();
  if (!chainOk() && !tripped) trip();           // bumper or e-stop: latch until RESET + E 1
  if (now - lastCmd > WATCHDOG_MS) {            // the Pi went quiet: stop the wheels, close the valves
    bool moving = false;
    for (uint8_t i = 0; i < 4; i++) moving |= (target[i] != 0 || current[i] != 0);
    if (moving || armed || anyValve()) { stopAll(); needNeutral = true; }
  }
  sprayTick(now);
  if (now - lastTick >= 10) {                   // ramp towards the target speed, watch the battery
    lastTick = now;
    for (uint8_t i = 0; i < 4; i++) {
      int d = target[i] - current[i];
      current[i] += constrain(d, -RAMP_PER_TICK, RAMP_PER_TICK);
      applyWheel(i);
    }
    batteryTick(now);
  }
  if (now - lastReport >= 50) {
    lastReport = now;
    noInterrupts();
    long p0 = pulses[0], p1 = pulses[1], p2 = pulses[2], p3 = pulses[3];
    interrupts();
    int flags = (tripped ? 1 : 0) | (latchOk() ? 2 : 0) | (battLow ? 4 : 0) | (battFlat ? 8 : 0) |
                (needNeutral ? 16 : 0) | (valveTimedOut ? 32 : 0) | (tankDryStop ? 64 : 0);
    Serial.print("S "); Serial.print(p0); Serial.print(' '); Serial.print(p1); Serial.print(' ');
    Serial.print(p2); Serial.print(' '); Serial.print(p3); Serial.print(' ');
    Serial.print(chainOk() ? 1 : 0); Serial.print(' ');
    Serial.print(tankOk() ? 1 : 0); Serial.print(' ');
    Serial.print(armed ? 1 : 0); Serial.print(' ');
    Serial.print((int)(battDV + 0.5f)); Serial.print(' ');
    Serial.println(flags);
  }
}
