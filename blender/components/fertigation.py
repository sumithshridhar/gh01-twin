"""Fertigation: fresh-water tank, stock tanks, peristaltic dosing pumps, mix tank, pH/EC probes, flow cell,
drain meter and slab weighing scale."""
import math

from gh import MB, TAU, Component, bm_lathe, fillet_path, xform
from parts import cable, helix, label_plate, radial, s_load_cell, screw


# ─────────────────────────────── fresh water tank ───────────────────────────────
def water_tank(cid="water_tank", title="Fresh-water tank (500 L)"):
    c = Component(
        cid, title, "Fertigation",
        summary="Buffer of clean water (borewell / rain / RO) for mixing nutrient solution and for the fog line.",
        how=("A mechanical float valve tops it up from the supply. An ultrasonic sensor on the lid measures the level "
             "continuously; a separate 2-point float switch is wired straight to the pump circuit so the pumps can never "
             "run dry, even if the computer or PLC fails."),
        sensors=("ultrasonic level sensor", "2-point float switch (hard-wired)", "water temperature"),
        control="Refill by mechanical float valve (+ optional solenoid). Low-low level cuts pumps in hardware.",
        state={"level_pct": 72, "volume_l": 360, "low_low": False},
        real="Sintex 500 L vertical tank (3-layer LLDPE) + brass float valve + reed float switch",
        cost="≈₹6k")
    R, H, t = 0.41, 0.95, 0.007
    prof = [(0.0, 0.0), (R - 0.03, 0.0), (R, 0.03)]
    for zr in (0.18, 0.36, 0.54, 0.72):
        prof += [(R, zr - 0.03), (R + 0.012, zr - 0.012), (R + 0.012, zr + 0.012), (R, zr + 0.03)]
    prof += [(R, H - 0.03), (R - 0.05, H + 0.04), (0.23, H + 0.08), (0.2, H + 0.09), (0.2, H + 0.13),
             (0.19, H + 0.13), (0.19, H + 0.09 - t), (0.23 - t, H + 0.08 - t), (R - 0.05 - t, H + 0.04 - t),
             (R - t, H - 0.03), (R - t, 0.03), (R - 0.03, t), (0.0, t)]
    tk = MB()
    tk.lathe(prof, "tank_black", segs=64)
    tk.cyl(0.03, 0.06, "pvc_white", segs=24, axis="X", loc=(R + 0.02, 0, 0.07))  # tank adapter
    tk.text("Sintex", 0.06, "sticker_white", depth=0.0008, bold=True, loc=(0, -R - 0.009, 0.63), rot=(90, 0, 0))
    tk.text("500 L", 0.04, "sticker_white", depth=0.0008, bold=True, loc=(0, -R - 0.006, 0.45), rot=(90, 0, 0))
    c.part("tank_shell", tk, desc="3-layer LLDPE tank shell (black outside stops algae growth).")
    lid = MB()
    lid.lathe([(0.0, 0.0), (0.215, 0.0), (0.215, 0.035), (0.2, 0.045), (0.0, 0.05)], "tank_black", segs=48)
    for x, y, a in radial(12, 0.16):
        lid.box((0.08, 0.008, 0.012), "tank_black", bevel=0.002, loc=(x * 0.75, y * 0.75, 0.05), rot=(0, 0, a))
    c.part("lid", lid, loc=(0, 0, H + 0.12), explode=(0, 0, 0.45), desc="Screw lid – the level sensor mounts here.")
    wt = MB()
    wt.cyl(R - t - 0.002, 0.66, "water", segs=48, z0=0.0)
    c.part("water", wt, loc=(0, 0, t + 0.001), explode=(0, 0, 0.0),
           desc="Water level (live): 72 % ≈ 360 L.", smooth_angle=60)
    fs = MB()
    fs.cyl(0.006, 0.85, "stainless", segs=12, z0=-0.85)
    fs.cyl(0.018, 0.02, "pvc_white", segs=6, z0=0.0)
    for zf, col in ((-0.62, "plastic_orange"), (-0.8, "plastic_red")):
        fs.cyl(0.022, 0.04, col, segs=24, bevel=0.006, z0=zf)
        fs.cyl(0.024, 0.004, "stainless", segs=24, z0=zf - 0.006)
    cable(fs, [(0, 0, 0.02), (0, 0, 0.08), (0.08, 0, 0.12), (0.16, 0, 0.12)], r=0.003)
    c.part("float_switch", fs, loc=(-0.12, 0.08, H + 0.1), explode=(0, 0, 1.25),
           desc="2-point float switch: LOW → alarm, LOW-LOW → pump contactor opens (hard-wired, no software).")
    fv = MB()
    fv.cyl(0.018, 0.06, "brass", segs=6, axis="X", z0=0.0)
    fv.cyl(0.007, 0.25, "brass", segs=10, axis="-X", loc=(0.0, 0, 0))
    fv.sphere(0.07, "plastic_orange", segs=24, rings=12, loc=(-0.3, 0, -0.03))
    c.part("float_valve", fv, loc=(R - 0.03, -0.05, H - 0.05), explode=(0.55, -0.3, 0.3),
           desc="Mechanical float valve – refills from the supply line and shuts when full.")
    bv = MB()
    bv.cyl(0.024, 0.07, "brass", segs=6, axis="X", z0=0)
    bv.cyl(0.02, 0.03, "brass", segs=24, loc=(0.035, 0, 0.0))
    bv.box((0.09, 0.012, 0.008), "plastic_blue", bevel=0.003, loc=(0.035, -0.03, 0.03), rot=(0, 0, -20))
    c.part("outlet_valve", bv, loc=(R + 0.05, 0, 0.07), explode=(0.25, 0, 0),
           desc="Manual outlet ball valve (service isolation).")
    return c


# ─────────────────────────────── stock tank ───────────────────────────────
def stock_tank(cid="stock_A", title="Stock tank A (60 L)", label="A", note="Calcium nitrate + iron chelate (A)",
               color="hdpe_white"):
    c = Component(
        cid, title, "Fertigation",
        summary=f"Concentrated nutrient stock: {note}. Diluted ~100× by the dosing pump.",
        how=("Fertilisers are split into A and B tanks so calcium never meets sulphate/phosphate at high concentration "
             "(they would form insoluble gypsum/phosphate sludge). A suction lance feeds the peristaltic pump; a "
             "low-level float warns before the tank runs empty."),
        sensors=("low-level float on lance",),
        control="Read by PLC; dosing pumps stop and alarm when low.",
        state={"level_pct": 64, "concentration": "100×"},
        real="60 L HDPE drum + suction lance with foot filter and low-level float", cost="₹1.5–2.5k")
    R, H = 0.19, 0.56
    d = MB()
    d.lathe([(0.0, 0.0), (R - 0.02, 0.0), (R, 0.02), (R, 0.08), (R - 0.006, 0.1), (R, 0.12), (R, H - 0.1),
             (R - 0.006, H - 0.08), (R, H - 0.06), (R, H - 0.02), (R - 0.03, H), (0.07, H), (0.07, H + 0.02),
             (0.065, H + 0.02), (0.065, H - 0.005), (R - 0.036, H - 0.006), (R - 0.006, H - 0.024),
             (R - 0.006, 0.02), (R - 0.022, 0.006), (0.0, 0.006)], color, segs=48)
    d.add(bm_lathe([(R + 0.0015, H * 0.42), (R + 0.0015, H * 0.7)], 24, arc=math.radians(60),
                   phase=math.radians(-120)), "sticker_yellow" if label == "pH-" else "sticker_white")
    d.text(label, 0.09, "plastic_black", depth=0.002, loc=(0, -R - 0.004, H * 0.56), rot=(90, 0, 0), bold=True)
    c.part("drum", d, desc=f"HDPE drum with stock solution ({note}).")
    liq = MB()
    liq.cyl(R - 0.008, H * 0.6, "nutrient", segs=40, z0=0.0)
    c.part("solution", liq, loc=(0, 0, 0.007), desc="Stock solution level (live).", smooth_angle=60)
    cap = MB()
    cap.lathe([(0.0, 0.0), (0.075, 0.0), (0.075, 0.03), (0.0, 0.032)], "plastic_black", segs=40)
    cap.cyl(0.005, 0.03, "pvc_white", segs=12, z0=0.03, loc=(0.03, 0, 0))
    c.part("cap", cap, loc=(0, 0, H + 0.005), explode=(0, 0, 0.18), desc="Cap with lance entry.")
    ln = MB()
    ln.cyl(0.005, H, "pvc_white", segs=12, z0=-H)
    ln.cyl(0.016, 0.05, "plastic_black", segs=20, bevel=0.003, z0=-H)  # foot filter
    ln.cyl(0.014, 0.03, "plastic_orange", segs=20, bevel=0.004, z0=-H + 0.08)  # low-level float
    cable(ln, [(0.0, 0.0, 0.03), (0.0, 0.0, 0.1), (0.08, 0, 0.16)], r=0.003, m="pe_black", fillet=0.05)
    c.part("suction_lance", ln, loc=(0.03, 0, H + 0.03), explode=(0, 0, 0.7),
           desc="Suction lance: foot filter + low-level float. Feeds the dosing pump.")
    return c


# ─────────────────────────────── peristaltic dosing pump ───────────────────────────────
def dosing_pump(cid="dosing_pump_A", title="Peristaltic dosing pump", liquid="stock A"):
    c = Component(
        cid, title, "Fertigation",
        summary=f"Doses exact millilitres of {liquid} into the mix tank.",
        how=("A motor turns a rotor with 3 rollers that squeeze a flexible tube against a curved track. Each roller "
             "pushes a fixed pocket of liquid, so volume = revolutions × mL/rev. The liquid only touches the tube – "
             "no valves to corrode. Calibrate mL/rev once a month."),
        sensors=("EC/pH in the mix tank confirm the dose",),
        control="PLC output (PWM / step). Max mL per batch enforced in the PLC.",
        state={"running": False, "ml_per_rev": 1.6, "dosed_today_ml": 780},
        real="24 V DC peristaltic pump, 3-roller head, Norprene tube (Kamoer / Williamson class)", cost="₹2–6k")
    hs = MB()
    hs.box((0.09, 0.08, 0.1), "plastic_white", bevel=0.006)
    hs.box((0.03, 0.002, 0.012), "led_green", loc=(0.025, -0.041, -0.038))
    c.part("housing", hs, desc="Pump housing (driver electronics inside).")
    hd = MB()
    hd.box((0.078, 0.03, 0.09), "plastic_dark", bevel=0.004)
    hd.cyl(0.03, 0.001, "plastic_black", segs=40, axis="-Y", loc=(0, -0.0155, 0.008))
    hd.add(bm_lathe([(0.0315, 0.0), (0.037, 0.0), (0.037, 0.012), (0.0315, 0.012)], 40, closed=True,
                    arc=math.pi * 1.25, phase=-math.pi * 0.125),
           "plastic_dark", M=xform((0, -0.015, 0.008)) @ xform(rot=(90, 0, 0)))
    c.part("pump_head", hd, loc=(0, -0.055, 0), explode=(0, -0.06, 0),
           desc="Pump head with the curved track the tube is squeezed against.")
    ro = MB()
    ro.cyl(0.021, 0.003, "plastic_black", segs=36, axis="-Y", loc=(0, 0.004, 0))
    ro.cyl(0.021, 0.003, "plastic_black", segs=36, axis="-Y", loc=(0, -0.006, 0))
    for x, z, _ in radial(3, 0.018, start=0.5):
        ro.cyl(0.0065, 0.011, "stainless", segs=20, axis="-Y", loc=(x, 0, z))
    ro.cyl(0.004, 0.016, "stainless", segs=12, axis="-Y", loc=(0, 0.004, 0))
    c.part("rotor", ro, loc=(0, -0.076, 0.008), explode=(0, -0.11, 0),
           desc="Rotor with 3 rollers – each roller pushes a pocket of liquid along the tube.")
    tb = MB()
    arc = [(0.028 * math.cos(math.radians(a)), 0.0, 0.028 * math.sin(math.radians(a))) for a in range(200, -21, -8)]
    pts = [(-0.03, 0, -0.07), (-0.03, 0, -0.03)] + arc + [(0.03, 0, -0.03), (0.03, 0, -0.07)]
    tb.sweep(fillet_path(pts, 0.01), 0.0035, "norprene", segs=12)
    for sx in (-1, 1):
        tb.cyl(0.0042, 0.018, "plastic_white", segs=12, loc=(sx * 0.03, 0, -0.078))
    c.part("tube", tb, loc=(0, -0.076, 0.008), explode=(0, -0.16, 0),
           desc="Norprene tube – the only part the liquid touches (replace yearly).")
    cv = MB()
    cv.box((0.076, 0.003, 0.088), "acrylic", bevel=0.003)
    c.part("cover", cv, loc=(0, -0.087, 0), explode=(0, -0.2, 0), desc="Clear front cover.")
    mo = MB()
    mo.cyl(0.018, 0.05, "alu", segs=32, bevel=0.002, axis="Y", z0=0.0)
    mo.cyl(0.02, 0.02, "steel_dark", segs=32, axis="Y", z0=-0.005)
    cable(mo, [(0.0, 0.055, 0.0), (0.0, 0.07, 0.0), (0.02, 0.09, -0.04)], r=0.002, m="wire_red")
    c.part("motor_gearbox", mo, loc=(0, 0.04, 0), explode=(0, 0.1, 0), desc="24 V DC motor + gearbox.")
    return c


# ─────────────────────────────── mix tank ───────────────────────────────
def mix_tank(cid="mix_tank", title="Nutrient mix tank (200 L blue drum)"):
    """200 L open-top HDPE drum (Ø 580 × 935 mm, two rolling hoops) with a clamp-ring lid and a 24 V circulation
    pump inside that stirs the batch."""
    c = Component(
        cid, title, "Fertigation",
        summary="Where fresh water + stock A + stock B + acid are mixed into the final feed recipe.",
        how=("Fill with fresh water → dosing pumps add A, B and acid in small steps → the circulation pump stirs the "
             "drum → the pH/EC flow cell checks the result → repeat until on target (e.g. EC 3.0, pH 5.8). Batch mixing "
             "is slower than in-line injection but far safer for a first system: a mistake stays in the drum, not on "
             "the plants."),
        sensors=("ultrasonic level", "pH + EC + temperature (flow cell)"),
        control="PLC runs the fill/dose/mix sequence; AI only sets the EC/pH target per crop stage.",
        state={"level_pct": 58, "ec_ms_cm": 3.02, "ph": 5.84, "recipe": "fruiting-v3"},
        real="200 L open-top blue HDPE drum with clamp ring + 24 V brushless circulation pump", cost="≈₹4.5k")
    R, H, t = 0.29, 0.935, 0.006
    prof = [(0.0, 0.0), (R - 0.03, 0.0), (R, 0.03)]
    for zr in (H * 0.33, H * 0.66):         # two rolling hoops
        prof += [(R, zr - 0.03), (R + 0.012, zr - 0.012), (R + 0.012, zr + 0.012), (R, zr + 0.03)]
    prof += [(R, H - 0.02), (R + 0.01, H), (R - t, H), (R - t, 0.03), (R - 0.03, t), (0.0, t)]
    tk = MB()
    tk.lathe(prof, "hdpe_blue", segs=64)
    tk.cyl(0.025, 0.05, "pvc_white", segs=24, axis="X", loc=(R + 0.015, 0, 0.06))
    tk.add(bm_lathe([(R + 0.0015, H * 0.4), (R + 0.0015, H * 0.58)], 24, arc=math.radians(50),
                    phase=math.radians(-115)), "sticker_white")
    tk.text("MIX 200 L", 0.042, "plastic_blue", depth=0.0008, loc=(0, -R - 0.004, H * 0.49), rot=(90, 0, 0), bold=True)
    c.part("drum", tk, desc="200 L food-grade HDPE drum (blue keeps light out: no algae).")
    lq = MB()
    lq.cyl(R - t - 0.002, 0.52, "nutrient", segs=48, z0=0.0)
    c.part("solution", lq, loc=(0, 0, t + 0.001), desc="Feed solution (live level / EC / pH).", smooth_angle=60)
    lid = MB()
    lid.lathe([(0.0, 0.0), (R + 0.012, 0.0), (R + 0.012, 0.022), (R - 0.02, 0.03), (0.0, 0.034)], "hdpe_blue", segs=64)
    lid.torus(R + 0.014, 0.008, "galv", segs=64, rsegs=8, loc=(0, 0, 0.004))           # clamp ring
    lid.box((0.05, 0.03, 0.03), "galv", bevel=0.004, loc=(R + 0.02, 0, 0.004))           # ring lever
    for x, a in ((0.1, 0), (-0.1, 0)):
        lid.cyl(0.012, 0.02, "pvc_white", segs=16, z0=0.02, loc=(x, 0.06, 0))            # tube glands
    c.part("lid", lid, loc=(0, 0, H), explode=(0, 0, 0.45), desc="Clamp-ring lid with glands for the dosing tubes.")
    mp = MB()
    mp.cyl(0.035, 0.06, "plastic_black", segs=32, bevel=0.005, z0=0.0)
    mp.cyl(0.01, 0.07, "pvc_white", segs=16, axis="X", loc=(0.06, 0, 0.03))
    cable(mp, [(-0.02, 0, 0.06), (-0.02, 0, 0.3), (-0.05, 0.02, 0.75), (-0.08, 0.06, 0.95)], r=0.003)
    c.part("mixing_pump", mp, loc=(-0.12, 0, t + 0.002), explode=(0, 0, 1.0),
           desc="24 V brushless circulation pump on the floor of the drum: stirs the batch before measuring.")
    return c


# ─────────────────────────────── pH / EC probes ───────────────────────────────
def ph_probe(cid="ph_probe", title="pH probe (lab-grade, gel)"):
    c = Component(
        cid, title, "Sensors",
        summary="Measures acidity of the feed. Tomatoes in coco want pH 5.5–6.0.",
        how=("A thin glass bulb develops a voltage that depends on the hydrogen-ion concentration (~59 mV per pH unit). "
             "A reference electrode (Ag/AgCl in KCl gel) gives the fixed comparison voltage through a porous junction. "
             "An isolated circuit (so EC current cannot disturb it) converts mV → pH. Calibrate monthly with pH 4 / 7 buffers."),
        sensors=("self", "temperature for compensation"),
        control="Read by the edge server + PLC. PLC blocks irrigation if pH < 4.8 or > 7.0.",
        state={"ph": 5.84, "mv": 68, "last_calibration": "2026-09-01", "drift_warning": False},
        real="Atlas Scientific-class lab-grade pH probe + isolated EZO circuit, BNC", cost="₹8–15k")
    bd = MB()
    bd.lathe([(0.0, 0.0), (0.0055, 0.0), (0.006, 0.004), (0.006, 0.115), (0.0065, 0.12), (0.0065, 0.13),
              (0.0, 0.13)], "epoxy_black", segs=32)
    bd.text("pH", 0.006, "sticker_white", loc=(0, -0.0062, 0.09), rot=(90, 0, 0), bold=True)
    c.part("body", bd, loc=(0, 0, 0.012), desc="Epoxy body.")
    gb = MB()
    gb.lathe([(0.0, -0.012), (0.003, -0.0115), (0.0048, -0.008), (0.0052, -0.004), (0.0045, 0.0), (0.0045, 0.013),
              (0.0, 0.013)], "glass", segs=32)
    c.part("glass_bulb", gb, loc=(0, 0, 0.0), explode=(0, 0, -0.04),
           desc="Glass membrane bulb – the pH-sensitive part. Never let it dry out.")
    ag = MB()
    ag.cyl(0.0006, 0.1, "stainless", segs=8, z0=0.0)
    ag.sphere(0.0015, "brass", segs=12, rings=6)
    c.part("ag_agcl_wire", ag, loc=(0, 0, -0.004), explode=(0.03, 0, -0.01), desc="Internal Ag/AgCl electrode wire.")
    jn = MB()
    jn.cyl(0.0012, 0.003, "plastic_white", segs=10, axis="-Y")
    c.part("reference_junction", jn, loc=(0, -0.0058, 0.02), explode=(0, -0.03, 0),
           desc="Porous ceramic junction – lets the reference electrolyte touch the sample.")
    cp = MB()
    cp.cyl(0.0068, 0.018, "plastic_black", segs=24, bevel=0.001, z0=0.0)
    cable(cp, [(0, 0, 0.018), (0, 0, 0.05), (0.03, 0, 0.09), (0.07, 0, 0.1)], r=0.0022)
    cp.cyl(0.0055, 0.018, "chrome", segs=16, axis="X", loc=(0.08, 0, 0.1))
    c.part("cap_cable_bnc", cp, loc=(0, 0, 0.142), explode=(0, 0, 0.05), desc="Cap, cable and BNC connector.")
    sc = MB()
    sc.lathe([(0.0, 0.0), (0.009, 0.0), (0.009, 0.03), (0.0068, 0.031), (0.0068, 0.004), (0.0, 0.004)],
             "acrylic", segs=32, closed=True)
    c.part("storage_cap", sc, loc=(0, 0, -0.016), explode=(0, 0, -0.085),
           desc="Storage cap with KCl solution (removed when installed in the flow cell).")
    return c


def ec_probe(cid="ec_probe", title="EC probe (K 1.0)"):
    c = Component(
        cid, title, "Sensors",
        summary="Measures total dissolved fertiliser (electrical conductivity). Tomato feed: EC 2.5–3.5 mS/cm.",
        how=("An AC current is passed between two electrodes a fixed distance apart. More dissolved salts → more "
             "current → higher EC. AC (not DC) prevents electrode plating. Readings are corrected to 25 °C. "
             "EC says 'how much', not 'which' nutrient – so a lab analysis is still needed every few weeks."),
        sensors=("self", "temperature for compensation"),
        control="Dosing loop target; PLC blocks irrigation if EC < 0.8 or > 4.5 mS/cm.",
        state={"ec_ms_cm": 3.02, "temp_c": 23.4},
        real="K 1.0 conductivity probe + isolated EZO-EC circuit", cost="₹8–15k")
    bd = MB()
    bd.lathe([(0.0, 0.0), (0.0075, 0.0), (0.0075, 0.12), (0.008, 0.125), (0.008, 0.135), (0.0, 0.135)],
             "epoxy_black", segs=36)
    bd.text("EC", 0.006, "sticker_white", loc=(0, -0.0077, 0.09), rot=(90, 0, 0), bold=True)
    c.part("body", bd, loc=(0, 0, 0.02), desc="Epoxy body.")
    gd = MB()
    gd.lathe([(0.0068, 0.0), (0.0075, 0.0), (0.0075, 0.022), (0.0068, 0.022)], "epoxy_black", segs=36, closed=True)
    c.part("guard", gd, loc=(0, 0, -0.002), explode=(0, 0, -0.03), desc="Open guard sleeve (lets solution flow between electrodes).")
    el = MB()
    for sx in (-1, 1):
        el.box((0.0015, 0.006, 0.016), "steel_dark", loc=(sx * 0.0025, 0, 0.0))
    c.part("electrodes", el, loc=(0, 0, 0.012), explode=(0, 0, -0.065), desc="Two graphite electrodes, fixed spacing (cell constant K = 1.0).")
    cp = MB()
    cp.cyl(0.0085, 0.016, "plastic_black", segs=24, bevel=0.001, z0=0.0)
    cable(cp, [(0, 0, 0.016), (0, 0, 0.05), (0.03, 0, 0.09), (0.07, 0, 0.1)], r=0.0022)
    c.part("cap_cable", cp, loc=(0, 0, 0.155), explode=(0, 0, 0.05), desc="Cap + cable to the isolated EC circuit.")
    return c


def flow_cell(cid="sensor_flow_cell", title="pH / EC flow cell panel"):
    c = Component(
        cid, title, "Sensors",
        summary="A clear block where a side-stream of the feed flows past the pH, EC and temperature probes.",
        how=("Measuring in a flow cell (not in the tank) gives fresh, bubble-free samples and lets you take probes out "
             "for calibration without draining anything. Each probe has its own electrically isolated circuit so they "
             "don't interfere."),
        sensors=("pH probe", "EC probe", "DS18B20 temperature"),
        control="Circuits talk I²C to an ESP32 node → MQTT; copies to the PLC for safety limits.",
        state={"sample_flow_l_min": 0.5},
        real="Acrylic 3-port flow cell + 2 isolated EZO carriers (Atlas Scientific style)", cost="₹6–10k")
    pn = MB()
    pn.box((0.36, 0.012, 0.26), "pvc_white", bevel=0.003)
    c.part("panel", pn, loc=(0, 0.03, 0.08), desc="Mounting panel.")
    blk = MB()
    blk.box((0.2, 0.05, 0.05), "acrylic", bevel=0.004)
    for k, x in enumerate((-0.06, 0.0, 0.06)):
        blk.cyl(0.011, 0.02, "plastic_black", segs=6, z0=0.025, loc=(x, 0, 0))
    for sx in (-1, 1):
        blk.cyl(0.006, 0.03, "pvc_white", segs=16, axis="X", loc=(sx * 0.11, 0, -0.01))
    c.part("acrylic_block", blk, desc="Clear acrylic block – sample flows in on the left, out on the right.")
    tp = MB()
    tp.cyl(0.003, 0.06, "stainless", segs=12, z0=-0.03)
    tp.cyl(0.005, 0.02, "plastic_black", segs=16, z0=0.03)
    cable(tp, [(0, 0, 0.05), (0, 0, 0.08), (0.02, 0.02, 0.11)], r=0.002)
    c.part("temp_probe", tp, loc=(0.06, 0, 0.03), explode=(0, -0.05, 0.12), desc="DS18B20 temperature probe (for EC/pH compensation).")
    bx = MB()
    bx.box((0.11, 0.05, 0.08), "plastic_dark", bevel=0.004)
    bx.box((0.1, 0.004, 0.07), "acrylic", loc=(0, -0.026, 0))
    for k in range(2):
        bx.box((0.035, 0.002, 0.03), "pcb_blue", loc=(-0.022 + 0.044 * k, -0.02, 0))
        bx.box((0.008, 0.003, 0.008), "chip", loc=(-0.022 + 0.044 * k, -0.022, 0.004))
    c.part("isolated_circuits", bx, loc=(0.1, 0.0, 0.15), explode=(0.1, -0.1, 0.05),
           desc="Isolated pH + EC circuits (galvanic isolation stops probe cross-talk).")
    return c


# ─────────────────────────────── drain meter (tipping bucket) ───────────────────────────────
def drain_meter(cid="drain_meter", title="Drain meter + drain EC (tipping bucket)"):
    c = Component(
        cid, title, "Fertigation",
        summary="Measures how much water drains out of the slabs, and its EC. Target: 20–30 % drain per day.",
        how=("Drain from the gutter falls into a see-saw bucket. When one side holds 50 mL it tips, empties and the other "
             "side starts filling; a magnet passes a reed switch at each tip → count × 50 mL = drain volume. Drain % = "
             "drain ÷ water given. Rising drain EC means salts are building up in the slab → give more water or lower EC."),
        sensors=("reed switch (tips)", "drain EC probe"),
        control="Feeds the irrigation planner (AI) – the main feedback for shot size.",
        state={"drain_pct_today": 24.5, "drain_ec": 3.9, "tips_today": 311},
        real="Tipping-bucket drain gauge (50 mL/tip) + EC cup", cost="₹5–12k")
    hs = MB()
    hs.box((0.26, 0.2, 0.012), "pvc_grey", bevel=0.002, loc=(0, 0, 0.006))
    for sx in (-1, 1):
        hs.box((0.012, 0.2, 0.3), "pvc_grey", bevel=0.002, loc=(sx * 0.125, 0, 0.15))
    hs.box((0.26, 0.012, 0.3), "pvc_grey", bevel=0.002, loc=(0, 0.095, 0.15))
    hs.box((0.24, 0.18, 0.03), "pvc_grey", loc=(0, 0, 0.03))
    hs.cyl(0.02, 0.05, "pvc_grey", segs=24, axis="Y", loc=(0, -0.12, 0.03))
    c.part("frame", hs, desc="Housing frame with outlet sump.")
    fn = MB()
    fn.lathe([(0.02, 0.0), (0.024, 0.0), (0.1, 0.07), (0.1, 0.09), (0.095, 0.09), (0.095, 0.072), (0.02, 0.004)],
             "pvc_white", segs=40, closed=True)
    c.part("funnel", fn, loc=(0, 0, 0.26), explode=(0, 0, 0.18), desc="Funnel from the gutter drain.")
    tb = c.group("tipping_bucket", loc=(0, 0, 0.16), explode=(0, 0, 0.06), desc="See-saw bucket: 50 mL per tip.")
    bk = MB()
    tri = [(-0.1, 0.05), (-0.1, 0.0), (0.0, -0.035), (0.1, 0.0), (0.1, 0.05), (0.095, 0.05), (0.095, 0.004),
           (0.004, -0.028), (0.004, 0.05), (-0.004, 0.05), (-0.004, -0.028), (-0.095, 0.004), (-0.095, 0.05)]
    bk.prism(tri, 0.14, "plastic_white", z0=-0.07, M=xform(rot=(90, 0, 0)))
    bk.cyl(0.004, 0.18, "stainless", segs=12, axis="Y", loc=(0, 0, -0.02))
    bk.box((0.01, 0.008, 0.008), "steel_dark", loc=(0.0, -0.072, -0.03))
    c.part("bucket", bk, parent=tb, rot=(0, 12, 0), desc="Two-sided bucket on a pivot.")
    rd = MB()
    rd.box((0.03, 0.01, 0.01), "plastic_black", bevel=0.002)
    rd.cyl(0.0015, 0.01, "glass", segs=8, axis="X", loc=(0, -0.006, 0))
    cable(rd, [(0.015, 0, 0), (0.05, 0, 0), (0.1, 0.05, 0.02)], r=0.002)
    c.part("reed_switch", rd, loc=(0.0, -0.085, 0.12), explode=(0, -0.1, 0), desc="Reed switch – counts tips.")
    ecc = MB()
    ecc.cyl(0.03, 0.06, "acrylic", segs=32, z0=0.0)
    ecc.cyl(0.0075, 0.1, "epoxy_black", segs=24, z0=0.02)
    c.part("drain_ec_cup", ecc, loc=(0.06, 0.02, 0.045), explode=(0.18, 0, 0.05), desc="Drain EC cup + probe.")
    return c


# ─────────────────────────────── slab weighing scale ───────────────────────────────
def slab_scale(cid="slab_scale", title="Slab weighing scale (load cells)"):
    c = Component(
        cid, title, "Sensors",
        summary="Weighs one slab with its 3 plants every few seconds – the most honest signal of how much water the crop used.",
        how=("The slab tray hangs on two S-type load cells. Weight goes up during an irrigation shot and falls as the "
             "plants transpire. The slope = water uptake (mL/min); the weight just before the first shot = how dry the "
             "slab got overnight. The AI planner uses this to size and time shots, and flags a slab whose uptake drops "
             "(early root problem)."),
        sensors=("2 × 50 kg S-type load cells", "24-bit weighing transmitter (HX711-class or industrial)"),
        control="ESP32 node → MQTT (10 s samples). Used as reference for the whole zone.",
        state={"weight_kg": 21.84, "uptake_ml_min": 6.2, "since_last_shot_g": -410},
        real="2 × Zemic H3G-C3-50kg S-beam load cells + weight transmitter + stainless gutter segment 1.2 m",
        cost="≈₹10k (cells ₹2.5k each)")
    fr = MB()
    for sx in (-1, 1):
        fr.box((0.04, 0.04, 0.7), "galv", bevel=0.003, loc=(sx * 0.62, 0, 0.35))
        fr.box((0.04, 0.3, 0.04), "galv", bevel=0.003, loc=(sx * 0.62, 0, 0.7))
        fr.box((0.25, 0.25, 0.006), "galv", loc=(sx * 0.62, 0, 0.003))
    c.part("stand", fr, desc="Galvanised stands (the scale is independent of the normal gutter).")
    lc = c.group("load_cells", explode=(0, -0.25, 0.05), desc="Two S-type load cells.")
    for sx in (-1, 1):
        m = MB()
        s_load_cell(m)                                        # Zemic H3G-C3-50kg: 2" × 3" × ½" S-beam
        m.cyl(0.006, 0.022, "stainless", segs=12, z0=0.038)   # M12 rod ends top and bottom
        m.cyl(0.006, 0.022, "stainless", segs=12, z0=-0.06)
        cable(m, [(0.025, 0, 0.0), (0.05, 0, 0.0), (0.1, 0.05, 0.02)], r=0.002)
        c.part(f"load_cell_{'L' if sx < 0 else 'R'}", m, parent=lc, loc=(sx * 0.58, 0, 0.64),
               desc="S-type load cell: a strain gauge bridge that stretches under load.")
    tr = MB()

    prof = [(-0.13, 0.06), (-0.13, 0.0), (-0.1, -0.02), (0.1, -0.02), (0.13, 0.0), (0.13, 0.06), (0.125, 0.06),
            (0.125, 0.003), (0.098, -0.015), (-0.098, -0.015), (-0.125, 0.003), (-0.125, 0.06)]
    tr.prism(prof, 1.2, "stainless", z0=-0.6, M=xform(rot=(0, 90, 0)) @ xform(rot=(0, 0, 90)))
    for sx in (-1, 1):
        tr.box((0.02, 0.28, 0.01), "stainless", loc=(sx * 0.58, 0, 0.07))
    c.part("weighing_gutter", tr, loc=(0, 0, 0.52), explode=(0, 0, -0.12), desc="Stainless weighing gutter segment.")
    sl = MB()
    sl.box((1.0, 0.2, 0.075), "slab_film", bevel=0.012)
    for x in (-0.33, 0.0, 0.33):
        sl.box((0.1, 0.1, 0.075), "rockwool", bevel=0.004, loc=(x, 0, 0.065))
    c.part("slab_with_cubes", sl, loc=(0, 0, 0.54), explode=(0, 0, 0.3), desc="Coco slab + 3 plant cubes being weighed.")
    jb = MB()
    jb.box((0.12, 0.06, 0.08), "plastic_dark", bevel=0.004)
    jb.cyl(0.006, 0.012, "plastic_black", segs=6, z0=-0.052, loc=(0.03, 0, 0))
    jb.cyl(0.006, 0.012, "plastic_black", segs=6, z0=-0.052, loc=(-0.03, 0, 0))
    c.part("weighing_transmitter", jb, loc=(0.62, -0.08, 0.43), explode=(0.2, -0.2, 0), desc="24-bit weighing transmitter → ESP32.")
    return c
