"""Grow lighting: dimmable LED top-light bar."""
from gh import MB, Component, emissive, xform
from parts import cable


def led_toplight(cid="led_toplight", title="LED top-light (full-spectrum, dimmable)", on=False):
    c = Component(
        cid, title, "Lighting",
        summary="Adds light only when the day is too dark to reach the crop's daily light target (DLI).",
        how=("Rows of white + deep-red LEDs (≈2.8–3.2 µmol per joule – the most efficient light source for plants) on an "
             "aluminium heat sink. A 0–10 V dimmer lets the controller add just the missing light. The AI checks the "
             "morning forecast: if the DLI will fall short, it tops up at the cheapest hours. In sunny India this is "
             "mostly for monsoon weeks and the seedling nursery."),
        sensors=("PAR sensor (inside)", "pyranometer (outside)", "driver temperature"),
        control="0–10 V dimming + relay via PLC; AI sets hours/intensity; PLC enforces max power & temperature.",
        state={"on": on, "dim_pct": 0, "power_w": 0},
        real="600 W greenhouse LED top-light, IP66, 0–10 V (Signify/Fluence class)", cost="₹25–45k",
        view=(30, -28))
    L, W = 1.12, 0.11
    hs = MB()
    hs.box((L, W, 0.018), "alu", bevel=0.003)
    for k in range(9):
        y = -W / 2 + 0.01 + k * (W - 0.02) / 8
        hs.box((L - 0.02, 0.0025, 0.04), "alu", loc=(0, y, 0.028))
    for sx in (-1, 1):
        hs.box((0.02, W + 0.004, 0.06), "plastic_dark", bevel=0.004, loc=(sx * (L / 2 + 0.008), 0, 0.018))
    c.part("heatsink_body", hs, desc="Extruded aluminium heat sink (keeps LEDs cool = longer life, higher efficiency).")
    lb = MB()
    lb.box((L - 0.04, W - 0.02, 0.0016), "pcb", loc=(0, 0, 0))
    led_on = emissive("led_grow_on", (1.0, 0.72, 0.62), 18.0) if on else "led_white"
    red_on = emissive("led_red_on", (1.0, 0.05, 0.08), 12.0) if on else "led_red"
    for i in range(36):
        for j in range(3):
            x = -L / 2 + 0.04 + i * (L - 0.08) / 35
            y = -0.028 + j * 0.028
            m = red_on if (i + j) % 3 == 0 else led_on
            lb.box((0.0045, 0.0045, 0.0014), m, loc=(x, y, -0.0012))
    c.part("led_boards", lb, loc=(0, 0, -0.011), explode=(0, 0, -0.1), desc="LED boards: white + deep red (660 nm) mix.")
    ln = MB()
    ln.box((L - 0.03, W - 0.008, 0.003), "acrylic", bevel=0.001)
    c.part("lens_cover", ln, loc=(0, 0, -0.017), explode=(0, 0, -0.2), desc="Protective lens / cover (IP66, cleanable).")
    dv = MB()
    dv.box((0.3, 0.07, 0.045), "alu", bevel=0.005)
    dv.box((0.05, 0.02, 0.01), "sticker_white", loc=(0, -0.036, 0.0), rot=(90, 0, 0))
    cable(dv, [(0.15, 0, 0.0), (0.2, 0, 0.0), (0.26, 0, 0.1), (0.3, 0, 0.35)], r=0.004)
    c.part("driver", dv, loc=(0, 0, 0.075), explode=(0, 0, 0.18), desc="LED driver (230 V AC → constant current), 0–10 V dim input.")
    hg = MB()
    for sx in (-1, 1):
        hg.torus(0.012, 0.0025, "stainless", segs=16, rsegs=6, axis="Y", loc=(sx * 0.45, 0, 0.065))
        hg.sweep([(sx * 0.45, 0, 0.077), (sx * 0.45, 0, 0.5)], 0.0015, "stainless", segs=6)
    c.part("hangers", hg, explode=(0, 0, 0.3), desc="Steel wire hangers to the roof truss.")
    return c


def led_toplight_on():
    return led_toplight("led_toplight_on", on=True)
