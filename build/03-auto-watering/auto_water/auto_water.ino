// GH-01 Build Part 3: plants that water themselves.
//
// Hardware (see ../README.md):
//   ESP32 DevKit V1 (30 pin) on a 30-pin expansion board, 12 V into the board's DC jack, V-pin jumper on 5V
//   Capacitive soil moisture sensor v1.2  -> G-V-S of pin D34  (black G, red V, yellow S)
//   5 V 1-channel relay module            -> G-V-S of pin D26  (DC- to G, DC+ to V, IN to S)
//   12 V normally-closed solenoid valve   -> 12 V + through the relay's COM / NO, 12 V - straight to the valve
//
// What it does: every minute it reads the soil. If the soil has been drier than your "thirsty" line three times in a
// row, it opens the valve for 1 minute, then WAITS 30 minutes (water takes time to reach the sensor; without the wait
// it keeps watering and floods the pots).
//
// What keeps it safe (the decisions are in water_logic.h and are tested on a laptop, see ../tests):
//   - the valve is shut first thing at power-up, and a normally-closed valve shuts by itself when the power goes
//   - no watering in the first 30 minutes after power-up, so flickering power can't flood the bed
//   - an impossible sensor reading (cable out, sensor broken) never opens the valve
//   - if it waters twice and the soil does not get wetter, it stops and tells you (empty tank, blocked line, or the
//     sensor is out of the soil). It starts again by itself when the soil reads wet
//   - never more than MAX_PER_DAY waterings in 24 powered-on hours, remembered across power cuts
//   - if the program ever hangs, a watchdog restarts the board, and a restart shuts the valve
// Optional: a message on your phone through the free ntfy app. It waters the same with or without Wi-Fi.
//
// Starter code. The decisions are tested on a laptop; the sketch has not been run on real hardware yet. Try it with the
// valve on a bucket first, and keep the hand tap on the line.

#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <esp_task_wdt.h>
#include "water_logic.h"

// ── 1. Calibrate. Open Tools > Serial Monitor (115200). Note the number with the sensor in dry air, then in a glass of
//       water (up to the white line). Type both in here. Halfway between them is your "thirsty" line. ──
const int DRY = 2900;                   // your reading in dry air
const int WET = 1250;                   // your reading in water
const int THIRSTY = (DRY + WET) / 2;    // higher number = drier soil

// ── 2. Pins and timing ──
const int SENSOR_PIN = 34;              // D34: an input-only pin on ADC1 (works while Wi-Fi is on)
const int RELAY_PIN = 26;               // D26
const bool RELAY_ON_LOW = true;         // most blue 1-channel modules switch on when IN goes LOW
const int MAX_PER_DAY = 6;              // at most 12

// ── 3. Optional: Wi-Fi + phone messages (leave WIFI_NAME empty to run without) ──
const char* WIFI_NAME = "";
const char* WIFI_PASS = "";
const char* NTFY_TOPIC = "";            // a secret name, e.g. "my-farm-x7k2q"; subscribe to the same name in the ntfy app

WaterCfg cfg;
WaterState st;
Preferences store;                      // the board's own small memory: survives a power cut
unsigned long carried = 0;              // powered-on time from before this power-up
unsigned long lastSave = 0, lastWifiTry = 0;
unsigned long lastNote[5] = {0, 0, 0, 0, 0};

unsigned long poweredOn() { return carried + millis(); }

void valve(bool open) {
  digitalWrite(RELAY_PIN, (open ^ RELAY_ON_LOW) ? HIGH : LOW);
}

void save() {
  store.putBytes("times", st.waterings, sizeof(st.waterings));
  store.putInt("n", st.nWater);
  store.putInt("slot", st.nextSlot);
  store.putInt("noEffect", st.noEffect);
  store.putBool("locked", st.locked);
  store.putULong("on", poweredOn());
  lastSave = millis();
}

void load() {
  if (store.getBytesLength("times") == sizeof(st.waterings)) store.getBytes("times", st.waterings, sizeof(st.waterings));
  st.nWater = constrain(store.getInt("n", 0), 0, 12);
  st.nextSlot = constrain(store.getInt("slot", 0), 0, 11);
  st.noEffect = store.getInt("noEffect", 0);
  st.locked = store.getBool("locked", false);
  carried = store.getULong("on", 0);
}

// wait without ever going quiet: the watchdog is fed twice a second
void nap(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    esp_task_wdt_reset();
    delay(500);
  }
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

void notify(const String& msg) {
  Serial.println(msg);
  if (strlen(NTFY_TOPIC) == 0 || WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setTimeout(8000);
  http.begin(String("https://ntfy.sh/") + NTFY_TOPIC);
  int code = http.POST(msg);
  if (code != 200) Serial.printf("ntfy failed: %d\n", code);
  http.end();
}

// the same warning at most once every `everyMs`, so the phone doesn't fill up and get ignored
void notifyEvery(int kind, unsigned long everyMs, const String& msg) {
  if (lastNote[kind] != 0 && millis() - lastNote[kind] < everyMs) return;
  lastNote[kind] = millis() | 1;
  notify(msg);
}

void wifi() {
  if (strlen(WIFI_NAME) == 0 || WiFi.status() == WL_CONNECTED) return;
  if (lastWifiTry != 0 && millis() - lastWifiTry < 15UL * 60 * 1000) return;   // try again every 15 minutes
  lastWifiTry = millis() | 1;
  WiFi.begin(WIFI_NAME, WIFI_PASS);
  for (int i = 0; i < 20 && WiFi.status() != WL_CONNECTED; i++) nap(500);
}

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  valve(false);                          // valve shut first, always
  Serial.begin(115200);
#if ESP_ARDUINO_VERSION_MAJOR >= 3       // the watchdog call changed between versions of the ESP32 board package
  esp_task_wdt_config_t wdt = {.timeout_ms = 30000, .idle_core_mask = 0, .trigger_panic = true};
  esp_task_wdt_reconfigure(&wdt);
#else
  esp_task_wdt_init(30, true);
#endif
  esp_task_wdt_add(NULL);                // if loop() stops for 30 s the board restarts, and a restart shuts the valve
  analogSetPinAttenuation(SENSOR_PIN, ADC_11db);
  cfg.dry = DRY; cfg.wet = WET; cfg.thirsty = THIRSTY; cfg.maxPerDay = min(MAX_PER_DAY, 12);
  store.begin("water", false);
  load();
  wifi();
  notify("Watering box started. Thirsty line: " + String(THIRSTY) + (st.locked ? ". Still stopped: the soil did not get wetter last time." : ""));
}

void loop() {
  wifi();
  int raw = readSoil();
  Serial.printf("soil %d  (%d%% wet, thirsty above %d)\n", raw, wetPercent(raw), THIRSTY);
  WaterDecision d = decide(cfg, st, raw, poweredOn(), millis());

  if (d.act == W_WATER) {
    valve(true);
    nap(cfg.waterMs);
    valve(false);
    watered(cfg, st, raw, poweredOn());
    save();
    notify("Watered 1 min. Soil was " + String(wetPercent(raw)) + "% wet. Checking again in 30 min.");
  } else {
    valve(false);                        // belt and braces: every other answer means "shut"
    if (d.act == W_SENSOR_BAD)
      notifyEvery(W_SENSOR_BAD, 60UL * 60 * 1000, "Soil sensor reads " + String(raw) + ": check its cable. Not watering.");
    if (d.act == W_DAY_CAP)
      notifyEvery(W_DAY_CAP, 3UL * 3600 * 1000, "Still dry, but already watered " + String(cfg.maxPerDay) + " times today. Check the water line.");
    if (d.act == W_LOCKED)
      notifyEvery(W_LOCKED, 6UL * 3600 * 1000, "Watered twice and the soil did not get wetter. Stopped. Check the tank, the line and that the sensor is in the soil. It starts again when the soil reads wet.");
    if (d.changed) save();
  }
  if (millis() - lastSave > 30UL * 60 * 1000) save();    // remember the powered-on time, for the daily limit
  nap(d.waitMs);
}
