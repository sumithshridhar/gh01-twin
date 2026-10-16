"""Sensors: aspirated climate box (T/RH + CO2), PAR sensor, substrate sensor, ultrasonic level, weather station,
sticky-trap camera, fixed canopy camera."""
import math
import random

from gh import MB, TAU, Component, bm_lathe, xform
from parts import cable, radial, screw


def pcb_with_chips(mb, w, h, m="pcb", chips=((0, 0, 0.004, 0.004),), loc=(0, 0, 0), rot=(0, 0, 0)):
    M = xform(loc, rot)
    mb.add(__import__("gh").bm_box(w, h, 0.0016), m, M=M)
    for x, y, cw, ch in chips:
        mb.add(__import__("gh").bm_box(cw, ch, 0.0012), "chip", M=M @ xform((x, y, 0.0014)))
    return mb


# ─────────────────────────────── aspirated climate box ───────────────────────────────
def climate_box(cid="climate_box", title="Aspirated climate box (T / RH / CO₂)"):
    c = Component(
        cid, title, "Sensors",
        summary="Measures air temperature, humidity (→ VPD) and CO₂ at plant-head height.",
        how=("A small fan pulls greenhouse air through a white, shaded tube at ~3 m/s. The white shield blocks sunlight "
             "(an unshaded sensor in sun can read 5–10 °C too high) and the airflow keeps it at true air temperature. "
             "Inside: an SHT45 (temperature ±0.1 °C, RH ±1 %) and an SCD41 NDIR CO₂ sensor (infra-red absorption at 4.26 µm). "
             "VPD is computed from T and RH. The box hangs from the crop wire and is raised as the crop grows."),
        sensors=("SHT45 temp/RH", "SCD41 CO₂ (NDIR)", "fan tachometer (fan failure = bad data)"),
        control="ESP32 node → MQTT every 10 s. Two boxes in the house → cross-check; PLC also reads one (safety).",
        state={"temp_c": 24.6, "rh_pct": 71, "vpd_kpa": 0.9, "co2_ppm": 438, "fan_rpm": 4200},
        real="Aspirated radiation shield (Priva/Hoogendoorn-style) with SHT45 + SCD41", cost="₹5–7k")
    L, R = 0.36, 0.055
    hs = MB()
    hs.lathe([(R - 0.003, 0.0), (R, 0.0), (R, L), (R - 0.003, L)], "plastic_white", segs=40, closed=True, axis="X",
             loc=(-L / 2, 0, 0))
    hs.lathe([(R + 0.004, 0.0), (R + 0.022, 0.0), (R + 0.022, L * 0.7), (R + 0.004, L * 0.7)], "plastic_white",
             segs=40, closed=True, axis="X", loc=(-L / 2 + 0.04, 0, 0.0))  # outer sun-shield
    for k in range(6):
        hs.box((0.02, 0.004, 0.02), "plastic_white", loc=(-0.1 + 0.05 * k, 0, R + 0.012))
    for x in (-0.13, 0.13):
        hs.box((0.01, 0.01, 0.08), "stainless", loc=(x, 0, R + 0.06))
        hs.torus(0.01, 0.0018, "stainless", segs=16, rsegs=6, axis="Y", loc=(x, 0, R + 0.105))
    hs.text("CLIMATE 01", 0.012, "plastic_green", loc=(0.02, -R - 0.023, 0.0), rot=(90, 0, 0), bold=True)
    c.part("housing", hs, desc="Double-wall white radiation shield + hangers.")
    gr = MB()
    for k in range(5):
        gr.torus(0.012 + 0.009 * k, 0.0012, "plastic_dark", segs=32, rsegs=6, axis="X")
    for k in range(4):
        gr.box((0.002, 0.1, 0.002), "plastic_dark", rot=(45 * k, 0, 0))
    c.part("inlet_grille", gr, loc=(-L / 2 - 0.002, 0, 0), explode=(-0.12, 0, 0), desc="Air inlet grille (insect-proof).")
    pc = MB()
    pcb_with_chips(pc, 0.07, 0.04, chips=((-0.02, 0.0, 0.003, 0.003), (0.01, 0.0, 0.006, 0.004)))
    pc.box((0.025, 0.02, 0.012), "plastic_white", loc=(0.0, 0.0, 0.008))
    pc.box((0.004, 0.003, 0.004), "chip", loc=(-0.025, 0.0, 0.003))
    c.part("sensor_board", pc, loc=(-0.05, 0, -0.01), explode=(0, 0, -0.16),
           desc="SHT45 (T/RH, left) + SCD41 NDIR CO₂ module (white block) on one board.")
    co = MB()
    co.box((0.0102, 0.0102, 0.0065), "pcb", bevel=0.0004)
    co.box((0.008, 0.008, 0.004), "plastic_white", loc=(0, 0, 0.004))
    c.part("scd41_co2", co, loc=(-0.05, 0.03, -0.01), explode=(0, -0.06, -0.2),
           desc="SCD41: an IR source shines through air to a 4.26 µm detector; CO₂ absorbs that wavelength.")
    fn = MB()
    fn.box((0.06, 0.06, 0.025), "plastic_black", bevel=0.003, rot=(0, 90, 0))
    fn.cyl(0.026, 0.02, "plastic_dark", segs=32, axis="X")
    for k in range(7):
        fn.box((0.002, 0.022, 0.006), "plastic_dark", M=xform(rot=(360 / 7 * k, 0, 0)) @ xform((0.0, 0.014, 0), (0, 25, 0)))
    c.part("aspiration_fan", fn, loc=(L / 2 - 0.03, 0, 0), explode=(0.16, 0, 0),
           desc="12 V fan – pulls air across the sensors (tach signal proves it is running).")
    cb = MB()
    cable(cb, [(L / 2, 0, 0), (L / 2 + 0.05, 0, 0), (L / 2 + 0.1, 0, 0.08), (L / 2 + 0.12, 0, 0.2)], r=0.003)
    c.part("cable", cb, explode=(0.2, 0, 0), desc="Power + I²C/RS485 cable to the ESP32 node.")
    return c


# ─────────────────────────────── PAR sensor ───────────────────────────────
def par_sensor(cid="par_sensor", title="PAR quantum sensor"):
    c = Component(
        cid, title, "Sensors",
        summary="Measures the light plants can use (PAR, 400–700 nm) in µmol/m²/s; summed over a day = DLI.",
        how=("A white acrylic diffuser collects light from all angles; a filtered silicon photodiode under it responds "
             "only to 400–700 nm. The current is proportional to photon flux. The day's total (DLI) tells the system "
             "whether to shade (too much) or switch on LEDs (too little). Tomato target: DLI 20–30 mol/m²/day."),
        sensors=("self",), control="RS485 Modbus → ESP32 node → MQTT; used for shade decisions and irrigation.",
        state={"ppfd": 812, "dli_today": 17.4},
        real="Renke RS-GH-N01-AL PAR sensor (RS485 Modbus, 0–2500 µmol/m²/s, aluminium body)", cost="≈₹7.3k")
    bd = MB()
    bd.lathe([(0.0, 0.0), (0.027, 0.0), (0.027, 0.03), (0.024, 0.034), (0.0, 0.034)], "alu", segs=48)
    bd.cyl(0.006, 0.014, "plastic_black", segs=6, axis="X", loc=(0.031, 0, 0.012))       # cable gland
    c.part("body", bd, desc="Silver aluminium body (IP67).")
    df = MB()
    df.lathe([(0.0, 0.0), (0.014, 0.0), (0.014, 0.003), (0.011, 0.009), (0.0, 0.012)], "diffuser", segs=40)
    c.part("diffuser", df, loc=(0, 0, 0.034), explode=(0, 0, 0.05), desc="Cosine-corrected acrylic diffuser.")
    pdm = MB()
    pdm.cyl(0.006, 0.002, "glass", segs=24, z0=0.004)
    pdm.box((0.004, 0.004, 0.001), "chip", loc=(0, 0, 0.0025))
    pdm.cyl(0.009, 0.0016, "pcb", segs=24, z0=0.0)
    c.part("filter_photodiode", pdm, loc=(0, 0, 0.022), explode=(0, 0, 0.03), desc="Optical filter + silicon photodiode.")
    lp = MB()
    lp.box((0.08, 0.05, 0.004), "alu", bevel=0.001, loc=(0.02, 0, -0.002))
    for x, y in ((-0.012, 0.018), (0.052, 0.018), (0.052, -0.018)):
        screw(lp, (x, y, 0.0), length=0.01, r=0.0018, head_r=0.004)
    lp.cyl(0.006, 0.004, "glass", segs=16, z0=0.0, loc=(0.045, -0.01, 0))
    lp.box((0.2, 0.02, 0.004), "alu", loc=(0.16, 0, -0.006))
    c.part("levelling_plate", lp, explode=(0, 0, -0.04), desc="Levelling plate with bubble level + mounting arm.")
    cb = MB()
    cable(cb, [(0, 0, 0.004), (0, 0.02, 0.004), (0.06, 0.03, 0.0), (0.14, 0.01, -0.01)], r=0.002)
    c.part("cable", cb, explode=(0, 0, -0.06), desc="Signal cable.")
    return c


# ─────────────────────────────── substrate sensor ───────────────────────────────
def substrate_sensor(cid="substrate_sensor", title="Substrate sensor (moisture / EC / temp)"):
    c = Component(
        cid, title, "Sensors",
        summary="Pushed into a slab: measures water content, pore-water EC and root temperature.",
        how=("The three needles form a capacitor. Water has a very high dielectric constant (≈80) vs coco (≈3) and air (1), "
             "so the sensor's capacitance tracks volumetric water content. The same needles measure EC; a thermistor in "
             "the head reads root-zone temperature. Used together with the slab scale – scale for quantity, this for EC "
             "and distribution."),
        sensors=("self",), control="RS485 Modbus → ESP32 node → MQTT.",
        state={"vwc_pct": 62, "pore_ec": 4.1, "root_temp_c": 21.8},
        real="METER TEROS 12-class 3-needle sensor (budget: RS485 3-in-1 soil sensor)", cost="₹4–30k")
    hd = MB()
    hd.box((0.055, 0.018, 0.035), "epoxy_black", bevel=0.005)
    hd.text("SUB 02", 0.006, "sticker_white", loc=(0, -0.0092, 0.004), rot=(90, 0, 0), bold=True)
    c.part("head", hd, desc="Epoxy head (electronics + thermistor inside).")
    nd = MB()
    for x in (-0.018, 0.0, 0.018):
        nd.lathe([(0.0, -0.055), (0.0012, -0.053), (0.0017, -0.045), (0.0017, 0.0), (0.0, 0.0)], "stainless", segs=12,
                 loc=(x, 0, 0))
    c.part("needles", nd, loc=(0, 0, -0.0175), explode=(0, 0, -0.06), desc="3 stainless needles (5.5 cm) – the measuring field.")
    pcb = MB()
    pcb_with_chips(pcb, 0.045, 0.025, chips=((0.0, 0.0, 0.006, 0.006), (0.014, 0.0, 0.003, 0.003)), rot=(90, 0, 0))
    c.part("electronics", pcb, loc=(0, 0.0, 0.0), explode=(0, -0.05, 0.03), desc="Measurement electronics (sealed in epoxy).")
    cb = MB()
    cable(cb, [(0, 0, 0.0175), (0, 0, 0.04), (0.04, 0, 0.07), (0.12, 0, 0.08)], r=0.0025)
    c.part("cable", cb, explode=(0, 0, 0.05), desc="RS485 cable.")
    return c


# ─────────────────────────────── ultrasonic level sensor ───────────────────────────────
def level_sensor(cid="level_sensor", title="Ultrasonic level sensor"):
    c = Component(
        cid, title, "Sensors",
        summary="Looks down into a tank and measures the distance to the water surface → litres left.",
        how=("A piezo transducer sends a 40 kHz ultrasonic ping; the echo from the water surface comes back after "
             "t seconds. Distance = speed of sound × t ÷ 2 (temperature-corrected). Level = tank height − distance. "
             "No contact with the water, so no fouling. A separate float switch is the hard-wired backup."),
        sensors=("self",), control="UART → ESP32 node → MQTT; PLC gets the LOW alarm. Low level → PLC blocks the pump; AI plans refills.",
        state={"distance_mm": 312, "level_pct": 72},
        real="DFRobot A02YYUW waterproof ultrasonic sensor (IP67, 3–450 cm, ±1 cm, UART)", cost="≈₹1.7k (Robu)")
    hs = MB()
    hs.lathe([(0.0, 0.0), (0.0195, 0.0), (0.0195, 0.036), (0.016, 0.042), (0.0, 0.043)], "plastic_black", segs=40)
    hs.cyl(0.013, 0.022, "plastic_black", segs=24, z0=-0.022)
    for k in range(6):
        hs.torus(0.0135, 0.0009, "plastic_black", segs=24, rsegs=6, loc=(0, 0, -0.004 - 0.003 * k))
    hs.text("DFRobot", 0.006, "sticker_white", depth=0.0003, bold=True, loc=(0, 0, 0.0433))
    c.part("housing", hs, desc="Black IP67 probe housing, mounted through the tank lid.")
    tr = MB()
    tr.cyl(0.011, 0.004, "plastic_white", segs=32, z0=0.0)
    tr.cyl(0.006, 0.002, "silicone", segs=24, z0=0.004)
    c.part("transducer", tr, loc=(0, 0, -0.026), explode=(0, 0, -0.06), desc="Piezo transducer face – sends/receives the ping.")
    pc = MB()
    pcb_with_chips(pc, 0.03, 0.03, chips=((0.0, 0.0, 0.006, 0.006),))
    c.part("pcb", pc, loc=(0, 0, 0.02), explode=(0, 0, 0.08), desc="Timing + temperature-compensation electronics.")
    nt = MB()
    nt.cyl(0.02, 0.008, "plastic_black", segs=6, z0=0.0)
    c.part("lock_nut", nt, loc=(0, 0, -0.016), explode=(0, 0, -0.03), desc="Lock nut.")
    cb = MB()
    cable(cb, [(0, 0, 0.05), (0, 0, 0.08), (0.04, 0, 0.11), (0.12, 0, 0.12)], r=0.003)
    c.part("cable", cb, explode=(0, 0, 0.1), desc="4–20 mA cable.")
    return c


# ─────────────────────────────── weather station ───────────────────────────────
def weather_station(cid="weather_station", title="Outdoor weather station"):
    c = Component(
        cid, title, "Sensors",
        summary="Outside conditions the climate controller plans with: sun, wind, rain, temperature, humidity.",
        how=("Solar radiation (pyranometer) drives irrigation timing and shading. Wind speed/direction decide how far the "
             "roof vent may open (storm protection). Rain closes the vent. Outside T/RH + the weather forecast let the "
             "AI pre-cool or pre-close before conditions change."),
        sensors=("pyranometer", "cup anemometer", "wind vane", "rain gauge", "T/RH in radiation shield"),
        control="RS485 → edge server. PLC gets a direct wind/rain contact for vent storm-closing (safety).",
        state={"solar_w_m2": 742, "wind_m_s": 3.1, "wind_dir": "SW", "rain": False, "temp_c": 31.2, "rh_pct": 48},
        real="Davis Vantage Pro2-class / RS485 all-in-one station + separate pyranometer", cost="₹20–60k")
    ms = MB()
    ms.cyl(0.024, 1.6, "galv", segs=24, z0=0.0)
    ms.box((0.3, 0.3, 0.01), "galv", loc=(0, 0, 0.005))
    ms.cyl(0.018, 0.9, "galv", segs=16, axis="X", loc=(0.0, 0, 1.45))
    c.part("mast", ms, desc="Galvanised mast + cross-arm.")
    an = MB()
    an.cyl(0.012, 0.12, "plastic_white", segs=20, z0=0.0)
    an.cyl(0.02, 0.02, "plastic_white", segs=20, z0=0.12)
    for x, y, a in radial(3, 0.075):
        an.cyl(0.003, 0.075, "plastic_white", segs=8, axis="X", M=xform((0, 0, 0.13), (0, 0, a)) @ xform((0.037, 0, 0), (0, 90, 0)))
        an.lathe([(0.0, 0.0), (0.025, 0.012), (0.026, 0.014), (0.0, 0.004)], "plastic_white", segs=24,
                 M=xform((x, y, 0.13), (0, 0, a)) @ xform(rot=(90, 0, 0)))
    c.part("anemometer", an, loc=(0.4, 0, 1.47), explode=(0.1, 0, 0.25), desc="Cup anemometer – wind speed.")
    wv = MB()
    wv.cyl(0.01, 0.1, "plastic_white", segs=16, z0=0.0)
    wv.cyl(0.004, 0.3, "alu", segs=10, axis="X", loc=(0.0, 0, 0.12))
    wv.prism([(0.0, 0.0), (0.12, 0.0), (0.12, 0.07), (0.03, 0.02)], 0.004, "plastic_white", z0=-0.002,
             M=xform((-0.26, 0, 0.12), (90, 0, 0)))
    wv.cyl(0.012, 0.04, "plastic_white", segs=16, axis="X", loc=(0.16, 0, 0.12))
    c.part("wind_vane", wv, loc=(-0.4, 0, 1.47), explode=(-0.1, 0, 0.25), desc="Wind vane – wind direction.")
    rs = MB()
    for k in range(7):
        rs.lathe([(0.02, 0.0), (0.075, -0.012), (0.075, -0.008), (0.02, 0.004)], "plastic_white", segs=36, closed=True,
                 loc=(0, 0, -0.022 * k))
    rs.cyl(0.004, 0.2, "stainless", segs=8, z0=-0.18, loc=(0.03, 0, 0))
    c.part("radiation_shield", rs, loc=(0.0, 0.12, 1.25), explode=(0, 0.25, 0), desc="Radiation shield with outside T/RH sensor.")
    py = MB()
    py.cyl(0.035, 0.025, "plastic_white", segs=32, z0=0.0)
    py.sphere(0.015, "glass", segs=24, rings=12, loc=(0, 0, 0.025))
    py.cyl(0.01, 0.006, "chip", segs=16, z0=0.024)
    c.part("pyranometer", py, loc=(0.0, -0.12, 1.47), explode=(0, -0.2, 0.2), desc="Pyranometer – total solar radiation (W/m²).")
    rg = MB()
    rg.lathe([(0.0, 0.0), (0.08, 0.0), (0.08, 0.2), (0.075, 0.2), (0.02, 0.17), (0.0, 0.17)], "plastic_white", segs=40)
    rg.box((0.16, 0.04, 0.02), "galv", loc=(0, 0.09, 0.05))
    c.part("rain_gauge", rg, loc=(0.0, 0.0, 0.9), rot=(0, 0, 0), explode=(0.0, -0.3, 0), desc="Rain gauge (tipping bucket inside).")
    sp = MB()
    sp.box((0.3, 0.22, 0.02), "alu", bevel=0.003)
    sp.box((0.28, 0.2, 0.004), "pcb_blue", loc=(0, 0, 0.011))
    for i in range(1, 4):
        sp.box((0.28, 0.002, 0.005), "alu", loc=(0, -0.1 + 0.05 * i, 0.012))
    c.part("solar_panel", sp, loc=(0.0, -0.12, 0.7), rot=(-45, 0, 0), explode=(0, -0.3, 0), desc="Solar panel + battery (runs without mains).")
    lg = MB()
    lg.box((0.18, 0.1, 0.22), "plastic_white", bevel=0.01)
    lg.cyl(0.004, 0.18, "plastic_black", segs=8, z0=0.11, loc=(0.06, 0, 0))
    c.part("logger", lg, loc=(0.0, 0.08, 0.45), explode=(0, 0.3, 0), desc="Data logger + RS485/radio link.")
    return c


# ─────────────────────────────── sticky trap camera ───────────────────────────────
def sticky_trap_cam(cid="sticky_trap_cam", title="Sticky-trap pest camera"):
    c = Component(
        cid, title, "Sensors",
        summary="Photographs a yellow sticky card twice a day; AI counts whitefly, thrips, aphids and moths.",
        how=("Flying pests are attracted to yellow and stick to the card. A camera with a ring light takes a sharp photo "
             "at fixed times. A small object detector (YOLO-class) counts insects per species and compares with "
             "yesterday. A jump in counts on one trap = local outbreak → alert with the trap's location on the map."),
        sensors=("12 MP camera", "LED ring light", "battery voltage"),
        control=("18650 cell + TPL5110 timer: wakes every hour, one photo, Wi-Fi upload, powers off (~1 % awake, ~3 weeks "
                 "per charge). The edge Pi 5 + AI HAT+ counts the new catches per trap (tutorial 1, 14 Oct 2026)."),
        state={"whitefly": 23, "thrips": 4, "tuta_moth": 1, "trend_7d": "+40 %", "card_age_days": 9},
        real="DIY: Pi Zero 2 W + Camera Module 3 + TPL5110 + 18650 + LED ring + yellow card", cost="≈ ₹7k (DIY)")
    cd = MB()
    cd.box((0.25, 0.002, 0.1), "sticky", bevel=0.0008)
    rnd = random.Random(7)
    for _ in range(60):
        x, z = rnd.uniform(-0.115, 0.115), rnd.uniform(-0.045, 0.045)
        if rnd.random() < 0.7:
            cd.sphere(0.0011, "whitefly", segs=6, rings=3, squash=0.4, loc=(x, -0.0012, z), rot=(90, 0, 0))
        else:
            cd.box((0.0025, 0.0008, 0.001), "insect", loc=(x, -0.0012, z), rot=(0, rnd.uniform(0, 180), 0))
    c.part("sticky_card", cd, loc=(0, 0.0, 0.0), explode=(0, 0.06, 0.0),
           desc="Yellow sticky card (with trapped whitefly = white specks, thrips = dark lines). Replaced every ~2 weeks.")
    fr = MB()
    fr.box((0.27, 0.01, 0.006), "plastic_dark", loc=(0, 0, 0.053))
    fr.box((0.27, 0.01, 0.006), "plastic_dark", loc=(0, 0, -0.053))
    for sx in (-1, 1):
        fr.box((0.006, 0.01, 0.112), "plastic_dark", loc=(sx * 0.132, 0, 0))
    fr.box((0.01, 0.01, 0.5), "plastic_dark", loc=(0.0, 0.01, 0.3))
    fr.box((0.01, 0.2, 0.01), "plastic_dark", loc=(0.0, -0.09, 0.12))
    fr.box((0.01, 0.01, 0.07), "plastic_dark", loc=(0.0, -0.18, 0.085))
    fr.torus(0.015, 0.002, "stainless", segs=16, rsegs=6, axis="X", loc=(0.0, 0.01, 0.56))
    c.part("frame", fr, desc="Card frame + arm + hook for the crop wire.")
    cm = MB()
    cm.box((0.07, 0.05, 0.06), "plastic_white", bevel=0.006)
    cm.cyl(0.009, 0.006, "plastic_black", segs=24, axis="Y", loc=(0, 0.027, 0.0))
    cm.cyl(0.005, 0.002, "lens", segs=24, axis="Y", loc=(0, 0.031, 0.0))
    cm.torus(0.016, 0.002, "led_white", segs=24, rsegs=6, axis="Y", loc=(0, 0.026, 0.0))
    c.part("camera_unit", cm, loc=(0.0, -0.18, 0.02), explode=(0, -0.12, 0.0),
           desc="Camera + ring light unit (Pi Zero 2 W + Camera Module 3 inside).")
    pc = MB()
    pcb_with_chips(pc, 0.065, 0.03, chips=((0.0, 0.0, 0.008, 0.008), (0.02, 0.005, 0.005, 0.004)), rot=(90, 0, 0))
    pcb_with_chips(pc, 0.025, 0.024, m="pcb", chips=((0, 0, 0.008, 0.008),), loc=(0, 0.015, 0), rot=(90, 0, 0))
    c.part("electronics", pc, loc=(0.0, -0.19, 0.02), explode=(0, -0.2, -0.1), desc="Pi Zero 2 W + camera board.")
    sp = MB()
    sp.box((0.1, 0.08, 0.006), "alu", bevel=0.002)
    sp.box((0.095, 0.075, 0.002), "pcb_blue", loc=(0, 0, 0.003))
    c.part("solar_panel", sp, loc=(0.0, -0.18, 0.16), rot=(20, 0, 0), explode=(0, -0.12, 0.1), desc="Optional solar top-up panel (the 18650 alone lasts ~3 weeks).")
    return c


# ─────────────────────────────── fixed canopy camera ───────────────────────────────
def canopy_camera(cid="canopy_camera", title="Canopy camera (Hikvision 2 MP PoE bullet)"):
    """Hikvision DS-2CD1023G2-LIU 2 MP bullet: white body ~185 × 77 × 73 mm, sun shield, black face with lens and
    two white-light/IR LEDs, 3-axis bracket. Local +Y = looking direction (build rotates it to look down)."""
    c = Component(
        cid, title, "Cameras",
        summary="Looks down on a crop row from the roof truss: time-lapse of growth, canopy cover, wilting and colour.",
        how=("Every 15 min it takes a photo of the same view. Vision measures canopy cover %, colour changes (yellowing), "
             "and leaf droop in the afternoon (a fast sign of water stress). Cheap, always-on context for the robot's "
             "close-up images. Power and data come over one network cable (PoE)."),
        sensors=("2 MP 1/2.8\" CMOS, 4 mm lens, smart hybrid light (IR + white)",),
        control="PoE switch → edge server; image analysis on the Pi 5 + AI HAT+.",
        state={"canopy_cover_pct": 82, "wilting_index": 0.08, "last_image": "11:45"},
        real="Hikvision DS-2CD1023G2-LIU, 2 MP PoE bullet, IP67", cost="≈₹3k", view=(215, 14))
    bd = MB()
    bd.lathe([(0.0, -0.11), (0.03, -0.11), (0.034, -0.1), (0.035, 0.06), (0.036, 0.07), (0.0, 0.07)],
             "plastic_white", segs=40, M=xform(rot=(-90, 0, 0)) @ xform(scale=(1.0, 1.05, 1.0)))
    c.part("body", bd, desc="White IP67 aluminium/plastic body.")
    sh = MB()
    sh.add(bm_lathe([(0.041, -0.1), (0.041, 0.095)], 40, arc=math.pi * 0.8, phase=math.pi * 0.1), "plastic_white",
           M=xform(rot=(-90, 0, 0)) @ xform(rot=(0, 0, 180)))
    c.part("sun_shield", sh, explode=(0, 0, 0.06), desc="Sun shield.")
    fc = MB()
    fc.cyl(0.033, 0.004, "plastic_black", segs=40, axis="Y")
    fc.cyl(0.011, 0.005, "lens", segs=32, axis="Y", loc=(0, 0.002, 0.004))
    fc.tube(0.013, 0.011, 0.006, "plastic_dark", segs=32, axis="Y", loc=(0, 0.002, 0.004))
    for sx in (-1, 1):
        fc.cyl(0.006, 0.003, "led_white", segs=20, axis="Y", loc=(sx * 0.018, 0.001, -0.012))
    fc.text("HIKVISION", 0.0045, "sticker_white", depth=0.0003, bold=True, loc=(0, 0.0022, 0.024), rot=(-90, 0, 180))
    c.part("front_face", fc, loc=(0, 0.071, 0), explode=(0, 0.08, 0), desc="Lens (4 mm) + 2 smart-hybrid LEDs.")
    br = MB()
    # bracket behind the body: when the camera looks down (+Y → world −Z), local −Y is "up" towards the truss
    br.cyl(0.04, 0.008, "plastic_white", segs=40, axis="Y", loc=(0, -0.165, 0.048))   # truss base plate
    br.cyl(0.011, 0.07, "plastic_white", segs=20, axis="Y", loc=(0, -0.125, 0.048))
    br.sphere(0.014, "plastic_white", loc=(0, -0.09, 0.048))
    br.box((0.04, 0.07, 0.012), "plastic_white", bevel=0.003, loc=(0, -0.055, 0.04))
    c.part("bracket", br, explode=(0, -0.1, 0.04), desc="3-axis bracket that clamps to the roof truss.")
    cb = MB()
    cable(cb, [(0, -0.11, 0), (0, -0.14, 0), (0, -0.16, 0.05), (0, -0.2, 0.12)], r=0.003)
    c.part("poe_cable", cb, explode=(0, -0.08, 0), desc="PoE network cable (power + data).")
    return c
