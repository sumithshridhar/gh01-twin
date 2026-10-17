// GH-01 Build Part 3: plants that water themselves.
//
// Hardware (see ../README.md):
//   ESP32 DevKit V1 (30 pin) on a 30-pin expansion board, 12 V into the board's DC jack, V-pin jumper on 5V
//   Capacitive soil moisture sensor v1.2  -> G-V-S of pin D34  (black G, red V, yellow S)
//   5 V 1-channel relay module            -> G-V-S of pin D26  (DC- to G, DC+ to V, IN to S)
//   12 V normally-closed solenoid valve   -> 12 V + through the relay's COM / NO, 12 V - straight to the valve
//
// What it does: every minute it reads the soil. If the soil is drier than your "thirsty" line, it opens the valve for
// 1 minute, then WAITS 30 minutes before it checks again (water takes time to reach the sensor; without the wait it
// keeps watering and floods the pots). Never more than MAX_PER_DAY waterings in 24 h, and it refuses to water if the
// sensor reads something impossible (unplugged / broken). Optional: a message on your phone through the free ntfy app.
//
// Starter code, untested on your hardware: try it with the valve on a bucket first.

#include <WiFi.h>
#include <HTTPClient.h>

// ── 1. Calibrate. Open Tools > Serial Monitor (115200). Note the number with the sensor in dry air, then in a glass of
//       water (up to the white line). Type both in here. Halfway between them is your "thirsty" line. ──
const int DRY = 2900;                   // your reading in dry air
const int WET = 1250;                   // your reading in water
const int THIRSTY = (DRY + WET) / 2;    // higher number = drier soil

// ── 2. Pins and timing ──
const int SENSOR_PIN = 34;              // D34: an input-only pin on ADC1 (works while Wi-Fi is on)
const int RELAY_PIN = 26;               // D26
const bool RELAY_ON_LOW = true;         // most blue 1-channel modules switch on when IN goes LOW
const unsigned long WATER_MS = 60UL * 1000;          // water for 1 minute
const unsigned long SOAK_MS = 30UL * 60 * 1000;      // then wait 30 minutes
const unsigned long CHECK_MS = 60UL * 1000;          // otherwise check once a minute
const int MAX_PER_DAY = 6;

// ── 3. Optional: Wi-Fi + phone messages (leave WIFI_NAME empty to run without) ──
const char* WIFI_NAME = "";
const char* WIFI_PASS = "";
const char* NTFY_TOPIC = "";            // a secret name, e.g. "my-farm-x7k2q"; subscribe to the same name in the ntfy app

unsigned long waterings[MAX_PER_DAY];   // when the last waterings happened (millis)
int nWater = 0, nextSlot = 0;

void valve(bool open) {
  digitalWrite(RELAY_PIN, (open ^ RELAY_ON_LOW) ? HIGH : LOW);
}

int readSoil() {
  long sum = 0;
  for (int i = 0; i < 16; i++) {
    sum += analogRead(SENSOR_PIN);
    delay(20);
  }
  return sum / 16;
}

int wetPercent(int raw) {
  return constrain(map(raw, DRY, WET, 0, 100), 0, 100);
}

int wateredToday() {
  int n = 0;
  for (int i = 0; i < nWater; i++)
    if (millis() - waterings[i] < 24UL * 3600 * 1000) n++;
  return n;
}

void notify(const String& msg) {
  Serial.println(msg);
  if (strlen(NTFY_TOPIC) == 0 || WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(String("https://ntfy.sh/") + NTFY_TOPIC);
  int code = http.POST(msg);
  if (code != 200) Serial.printf("ntfy failed: %d\n", code);
  http.end();
}

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  valve(false);                          // valve shut first, always
  Serial.begin(115200);
  analogSetPinAttenuation(SENSOR_PIN, ADC_11db);
  if (strlen(WIFI_NAME) > 0) {
    WiFi.begin(WIFI_NAME, WIFI_PASS);
    for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  }
  notify("Watering box started. Thirsty line: " + String(THIRSTY));
}

void loop() {
  int raw = readSoil();
  Serial.printf("soil %d  (%d%% wet, thirsty above %d)\n", raw, wetPercent(raw), THIRSTY);

  if (raw > DRY + 400 || raw < WET - 400) {             // impossible reading: unplugged or broken sensor
    valve(false);
    notify("Soil sensor reads " + String(raw) + ": check its cable. Not watering.");
    delay(10UL * 60 * 1000);
    return;
  }

  if (raw > THIRSTY && wateredToday() < MAX_PER_DAY) {
    valve(true);
    delay(WATER_MS);
    valve(false);
    waterings[nextSlot] = millis();
    nextSlot = (nextSlot + 1) % MAX_PER_DAY;
    nWater = min(nWater + 1, MAX_PER_DAY);
    notify("Watered 1 min. Soil was " + String(wetPercent(raw)) + "% wet. Checking again in 30 min.");
    delay(SOAK_MS);                                       // the trick: let the water reach the sensor
  } else {
    if (raw > THIRSTY) notify("Still dry, but already watered " + String(MAX_PER_DAY) + " times today. Check the water line.");
    delay(CHECK_MS);
  }
}
