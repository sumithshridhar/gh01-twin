"""Control hardware: main control cabinet (safety PLC + edge computer), ESP32 field node, farmer wall tablet."""
import math
from pathlib import Path

from gh import MB, Component, bm_box, emissive, image_mat, xform
from parts import cable

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def din_module(mb, x, z, w, h, d, body="plastic_white", face=None, y0=0.0, toggle=None, label=None):
    """A DIN-rail device: body standing on the plate (y0 = plate front), optional coloured face and toggle."""
    mb.box((w - 0.001, d, h), body, bevel=0.002, loc=(x, y0 - d / 2, z))
    mb.box((w * 0.7, d * 0.25, h * 0.5), body, bevel=0.002, loc=(x, y0 - d - d * 0.1, z))  # front 'nose'
    if face:
        mb.box((w * 0.62, 0.001, h * 0.18), face, loc=(x, y0 - d * 1.23, z + h * 0.12))
    if toggle:
        mb.box((w * 0.35, 0.012, h * 0.1), toggle, bevel=0.001, loc=(x, y0 - d * 1.28, z - h * 0.05))
    if label:
        mb.box((w * 0.8, 0.001, h * 0.08), "sticker_white", loc=(x, y0 - d * 1.23, z - h * 0.3))
    return mb


# ─────────────────────────────── control cabinet ───────────────────────────────
def control_cabinet(cid="control_cabinet", title="Main control cabinet (safety PLC + edge computer)"):
    c = Component(
        cid, title, "Control",
        summary="The brain and the safety guard. Every pump, valve, fan and vent is switched from here.",
        how=("Two separate computers on purpose. The EDGE COMPUTER (Raspberry Pi 5) stores data, runs the AI and the "
             "dashboard – it only SUGGESTS actions. The SAFETY PLC owns every relay: it checks each suggestion against hard "
             "limits and sensor plausibility, runs a fixed fallback program if the edge computer goes silent, and cannot be "
             "overridden by software. Under both: hard-wired protection – RCCB 30 mA against electric shock (water + "
             "electricity), motor breakers, the dry-run float and the high-temperature thermostat wired straight into the "
             "contactor coils, and the E-stop that cuts all actuator power."),
        sensors=("all field sensors (via ESP32 nodes + direct PLC inputs)", "door switch", "cabinet temperature"),
        control="PLC = actuator owner; edge computer = advisor; E-stop + interlocks = hardware.",
        state={"mode": "AUTO", "plc_heartbeat": "ok", "edge_heartbeat": "ok", "estop": False, "ups_pct": 100},
        real="EC Box 800×1000×300 IP65 steel enclosure, Arduino Opta RS485 PLC (AFX00001), Raspberry Pi 5 8 GB + AI HAT+ "
             "26 TOPS, Schneider TeSys LC1D09 contactors + GV2ME motor breakers, 30 mA RCCB, 4G router, DC UPS",
        cost="≈₹1.13 L fully built")
    W, H, D = 0.8, 1.0, 0.3
    en = MB()
    t = 0.0015
    en.box((W, t * 2, H), "ral7035", loc=(0, D / 2, 0))           # back
    for sx in (-1, 1):
        en.box((t * 2, D, H), "ral7035", loc=(sx * W / 2, 0, 0))
    for sz in (-1, 1):
        en.box((W, D, t * 2), "ral7035", loc=(0, 0, sz * H / 2))
    en.box((W + 0.02, 0.02, 0.02), "ral7035", bevel=0.004, loc=(0, -D / 2 + 0.01, H / 2 + 0.005))
    for k, x in enumerate((-0.25, -0.12, 0.0, 0.12, 0.25)):  # glands in the bottom plate
        en.cyl(0.012, 0.025, "plastic_dark", segs=6, z0=-H / 2 - 0.025, loc=(x, 0.0, 0))
        cable(en, [(x, 0.0, -H / 2 - 0.02), (x, 0.0, -H / 2 - 0.12), (x + 0.05, -0.05, -H / 2 - 0.35)],
              r=0.006 if k else 0.009)
    en.box((0.12, 0.004, 0.12), "plastic_dark", loc=(W / 2 + 0.002, 0, 0.3), rot=(0, 0, 90))  # filter fan grille
    for sx in (-1, 1):
        en.box((0.06, 0.03, 0.02), "steel_dark", loc=(sx * 0.3, D / 2 + 0.015, H / 2 - 0.05))
        en.box((0.06, 0.03, 0.02), "steel_dark", loc=(sx * 0.3, D / 2 + 0.015, -H / 2 + 0.05))
    c.part("enclosure", en, desc="IP65 powder-coated steel enclosure, cable glands in the bottom (no water from above).")
    dr = MB()
    dr.box((W - 0.004, 0.02, H - 0.004), "ral7035", bevel=0.004)
    dr.box((0.03, 0.03, 0.14), "plastic_black", bevel=0.006, loc=(W / 2 - 0.06, -0.02, 0.0))
    dr.cyl(0.035, 0.006, "sticker_yellow", segs=32, axis="-Y", loc=(0.25, -0.012, 0.32))
    dr.cyl(0.02, 0.018, "plastic_red", segs=32, axis="-Y", loc=(0.25, -0.02, 0.32))
    dr.sphere(0.024, "plastic_red", segs=24, rings=10, squash=0.5, loc=(0.25, -0.03, 0.32), rot=(90, 0, 0))
    for k, (m, lab) in enumerate((("led_green", "RUN"), ("led_amber", "ALARM"), ("led_red", "FAULT"))):
        x = -0.25 + 0.1 * k
        dr.cyl(0.013, 0.012, "chrome", segs=24, axis="-Y", loc=(x, -0.012, 0.32))
        dr.cyl(0.01, 0.006, m, segs=24, axis="-Y", loc=(x, -0.02, 0.32))
        dr.text(lab, 0.014, "plastic_black", loc=(x, -0.0105, 0.28), rot=(90, 0, 0), bold=True)
    dr.cyl(0.016, 0.012, "plastic_black", segs=24, axis="-Y", loc=(0.05, -0.012, 0.32))
    dr.box((0.008, 0.01, 0.03), "plastic_white", loc=(0.05, -0.022, 0.32), rot=(0, 30, 0))
    dr.text("AUTO  OFF  MAN", 0.01, "plastic_black", loc=(0.05, -0.0105, 0.28), rot=(90, 0, 0))
    dr.box((0.36, 0.001, 0.08), "sticker_white", loc=(0, -0.0102, 0.1))
    dr.text("GH-01  CONTROL", 0.03, "plastic_black", loc=(0, -0.011, 0.11), rot=(90, 0, 0), bold=True)
    dr.text("230 V · 24 V DC · 24 V AC", 0.016, "plastic_black", loc=(0, -0.011, 0.075), rot=(90, 0, 0))
    dr.add(bm_box(0.12, 0.001, 0.11), "sticker_yellow", loc=(-0.25, -0.0102, -0.3))
    dr.text("DANGER", 0.022, "plastic_black", loc=(-0.25, -0.011, -0.285), rot=(90, 0, 0), bold=True)
    dr.text("230 V", 0.022, "plastic_black", loc=(-0.25, -0.011, -0.315), rot=(90, 0, 0), bold=True)
    c.part("door", dr, loc=(0, -D / 2 - 0.01, 0), explode=(-0.95, -0.2, 0),
           desc="Door: E-stop (cuts ALL actuator power), RUN/ALARM/FAULT lamps, AUTO-OFF-MANUAL selector.")
    pl = MB()
    pl.box((W - 0.06, 0.004, H - 0.06), "galv_dull", loc=(0, 0, 0))
    for z in (0.33, 0.1, -0.13, -0.36):
        pl.box((W - 0.12, 0.008, 0.035), "galv", loc=(0, -0.006, z))  # DIN rails
    y_front = -0.01
    c.part("mounting_plate", pl, loc=(0, D / 2 - 0.03, 0), explode=(0, -0.4, 0), desc="Mounting plate with DIN rails.")
    duct = MB()
    for z in (0.44, 0.215, -0.015, -0.245, -0.44):
        duct.box((W - 0.1, 0.06, 0.04), "pvc_grey", loc=(0, -0.03, z))
        for k in range(28):
            duct.box((0.004, 0.061, 0.03), "plastic_dark", loc=(-0.34 + k * 0.025, -0.03, z))
    for sx in (-1, 1):
        duct.box((0.04, 0.06, H - 0.1), "pvc_grey", loc=(sx * (W / 2 - 0.05), -0.03, 0))
    c.part("cable_ducts", duct, loc=(0, D / 2 - 0.035, 0), explode=(0, -0.5, 0), desc="Slotted cable ducts (tidy wiring = easy service).")
    Y0 = D / 2 - 0.036
    rows = {}
    # row 1: incoming power & protection
    r1 = MB()
    din_module(r1, -0.3, 0.33, 0.07, 0.1, 0.06, body="plastic_dark", toggle="plastic_red")          # main isolator
    din_module(r1, -0.21, 0.33, 0.036, 0.09, 0.065, face="plastic_yellow", toggle="plastic_blue", label=True)  # RCCB
    din_module(r1, -0.175, 0.33, 0.036, 0.09, 0.065, face="plastic_yellow", toggle="plastic_blue", label=True)
    for k in range(8):
        din_module(r1, -0.12 + 0.019 * k, 0.33, 0.018, 0.09, 0.065, toggle="plastic_black", label=True)  # MCBs
    din_module(r1, 0.1, 0.33, 0.036, 0.09, 0.065, body="plastic_dark", face="led_green")  # surge
    c.part("protection_row", r1, loc=(0, Y0, 0), explode=(0.0, -0.65, 0.04),
           desc="Main isolator, 30 mA RCCB (shock protection), 8 circuit breakers, surge protector.")
    # row 2: power supplies + comms
    r2 = MB()
    r2.box((0.1, 0.1, 0.13), "alu", bevel=0.003, loc=(-0.28, -0.05, 0.1))
    for k in range(10):
        r2.box((0.09, 0.002, 0.004), "steel_dark", loc=(-0.28, -0.1, 0.1 + 0.05 - k * 0.011))
    c.part("psu_24vdc", r2, loc=(0, Y0, 0), explode=(0.0, -0.67, 0.02), desc="24 V DC power supply (sensors, PLC, relays).")
    tr = MB()
    tr.box((0.1, 0.09, 0.1), "steel_dark", bevel=0.003, loc=(-0.15, -0.045, 0.1))
    tr.box((0.07, 0.07, 0.06), "copper", loc=(-0.15, -0.045, 0.1))
    tr.box((0.1, 0.004, 0.02), "sticker_yellow", loc=(-0.15, -0.092, 0.15))
    c.part("transformer_24vac", tr, loc=(0, Y0, 0), explode=(0.0, -0.69, 0.02), desc="Safety transformer 230 → 24 V AC for the valve solenoids.")
    rt = MB()
    rt.box((0.12, 0.035, 0.09), "plastic_white", bevel=0.005, loc=(0.05, -0.02, 0.1))
    for sx in (-1, 1):
        rt.cyl(0.005, 0.1, "plastic_black", segs=12, z0=0.14, loc=(0.05 + sx * 0.045, -0.02, 0))
    for k in range(4):
        rt.box((0.006, 0.001, 0.004), "led_green", loc=(0.02 + k * 0.015, -0.038, 0.12))
    c.part("router_4g", rt, loc=(0, Y0, 0), explode=(0.0, -0.71, 0.05),
           desc="4G/Wi-Fi router – alerts + remote dashboard; greenhouse still runs fully offline.")
    up = MB()
    up.box((0.15, 0.1, 0.1), "plastic_black", bevel=0.004, loc=(0.25, -0.05, 0.1))
    up.box((0.04, 0.002, 0.01), "led_green", loc=(0.25, -0.101, 0.13))
    c.part("ups_battery", up, loc=(0, Y0, 0), explode=(0.0, -0.65, 0.02),
           desc="DC UPS + 12 V battery: PLC, edge computer and network keep running ~2 h in a power cut.")
    # row 3: the two brains
    plc = MB()
    din_module(plc, -0.26, -0.13, 0.07, 0.1, 0.06, body="plastic_white", face="led_green")
    plc.box((0.06, 0.002, 0.03), "plastic_blue", loc=(-0.26, -0.075, -0.1))
    for k in range(2):
        din_module(plc, -0.195 + 0.045 * k, -0.13, 0.043, 0.1, 0.06, body="plastic_white", face="led_amber")
    for k in range(16):
        plc.box((0.0025, 0.001, 0.0025), "led_green" if k % 3 else "led_amber",
                loc=(-0.28 + (k % 8) * 0.006, -0.0767, -0.155 + (k // 8) * 0.007))
    plc.text("ARDUINO OPTA", 0.0085, "plastic_black", loc=(-0.26, -0.0775, -0.17), rot=(90, 0, 0), bold=True)
    c.part("safety_plc", plc, loc=(0, Y0, 0), explode=(0.0, -0.75, 0.0),
           desc="SAFETY PLC + 2 I/O expansions. Owns every actuator; checks limits; runs fallback if the AI computer is silent.")
    pi = MB()
    pi.box((0.1, 0.06, 0.11), "plastic_black", bevel=0.004, loc=(-0.05, -0.03, -0.13))
    for k in range(6):
        pi.box((0.08, 0.002, 0.004), "alu_black", loc=(-0.05, -0.061, -0.1 - k * 0.01))
    pi.box((0.012, 0.002, 0.006), "led_green", loc=(-0.02, -0.061, -0.17))
    pi.box((0.012, 0.002, 0.006), "led_red", loc=(-0.035, -0.061, -0.17))
    pi.text("Pi 5 + AI HAT+", 0.0095, "plastic_white", loc=(-0.05, -0.0615, -0.155), rot=(90, 0, 0), bold=True)
    c.part("edge_computer_pi5", pi, loc=(0, Y0, 0), explode=(0.0, -0.79, 0.03),
           desc="Edge computer: Raspberry Pi 5 8 GB + NVMe + Hailo AI HAT+ (26 TOPS). Database, AI models, dashboard.")
    sw = MB()
    sw.box((0.09, 0.04, 0.1), "alu", bevel=0.003, loc=(0.08, -0.02, -0.13))
    for k in range(5):
        sw.box((0.012, 0.002, 0.01), "plastic_black", loc=(0.05 + k * 0.016, -0.041, -0.11))
        sw.box((0.003, 0.001, 0.003), "led_green", loc=(0.05 + k * 0.016, -0.042, -0.125))
    c.part("network_switch", sw, loc=(0, Y0, 0), explode=(0.0, -0.75, 0.04), desc="Industrial PoE network switch (cameras, nodes).")
    # row 4: switching
    s4 = MB()
    for k in range(4):
        x = -0.3 + 0.06 * k
        s4.box((0.045, 0.08, 0.08), "plastic_dark", bevel=0.003, loc=(x, -0.04, -0.36))
        s4.box((0.03, 0.004, 0.02), "sticker_white", loc=(x, -0.081, -0.345))
        s4.box((0.02, 0.01, 0.015), "plastic_white", loc=(x, -0.085, -0.375))
    c.part("contactors", s4, loc=(0, Y0, 0), explode=(0.0, -0.73, -0.03),
           desc="Contactors: irrigation pump, fan 1, fan 2, pad pump. Float switch + thermostat are wired into their coils.")
    mp = MB()
    mp.box((0.045, 0.08, 0.09), "plastic_dark", bevel=0.003, loc=(-0.05, -0.04, -0.36))
    mp.cyl(0.012, 0.012, "plastic_red", segs=24, axis="-Y", loc=(-0.05, -0.086, -0.35))
    c.part("motor_breaker", mp, loc=(0, Y0, 0), explode=(0.0, -0.75, -0.03), desc="Motor-protection breaker for the pump (overload trip).")
    rl = MB()
    for k in range(8):
        x = 0.02 + 0.017 * k
        rl.box((0.015, 0.06, 0.07), "plastic_blue" if k < 6 else "plastic_white", bevel=0.002, loc=(x, -0.03, -0.36))
        rl.box((0.004, 0.001, 0.004), "led_amber", loc=(x, -0.061, -0.34))
    c.part("relays", rl, loc=(0, Y0, 0), explode=(0.0, -0.71, -0.03), desc="Interface relays: 6 zone/dosing outputs + 2 alarm outputs.")
    tb = MB()
    cols = ["plastic_blue", "plastic_dark", "plastic_dark", "plastic_green"]
    for k in range(40):
        x = -0.34 + k * 0.0085
        tb.box((0.0075, 0.05, 0.05), cols[k % 4] if k % 4 != 3 else "sticker_yellow", bevel=0.001, loc=(x, -0.025, -0.44 + 0.0))
    c.part("terminal_blocks", tb, loc=(0, Y0, 0.01), explode=(0.0, -0.65, -0.06), desc="Terminal blocks – every field wire lands here, numbered.")
    return c


# ─────────────────────────────── ESP32 field node ───────────────────────────────
def esp32_node(cid="esp32_node", title="ESP32 sensor node (IP65)"):
    c = Component(
        cid, title, "Control",
        summary="A small box near the sensors: reads them and publishes the values over Wi-Fi/Ethernet (MQTT).",
        how=("An ESP32 microcontroller runs ESPHome firmware: it polls I²C sensors (climate box), RS485 Modbus sensors "
             "(substrate, weather) and pulse inputs, then sends readings every 10 s to the edge computer. It never switches "
             "safety-critical outputs – that is the PLC's job. Firmware updates go over the air."),
        sensors=("I²C, RS485, pulse and analog inputs",), control="MQTT → edge server; heartbeat monitored.",
        state={"rssi_dbm": -61, "uptime_h": 312, "last_msg_s": 4},
        real="ESP32-S3 on DIN carrier + MAX485 + 24→5 V buck in an IP65 box with clear lid", cost="₹1.5–3k")
    bx = MB()
    bx.box((0.2, 0.1, 0.15), "plastic_cream", bevel=0.006)
    for k in range(4):
        bx.cyl(0.008, 0.018, "plastic_black", segs=6, z0=-0.093, loc=(-0.06 + 0.04 * k, 0, 0))
        cable(bx, [(-0.06 + 0.04 * k, 0, -0.09), (-0.06 + 0.04 * k, 0, -0.14), (-0.08 + 0.05 * k, -0.04, -0.25)], r=0.0035)
    bx.cyl(0.004, 0.1, "plastic_black", segs=12, z0=0.075, loc=(0.07, 0.02, 0))
    c.part("enclosure", bx, desc="IP65 enclosure, glands at the bottom, external antenna.")
    ld = MB()
    ld.box((0.196, 0.006, 0.146), "acrylic", bevel=0.004)
    for sx in (-1, 1):
        for sz in (-1, 1):
            ld.cyl(0.004, 0.004, "stainless", segs=12, axis="-Y", loc=(sx * 0.085, -0.004, sz * 0.06))
    c.part("clear_lid", ld, loc=(0, -0.053, 0), explode=(0, -0.12, 0), desc="Clear lid – status LEDs visible without opening.")
    el = MB()
    el.box((0.17, 0.008, 0.035), "galv", loc=(0, 0.04, 0.02))
    el.box((0.055, 0.02, 0.028), "pcb", loc=(-0.045, 0.02, 0.02))
    el.box((0.018, 0.004, 0.025), "alu", loc=(-0.045, 0.008, 0.02))
    el.box((0.003, 0.002, 0.003), "led_blue", loc=(-0.02, 0.008, 0.03))
    el.box((0.035, 0.02, 0.025), "pcb_blue", loc=(0.015, 0.02, 0.02))
    el.box((0.03, 0.025, 0.03), "plastic_dark", loc=(0.06, 0.018, 0.02))
    for k in range(8):
        el.box((0.0075, 0.03, 0.03), "plastic_dark" if k % 2 else "plastic_blue", loc=(-0.035 + k * 0.009, 0.02, -0.035))
    c.part("electronics", el, explode=(0, -0.06, 0.0), desc="ESP32-S3 board, RS485 transceiver, 24→5 V converter, terminals.")
    return c


# ─────────────────────────────── farmer wall tablet ───────────────────────────────
def hmi_tablet(cid="farmer_tablet", title="Farmer wall tablet (dashboard)"):
    c = Component(
        cid, title, "Interface",
        summary="What the farmer sees at the door: live conditions, what the AI decided and why, and alerts.",
        how=("A rugged Android tablet shows the local web dashboard served by the edge computer (works without internet). "
             "Every automatic action is listed with its reason ('Zone 2 shot 180 mL because radiation sum reached 120 J/cm² "
             "and slab weight fell 400 g'). Alerts also go to the farmer's phone (Telegram/WhatsApp) in the local language."),
        sensors=("touch input",), control="Read-only by default; manual overrides go through the PLC's limits.",
        state={"page": "overview", "alerts": 2},
        real="Samsung Galaxy Tab Active5 (8\", IP68, MIL-STD-810H) on a wall bracket — optional: the farmer's phone runs the same app",
        cost="₹49,999 (optional)")
    fr = MB()
    fr.box((0.2138, 0.0101, 0.1268), "plastic_dark", bevel=0.006)
    for sx in (-1, 1):
        for sz in (-1, 1):
            fr.box((0.03, 0.016, 0.03), "rubber", bevel=0.008, loc=(sx * 0.097, 0.001, sz * 0.053))   # bumper corners
    fr.box((0.012, 0.004, 0.03), "plastic_black", loc=(0.1075, 0, 0.02))                               # side keys
    c.part("rugged_case", fr, desc="Rugged IP68 body with rubber corner bumpers (wet hands, dust, drops).")
    sc = MB()
    scr = image_mat("hmi_screen", ASSETS / "hmi_dashboard.png", emit=1.2, rough=0.1)
    sc.add(bm_box(0.19, 0.119, 0.002), scr, M=xform((0, -0.0062, 0), (90, 0, 0)) @ xform(rot=(0, 0, 0)),
           planar_uv=(0, 1, 1 / 0.19, 1 / 0.119))
    c.part("screen", sc, explode=(0, -0.06, 0), desc="8\" WUXGA touch screen – local dashboard.")
    br = MB()
    br.box((0.12, 0.012, 0.1), "alu", bevel=0.003, loc=(0, 0.011, 0))
    br.box((0.16, 0.006, 0.16), "alu", bevel=0.003, loc=(0, 0.034, 0))
    br.cyl(0.01, 0.024, "alu", segs=16, axis="Y", loc=(0, 0.022, 0))
    c.part("wall_bracket", br, explode=(0, 0.08, 0), desc="Tilting wall bracket.")
    return c
