# Build GH-01 · Part 5: the hydro box

A small box that makes a hydroponic system run itself: it keeps the pump honest, keeps the nutrients and the pH in
their band with tiny doses, and **checks that every action worked**. If an action does nothing twice, it stops and
tells you. For NFT channels, or any system with a reservoir and one pump.

**Status (Nov 2026): the decisions are written and pass 19 laptop checks. Nothing is built, and there is no sketch for
the board yet.** It reuses the watering box's brain (ESP32, relays, 12 V) and its main rule.

## Why this box

Home NFT kits in India sell for about ₹5,100 (20 plants) to ₹46,800 (Pindfresh Tashi Pro), and a basic rooftop setup
is usually run with manual nutrient mixing and little automation ([farmonaut](https://farmonaut.com/asia/hydroponic-farming-setup-cost-solutions-companies-india),
[Casa De Amor](https://casadeamor.in/products/copy-of-casafresh-hydroponics-kit-for-home-5-plants-beginners-hydroponic-system-reusable-for-indoor-outdoor-hydroponics-seeds-included),
[price-history](https://price-history.in/product/hydroponics-kit-home-tashi-junior-indoor-pYAOXgw8)). Automatic pH and
nutrient controllers exist, but as imported units ([Bluelab](https://global.bluelab.com/bluelab-intellidose-controller-kit))
or industrial ones (one Indian listing: ₹1,50,000, [IndiaMART](https://m.indiamart.com/hyperfarms-bengaluru/hydroponics-nutrient-controller.html)).
The gap: a cheap box that runs the boring parts by itself and fails safe. Prices checked 14 Nov 2026.

## What it does

| It sees | It does | Why |
| --- | --- | --- |
| Reservoir below the float switch | Pump off at once, message | A pump that runs dry burns out |
| Pump on, but no water moving for 2 minutes | Pump off, message at once, tries again every 30 minutes | Dead pump, blocked line or an air lock: roots in NFT channels have no water, so a person must know now |
| EC (nutrient strength) low for 10 minutes | A 4-second dose of nutrient A and B, then 15 minutes of mixing | Small steps can't overshoot |
| pH high for 10 minutes | A 4-second dose of pH-down, then 15 minutes of mixing | Nutrients first: they shift the pH |
| A dose that didn't move the reading, twice in a row | Stops dosing that channel, message | Bottle empty, tube blocked, or **the probe has drifted** |
| A dose that moved the reading the wrong way | Stops at once, message | Wrong bottle in the wrong pump, or a broken probe |
| A probe reading impossible numbers, or the exact same number for an hour | No dosing at all, message | A pump never acts on a broken probe |
| EC too high, or pH too low | Message only (add plain water / it carries pH-down only) | Dosing can't fix these |
| Power just came back | No dosing for 30 minutes; the daily limit (6 doses a channel) is kept across cuts | Flickering power can't dose the tank 20 times |

A dosing lock clears by itself once the reading is back in its band. The bands (pH 5.5-6.5, EC 1.2-2.2 mS/cm) are
starting points: set them for the crop, and tune them on a real tank.

**The probe is the weak part.** A hobby pH probe drifts and needs regular calibration. A box that trusts a drifted probe
keeps dosing acid into a tank that is fine. This one stops after 2 doses that changed nothing (laptop test: a probe
stuck at 7.0 gets 2 doses of pH-down, not 30).

## Parts (≈ ₹9,400 for everything; build it in three steps)

| Part | Why | ≈ ₹ |
| --- | --- | --- |
| ESP32 DevKit + expansion board | the brain, Wi-Fi for messages (same as Part 3) | 570 |
| 4-channel 5 V relay module | pump + 3 dosing pumps | 180 (estimate) |
| 12 V brushless submersible pump, 240 L/h | moves the water ([robu](https://aws.robu.in/?p=815882)) | 534 |
| Vertical reed float switch | low-water cut-off; also wire it in series with the pump, so it works with no computer | 450 (GH-01 catalogue) |
| Hall flow sensor on the pump line | proves water is moving | 250 (estimate) |
| 12 V adapter, IP65 box, tubing, 3 bottles | | 900 (estimate) |
| **Step 1: pump guard** | | **≈ 2,900** |
| DFRobot Gravity pH kit V2 | pH ([robu](https://stgaws.robu.in/product/dfrobot-gravity-lab-grade-analog-ph-sensor-meter-kit-v2)) | 3,909 |
| DFRobot Gravity analog TDS sensor | nutrient strength (EC) ([Tntecomp](https://www.tntecomp.com/products/dfrobot-gravity-analog-tds-sensor-meter-for-arduino), ₹1,248-1,939) | 1,248 |
| DS18B20 waterproof temperature probe | EC changes with water temperature | 150 (estimate) |
| **Step 2: + watching pH and EC** | | **≈ 8,200** |
| 3 × Kamoer 12 V 37 mL/min peristaltic pump | nutrient A, nutrient B, pH-down ([robu](https://stg.robu.in/?p=857298)) | 1,197 |
| **Step 3: + dosing by itself** | | **≈ 9,400** |

## Test it on a laptop

```bash
pip install ziglang
bash build/05-hydro-box/tests/run_test.sh
```

19 checks on a model tank (the plants use nutrients and push the pH up): a normal week, fast drift, a short spike, low
water, a dead pump and its fix, an empty nutrient bottle, a drifted pH probe, the wrong bottle, an unplugged probe,
impossible numbers, a stuck probe, 20 power cuts, EC too high, dosing with the pump off, and a refilled bottle.

## Not solved yet

- The box is not built and has no board sketch.
- A dead pump can only be reported. Plants in NFT channels need water back soon; a spare pump is the real fix.
- Probe calibration is by hand. How often a hobby probe needs it here is unknown until a real tank runs.
- Wi-Fi only: with no internet, no message arrives.
- The bands and dose sizes are starting points, not tuned on a real crop.
