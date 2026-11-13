# R1: every problem raised so far, and what was done about each (13 Nov 2026)

**R1 is still a concept. Nothing on this page has run on a real rover.** "Fixed" means fixed in the design, the code or
the sums, and proven on a laptop. Every line says what still needs real hardware, and the bench tests at the end say
exactly how to check it.

## Where the list comes from

- **Sumith, 10 Nov:** the rover is too costly; a small unexpected obstacle breaks everything (the house-change video);
  "we still don't know how we identify the diseases"; plants grow in different ways; the camera can miss many things.
- **Sumith, 14 Oct:** melons that crawl on the ground; plants don't grow in patterns; leaves overlap.
- **Sumith, 15 Oct (from the Rajanukunte grower):** no rails, low margins, one rover for 3 houses and different
  crops, and the rover itself can carry disease.
- **Sumith, 19 Oct:** do the payback maths and fix the parts prices.
- **Reality Check #1 (4 Nov):** heat, mud, theft, no local repair.
- **[FAILURES.md](../../FAILURES.md), R1 section (11 Nov):** the five open lines.
- **A code review of this folder (13 Nov)** found 14 more problems (E1–E14) that would have stopped R1 working even on
  a perfect farm. The laptop tests below show each one, then show it fixed.

## Check it yourself (from this folder)

```
bash r1/tests/run_test.sh          firmware on a fake Arduino, with the e-stop circuit: 39 of 39 checks
python -m pytest r1/tests -q       Pi code, simulator scenarios, sums, disease key, prices in the docs: 82 passed
python r1/calc/r1_calcs.py         power, heat, steps, tipping, stopping, cameras, path width: 26 of 26
python r1/calc/r1_costs.py         cost and payback from one parts list: 6 of 6
python r1/pi/r1_sim.py             200 random paths with people, crates, stakes, hoses, pipes, mud, leaves
```

## Sumith's problems

| # | Problem | What changed | Evidence (laptop) | Still needs hardware |
|---|---|---|---|---|
| S1 | **A small obstacle breaks everything** (hose, crate, mud, stake) | New driving logic [`r1_supervisor.py`](r1/pi/r1_supervisor.py). The rule: an obstacle is a pause, never a crash. It brakes when something stands within 30 cm of the bumper and waits 30 s (people and dogs move on). On dry soil it crosses drip hoses up to 20 mm, slowly; on soft ground only up to 11 mm. It stops in front of anything higher (a header pipe) and asks for a ramp. For anything else it sends one message with the house, bed, metre, reason and a photo, then carries on from the same metre after Resume. New sensors: 2 small ToF sensors for things below the lidar, and an optical-flow sensor that sees mud. | Simulator, 200 random paths, about 5 things per 20 m path (results below). Each case × 10 seeds, all finished, 0 hits: crate, stake, leaves (stops ≥ 10 cm short, asks), person (waits, drives on, no call), 16 mm hose (crossed 9 of 10; once the sensor noise made it ask), header pipe (asks), deep mud (caught within 3 s of spin), mild mud. The old idea (centring only, firmware v1) hits the crate and never finishes. | B3–B7, B13 |
| S2 | **Changing greenhouses** breaks in reality | It doesn't change houses by itself any more. A worker drives it from the phone through the door and the wheel bath. It starts driving itself only from a checked start: the bed tag reads right, and the lidar's path width matches the config ([`r1_mission.py`](r1/pi/r1_mission.py)). | `test_it_starts_only_from_a_checked_start`, `test_wheel_bath_must_be_confirmed...` | B12 |
| S3 | **We don't know how to identify the diseases** | R1 stops claiming it. The rover only scores "different from this farm's healthy leaves". A person names it, and no spray happens without a person's name. The climate (wet-leaf hours, the heat-and-dew alarm's sum) sets how urgent it is. One morning summary with at most 10 photos. If the farmer's "Not disease" taps show it is wrong too often, it sends fewer alerts ([`r1_triage.py`](r1/pi/r1_triage.py)). **The name** now comes the way a plant clinic gets it: the crop, up to 5 one-tap questions answered at the plant, and the house's climate ([`r1_diagnose.py`](r1/pi/r1_diagnose.py), [DISEASE-NAMES.md](DISEASE-NAMES.md)). It says "likely X" or "not sure, ask a lab", never a chemical. | 20 problems (strawberry, tomato). 378 simulated cases: 0 wrong names, 99 of 105 named, the rest "not sure". A photo alone never gets a name. 29 tests | **The key is unreviewed and untried.** An agronomist must check it; B15 measures it: "likely" right ≥ 8 in 10 over 4 weeks |
| S4 | **Plants grow differently, into the path, no pattern** | The lidar moves down to about 15 cm, under the bed tops, so it follows the soil walls, which don't change, not the leaves. The wall estimate ignores anything closer than the wall. Plants growing into the path make it stop and say where to tie them back: it never pushes through them. | Simulator: **0 m of leaves brushed** in 3,800 m; walls touched on 0.9 m. Tracking error 0.8 cm (1σ). | B3, B12 |
| S5 | **Cameras miss things, leaves overlap** | Cameras turned to portrait (the long side up the plant), low camera tilt 25° → 10°, strawberry camera raised from 0.62 m to 0.85 m and tilted −52°. In amber/red houses the stations are 12.5 cm apart, so every leaf is seen from 2 positions. Fixed exposure, with the light on for the whole path. A camera that fails writes that metre to the "unseen" list (photos.db) for a person to check by hand, instead of leaving a silent gap. | Sums: v1 saw **63 %** of the tomato canopy band, v2 sees **99 %**; v1 strawberry missed the bed centre and the hanging fruit, v2 sees both. Fake-camera tests: one camera at a time, portrait, dead camera listed. | B8, B9. Leaves fully hidden behind others stay unseen: the up-tilted camera, the second angle and the hand-check list reduce it but don't end it |
| S6 | **Too costly / payback** | One parts list ([`bom.csv`](r1/calc/bom.csv)) for three builds, and a payback calculator ([`r1_costs.py`](r1/calc/r1_costs.py)) that counts only money you can see. Full R1 ₹2.00–2.18 lakh. R1-Scout (no sprayer, no AI chip, 2+1 cameras) ₹1.25–1.38 lakh. Camera trolley ₹0.58–0.63 lakh; 87 % of it carries over into the Scout later. | It reproduces the 4 Nov reel (₹2,00,000 ÷ ₹150/day = 1,333 days). On 3 houses of 1,000 m² no build pays back on labour + spray: full 6.6 years, Scout 4.0. To pay back in one season the trolley must save ₹77k of crop per season, the Scout ₹1.30 lakh. | **Honest result: engineering can't fix this.** Only earlier disease warnings that save crop can pay for it, and nobody has measured that. B15 measures it before anything bigger is bought |
| S7 | **Melons that crawl on the ground** | Polyhouse growers train melons up strings (one vine, one fruit), and R1 handles those like tomato. Ground-trailing crops are refused with a reason, because their vines cross the paths. | `test_order_healthiest_first_and_refusals...` | none |
| S8 | **The rover carries disease** | Healthiest house first, riskiest last. It never goes back into a cleaner house the same day after a sicker one. The wheel bath must be confirmed at every door within 10 minutes. It doesn't drive through wet leaves (dew-point gap ≥ 2 °C), and it never brushes plants (S4). | `test_never_back_into_a_cleaner_house...`, `test_patrol_gate_...`, simulator 0 m brushed | none for the logic. Whether the bath really cleans the tyres is a lab question |
| S9 | **One rover, different crops** | Crop profiles: mast height, which cameras and how long each stop takes, for tomato, capsicum, cucumber, trellised melon and strawberry. | `test_strawberry_uses_its_two_cameras...` | B8 |

## Reality Check #1 (4 Nov)

| # | Problem | What changed | Evidence | Hardware |
|---|---|---|---|---|
| R1 | **Heat** | The DC-DC converters move out of the sealed box onto the aluminium deck. A white sun shield goes on with a 2 cm air gap. Patrols run in the morning or late afternoon: it won't start with the box over 50 °C, and it stops and calls a person at 60 °C. | v1 box at noon ≈ **83 °C**. v2 ≈ 53 °C at noon, 44 °C at 8–9 AM, Pi chip ≈ 69 °C | B10 |
| R2 | **Mud** | It watches wheel speed against ground speed. When the wheels turn but the rover doesn't move for 1.5 s, it stops before it digs in, backs out 15 cm once, and tries again slowly. If it sticks again it asks for a board or a push. Any steady slip marks the ground as soft, which lowers the step limit (the 200-path batch found that wet tyres couldn't climb a 16 mm hose in mild mud, which never counted as "stuck"; test added). Photo metres come from the ground sensor. | deep mud × 10 seeds: caught every time, at most 3 s of spin. Mild mud: photos stay 25 cm apart, where wheel-turn photos bunch up. Hose in mud: asks, 10 of 10 | B5, B13 |
| R3 | **Theft** (pumps and batteries go missing on farms) | Design: the battery (quick-release strap, one Anderson plug) and the brain box (4 wing nuts, one connector) come off in about a minute and go indoors at night. The rover is cable-locked to the dock. | none: a habit, not code | none |
| R4 | **Nobody to repair it** | Every part is a standard Indian-market part (bom.csv). Each stop message says what to do ("press the green RESET", "lay a ramp", "tie back the plants"). The spare box holds a camera, a ToF sensor, a valve, a fuse kit and a ZS-X11H. | the supervisor's messages are tested | none |

## Problems found in the code and design (13 Nov)

| # | Problem | Fix | Evidence |
|---|---|---|---|
| E1 | **After a bumper or e-stop was released, the wheels started again by themselves** (a person who stepped away could be hit again) | A hardware latch: a green RESET button and a ₹150 relay. The firmware also latches: it needs RESET, then E 1, then a neutral stick before anything moves. | Probe of the old firmware: "RESTARTS BY ITSELF". New: stays stopped 5 s with the Pi still sending; Resume refused until RESET (firmware checks 6–7) |
| E2 | **A valve stayed open as long as the Pi kept pinging** (60 s and counting: half a litre on one plant) | The firmware closes any valve after 4 s, whatever the Pi says | old: "STILL OPEN" after 60 s. New: closed at 4.001 s |
| E3 | **A broken line "V 1" opened valve 1** | Strict parsing. Broken lines do nothing and don't feed the watchdog | 7 broken lines: no valve opens; the watchdog still stops the wheels at 302 ms |
| E4 | **No battery watch**: the BMS cut-off mid-row would kill the Pi too | A2 reads the battery. Low (24.0 V for 10 s): no spraying, half speed. Flat (22.4 V for 3 s): the wheels stop while the Pi can still report where it is. A 0.5 s dip when the motors start is ignored | 6 battery checks |
| E5 | **No code read the lidar**: R1 could only be driven by hand | `r1_supervisor.py` + `r1_auto.py` (one path by itself), tested with the simulator standing in for the hardware | `test_auto_loop_with_the_simulator` |
| E6 | **Lidar at bed-top height** (45 cm) saw the leaves, not the bed walls | Mounted at about 15 cm, under the bed tops | S4 |
| E7 | **Cameras:** 6 USB cameras streaming at once on one USB 2 bus; an 80 ms flash that auto-exposure can't follow; landscape gaps | One camera at a time, fixed exposure, light on for the whole path, portrait | S5; fake-camera tests |
| E8 | **Wheel-turn metres** went wrong in mud: duplicate photos, wrong stamps | Optical-flow ground speed | R2 |
| E9 | **The 36 cm rover in 40–50 cm strawberry paths** | It needs paths of about 46 cm (0.8 cm tracking, a crooked soil wall, a 1 cm leaf margin); the planner uses 48 cm. Houses with narrower paths get the trolley. Measure the paths first | sums 7; width sweep below |
| E10 | **Phone driving:** a 4-digit example PIN, unlimited guesses (10,000 tries take minutes), two phones at once | It refuses to start with a weak or example PIN (6 digits minimum). 5 wrong tries lock it for 5 minutes. One driver at a time. Also give the rover its own Wi-Fi password | 4 drive tests (8 cases) |
| E11 | **Price drift:** ₹1.5 L (docs), ₹1,82,700 (reel #43), ₹2.0–2.1 L (README). The "₹15–25k trolley" is ~₹58k at Nov 2026 prices (a Pi 5 is ₹24k) | `bom.csv` is the only source. A test fails if this page, the README, FAILURES.md or rover/README.md quotes another total | `test_docs_quote_the_same_prices_as_the_parts_list` |
| E12 | **The e-stop didn't cut the sprayer in hardware** (the pump was fed from before the contactor) | Pump and valves now fed from after the contactor, on their own 10 A fuse | wiring table; sums 1 |
| E13 | **The spray script logged "SPRAYED" even if the board had refused to arm** | It reads the board's armed flag before it opens a valve | `r1_spray.py` |
| E14 | **Tipping:** tall mast + full tank + one wheel in a 10 cm rut + 5° slope = only 2° from tipping | The ToF sensors stop it before any rut deeper than 6 cm: margin 10.4° | sums 4 |

Also counted now: the wheel bath (₹4–6k), mist arch (₹8–12k) at each door and the 4G pole (₹12–18k) were not in
the ₹2 lakh. `r1_costs.py` adds them ("with doors/farm"). The Scout and the trolley replace the mist arch with a
₹500 hand sprayer.

## Simulator results (200 random paths)

A model, not the farm: it is only as good as its noise and terrain numbers (top of [`r1_sim.py`](r1/pi/r1_sim.py)).
The mix is harsh on purpose: about 5 things in every 20 m path (people who stay up to 60 s, crates, stakes, hoses,
header pipes, mud, deep mud, leaves growing in).

| | R1 now (driving logic + firmware v2) | Before: centring only + firmware v1 |
|---|---|---|
| Paths | 200 (3,800 m) | 60 (1,140 m) |
| Finished | **200 of 200** | 35 of 60 |
| Hit something standing | **0** | 49 |
| Drove into a step too high | **0** | 9 |
| Wheels spinning in place | 181 s in all (58 mud stops, ~3 s each) | 820 s |
| Photos closer than 15 cm (bunched) | **0 of 15,400** (none further than 35 cm apart) | 975 of 3,581 |
| Stops for nothing real | 0 | 0 |
| Touching a bed wall / brushing leaves | 0.9 m / 0 m of 3,800 m | 0.1 m / 0.9 m |
| Calls to a person | 8.0 per 100 m: blocked 180, step 65, stuck 58 | none: it just stayed stuck |
| Time per 100 m | 17 min, including waiting for people | — |

8 calls per 100 m is the price of never hitting anything in this harsh mix. On a farm that keeps its paths clear
it will be far fewer; B12 and B15 measure the real number.

Path width (30 random paths each, no obstacles, leaves growing in): the wall is touched on 19 % of the distance in a
40 cm path, 0.8 % at 42 cm, 0.24 % at 46 cm, 0.09 % at 48 cm and 0 at 55 cm. Hence the 48 cm rule.

## Bench tests (what only real hardware can settle)

Do them in this order, wheels off the ground until B6. Each one updates a number in the code or the sums.

| # | Test | Pass |
|---|---|---|
| B1 | `arduino-cli compile --fqbn arduino:avr:mega --warnings all r1/firmware/r1_io`, upload. Press a bumper while it drives: the wheels stop. Release it: nothing moves for 10 s. Tap Resume: refused. Press RESET, tap Resume, centre the stick: it drives | all of it |
| B2 | Pump running on water, press the e-stop | the pump stops at once (hardware, after the contactor) |
| B3 | Lidar at 15 cm, a plank 25 cm to the LEFT: print `r1_auto` points | the plank shows at y ≈ +0.25 (flip the angle sign if not) |
| B4 | A 16 mm hose and a 50 mm pipe on the floor under each ToF sensor | step readings within ±4 mm (fix `tof_height_m` / `tof_ahead_m`) |
| B5 | Push it 5 m over soil, then over wet soil | flow distance within ±3 %; set `flow_m_per_count` |
| B6 | Wooden strips of 10, 16, 20, 25, 30 and 40 mm, on dry and on wet soil | the highest it climbs → `step_max` = 80 % of it |
| B7 | Drive at 0.3 m/s at a cardboard box, 10 tries | it always stops at least 15 cm short |
| B8 | 6 cameras, one at a time, through the hub | each photo ≤ 0.6 s, none fails in 500 stations; then try 2 at once on the Pi's 2 USB ports |
| B9 | 20 coloured dots hidden under and behind leaves on 5 tomato plants | ≥ 16 of 20 in the photos with 12.5 cm stations |
| B10 | Closed box, Pi under load, white shield on, in a polyhouse from 10 AM to 2 PM | box ≤ 55 °C, Pi chip ≤ 80 °C |
| B11 | Clamp meter on the battery lead over a 30 m soil path | within 25 % of 113 W driving (full) / 75 W (Scout) |
| B12 | At the farm: 10 path widths per house, measured at the bottom; one real path with a chalk line | widths ≥ 48 cm for R1; tracking ≤ 1 cm (1σ) |
| B13 | A wet patch | it stops within 2 s of wheel spin, backs out, asks |
| B14 | Phone page: 5 wrong PINs; two phones | locked 5 min; the second phone refused |
| B15 | **The one that decides if R1 is worth it:** 4 weeks of photos on the grower's daily round (a phone on a stick, or the trolley), his taps on every alert, and his record of every problem he found himself | alert precision ≥ 8 in 10, and at least one problem seen earlier than his own eyes. That is the number the payback needs |

## How to actually build it

Stage by stage, cheapest first, with the hard parts (low-speed motors, turning on soil, door steps) and what is still
not done: [BUILD-PLAN.md](BUILD-PLAN.md).

## Out of date elsewhere (not changed here)

- The Blender model and the reels still show the v1 lidar height, the landscape cameras, the 25° low tilt and the
  0.68 m strawberry mast. Reels #43 and the Build R1 series quote older totals.
- The older copy in `OneDrive/Desktop/webs/greenhouse-twin/tutorials/02-r1-rover` is not updated; this repo is the
  source.
