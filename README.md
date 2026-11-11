# GH-01

**Two small boxes that water and warn a farm.** Designed and tested in software first, for polyhouse and open-bed
growers in Karnataka. Plus a 3D design of the greenhouse they could grow into.

**Open it:** https://sumithshridhar.github.io/gh01-twin/

| | What it is | Where it stands |
| --- | --- | --- |
| 💧 **[Watering box](build/03-auto-watering/)** | Waters one bed by itself for about ₹1,750 a zone (ESP32, soil sensor, 12 V valve, no soldering). If anything is wrong, the valve stays shut and you get a message. | Being built first. Its rules pass 16 laptop checks. |
| 🌡 **[Heat-and-dew alarm](build/04-heat-dew-alarm/)** | Warns before heat stress or a wet-leaf night, for about ₹2,100. | Rules pass 16 laptop checks. No board sketch yet. |
| 🏠 **The full greenhouse** | The showroom: a 45 m² tomato house and its farm in 3D, every machine at real size. | A design. Not built. |

## Try to break the watering box

Open the site and pick **Watering box**. A bed is cut open so you can see the water in the soil. Then break things:
pull the sensor cable, knock a wire, flicker the power, empty the tank, hang the program, stick the valve open.
The page runs the box's real rules ([water_logic.h](build/03-auto-watering/auto_water/water_logic.h), ported line for
line in [js/water_logic.js](js/water_logic.js); the same 16 checks pass against both: `node tools/test_water_logic_js.mjs`). Dark soil is real water. Red stripes are what a box without that rule would do.

One thing code can't fix: a valve that sticks open. So the hand tap stays on the line.

## Where it really stands

- [x] Designed in 3D, every part modelled on a real product at real size
- [x] The two boxes' rules pass 32 laptop checks
- [ ] Runs on a real board
- [ ] One bed, one season
- [ ] Three farms

Nothing is built yet. What is known to break each part, and what is still unsolved, is in **[FAILURES.md](FAILURES.md)**.
Each real test adds a line there.

## Build guides

- [Part 3: the watering box](build/03-auto-watering/): parts, every wire, the code and its tests
- [Part 4: the heat-and-dew alarm](build/04-heat-dew-alarm/): how it decides, and its tests
- [Part 1: a pest-counting camera](build/01-pest-camera/): Pi Zero 2 W + Camera Module 3, a tutorial
- [Part 2: the R1 rover](build/02-r1-rover/): a **concept**. A hose, mud or a crate on the path would stop it, and that is not solved

## The showroom

Pick **The full greenhouse** on the site. It opens clean; **🎛 Control room** shows the live numbers, every system and
the failure tests (pump failure, sensor failure, heat wave, water shortage, power cut, and ten more).
Click any machine to open it into its parts with a blueprint. **✂ Slice** cuts the greenhouse open like a cake.
Walk mode: W A S D. The farm is shown as a slice of land lifted out of the ground; `?world=full` puts the village,
fields and hills back round it.

The rule the whole design follows: the edge AI **suggests**, a safety PLC **decides** within hard limits, and hard-wired
cut-offs (float switch, thermostat) **protect** the crop even if every computer fails.

<details><summary>What is in the showroom, and older ideas</summary>

- **The farm round the house:** a solar packhouse (6 × 540 W panels, hybrid inverter, 5 kWh LiFePO4 battery,
  zero-energy cool chamber), a lined farm pond with a level sensor, rainwater gutters with a first-flush chamber,
  a double-door entry room with a footbath, a retractable shade net, and the borewell as backup.
- **Other scenes** (🗺 Scenes in the bottom bar, or `?scene=water`, `?scene=bench`, `?scene=rover`, `?scene=buildr1`):
  the watering box on a strawberry bed, the pest-camera bench, the R1 rover concept in a soil polyhouse, and R1 as a
  kit of 43 parts.
- **R1 rover (concept):** 36 cm wide, 6 cameras, 6 spray valves. Design notes: [rover/](rover/).
- **Dropped: the rail robot.** Local polyhouses have no rails, rails cost about ₹17.7 lakh an acre, and any obstacle
  breaks the handover. The old idea can still be seen with `?rails`.
- `?control` opens the showroom with the control room on. `?look=v1` brings back the old flat look.

</details>

## Run it on your computer

`python tools/serve.py`, then open http://127.0.0.1:8765. Blender source for every part: [blender/](blender/).

Built with Blender 5.2, three.js and Claude Code. Ground, brick, plaster, concrete and roof textures: [Poly Haven](https://polyhaven.com) (CC0). Updates: [LinkedIn](https://www.linkedin.com/in/sumith-shridhar-b9919924a) · [X](https://x.com/sumithshridhar) · [Instagram](https://www.instagram.com/ghost.ops.ai.service/)
