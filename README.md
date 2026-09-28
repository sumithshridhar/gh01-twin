# GH-01 · digital twin

**Live:** https://sumithshridhar.github.io/gh01-twin/

An interactive 3D digital twin of GH-01, a small AI + robotics tomato greenhouse designed for polyhouse farmers in Karnataka.
It has 115 components and 54 tagged plants, each modelled in Blender on a real product at real size.

**Try:**
- Click any machine, sensor or plant to explode it into its parts, with a blueprint.
- Run the failure tests (bottom left):
  - pump failure
  - sensor failure
  - water shortage
  - heat wave
  - disease found
  - robot stuck
- Walk mode (W A S D) and the guided tour.

**The rule the whole design follows:**
- the edge AI **suggests**;
- a safety PLC **decides** within hard limits;
- hard-wired cut-offs (float switch, thermostat) **protect** the crop even if every computer fails.

**Status:** design and simulation only. Nothing is built yet; next is talking to polyhouse farmers and a bench kit.

Built with Blender 5.2, three.js and Claude Code. Updates: [LinkedIn](https://www.linkedin.com/in/sumith-shridhar-b9919924a) · [X](https://x.com/sumithshridhar) · [Instagram](https://www.instagram.com/ghost.ops.ai.service/)
