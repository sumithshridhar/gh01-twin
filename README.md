# GH-01 · digital twin

**Live:** https://sumithshridhar.github.io/gh01-twin/

An interactive 3D digital twin of GH-01, a small AI + robotics tomato greenhouse designed for polyhouse farmers in Karnataka.
It has 127 components and 54 tagged plants, each modelled in Blender on a real product at real size.

**The farm round the house (Oct 2026):** a solar packhouse (6 × 540 W panels, hybrid inverter, 5 kWh LiFePO4 battery,
zero-energy cool chamber), a lined farm pond with a level sensor and safety fence, rainwater gutters with a first-flush
chamber, a double-door entry room with a footbath, a retractable aluminet shade net, and the farm's borewell as backup.

**Robot row change (Oct 2026):** the scout robot now changes rows on its own. It backs off the pipe rails over a sloped
handover plate onto 4 mecanum wheels, slides sideways to the next aisle, lines up on a floor code read by a camera underneath,
and drives back onto the pipes. Write-up: why the rails cost ~₹17.7 lakh an acre in Indian polyhouses (no heating pipes).

**R1, a rover for soil-bed polyhouses (Oct 2026):** no rails, 36 cm wide, 6 cameras, 6 spray valves, Pi 5 + AI HAT+.
Semi-automatic: it scouts and predicts on its own, and every chemical spray needs a human yes. Plus how it avoids carrying
disease between houses. Design, parts, software and biosecurity: [rover/](rover/). Blender source for every part: [blender/](blender/).

**Build it yourself:** [Part 1: a pest-counting camera](build/01-pest-camera/) (Pi Zero 2 W + Camera Module 3 + TPL5110 timer,
AI on the farm's Pi 5 + AI HAT+): parts, wiring, code.

**Try:**
- Click any machine, sensor or plant to explode it into its parts, with a blueprint.
- Run the failure tests (bottom left):
  - pump failure
  - sensor failure
  - water shortage
  - heat wave
  - disease found
  - robot stuck
  - power cut (Karnataka farm feeders give 7 h of three-phase power a day; the solar + battery keep the cooling running)
  - pond running dry (the twin keeps a 20 % reserve and switches the tank to the borewell)
- Walk mode (W A S D) and the guided tour.

**The rule the whole design follows:**
- the edge AI **suggests**;
- a safety PLC **decides** within hard limits;
- hard-wired cut-offs (float switch, thermostat) **protect** the crop even if every computer fails.

**Status:** design and simulation only. Nothing is built yet; next is talking to polyhouse farmers and a bench kit.

Built with Blender 5.2, three.js and Claude Code. Ground, brick, plaster, concrete and roof textures: [Poly Haven](https://polyhaven.com) (CC0). Updates: [LinkedIn](https://www.linkedin.com/in/sumith-shridhar-b9919924a) · [X](https://x.com/sumithshridhar) · [Instagram](https://www.instagram.com/ghost.ops.ai.service/)
