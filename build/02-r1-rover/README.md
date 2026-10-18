# Build GH-01 · Part 2: the R1 rover

A 36 cm wide rover for soil-bed polyhouses. It drives in the path between the beds, photographs every plant from both
sides, and sprays only the plants you approve on your phone. No rails, no welding, no 3D printing: aluminium bars,
bolts, plug-in electronics.

- Video: Instagram @ghost.ops.ai.service (GH-01 #27, "Build R1").
- Design, software and biosecurity: [rover/](../../rover/).
- Status (16 Oct 2026): designed and modelled part by part in Blender. The parts, wiring and code below come from the
  makers' documents. **It has not been built on our bench yet.** The code is a starter: run it with the wheels off the
  ground first. When we've built one, this page will say what we had to change.

## Tools

Metric hex keys (2.5–6 mm), a 10/13 mm spanner, a screwdriver, a wire stripper, a crimper for ring terminals and ferrules,
a multimeter, a hacksaw (if the shop won't cut the bars), and a cordless drill for 4 holes. That's all.

## Parts (Indian prices, Oct 2026; estimates, check before buying)

| # | Part | Why | ≈ ₹ |
|---|---|---|---|
| 1 | 2040 V-slot aluminium extrusion, 3 m (cut: 2 × 680 mm, 3 × 176 mm, 1 × 750 mm, 1 × 1,150 mm) + 3030 × 1,150 mm for the upper mast | the frame and the mast | 3,000 |
| 2 | 40 × M5 T-nuts, 40 × M5 × 10 bolts, 12 corner brackets | everything bolts into the slots | 1,200 |
| 3 | 4 × 6 mm aluminium plate, 70 × 90 mm, drilled for the axle | wheel brackets (any fabrication shop) | 800 |
| 4 | 4 × 10" 24 V 350 W brushless hub motor with pneumatic tyre **and Hall sensors** | each wheel is its own motor | 4 × 6,300 |
| 5 | 4 × ZS-X11H BLDC driver (6–60 V, 400 W, Hall type) | one per wheel | 4 × 1,200 |
| 6 | 24 V 30 Ah LiFePO4 battery, **BMS ≥ 50 A continuous** | 5 h of scouting; 4 motors can pull > 30 A when starting | 15,000–25,000 |
| 7 | 60 A MIDI fuse + holder, red battery isolator switch, 24 V DC 100 A contactor | the power chain | 2,500 |
| 8 | 22 mm emergency stop (NC), 2 × bumper microswitches (NC) | they cut the motor power without any software | 600 |
| 9 | 24→5 V 5 A converter (Pi), 24→12 V 3 A converter (USB hub), 24→5 V 3 A converter (relay board) | three clean supplies | 1,800 |
| 10 | Raspberry Pi 5 8 GB + 27 W cooler + 64 GB microSD | the brain | 8,500 |
| 11 | Raspberry Pi AI HAT+ 26 TOPS (Hailo-8) | checks every photo on the rover, no internet | 14,999 |
| 12 | Arduino Mega 2560 (or clone) + USB cable | talks to the motor drivers, valves and switches | 900 |
| 13 | 7 × USB camera: Arducam 12 MP IMX708 USB-C UVC (66°) | 6 on the mast, 1 at the front; plug and play | 7 × 5,500 |
| 14 | 7-port powered USB 3.0 hub (12 V input) | one cable from the mast to the Pi | 2,000 |
| 15 | 7 × white LED ring 12 V + 7 × IP67 aluminium camera box with glass | the same light for every photo | 4,000 |
| 16 | Slamtec RPLIDAR C1 | sees both bed walls, keeps the rover in the middle | 7,000–13,000 |
| 17 | 15–16 L HDPE tank + 24 V diaphragm pump (~100 psi class) + inline filter | the sprayer | 5,000 |
| 18 | 6 × 24 V 1/4" 2-way normally-closed solenoid valve | one valve per nozzle | 6 × 600 |
| 19 | 6 × TeeJet ConeJet TXA8001VK hollow-cone tip + Quick TeeJet cap and body | a fine cone that wraps the leaf | 6 × 700 |
| 20 | 6 mm PU tube 10 m + push-fit fittings (tees, elbows, 1/4" BSP adapters) | no glue, no clamps | 1,500 |
| 21 | 16-channel 5 V relay module (opto-isolated) | the Mega switches valves, pump and lights through it | 700 |
| 22 | 24 V 3-colour LED tower light | green scouting · amber spraying · red stopped | 1,500 |
| 23 | IP65 ABS box 300 × 220 × 120 mm, cable glands, DIN terminal blocks | weatherproof electronics | 1,800 |
| 24 | 4 mm aluminium deck plate 700 × 235 mm, 2 mm tray 640 × 170 mm, rubber bumper strip | deck and tray | 2,500 |
| 25 | 29.2 V 10 A LiFePO4 charger + 2 spring contacts + 2 copper pads | the drive-on dock | 6,000 |
| 26 | Wire: 6 mm² red/black (power), 2.5 mm² (motors, 3 colours), 0.5 mm² (signals); ferrules, ring terminals | | 2,500 |
| | **Total** (depends mostly on the battery and lidar seller; ₹6k of it is the dock) | | **≈ ₹1.5–1.7 lakh** |

Time: about a weekend (~7–8 hours) once the parts are in hand.

Changed from the first design (16 Oct): **USB cameras instead of Camera Module 3 + a 4-way adapter.** Users report that
the Arducam B012001 multi-camera adapter doesn't detect IMX708 cameras on a Pi 5 running Bookworm. The USB version of the
same sensor just plugs in. It costs ~₹8k more, saves a weekend.

## Build steps (what the video shows)

1. **Frame.**
   - The two 680 mm bars are the sides, 196 mm apart (centre to centre). The three 176 mm bars are cross members: front, middle, back.
   - Slide a T-nut into the slot, put a corner bracket on it, and tighten an M5 bolt. Square each corner before the final tightening.
2. **Wheels.**
   - Bolt a 6 mm plate to the outside of each side bar with 4 M5 bolts into T-nuts.
   - The hub motor's axle goes through the plate's slot. Tighten the axle nuts with a spanner. Most hub motors have flats on the axle: line them up with the slot so the axle can't turn.
   - Route the motor cable inwards along the bar.
3. **Heavy parts low.**
   - The 2 mm tray hangs 10 cm off the ground between the side bars.
   - The battery (front) and the tank (back) sit on it, held by straps. Low weight means the 2 m mast can't tip it.
4. **Power.** Battery + → 60 A fuse → isolator switch → contactor → the motor drivers' + terminals. Battery − goes to a common ground bar.
   - The contactor's coil runs through the e-stop and both bumper switches **in series**. Any one of them opens the coil and the motors lose power, whatever the software is doing.
   - The electronics (Pi, hub, relays) come off a separate 5 A fuse **before** the contactor, so the Pi stays on when you press the e-stop.
5. **Motor drivers.** Each ZS-X11H gets:
   - its 24 V supply;
   - the motor's 3 thick phase wires (usually yellow, green, blue);
   - the motor's 5-wire Hall plug;
   - 3 signals from the Mega: speed (PWM), direction, brake. Board versions label these differently (VR or PWM, Z/F, EL or STOP), so check your board's silkscreen and the seller's diagram.
   - **If a wheel shudders or hums instead of turning:** swap two of the three thick phase wires on that wheel (power off first).
6. **Brain.**
   - Pi 5 with the AI HAT+ and the Mega go into the IP65 box with the 3 converters and the relay board.
   - One USB cable connects the Pi to the Mega, one to the hub.
   - The Pi gets 5 V 5 A through its USB-C port. Because a plain converter can't negotiate 5 A, add `usb_max_current_enable=1` to `/boot/firmware/config.txt`, otherwise the Pi limits its USB ports to 600 mA.
7. **Mast and cameras.**
   - The 40 × 40 lower mast bolts to the deck with a base plate and 4 gussets. The 30 × 30 upper mast slides inside and locks with a collar.
   - Three 250 mm arms at 0.62 / 1.22 / 1.82 m. The lowest pair of cameras tilts 25° up, to see under the leaves.
   - All 6 camera cables run down the mast to the hub. The LED rings get 12 V and switch with relay 10 (so they flash only for the photo).
8. **Sprayer.**
   - Path of the water: tank → filter → pump → a 6-way manifold of solenoid valves (L1 R1 L2 R2 L3 R3) → 6 mm tubes up the mast → TeeJet tips.
   - All push-fit fittings. Wrap the BSP threads with PTFE tape.
   - Valves and pump switch through the relay board. The pump only runs while a valve is open.
9. **Safety and sensing.**
   - Front and rear bumpers on microswitches.
   - The tower light on top of the mast.
   - The lidar on a short post above the box, where it can see both bed walls.
10. **Software** (below). Start with the wheels **off the ground on blocks**.

## Wiring

### Arduino Mega pins

| Mega pin | To | Notes |
|---|---|---|
| D4, D5, D6, D7 | speed input of drivers FL, FR, RL, RR | PWM, 0–5 V |
| D22, D24, D26, D28 | direction input of FL, FR, RL, RR | HIGH = forward; the two right wheels are mirrored (handled in firmware) |
| D30 | brake input of all 4 drivers | HIGH = brake (check your board: some brake on LOW) |
| D18, D19, D20, D21 | speed-pulse output (S) of FL, FR, RL, RR | interrupts: wheel distance for the 25 cm photo spacing |
| D38–D43 | relay IN1–IN6 | valves L1 R1 L2 R2 L3 R3 |
| D44 | relay IN7 | pump |
| D45, D46, D47 | relay IN8–IN10 | tower light green, amber, red |
| D48 | relay IN11 | LED camera rings (12 V) |
| D49 | relay IN12 | "drive enable": closes the last link of the contactor loop |
| A0 | e-stop loop sense: the loop voltage through a 56 k / 10 k divider | 3.6–4.4 V when the loop is closed (battery 24–29.2 V) |
| A1 | tank float switch to GND (INPUT_PULLUP) | LOW = water present |
| GND | driver GNDs, relay GND, divider GND | one common ground |

The relay module runs on its own 5 V converter (remove its JD-VCC jumper and feed JD-VCC from that converter). The
Mega's 5 V only drives the opto inputs.

### Power

| From | To | Wire |
|---|---|---|
| Battery + | 60 A MIDI fuse → isolator switch | 6 mm² red |
| Isolator | contactor main contact → + bus | 6 mm² red |
| + bus | ZS-X11H × 4 (+) | 2.5 mm² red |
| Isolator | 5 A fuse → the three converters, tower light, relays' 24 V side | 1 mm² red |
| Battery − | − bus → drivers, converters, pump, valves | 6 mm² / 2.5 mm² black |
| Isolator (after the 5 A fuse) | e-stop → front bumper → rear bumper → relay 12 → contactor coil + | 0.5 mm² |
| Contactor coil − | − bus | 0.5 mm² black |
| Dock pads (front bumper) | battery charge port | 2.5 mm², with an inline 15 A fuse |

## Software (starter code, untested on hardware)

```
r1/
  firmware/r1_io/r1_io.ino   Arduino Mega: motors, wheel pulses, relays, e-stop loop, 300 ms watchdog
  pi/r1_link.py              the serial link to the Mega (keeps its watchdog fed, reads wheel pulses + e-stop)
  pi/r1_drive.py             phone joystick (web page on the rover, PIN-protected); --house/--bed also takes photos
  pi/r1_capture.py           6 photos every 25 cm, stamped with house · bed · metre · side · height (SQLite)
  pi/r1_spray.py             a spray only happens if every lock passes; every spray or refusal is logged
  pi/config.yaml             your farm: houses, crops, picking dates, products from their labels, PIN
```

1. Flash Raspberry Pi OS (64-bit, Bookworm) with Raspberry Pi Imager. Set the Wi-Fi to the farm router.
2. Upload `r1_io.ino` to the Mega with the Arduino IDE.
3. On the Pi: `sudo apt install python3-flask python3-serial python3-opencv python3-yaml`, then copy the `pi/` folder.
4. Wheels off the ground: `python3 r1_drive.py`. Open `http://<rover-ip>:8080` on your phone, type the PIN, and push the stick gently.
   - Each wheel should turn the right way. Fix any that don't in `config.yaml`, not with wires.
   - Press the e-stop: everything must stop, and the page must show **E-STOP**.
5. On the ground, in one path: `python3 r1_drive.py --house 1 --bed 3` and drive it slowly. Check the photos in `~/r1/photos/`.
6. Spraying comes last, with **water only** until every lock has been tested: stop `r1_drive.py`, then
   `python3 r1_spray.py --house 1 --valve R2 --product "Water (test)" --approved-by "<your name>"`.
   Try to break each lock on purpose (wrong crop, picking tomorrow, door sensor "1", e-stop pressed): each must refuse.

## Test the firmware on your laptop (no Arduino needed)

1. **Does it compile?** With [arduino-cli](https://arduino.github.io/arduino-cli/):
   `arduino-cli core install arduino:avr`, then
   `arduino-cli compile --fqbn arduino:avr:mega --warnings all r1/firmware/r1_io`
   (18 Oct 2026: 0 warnings in r1_io.ino, 8,722 bytes = 3 % of the Mega's flash, 304 bytes = 3 % of its RAM).
2. **Does it behave?** `r1/tests` compiles the REAL `r1_io.ino` against a fake Arduino (`Arduino.h`: a fake clock, pins and
   serial port) and plays the Pi: `pip install ziglang` (a C++ compiler), then `bash r1/tests/run_test.sh`.
   It checks: no driving until enabled, a smooth start, **the wheels stop ~300 ms after the Pi goes quiet** (302 ms),
   the e-stop stops them at once (1 ms) even while the Pi keeps sending, a valve only opens when spraying is armed, and
   the watchdog closes it again. 14 / 14 pass.

These test the code, not the wiring: the bench test (wheels off the ground, e-stop, water only) still comes before the field.

## Safety

- The e-stop and bumpers work in hardware. Test them every morning.
- Never spray with someone in the house. The tower light is amber while spraying.
- LiFePO4 is the safe chemistry. Still: fuse at the battery, never charge a damaged pack, and use the matching charger (29.2 V).
- Pesticides: only products approved for that crop, at the label dose. Respect the waiting period before picking.

## Sources

- ZS-X11H (6–60 V, 400 W, Hall motors, PWM / 0–5 V speed): https://probots.co.in/zs-x11h-400w-bldc-3-phase-brushless-motor-controller-6v-60v-pwm-hall-driver-module.html
- Arducam B012001 + IMX708 on Pi 5 reports: https://forum.arducam.com/t/multi-camera-adapter-v2-2-not-detecting-imx708-cameras-on-pi-5-bookworm/9978
- Arducam 12 MP IMX708 USB-C UVC camera: https://thepihut.com/collections/raspberry-pi-camera/products/arducam-12mp-imx708-usb-c-uvc-fixed-focus-camera-module
- RPLIDAR C1: https://www.waveshare.com/product/rplidar-c1.htm
- Raspberry Pi AI HAT+ 26 TOPS (India): https://probots.co.in/official-raspberry-pi-ai-hat-26-tops.html
- 2040 extrusion, ₹540/m: https://m.indiamart.com/simplexprofilosystems
- 24 V 30 Ah LiFePO4 (₹15,000 listing): https://m.indiamart.com/himaksh-enterpriseskota
- 24 V 1/4" NC solenoid valve: https://aws.robu.in/?p=975728
