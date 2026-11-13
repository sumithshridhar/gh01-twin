# A practical way to build R1 (13 Nov 2026)

**Nothing here is built. Prices marked "estimate" are not price-checked.** The idea: never spend the next rupee
until the stage before has proved something on a real plant. Each stage reuses what the last one bought or wrote.

## The stages

| Stage | What you build | Cost | What it proves | Go on only if |
|---|---|---|---|---|
| **0. Phone + 5 taps** | Nothing. A phone, QR tags on the bed-end stakes, the disease key ([DISEASE-NAMES.md](DISEASE-NAMES.md)) | ₹0 | Whether flags and names are right, and whether a warning comes earlier than the grower's own eyes | "likely" is right ≥ 8 in 10 over 4 weeks, and at least one problem was caught early |
| **1. Desk rover** | The small 4-wheel kit already chosen in the Amazon cart (ESP32, L298, ultrasonic sensor, ESP32-CAM) | ₹3,473 (cart of 26 Oct) | The safety logic on real wires: watchdog, RESET latch, stop before an obstacle, phone driving. On a floor, not soil | every B1-style test passes on the desk |
| **2. Phone trolley** | A garden trolley, a pole, a used Android phone as camera + brain + 4G, a 12 V LED bar, a power bank | ≈ ₹8–12k (estimate) | The daily photo round at fixed heights with the same light, on the real farm | the worker really uses it daily for a month; the photos are usable |
| **3. R1-Scout** | The self-driving rover without sprayer or AI chip | ₹1.25–1.38 lakh ([bom.csv](r1/calc/bom.csv)) | Driving a real soil path by itself: bench tests B1–B14 in [ISSUES.md](ISSUES.md) | it finishes real paths without touching anything, and the calls to a person are few enough to live with |
| **4. Full R1** | Add the sprayer, AI chip, 4 more cameras, dock | ₹2.00–2.18 lakh in all | Spot spraying with the locks | water-only tests pass every lock |

Stages 0–2 cost under ₹16k together and answer the question the ₹1.25 lakh stage depends on. The Pi-based camera
trolley (₹0.58–0.63 lakh) is skipped: a used phone does the same job for a fifth of the money.

## Practical answers to the hard parts

| Hard part | Practical answer |
|---|---|
| **Low speed.** 10" hub motors are made for ~20 km/h. At 0.3 m/s (about 23 turns a minute) they can jerk, and the same PWM gives a different speed in soft soil | The firmware drives them open-loop today. **Not done yet:** a speed loop on the wheel pulses (about 34 pulses a second at 0.3 m/s, if the driver gives 90 pulses a turn: to be measured). Decide after bench test B11 shows how uneven it really is |
| **Turning.** 4 fixed wheels, 48 cm apart front to back but only 29 cm side to side: turning on the spot scrubs hard on soil and pulls a lot of current | Don't turn in the path. It drives in forwards and reverses out, or a worker swings it by a handle at the bed end. A rubber mat at each bed end if it must pivot |
| **60 kg over door steps** | Two aluminium ramps per door (they are in the wheel-bath design), and a T-handle so one person can guide it |
| **Buying parts** | Robu, Robocraze, Probots, Tannatech online; SP Road in Bengaluru for wire, fuses, relays, switches. Order the hub motors and their drivers FIRST and bench-test one wheel before buying the other three |
| **Metalwork** | Extrusion sellers cut to length. Only the 4 wheel plates need a fabrication shop: give them the axle size from the motor you actually received |
| **Cheaper Scout** | 2 Camera Module 3 on the Pi 5's own camera ports instead of 2 USB cameras saves about ₹12k (needs a picamera2 path in `r1_capture.py`). The lower-priced lidar listing saves ₹3.7k |
| **Wiring mistakes** | Build and test in the order of the bench tests: power chain and e-stop latch with NO motors connected (B1), then one wheel, then four, then sensors, then cameras. Sprayer last, water only |
| **Theft, heat, repair** | Battery and brain box come off in a minute and go indoors; white sun shield and morning patrols; the spare box (ISSUES.md R1–R4) |

## Order of work for stage 3 (when it is earned)

1. One hub motor + one ZS-X11H on the bench: does it turn smoothly at low speed? (If not, stop and rethink the drive.)
2. Frame, 4 wheels, power chain, e-stop + RESET latch. Test B1, B2.
3. Mega + firmware, phone driving on blocks, then on the floor. B14.
4. Lidar, step sensors, ground sensor: B3, B4, B5. Then `r1_auto.py` in a chalked corridor indoors: B7.
5. Soil: B6, B13, then one real path: B12.
6. Mast and cameras: B8, B9. Heat and power: B10, B11.

## What to do this week

Stage 0 needs no money: print QR tags, take the daily photos by phone, run `python r1/pi/r1_diagnose.py tomato` at
each odd-looking plant, and get the key reviewed by an agronomist.
