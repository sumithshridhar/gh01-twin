# Build GH-01 · Part 1: a camera that counts pests

A yellow sticky card catches flying pests (whitefly, thrips, fungus gnats). This camera photographs the card every hour, and the farm's own computer counts what is new. When one trap jumps, the farmer's phone gets an alert with the row and the photo.

- Video: Instagram @ghost.ops.ai.service
- 3D twin of the whole greenhouse: https://sumithshridhar.github.io/gh01-twin/
- Status (14 Oct 2026): designed and modelled. The parts, pins and code below are from the makers' documents. **It has not been built on our bench yet.** When it has, this page will say so, along with what we had to change.

## Parts (Indian prices, Oct 2026)

| Part | Why | ≈ ₹ |
|---|---|---|
| Raspberry Pi Zero 2 W (or Zero 2 **WH**, header already soldered) | the computer: takes the photo, sends it over Wi-Fi | 1,770 |
| Raspberry Pi Camera Module 3 (standard, not Wide) | 12 MP Sony IMX708, autofocus down to 10 cm, 66° × 41° view | 3,158 |
| Raspberry Pi Zero camera cable (22-pin 0.5 mm → 15-pin 1 mm) | the Zero has the smaller camera connector | 150 |
| Adafruit TPL5110 power timer (product 3435) | wakes the Pi every hour and cuts its power when it says "done" | ~750 (import) |
| MT3608 boost board | 3.0–4.2 V from the cell → 5.1 V for the Pi | 50 |
| 18650 Li-ion cell 3000 mAh + 1-cell holder with leads | about 11 Wh: ~3 weeks per charge | 300 |
| 5 V white LED ring, ~44 mm, < 300 mA (a USB ring light with its plug cut off also works) | the same light for every photo | 150 |
| IRLZ44N MOSFET, 1 kΩ + 100 kΩ resistors, a 170-point mini breadboard or perfboard, jumper wires | lets a 3.3 V pin switch the LED ring | 120 |
| ABS IP65 box ~115 × 90 × 55 mm + 3 mm acrylic disc (50 mm) + silica gel | weatherproof; the window keeps the lens dry | 350 |
| microSD 32 GB | Raspberry Pi OS Lite (64-bit) | 350 |
| Yellow sticky cards 25 × 10 cm | change every ~2 weeks | 25 each |
| **Total** | | **≈ 7,000** |

You also need a multimeter, a soldering iron and, on the farm side, the GH-01 edge computer (Raspberry Pi 5 + AI HAT+ 26 TOPS) that the counting runs on.

## Wiring

**Pin numbers are header positions (1–40), not GPIO numbers.** Pin 1 is at the SD-card end, inner row.

| From | To | Wire |
|---|---|---|
| 18650 holder + | TPL5110 **VDD** | red |
| 18650 holder − | TPL5110 **GND** | black |
| TPL5110 **DRV** (switched battery) | MT3608 **VIN+** | red |
| TPL5110 **GND** | MT3608 **VIN−** | black |
| MT3608 **VOUT+** (set to **5.1 V first**) | Pi **pin 2** (5 V) | red |
| MT3608 **VOUT−** | Pi **pin 6** (GND) | black |
| Pi **pin 11** (GPIO 17) | 1 kΩ → IRLZ44N **gate** | green |
| IRLZ44N gate | 100 kΩ → IRLZ44N **source** (keeps the light off while the Pi boots) | |
| IRLZ44N **source** | Pi **pin 9** (GND) | black |
| LED ring − | IRLZ44N **drain** | black |
| LED ring + | Pi **pin 4** (5 V) | red |
| Pi **pin 37** (GPIO 26) | TPL5110 **DONE** | yellow |
| Camera Module 3 | Pi camera connector, Zero cable | metal contacts face the board at both ends |

Why each part is wired like that:

1. **Set the boost board before connecting the Pi.**
   - These boards can come set to any voltage.
   - Pin 2 feeds the Pi's 5 V rail directly, without the protection on the USB power input.
   - Connect only the cell and the multimeter, and turn the brass screw until it reads 5.1 V. It is a multi-turn pot, so turn it slowly.
2. **The pin switches a MOSFET, not the LEDs.**
   - A Pi GPIO pin gives a few mA at 3.3 V; the ring needs ~150 mA at 5 V.
   - The IRLZ44N is a *logic-level* MOSFET: fully on at 3.3 V on the gate.
   - The common "IRF520 module" is not, and will leave the ring dim or off.
3. **DONE is the battery trick.**
   - The TPL5110 powers the Pi once per period (set by its trimpot: fully right ≈ every 2 h; set it to ~1 h).
   - The Pi does its job, shuts down, and then raises GPIO 26. The TPL cuts the power and draws ~20 µA until the next hour.
   - If the Pi ever hangs, the TPL power-cycles it at the next period anyway.

## Software on the Pi Zero 2 W

1. **Raspberry Pi OS Lite (64-bit).** Set Wi-Fi, a hostname (e.g. `trap-2`) and SSH in Raspberry Pi Imager.
2. **`/boot/firmware/config.txt`:** add the two lines below. The first raises GPIO 26 after shutdown; that pin feeds the TPL's DONE.
   ```
   dtoverlay=gpio-poweroff,gpiopin=26
   camera_auto_detect=1
   ```
3. **Copy the capture script:** `trap_cam.py` → `/home/pi/trap_cam.py`.
4. **Install the service:** `trap-cam.service` → `/etc/systemd/system/`. Then run `sudo systemctl enable systemd-time-wait-sync trap-cam`. The script then waits for the clock (the Zero has no clock battery; it gets the time over Wi-Fi).
5. **Focus.** The camera sits 20 cm from the card, so the lens is fixed at 5 dioptres (1 / 0.20 m) instead of hunting for focus.
   - At 20 cm, Camera Module 3 sees 26 × 15 cm: the whole card.
   - 4608 px across 26 cm is ~18 px per mm, so a whitefly (~1–1.5 mm) is about 20 pixels wide.

Each wake-up takes ~40 s: boot, photo with the ring on, upload, shutdown. With 24 wake-ups a day that's ~0.35 Wh, so one 11 Wh cell lasts about 3 weeks. Swap the cell when you change the card.

## Test it on your laptop (no Pi needed)

`tests/` runs the real `trap_cam.py` with a fake camera and LED pin (`tests/fakes`) and a real little web server standing in
for the farm's Pi 5. Each test is one wake-up of the trap:

```
pip install pytest
python -m pytest tests -v
```

| Test | What it checks |
|---|---|
| day wake (11:00) | light on → photo → light off → upload → power off |
| night wake (22:00) | no photo, no light, straight back off |
| Wi-Fi down | the photo waits in the outbox, the Pi still powers off within seconds |
| next wake | the waiting photos go first, oldest first |
| camera error | the light goes off **and the Pi still powers off** |

The last test found a real bug (18 Oct 2026): a camera error (a loose ribbon) crashed the script before `poweroff`, so the
Pi stayed on and the timer never got DONE: the battery would have drained in under a day instead of ~3 weeks. Now a failed
photo is only logged and the power-off always runs (`trap_cam.py`, `main()`). All 5 pass.

## Where the AI runs (and why)

| Where | Verdict |
|---|---|
| On the Pi Zero | Possible, but slow (a 12 MP photo is ~40 tiles for a small detector), and every extra second awake drains the battery. |
| In the cloud | Strong models, but counting stops whenever the farm's 4G drops, and every photo leaves the farm. |
| **The farm's Raspberry Pi 5 + AI HAT+ (Hailo-8, 26 TOPS)** | Already in the GH-01 control cabinet. Counts a card in about a second, works offline. **This is what we use.** |

The cloud only gets the counts, plus a weekly sample of photos to improve the model.

`count_server.py` runs on the Pi 5. For each photo it:

1. receives it over Wi-Fi;
2. cuts it into overlapping 640 × 640 tiles;
3. runs the detector on the Hailo-8 for every tile;
4. merges the boxes across tile edges;
5. compares them with the last photo from the same trap (stuck insects don't move), so only **new** catches count;
6. logs them;
7. raises an alert when the new whiteflies in an hour reach 3× that trap's usual rate.

## Training the detector

**Start with free, labelled photos of real cards:**
- *Raw data from Yellow Sticky Traps with insects for training of deep learning Convolutional Neural Network for object detection*, 4TU.ResearchData, 2019, CC0. Classes: whitefly, Macrolophus, Nesidiocoris. https://doi.org/10.4121/uuid:8b8ba63a-1010-4de7-a7fb-6f9e3baf128e
- *Pest Sticky Traps (PST)*, University of Pisa / CNR, Zenodo (whitefly, point labels). https://zenodo.org/records/7801239

**Then label your own Kolar cards (CVAT is free).** Thrips and Indian whitefly (*Bemisia tabaci*) need local photos. Keep the friends as their own classes: *Macrolophus* and *Nesidiocoris* eat whitefly, and they must not trigger a spray.

**Train a small detector on 640 px tiles** (YOLOv8s / YOLOX-s), then compile it for the Hailo-8 with the Hailo Dataflow Compiler (x86 Linux), with NMS on the chip.
- Licence note: Ultralytics YOLO is AGPL-3.0. YOLOX is Apache-2.0.

## Safety

- **Li-ion:** use a protected cell or a holder with protection, never short the leads, and charge it in a proper charger off the farm.
- **Fog on the window:** keep silica gel in the box. GH-01 sits at 95–99 % humidity at night.
