# Build GH-01 · Part 3: plants that water themselves

A soil sensor tells a ₹450 Wi-Fi computer when the pots are dry. The computer presses a relay, the relay opens a 12 V water
valve, and drip pipe takes the water to every pot. No soldering: everything plugs in or screws down.

- Video: Instagram @ghost.ops.ai.service (GH-01 Build Part 3, "Plants that water themselves").
- Cost: **about ₹2,000** (₹1,800–2,500 depending on the shop), plus the pots.
- Time: an afternoon.
- Status (17 Oct 2026): designed part by part at real size in Blender; parts and wiring come from the sellers' listings.
  **Not built on our bench yet.** The code is a starter: test it with the valve over a bucket first.

## Tools

A small screwdriver, scissors or a knife for the drip pipe, the drip-kit hole punch, a laptop with a USB cable,
PTFE (thread) tape.

## Parts (Indian prices, Oct 2026; estimates, check before buying)

| # | Part | Why | ≈ ₹ |
|---|---|---|---|
| 1 | ESP32 DevKit V1, 30 pin | the computer: reads the sensor, decides, has Wi-Fi | 450–550 |
| 2 | ESP32 30-pin expansion board with DC jack (6.5–16 V in, 3.3/5 V jumper) ([techiesms](https://techiesms.com/product/esp32-expansion-board-with-gpio-breakout/)) | takes 12 V straight in; a G-V-S pin trio beside every pin, so sensors plug in | 120 |
| 3 | Capacitive soil moisture sensor v1.2 ([Robu](https://robu.in/?p=130230)) | no bare metal in the soil, so it doesn't rust like the cheap two-prong ones | 50–120 |
| 4 | 5 V 1-channel relay module (with optocoupler) | a switch the ESP32 can press; the only thing that can open the valve | 35–60 |
| 5 | 12 V DC ½" normally-closed solenoid valve ([Robu](https://robu.in/?p=31396)) | shut when there's no power, so a power cut can't flood anything | 230–420 |
| 6 | 12 V 2 A DC adapter (5.5 × 2.1 mm plug) | powers everything | 180–250 |
| 7 | DC splitter cable, 1 female → 2 male (5.5 × 2.1) | one plug for the board, one for the valve | 40–60 |
| 8 | DC female jack to 2-way screw terminal | 12 V for the valve without soldering | 15–25 |
| 9 | IP65 junction box ~150 × 110 × 70 with a clear lid + 3 cable glands | rain and spray stay out; you can see the lights | 250–350 |
| 10 | Drip kit: 16 mm LDPE pipe (as long as your row), ½" female → 16 mm connector, end cap, 1 button dripper (2–4 L/h) per pot, 4 mm micro tube, arrow stakes, hole punch | the water line | 300–450 |
| 11 | Female–female jumper wires, 2 m of 2-core wire | the connections | 100 |

Two things to check before you buy the valve:
- **It needs pressure.** The common ½" plastic valve opens only above about 0.02 MPa: a tap line, a pump, or a tank at
  least 2 m above the valve. For a low bucket, buy a "zero pressure" (direct-acting) valve instead.
- **Water flows one way.** The arrow on the valve points to the plants.

## Build (the video's 5 steps)

1. **The water line.** PTFE tape on the threads. Valve onto your tap line (after a hand valve, so you can always shut the
   water yourself), arrow to the plants. Connector on the valve, 16 mm pipe pushed onto the connector, end cap on the far
   end. Punch one hole beside each pot, push in a dripper, micro tube from the dripper to an arrow stake in the pot.
2. **The sensor.** Push it into the soil up to the white line, a few cm from the plant, where the dripper's water reaches.
   Keep the electronics end (above the line) dry.
3. **The brain.** Mount the expansion board and the relay inside the box on short standoffs. Push the ESP32 into the
   expansion board (antenna end away from the DC jack). **Set the V-pin jumper to 5V.**
4. **Power and wires** (colour to colour):

   | From | To |
   |---|---|
   | 12 V adapter → splitter → plug 1 | expansion board DC jack |
   | splitter → plug 2 | DC screw terminal |
   | DC screw terminal **+** | relay **COM** |
   | relay **NO** | valve wire 1 |
   | DC screw terminal **−** | valve wire 2 |
   | relay DC+ / DC− / IN | **V / G / S of D26** |
   | soil sensor VCC / GND / AOUT (red / black / yellow) | **V / G / S of D34** |

   The valve doesn't care which of its two wires is which. Close the lid.
5. **The code.** Install the [Arduino IDE](https://www.arduino.cc/en/software), add the ESP32 boards (Boards Manager →
   "esp32" by Espressif), open [`auto_water/auto_water.ino`](auto_water/auto_water.ino), choose "DOIT ESP32 DEVKIT V1", upload.
   Open the Serial Monitor (115200): hold the sensor in the air and note the number, then dip it in a glass of water up
   to the line and note that number. Type both into `DRY` and `WET` and upload again. Halfway between them is your
   "thirsty" line.

## The trick most people miss

Water reaches the sensor slowly. If the box checks again straight after watering, the soil still reads dry, so it waters
again, and again: the pots flood. So the code waters for **1 minute, then waits 30 minutes** before it checks again, and
never waters more than 6 times a day. Change `WATER_MS`, `SOAK_MS` and `MAX_PER_DAY` for your pots and your dripper flow.

It also refuses to water if the sensor reads something impossible (a pulled-out cable reads like bone-dry soil).

## Phone messages (optional)

Install the free **ntfy** app (Android / iOS, no account), subscribe to a secret name, put your Wi-Fi and the same name in
the code. You get "Watered 1 min…" and "check the sensor" messages. Without Wi-Fi the box still waters on its own.

## Safety

- Only 12 V goes anywhere near water. The 230 V side is the adapter in a socket, indoors or in a covered spot.
- A hand valve before the solenoid valve lets you shut the water whatever the electronics do.
- Normally-closed valve: no power = no water.

## Sources

- Valve rating (12 V, NC, 0.02–0.8 MPa, not for gravity feed): [Robu listing](https://robu.in/?p=31396)
- Capacitive sensor v1.2: [Robu listing](https://robu.in/?p=130230)
- ESP32 expansion board (DC 6.5–16 V, 3.3/5 V jumper, G-V-S pins): [techiesms](https://techiesms.com/product/esp32-expansion-board-with-gpio-breakout/)
- Phone messages: [ntfy.sh](https://ntfy.sh)
