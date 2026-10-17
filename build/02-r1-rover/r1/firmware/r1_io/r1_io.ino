// R1 rover I/O board (Arduino Mega 2560). Starter code, untested on hardware: run it with the wheels off the ground.
//
// The Pi talks to this board over USB serial (115200 baud), one command per line:
//   D <left> <right>   wheel speeds, -100..100 (% of max). Left = FL+RL, right = FR+RR (skid steer).
//   V <n> <0|1>        valve n (0..5 = L1 R1 L2 R2 L3 R3) closed/open. Refused unless spraying is armed.
//   A <0|1>            arm spraying (the Pi only sends A 1 after every spray lock has passed).
//   L <g|a|r|o>        tower light: green, amber, red, off.
//   F <0|1>            camera LED rings off/on (the flash for a photo).
//   E <0|1>            drive enable (relay 12, the last link of the contactor loop).
//   P                  ping (the Pi sends a command at least every 200 ms; nothing for 300 ms = stop).
// Every 50 ms the board reports:  S <fl> <fr> <rl> <rr> <estop_ok> <tank_ok> <armed>
//   the wheel pulse counts since start (for the 25 cm photo spacing), whether the e-stop loop is closed (1 = ok),
//   whether there is water in the tank, and whether spraying is armed.
//
// Safety does not depend on this code: the e-stop and bumpers cut the contactor coil in hardware. This code adds a
// watchdog, closes every valve when anything goes wrong, and refuses to drive while the e-stop loop is open.

const uint8_t PWM_PIN[4] = {4, 5, 6, 7};        // FL FR RL RR -> driver speed input
const uint8_t DIR_PIN[4] = {22, 24, 26, 28};    // driver direction input
const uint8_t BRAKE_PIN = 30;                   // all four drivers' brake input
const uint8_t PULSE_PIN[4] = {18, 19, 20, 21};  // driver speed-pulse output (interrupt pins)
const uint8_t VALVE_PIN[6] = {38, 39, 40, 41, 42, 43};
const uint8_t PUMP_PIN = 44, LIGHT_G = 45, LIGHT_A = 46, LIGHT_R = 47, RINGS_PIN = 48, ENABLE_PIN = 49;
const uint8_t ESTOP_SENSE = A0, TANK_SENSE = A1;

// Wiring choices that vary by board / build: change them here, not with wires.
const bool RELAY_ACTIVE_LOW = true;             // most opto relay modules switch ON when the input is LOW
const bool BRAKE_ACTIVE_HIGH = true;            // some ZS-X11H versions brake on LOW: set false
const bool MIRROR[4] = {false, true, false, true};  // right-side motors face the other way
const int ESTOP_OK_ADC = 600;                   // ~2.9 V: the loop reads 3.6-4.4 V when closed
const int MAX_PWM = 200;                        // cap at ~80 % while testing
const int RAMP_PER_TICK = 6;                    // smooth starts: PWM change per 10 ms

volatile long pulses[4] = {0, 0, 0, 0};
int target[4] = {0, 0, 0, 0};                   // -MAX_PWM..MAX_PWM
int current[4] = {0, 0, 0, 0};
bool armed = false;
bool enabled = false;
unsigned long lastCmd = 0, lastReport = 0, lastRamp = 0;
String line;

void pulse0() { pulses[0] += (current[0] >= 0) ? 1 : -1; }
void pulse1() { pulses[1] += (current[1] >= 0) ? 1 : -1; }
void pulse2() { pulses[2] += (current[2] >= 0) ? 1 : -1; }
void pulse3() { pulses[3] += (current[3] >= 0) ? 1 : -1; }

void relay(uint8_t pin, bool on) { digitalWrite(pin, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW); }

void allValvesClosed() {
  for (uint8_t i = 0; i < 6; i++) relay(VALVE_PIN[i], false);
  relay(PUMP_PIN, false);
}

void brake(bool on) { digitalWrite(BRAKE_PIN, (on == BRAKE_ACTIVE_HIGH) ? HIGH : LOW); }

void stopAll() {
  for (uint8_t i = 0; i < 4; i++) { target[i] = 0; current[i] = 0; analogWrite(PWM_PIN[i], 0); }
  brake(true);
  allValvesClosed();
  armed = false;
}

bool estopOk() { return analogRead(ESTOP_SENSE) > ESTOP_OK_ADC; }

void setLight(char c) {
  relay(LIGHT_G, c == 'g');
  relay(LIGHT_A, c == 'a');
  relay(LIGHT_R, c == 'r');
}

void applyWheel(uint8_t i) {
  int v = current[i];
  bool fwd = (v >= 0) ^ MIRROR[i];
  digitalWrite(DIR_PIN[i], fwd ? HIGH : LOW);
  analogWrite(PWM_PIN[i], abs(v));
}

void handle(String s) {
  s.trim();
  if (s.length() == 0) return;
  lastCmd = millis();
  char c = s.charAt(0);
  if (c == 'D') {
    int sp = s.indexOf(' '), sp2 = s.indexOf(' ', sp + 1);
    if (sp < 0 || sp2 < 0) return;
    int l = constrain(s.substring(sp + 1, sp2).toInt(), -100, 100);
    int r = constrain(s.substring(sp2 + 1).toInt(), -100, 100);
    if (!estopOk() || !enabled) { l = 0; r = 0; }
    int pl = (long)l * MAX_PWM / 100, pr = (long)r * MAX_PWM / 100;
    target[0] = pl; target[2] = pl; target[1] = pr; target[3] = pr;
    brake(l == 0 && r == 0);
  } else if (c == 'V') {
    int n = s.substring(2, 3).toInt();
    bool open = s.endsWith("1");
    if (n < 0 || n > 5) return;
    if (open && !(armed && estopOk() && digitalRead(TANK_SENSE) == LOW)) return;   // refused
    relay(VALVE_PIN[n], open);
    bool any = false;
    for (uint8_t i = 0; i < 6; i++) any |= (digitalRead(VALVE_PIN[i]) == (RELAY_ACTIVE_LOW ? LOW : HIGH));
    relay(PUMP_PIN, any);                        // the pump only runs while a valve is open
  } else if (c == 'A') {
    armed = s.endsWith("1") && estopOk();
    if (!armed) allValvesClosed();
  } else if (c == 'L') {
    setLight(s.length() > 2 ? s.charAt(2) : 'o');
  } else if (c == 'F') {
    relay(RINGS_PIN, s.endsWith("1"));
  } else if (c == 'E') {
    enabled = s.endsWith("1");
    relay(ENABLE_PIN, enabled);
    if (!enabled) stopAll();
  }
  // 'P' only refreshes lastCmd
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
  stopAll();
  setLight('r');
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n') { handle(line); line = ""; }
    else if (line.length() < 40) line += ch;
  }
  unsigned long now = millis();
  if (now - lastCmd > 300 || !estopOk()) {       // watchdog or e-stop: stop the wheels, close the valves
    bool moving = false;
    for (uint8_t i = 0; i < 4; i++) moving |= (target[i] != 0 || current[i] != 0);
    if (moving || armed) stopAll();
    if (!estopOk()) setLight('r');
  }
  if (now - lastRamp >= 10) {                     // ramp towards the target speed
    lastRamp = now;
    for (uint8_t i = 0; i < 4; i++) {
      int d = target[i] - current[i];
      current[i] += constrain(d, -RAMP_PER_TICK, RAMP_PER_TICK);
      applyWheel(i);
    }
  }
  if (now - lastReport >= 50) {
    lastReport = now;
    noInterrupts();
    long p0 = pulses[0], p1 = pulses[1], p2 = pulses[2], p3 = pulses[3];
    interrupts();
    Serial.print("S "); Serial.print(p0); Serial.print(' '); Serial.print(p1); Serial.print(' ');
    Serial.print(p2); Serial.print(' '); Serial.print(p3); Serial.print(' ');
    Serial.print(estopOk() ? 1 : 0); Serial.print(' ');
    Serial.print(digitalRead(TANK_SENSE) == LOW ? 1 : 0); Serial.print(' ');
    Serial.println(armed ? 1 : 0);
  }
}
