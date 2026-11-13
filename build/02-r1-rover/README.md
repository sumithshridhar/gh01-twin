# Build GH-01 · Part 2: the R1 rover

A 36 cm wide rover for soil-bed polyhouses. It drives in the path between the beds, photographs the plants from both
sides, lists anything it could not see, and sprays only the plants you approve on your phone. No rails, no welding,
no 3D printing: aluminium bars, bolts, plug-in electronics.

- Video: Instagram @ghost.ops.ai.service (GH-01 #27, "Build R1").
- Design, software and biosecurity: [rover/](../../rover/).
- Status (16 Oct 2026): designed and modelled part by part in Blender. The parts, wiring and code below come from the
  makers' documents. **It has not been built on our bench yet.** The code is a starter: run it with the wheels off the
  ground first. When we've built one, this page will say what we had to change.
- **13 Nov 2026: every problem raised so far, the fix for each, the laptop evidence and the bench tests still to do:
  [ISSUES.md](ISSUES.md).** The changes below are marked NEW.
- How a flagged plant gets a name: [DISEASE-NAMES.md](DISEASE-NAMES.md). The cheapest order to build in: [BUILD-PLAN.md](BUILD-PLAN.md).

## Tools

Metric hex keys (2.5–6 mm), a 10/13 mm spanner, a screwdriver, a wire stripper, a crimper for ring terminals and ferrules,
a multimeter, a hacksaw (if the shop won't cut the bars), and a cordless drill for 4 holes. That's all.

## Three ways to build it

Prices come from one list, [`r1/calc/bom.csv`](r1/calc/bom.csv) (Nov 2026; lines marked "estimate" are not
price-checked), summed by [`r1/calc/r1_costs.py`](r1/calc/r1_costs.py). A test checks that this table matches it.

| Build | What it is | Parts | With wheel baths + farm items, 3 houses |
|---|---|---|---|
| **Full R1** | drives itself, 6 + 1 cameras, AI chip, sprayer, drive-on dock | ₹2.00–2.18 lakh | ₹2.48–2.90 lakh |
| **R1-Scout** | drives itself and photographs; no sprayer, no AI chip (scores photos overnight), 2 + 1 cameras, 15 Ah battery | ₹1.25–1.38 lakh | ₹1.38–1.59 lakh |
| **Camera trolley** | the same cameras and brain on a hand-pushed trolley for the worker's daily round | ₹0.58–0.63 lakh | ₹0.72–0.83 lakh |

On three houses of about 1,000 m² none of them pays back on saved labour and spray alone (full R1: about 6.6 years).
They pay back only if earlier warnings save crop, which nobody has measured yet. Run `python r1/calc/r1_costs.py`
with your own farm's numbers, and start with the cheapest build (87 % of the trolley's money carries over into the
Scout).

## Parts for the full R1 (Indian prices, Nov 2026; estimates, check before buying)

| # | Part | Why | ≈ ₹ |
|---|---|---|---|
| 1 | 2040 V-slot aluminium extrusion, 3 m (cut: 2 × 680 mm, 3 × 176 mm, 1 × 750 mm, 1 × 1,150 mm) + 3030 × 1,150 mm for the upper mast | the frame and the mast | 3,000 |
| 2 | 40 × M5 T-nuts, 40 × M5 × 10 bolts, 12 corner brackets | everything bolts into the slots | 1,200 |
| 3 | 4 × 6 mm aluminium plate, 70 × 90 mm, drilled for the axle | wheel brackets (any fabrication shop) | 800 |
| 4 | 4 × 10" 24 V 350 W brushless hub motor with pneumatic tyre **and Hall sensors** | each wheel is its own motor | 4 × 6,250 |
| 5 | 4 × ZS-X11H BLDC driver (6–60 V, 400 W, Hall type) | one per wheel | 4 × 1,000 |
| 6 | 24 V 30 Ah LiFePO4 battery, **BMS ≥ 50 A continuous**, Anderson SB50 plug, quick-release strap | 5 h of scouting; 4 motors can pull > 30 A when starting. NEW: off in a minute and indoors at night (theft) | 15,500–25,900 |
| 7 | 60 A MIDI fuse + holder, red battery isolator switch, 24 V DC 100 A contactor | the power chain | 2,500 |
| 8 | 22 mm emergency stop (NC), 2 × bumper microswitches (NC) | they cut the motor power without any software | 600 |
| 9 | NEW: green 22 mm RESET push button (NO) + 24 V DPDT relay with socket | the latch: a released bumper or e-stop can't restart the wheels | 400–600 |
| 10 | NEW: 10 A fuse + holder | the sprayer's own branch, after the contactor, so the e-stop cuts the pump too | 150–200 |
| 11 | 24→5 V 5 A converter (Pi), 24→12 V 3 A converter (USB hub, LED rings), 24→5 V 3 A converter (relay board) | three clean supplies. NEW: on the aluminium deck, outside the sealed box (heat) | 1,800 |
| 12 | Raspberry Pi 5 8 GB + 27 W cooler + 64 GB microSD | the brain | 24,000 |
| 13 | Raspberry Pi AI HAT+ 26 TOPS (Hailo-8) | checks every photo on the rover, no internet | 11,300 |
| 14 | Arduino Mega 2560 (or clone) + USB cable | talks to the motor drivers, valves and switches | 1,052–1,200 |
| 15 | 7 × USB camera: Arducam 12 MP IMX708 USB-C UVC (66°) | 6 on the mast (NEW: turned to portrait), 1 at the front reading the bed tags | 7 × 9,200 |
| 16 | 7-port powered USB 3.0 hub (12 V input) | one cable from the mast to the Pi | 2,000 |
| 17 | 7 × white LED ring 12 V + 7 × IP67 aluminium camera box with glass | the same light for every photo | 4,000–4,200 |
| 18 | Slamtec RPLIDAR C1 | sees both bed walls. NEW: mounted low, under the bed tops | 6,100–9,800 |
| 19 | NEW: 2 × VL53L1X ToF distance sensor | see hoses, pipes and holes below the lidar | 1,200–1,800 |
| 20 | NEW: PMW3901 optical-flow sensor | real speed over the ground: notices mud, keeps photos 25 cm apart | 1,500–2,500 |
| 21 | 15–16 L HDPE tank + 24 V diaphragm pump (~100 psi class) + inline filter | the sprayer | 5,000 |
| 22 | 6 × 24 V 1/4" 2-way normally-closed solenoid valve | one valve per nozzle | 6 × 600 |
| 23 | 6 × TeeJet ConeJet TXA8001VK hollow-cone tip + Quick TeeJet cap and body | a fine cone that wraps the leaf | 6 × 700 |
| 24 | 6 mm PU tube 10 m + push-fit fittings (tees, elbows, 1/4" BSP adapters) | no glue, no clamps | 1,500 |
| 25 | 16-channel 5 V relay module (opto-isolated) | the Mega switches valves, pump and lights through it | 700 |
| 26 | 24 V 3-colour LED tower light | green scouting · amber spraying · red stopped | 1,500 |
| 27 | IP65 ABS box 300 × 220 × 120 mm, cable glands, DIN terminal blocks + NEW: white sun shield on 2 cm standoffs | weatherproof electronics that stay under 60 °C at noon | 2,100–2,300 |
| 28 | 4 mm aluminium deck plate 700 × 235 mm, 2 mm tray 640 × 170 mm, rubber bumper strip | deck and tray | 2,500 |
| 29 | 29.2 V 10 A LiFePO4 charger + 2 spring contacts + 2 copper pads | the drive-on dock | 6,000 |
| 30 | Wire: 6 mm² red/black (power), 2.5 mm² (motors, 3 colours), 0.5 mm² (signals); ferrules, ring terminals | | 2,500 |
| | **Total, full R1** ([bom.csv](r1/calc/bom.csv)) | | **₹2.00–2.18 lakh** |

Per door: a wheel bath (₹4–6k) and a mist arch (₹8–12k). Per farm: a 4G router + LoRa gateway on a pole (₹12–18k).
The Scout and the trolley use a ₹500 hand sprayer at each door instead of the arch.

Prices checked on 4 Nov 2026 (web search; the other lines are Oct 2026 estimates):
Pi 5 8 GB ₹21,999 ([Robocraze](https://robocraze.com/products/raspberry-pi-5-8gb); ₹22,799 on Amazon.in, [price tracker](https://pricehistory.app/p/raspberry-pi-5-8gb-ram-wifi-bluetooth-h6loew2h)) + cooler ₹499 ([Indian Hobby Center](https://indianhobbycenter.com/products/pi-5-active-cooler)) + 64 GB card ₹1,450 ([KSP](https://kspelectronics.in/product/official-raspberry-pi-5-active-cooler/)) ·
AI HAT+ 26 TOPS ₹11,309 ([Robocraze](https://robocraze.com/products/official-raspberry-pi-ai-hat-26-tops); ₹11,800 at [Makestore](https://www.makestore.in/product/official-raspberry-pi-ai-hat-26-tops/)) ·
Mega clone ₹1,052 ([Robocraze](https://robocraze.com/products/arduino-mega-2560-r3-board-compatible-with-arduino)) ·
Arducam USB IMX708 ₹9,238 ([Amazon.in](https://www.amazon.in/Arducam-IMX708-Fixed-Focus-Camera-Module/dp/B0CJF1NYNP), the only rupee listing we found) ·
RPLIDAR C1 ₹6,099 ([Tannatech](https://tannatechbiz.com/rplidar-c1-360-degree-laser-scanner.html)) to ₹9,800 ([ThinkRobotics](https://thinkrobotics.com/products/slamtec-rplidar-c1-laser-ranging-sensor)).
Still about right: hub motors ([Robokits](https://robokits.co.in/e-bike/hub-motor/10inch-bldc-hub-motor-with-24v-350w-controller-and-throttle), ₹6,250), ZS-X11H ([Probots](https://probots.co.in/zs-x11h-400w-bldc-3-phase-brushless-motor-controller-6v-60v-pwm-hall-driver-module.html), ₹999), solenoid valve ([Robu](https://aws.robu.in/?p=975728), ₹597), 24 V 30 Ah LiFePO4 (IndiaMART, ₹10,800–14,750 before GST; a ≥ 50 A BMS costs more).

Time: about a weekend (~7–8 hours) once the parts are in hand.

Changed from the first design (16 Oct): **USB cameras instead of Camera Module 3 + a 4-way adapter.** Users report that
the Arducam B012001 multi-camera adapter doesn't detect IMX708 cameras on a Pi 5 running Bookworm. The USB version of the
same sensor just plugs in. It costs ~₹34k more at Nov 2026 Amazon.in prices (7 × ₹9,200), saves a weekend. (The Scout
and the trolley need only 2 side cameras: the Pi 5's own 2 camera ports could take 2 Camera Module 3 and save about
₹12k, but `r1_capture.py` would need a picamera2 path first.)

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
   - The battery (front) and the tank (back) sit on it, held by straps. Low weight means the 2 m mast can't tip it
     (it is only 2° from tipping with a full tank in a 10 cm rut on a 5° slope, so the software stops before any
     rut deeper than 6 cm: [r1_calcs.py](r1/calc/r1_calcs.py)).
4. **Power.** Battery + → 60 A fuse → isolator switch → contactor → the motor drivers' + terminals. Battery − goes to a common ground bar.
   - NEW, the e-stop chain with a latch: 24 V → e-stop → front bumper → rear bumper → [green RESET button **in parallel
     with** contact 1 of the latch relay K2] → K2's coil. K2's contact 2 → relay 12 (drive enable) → the contactor's coil.
     Press the e-stop or touch a bumper and K2 drops, so the contactor drops. **Releasing it changes nothing** until
     someone presses RESET on the rover. (v1 restarted the wheels by itself as soon as a bumper sprang back.)
   - The electronics (Pi, hub, relays) come off a separate 5 A fuse **before** the contactor, so the Pi stays on when you press the e-stop.
   - NEW: the pump and valves are fed from **after** the contactor, through their own 10 A fuse, so the e-stop stops the sprayer in hardware too.
5. **Motor drivers.** Each ZS-X11H gets:
   - its 24 V supply;
   - the motor's 3 thick phase wires (usually yellow, green, blue);
   - the motor's 5-wire Hall plug;
   - 3 signals from the Mega: speed (PWM), direction, brake. Board versions label these differently (VR or PWM, Z/F, EL or STOP), so check your board's silkscreen and the seller's diagram.
   - **If a wheel shudders or hums instead of turning:** swap two of the three thick phase wires on that wheel (power off first).
6. **Brain.**
   - Pi 5 with the AI HAT+ and the Mega go into the IP65 box with the relay board. NEW: the 3 converters go on the
     aluminium deck outside the box (they are its biggest heat source), and a white sun shield sits 2 cm above the lid.
   - One USB cable connects the Pi to the Mega, one to the hub.
   - The Pi gets 5 V 5 A through its USB-C port. Because a plain converter can't negotiate 5 A, add `usb_max_current_enable=1` to `/boot/firmware/config.txt`, otherwise the Pi limits its USB ports to 600 mA.
7. **Mast and cameras.**
   - The 40 × 40 lower mast bolts to the deck with a base plate and 4 gussets. The 30 × 30 upper mast slides inside and locks with a collar.
   - Tomato: three 250 mm arms at 0.62 / 1.22 / 1.82 m. NEW: cameras turned 90° in their boxes (portrait), tilts
     +10° / 0° / −10° (v1's +25° on the low pair left the lowest leaves unseen). Strawberry: NEW mast at 0.91 m, one pair
     at 0.85 m tilted −52° (v1 at 0.62 m was below the top of the plants).
   - All camera cables run down the mast to the hub. The LED rings get 12 V through relay 10. NEW: they stay on for the whole path.
8. **Sprayer.**
   - Path of the water: tank → filter → pump → a 6-way manifold of solenoid valves (L1 R1 L2 R2 L3 R3) → 6 mm tubes up the mast → TeeJet tips.
   - All push-fit fittings. Wrap the BSP threads with PTFE tape.
   - Valves and pump switch through the relay board. The pump only runs while a valve is open, and no valve stays open longer than 4 s.
9. **Safety and sensing.**
   - Front and rear bumpers on microswitches. The tower light on top of the mast.
   - NEW: the lidar on a bracket at the front, **about 15 cm off the ground**, under the bed tops, where it sees the soil
     walls of both beds instead of the leaves (v1 had it at 45 cm, the top of a strawberry bed).
   - NEW: the 2 ToF sensors at the front corners, 15 cm up, aimed down at the ground 25 cm ahead. The optical-flow
     sensor under the deck, 8–10 cm above the soil.
   - NEW: a QR tag on a stake at each bed end, printed with `H<house>-B<bed>` (for example `H1-B3`).
10. **Software** (below). Start with the wheels **off the ground on blocks**.

## Wiring

### Arduino Mega pins

| Mega pin | To | Notes |
|---|---|---|
| D4, D5, D6, D7 | speed input of drivers FL, FR, RL, RR | PWM, 0–5 V |
| D22, D24, D26, D28 | direction input of FL, FR, RL, RR | HIGH = forward; the two right wheels are mirrored (handled in firmware) |
| D30 | brake input of all 4 drivers | HIGH = brake (check your board: some brake on LOW) |
| D18, D19, D20, D21 | speed-pulse output (S) of FL, FR, RL, RR | interrupts: wheel distance |
| D38–D43 | relay IN1–IN6 | valves L1 R1 L2 R2 L3 R3 |
| D44 | relay IN7 | pump |
| D45, D46, D47 | relay IN8–IN10 | tower light green, amber, red |
| D48 | relay IN11 | LED camera rings (12 V) |
| D49 | relay IN12 | "drive enable": in the contactor coil's line, after the latch |
| A0 | e-stop chain sense, tapped after the rear bumper, through a 56 k / 10 k divider | 3.6–4.4 V when closed (battery 24–29.2 V) |
| A1 | tank float switch to GND (INPUT_PULLUP) | LOW = water present |
| A2 | NEW: battery + (after the 5 A fuse) through a 56 k / 10 k divider | the firmware's low (24.0 V) and flat (22.4 V) battery rules |
| A3 | NEW: the latch relay K2's coil (+) through a 56 k / 10 k divider | high = someone pressed RESET since the last trip |
| GND | driver GNDs, relay GND, divider GNDs | one common ground |

The relay module runs on its own 5 V converter (remove its JD-VCC jumper and feed JD-VCC from that converter). The
Mega's 5 V only drives the opto inputs.

### Pi 5 pins (NEW)

| Pi | To |
|---|---|
| I2C1 (GPIO 2, 3), 3.3 V, GND | both VL53L1X (give one the address 0x30 at start-up with its XSHUT pin on GPIO 17) |
| SPI0 (GPIO 8–11), 3.3 V, GND | PMW3901 optical-flow sensor (CS on GPIO 7) |
| USB | the Mega, the hub (cameras), the lidar's USB adapter |

### Power

| From | To | Wire |
|---|---|---|
| Battery + | 60 A MIDI fuse → isolator switch | 6 mm² red |
| Isolator | contactor main contact → + bus | 6 mm² red |
| + bus | ZS-X11H × 4 (+) | 2.5 mm² red |
| + bus (after the contactor) | NEW: 10 A fuse → pump and valve supply | 1.5 mm² red |
| Isolator | 5 A fuse → the three converters, tower light, relays' 24 V side, the e-stop chain | 1 mm² red |
| Battery − | − bus → drivers, converters, pump, valves | 6 mm² / 2.5 mm² black |
| Isolator (after the 5 A fuse) | e-stop → front bumper → rear bumper → [RESET ∥ K2 contact 1] → K2 coil + | 0.5 mm² |
| K2 coil + | K2 contact 2 → relay 12 → contactor coil + | 0.5 mm² |
| Contactor coil −, K2 coil − | − bus | 0.5 mm² black |
| Dock pads (front bumper) | battery charge port | 2.5 mm², with an inline 15 A fuse |

## Software (starter code, untested on hardware)

```
r1/
  firmware/r1_io/r1_io.ino   Arduino Mega: motors, wheel pulses, relays, the latched e-stop chain, battery, 300 ms watchdog
  pi/r1_link.py              the serial link to the Mega (keeps its watchdog fed, reads pulses, battery and status flags)
  pi/r1_drive.py             phone joystick (web page on the rover, 6-digit PIN, lockout, one driver at a time)
  pi/r1_auto.py              NEW: drives one path by itself: checks the start, then lidar + step + ground sensors -> supervisor
  pi/r1_supervisor.py        NEW: the in-row driver: centring, stop/wait/ask, low steps, holes, mud, photo stations
  pi/r1_mission.py           NEW: the day plan: house order, wheel bath, dry leaves, heat, battery, resumable progress
  pi/r1_capture.py           photos at each station, one camera at a time, portrait, fixed exposure; lists what it missed
  pi/r1_triage.py            NEW: which photos to show the farmer, and when to ring (never a diagnosis, never a spray)
  pi/r1_diagnose.py          NEW: a name for a flagged plant from 5 taps at the plant + the climate; or "not sure"
  pi/r1_spray.py             a spray only happens if every lock passes; every spray or refusal is logged
  pi/r1_sim.py               NEW: the laptop simulator for one path
  pi/config.yaml             your farm: houses, crops, path widths, picking dates, products from their labels, PIN
  calc/r1_calcs.py           NEW: power, heat, steps, tipping, stopping, cameras, path width, with pass/fail checks
  calc/r1_costs.py, bom.csv  NEW: the parts list and the payback
```

1. Flash Raspberry Pi OS (64-bit, Bookworm) with Raspberry Pi Imager. Give the rover its own Wi-Fi network and password
   (or a strong farm Wi-Fi password): only the workers' phones should reach its page.
2. Upload `r1_io.ino` to the Mega with the Arduino IDE.
3. On the Pi: `sudo apt install python3-flask python3-serial python3-opencv python3-yaml python3-numpy`, then
   `pip install rplidar-roboticia vl53l1x pmw3901`, then copy the `pi/` folder.
4. Set a 6-digit PIN in `config.yaml` (it won't start with the example). Wheels off the ground: `python3 r1_drive.py`.
   Open `http://<rover-ip>:8080` on your phone, type the PIN, and push the stick gently.
   - Each wheel should turn the right way. Fix any that don't in `r1_io.ino` (MIRROR), not with wires.
   - Press the e-stop: everything must stop, and the page must say **TRIPPED**. Twist it out: nothing moves. Press
     the green RESET on the rover, then Resume on the phone.
5. On the ground, in one path: `python3 r1_drive.py --house 1 --bed 3` and drive it slowly. Check the photos in `~/r1/photos/`.
6. Driving itself, after bench tests B1–B7 in [ISSUES.md](ISSUES.md): park it at a bed end with the tag in view, then
   `python3 r1_auto.py --house 1 --bed 3 --air-c 27 --rh 70`. It refuses with the reasons if the tag, the path width,
   the wheel bath, wet leaves, the heat or the battery say no. When it stops and asks, type `r` (Resume) or `s` (Skip).
7. Spraying comes last, with **water only** until every lock has been tested: stop the other scripts, then
   `python3 r1_spray.py --house 1 --valve R2 --product "Water (test)" --approved-by "<your name>"`.
   Try to break each lock on purpose (wrong crop, picking tomorrow, door sensor "1", e-stop pressed): each must refuse.

## Test it on your laptop (no rover needed)

From this folder:

1. **Firmware:** `pip install ziglang` (a C++ compiler), then `bash r1/tests/run_test.sh`. It compiles the REAL
   `r1_io.ino` against a fake Arduino (`Arduino.h`) and plays both the Pi and the hardware around the board (the e-stop
   chain, the RESET latch, the battery, the tank float). **39 of 39 checks pass**, including: the wheels stop ~300 ms
   after the Pi goes quiet (302 ms), a bumper stops them in 1 ms, a released bumper does NOT restart them, a valve
   closes itself after 4 s, broken lines do nothing, and the battery rules.
2. **Does it compile for the real Mega?** With [arduino-cli](https://arduino.github.io/arduino-cli/):
   `arduino-cli core install arduino:avr`, then `arduino-cli compile --fqbn arduino:avr:mega --warnings all r1/firmware/r1_io`
   (v1 on 18 Oct: 0 warnings; v2 not yet compiled for the Mega, it compiles clean with `-Wall -Wextra` on the laptop).
3. **Pi code, simulator, sums:** `pip install pytest numpy pyyaml flask opencv-python`, then `python -m pytest r1/tests -q`
   (82 tests pass), `python r1/calc/r1_calcs.py` (26 of 26), `python r1/calc/r1_costs.py` (6 of 6),
   `python r1/pi/r1_sim.py` (200 random paths).

These test the code and the sums, not the wiring: the bench tests in [ISSUES.md](ISSUES.md) still come before the field.

## Safety

- The e-stop and bumpers work in hardware, and they latch: nothing moves again until someone presses RESET on the rover. Test them every morning.
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
