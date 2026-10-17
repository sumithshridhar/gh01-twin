# Build GH-01 · Part 3: plants that water themselves

A soil sensor in one of your beds tells a ₹450 Wi-Fi computer when the soil is dry. The computer presses a relay, the
relay opens a 12 V valve on the feed pipe of one zone, and your existing drip lines do the rest. No soldering:
everything plugs in or screws down.

- Video: Instagram @ghost.ops.ai.service (GH-01 Build Part 3, "Plants that water themselves"), shown in a soil-bed
  strawberry polyhouse.
- Cost: **about ₹1,750** for one zone (₹1,600–2,300 depending on the shop). Your drip laterals stay as they are.
- Time: an afternoon.
- Status (17 Oct 2026): designed part by part at real size in Blender; parts and wiring come from the sellers' listings.
  **Not built on our bench yet.** The code is a starter: test it with the hand valve shut first.

## Tools

A small screwdriver, a spanner, PTFE (thread) tape, a hacksaw for the PVC feed pipe, PVC solvent cement, a laptop with
a USB cable.

## Parts (Indian prices, Oct 2026; estimates, check before buying)

| # | Part | Why | ≈ ₹ |
|---|---|---|---|
| 1 | ESP32 DevKit V1, 30 pin | the computer: reads the sensor, decides, has Wi-Fi | 450–550 |
| 2 | ESP32 30-pin expansion board with DC jack (6.5–16 V in, 3.3/5 V jumper) ([techiesms](https://techiesms.com/product/esp32-expansion-board-with-gpio-breakout/)) | takes 12 V straight in; a G-V-S pin trio beside every pin, so the sensor and relay plug in | 120 |
| 3 | Capacitive soil moisture sensor v1.2 ([Robu](https://robu.in/?p=130230)) | no bare metal in the soil, so it doesn't rust like the cheap two-prong ones | 50–120 |
| 4 | 5 V 1-channel relay module (with optocoupler) | a switch the ESP32 can press; the only thing that can open the valve | 35–60 |
| 5 | 12 V DC ½" normally-closed solenoid valve ([Robu](https://robu.in/?p=31396)) | shut when there's no power, so a power cut can't flood a zone | 230–420 |
| 6 | 12 V 2 A DC adapter (5.5 × 2.1 mm plug) | powers everything, from the house's socket | 180–250 |
| 7 | DC splitter cable, 1 female → 2 male (5.5 × 2.1) | one plug for the board, one for the valve | 40–60 |
| 8 | DC female jack to 2-way screw terminal | 12 V for the valve without soldering | 15–25 |
| 9 | IP65 junction box ~150 × 110 × 70 + 3 cable glands | spray and dust stay out | 250–350 |
| 10 | ½" fittings: 2 nipples, a reducer/tee into your zone's sub-main, PTFE tape | puts the valve in the feed pipe | 150 |
| 11 | A plank (~25 × 240 × 800 mm) + 2 steel straps | hangs the box on a GI column, no drilling | 100 |
| 12 | Female–female jumper wires, 3-core cable (sensor, as long as needed), 2-core cable (valve) | the connections | 100–200 |

**One valve = one zone.** A ½" valve passes roughly 8–15 L/min at drip pressure: enough for about 4 strawberry beds
(2 laterals per bed, 2 L/h emitters every 30 cm), fewer for tomato. For a bigger zone use a bigger 12 V DC valve; the
wiring is the same.

Before you buy the valve:
- **It needs pressure.** The common ½" plastic valve opens only above about 0.02 MPa: a pump, or a tank at least 2 m
  above the valve.
- **Water flows one way.** The arrow on the valve points to the beds.

## Build (the video's 5 steps)

1. **The valve on the zone.** Shut the main. Cut the feed pipe of one zone just before its sub-main header (after a
   hand ball valve, so you can always shut the water yourself). Valve in, arrow to the beds, PTFE tape on the threads.
   **Your drip laterals stay just as they are.**
2. **The sensor.** In the zone's driest bed (usually the one by the side wall), through a planting hole, between the
   two drip rows, a few cm from a plant. Push it in up to the white line; keep the electronics end dry.
3. **The brain.** Strap the plank to a GI column near the zone, away from the pad and the foggers. Box on the plank.
   Expansion board and relay inside on short standoffs; push the ESP32 into the expansion board (antenna end away from
   the DC jack). **Set the V-pin jumper to 5V.**
4. **Power and wires** (colour to colour):

   | From | To |
   |---|---|
   | 12 V adapter (in the house's socket) → splitter → plug 1 | expansion board DC jack |
   | splitter → plug 2 | DC screw terminal |
   | DC screw terminal **+** | relay **COM** |
   | relay **NO** | valve wire 1 |
   | DC screw terminal **−** | valve wire 2 |
   | relay DC+ / DC− / IN | **V / G / S of D26** |
   | soil sensor VCC / GND / AOUT (red / black / yellow) | **V / G / S of D34** |

   The valve doesn't care which of its two wires is which. Run the sensor and valve cables along the column and the
   bed foot, out of the paths. Close the lid.
5. **The code.** Install the [Arduino IDE](https://www.arduino.cc/en/software), add the ESP32 boards (Boards Manager →
   "esp32" by Espressif), open [`auto_water/auto_water.ino`](auto_water/auto_water.ino), choose "DOIT ESP32 DEVKIT V1", upload.
   Open the Serial Monitor (115200): hold the sensor in the air and note the number, then dip it in a glass of water up
   to the line and note that number. Type both into `DRY` and `WET` and upload again. Halfway between them is your
   "thirsty" line; adjust it after a week by watching your beds.

## The trick most people miss

Water reaches the sensor slowly. If the box checks again straight after watering, the soil still reads dry, so it waters
again, and again: the beds flood. So the code waters for **1 minute, then waits 30 minutes** before it checks again, and
never waters more than 6 times a day. Change `WATER_MS`, `SOAK_MS` and `MAX_PER_DAY` for your zone and emitter flow
(1 minute is only a starting point; a strawberry zone usually needs several minutes per shot).

It also refuses to water if the sensor reads something impossible (a pulled-out cable reads like bone-dry soil).

## Phone messages (optional)

Install the free **ntfy** app (Android / iOS, no account), subscribe to a secret name, put your Wi-Fi and the same name in
the code. You get "Watered…" and "check the sensor" messages. Without Wi-Fi the box still waters on its own.

## Safety

- Only 12 V goes anywhere near water. The 230 V side is the adapter in the house's socket (covered, with an RCCB).
- The hand valve before the solenoid valve lets you shut the water whatever the electronics do.
- Normally-closed valve: no power = no water.

## Sources

- Valve rating (12 V, NC, 0.02–0.8 MPa, not for gravity feed): [Robu listing](https://robu.in/?p=31396)
- Capacitive sensor v1.2: [Robu listing](https://robu.in/?p=130230)
- ESP32 expansion board (DC 6.5–16 V, 3.3/5 V jumper, G-V-S pins): [techiesms](https://techiesms.com/product/esp32-expansion-board-with-gpio-breakout/)
- Phone messages: [ntfy.sh](https://ntfy.sh)
