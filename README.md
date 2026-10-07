# GH-01 · digital twin

**Live:** https://sumithshridhar.github.io/gh01-twin/

An interactive 3D digital twin of GH-01, a small AI + robotics tomato greenhouse designed for polyhouse farmers in Karnataka.
It has 127 components and 54 tagged plants, each modelled in Blender on a real product at real size.

**The farm round the house (Oct 2026):** a solar packhouse (6 × 540 W panels, hybrid inverter, 5 kWh LiFePO4 battery,
zero-energy cool chamber), a lined farm pond with a level sensor and safety fence, rainwater gutters with a first-flush
chamber, a double-door entry room with a footbath, a retractable aluminet shade net, and the farm's borewell as backup.

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
