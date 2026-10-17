"""Irrigation hardware: zone valve, dripper + stake, disc filter, flow meter, pressure transmitter + gauge, pump."""
import math

from gh import MB, TAU, Component, bm_lathe, fillet_path, xform
from parts import cable, dial, helix, motor_x, screw, vane


# ─────────────────────────────── solenoid zone valve ───────────────────────────────
def solenoid_valve(cid="zone_valve", title="Zone solenoid valve (1\")"):
    c = Component(
        cid, title, "Irrigation",
        summary="Opens or closes water to one crop row. One valve per zone, 24 V AC.",
        how=("Water pressure holds the rubber diaphragm shut. When the PLC energises the solenoid, the plunger lifts, "
             "water above the diaphragm bleeds to the outlet, the pressure drops and the diaphragm lifts – the valve opens. "
             "De-energise → plunger closes the bleed port → pressure builds on top → diaphragm seals again."),
        sensors=("flow meter confirms flow", "pressure transmitter confirms pressure"),
        control="PLC relay output (24 V AC). AI only requests a shot; PLC checks limits then switches.",
        state={"open": False, "coil_current_mA": 0, "last_shot_ml": 180},
        real="Hunter PGV / Rain Bird 100-DV class, 1\" BSP, 24 V AC, normally closed",
        cost="₹1.5–3k")
    b = MB()
    b.tube(0.019, 0.0145, 0.104, "plastic_black", segs=40, axis="X")
    for sx in (-1, 1):
        b.tube(0.0225, 0.0145, 0.02, "plastic_black", segs=6, axis="X", loc=(sx * 0.062, 0, 0), rot=(30, 0, 0))
        b.tube(0.0165, 0.0135, 0.004, "plastic_dark", axis="X", loc=(sx * 0.0705, 0, 0))  # thread start
        b.cyl(0.0146, 0.002, "plastic_dark", axis="X", loc=(sx * 0.035, 0, 0))  # inner seat wall
    b.lathe([(0, -0.024), (0.03, -0.024), (0.038, -0.016), (0.041, 0.0), (0.042, 0.018), (0.044, 0.02),
             (0.044, 0.024), (0.0, 0.024)], "plastic_black", segs=48)
    for x, y, _ in [(0.042 * math.cos(TAU * a / 6), 0.042 * math.sin(TAU * a / 6), 0) for a in range(6)]:
        b.cyl(0.0055, 0.03, "plastic_black", segs=16, z0=-0.006, loc=(x, y, 0))  # screw bosses
    b.text("FLOW →", 0.008, "sticker_white", depth=0.0006, loc=(0, -0.0192, 0.0), rot=(90, 0, 0))
    c.part("body", b, desc="Valve body: inlet → seat → outlet. Water enters left, leaves right.")
    d = MB()
    d.lathe([(0, 0.0), (0.012, 0.0), (0.014, 0.004), (0.03, 0.006), (0.04, 0.004), (0.041, 0.0055), (0.041, 0.008),
             (0.03, 0.0095), (0.014, 0.008), (0.0, 0.009)], "rubber", segs=48)
    d.cyl(0.0035, 0.006, "stainless", segs=12, z0=0.008)  # metering pin
    c.part("diaphragm", d, explode=(0, 0, 0.055), loc=(0, 0, 0.022),
           desc="Rubber diaphragm – the actual seal. Pressure difference across it opens/closes the valve.")
    s = MB()
    s.sweep(helix(0.012, 0.007, 4.5), 0.0011, "stainless", segs=8)
    c.part("spring", s, explode=(0, 0, 0.1), loc=(0, 0, 0.03), desc="Return spring – pushes the diaphragm shut.")
    bo = MB()
    bo.lathe([(0, 0.0), (0.044, 0.0), (0.044, 0.008), (0.040, 0.012), (0.03, 0.022), (0.015, 0.03), (0.0, 0.031)],
             "plastic_dark", segs=48)
    for a in range(6):
        ang = TAU * a / 6
        bo.cyl(0.006, 0.01, "plastic_dark", segs=16, z0=0.0, loc=(0.042 * math.cos(ang), 0.042 * math.sin(ang), 0))
    bo.cyl(0.011, 0.02, "plastic_dark", segs=6, z0=0.02)
    bo.cyl(0.012, 0.022, "plastic_dark", segs=24, z0=-0.005, loc=(0.022, 0, 0.01), rot=(0, 30, 0))
    c.part("bonnet", bo, explode=(0, 0, 0.16), loc=(0, 0, 0.024),
           desc="Bonnet (cover). Holds the spring and forms the upper pressure chamber.")
    sc = MB()
    for a in range(6):
        ang = TAU * a / 6
        screw(sc, (0.042 * math.cos(ang), 0.042 * math.sin(ang), 0.0), length=0.028)
    c.part("bonnet_screws", sc, explode=(0, 0, 0.22), loc=(0, 0, 0.035), desc="6 stainless bonnet screws.")
    fc = MB()
    fc.cyl(0.004, 0.035, "stainless", segs=12, z0=0)
    fc.box((0.04, 0.008, 0.01), "plastic_dark", bevel=0.002, loc=(0, 0, 0.038))
    c.part("flow_control", fc, explode=(0, 0, 0.26), loc=(0, 0, 0.045),
           desc="Flow-control stem: limits how far the diaphragm can open (sets max flow).")
    so = MB()
    so.cyl(0.0145, 0.036, "plastic_black", segs=40, bevel=0.002, z0=0.0)
    so.cyl(0.009, 0.006, "plastic_black", segs=24, z0=0.036)
    so.cyl(0.0105, 0.008, "brass", segs=6, z0=-0.008)
    for dy in (-0.004, 0.004):
        cable(so, [(0.008, dy, 0.03), (0.02, dy, 0.035), (0.05, dy * 3, 0.02), (0.08, dy * 5, -0.02)], r=0.0012,
              m="wire_black", fillet=0.01)
    c.part("solenoid", so, explode=(0.08, 0, 0.12), loc=(0.031, 0, 0.047), rot=(0, 30, 0),
           desc="24 V AC solenoid coil. Energised → magnetic field lifts the plunger → valve opens.")
    pl = MB()
    pl.cyl(0.0035, 0.024, "stainless", segs=16, z0=0.0)
    pl.cyl(0.0033, 0.003, "rubber", segs=16, z0=-0.003)
    pl.sweep(helix(0.0045, 0.003, 4), 0.0005, "stainless", segs=6)
    c.part("plunger", pl, explode=(0.05, 0, 0.07), loc=(0.028, 0, 0.042), rot=(0, 30, 0),
           desc="Plunger + spring: the tiny pilot valve that the coil moves.")
    return c


# ─────────────────────────────── dripper + stake ───────────────────────────────
def dripper(cid="dripper", title="Drip emitter + stake (2 L/h, pressure-compensating)"):
    c = Component(
        cid, title, "Irrigation",
        summary="Delivers the same 2 L/h to every plant, even at the far end of the row.",
        how=("Water from the 16 mm lateral enters the button dripper, runs through a long labyrinth (turbulence stops "
             "clogging) and past a silicone diaphragm. Higher pressure pushes the diaphragm closer to the outlet, "
             "so flow stays constant (pressure-compensating). A 4 mm micro-tube carries it to an arrow stake in the "
             "plant's cube."),
        sensors=("row flow meter", "slab scale / drain meter show delivered volume"),
        control="Passive. Opened/closed by its zone valve.",
        state={"flow_l_h": 2.0, "clog_risk": "low"},
        real="PC button dripper 2 L/h + 4 mm micro-tube + angled arrow stake (Netafim/Jain/Rivulis class)",
        cost="₹15–30 per plant")
    lat = MB()
    lat.tube(0.008, 0.0065, 0.14, "pe_black", segs=24, axis="X")
    c.part("lateral", lat, desc="16 mm PE lateral pipe running along the row.")
    base = MB()
    base.lathe([(0, 0.0), (0.0105, 0.0), (0.0105, 0.004), (0.0, 0.004)], "plastic_black", segs=40)
    base.cyl(0.0022, 0.009, "plastic_black", segs=12, z0=-0.009)
    base.lathe([(0.0, -0.009), (0.0028, -0.0075), (0.0022, -0.006), (0, -0.006)], "plastic_black", segs=12)
    c.part("dripper_base", base, loc=(0, 0, 0.008), explode=(0, 0, 0.012),
           desc="Dripper base with barb (punched into the lateral).")
    lab = MB()
    lab.cyl(0.0098, 0.0012, "plastic_dark", segs=40, z0=0)
    for k, rr in enumerate((0.0085, 0.0068, 0.0051, 0.0034)):
        lab.add(bm_lathe([(rr - 0.0004, 0.0012), (rr + 0.0004, 0.0012), (rr + 0.0004, 0.0024), (rr - 0.0004, 0.0024)],
                         40, closed=True, arc=TAU * 0.88, phase=k * 1.3), "plastic_dark")
    c.part("labyrinth", lab, loc=(0, 0, 0.012), explode=(0, 0, 0.026),
           desc="Labyrinth path – turbulent flow keeps particles moving so the emitter does not clog.")
    dia = MB()
    dia.cyl(0.0085, 0.0012, "silicone", segs=40, z0=0)
    c.part("diaphragm", dia, loc=(0, 0, 0.0145), explode=(0, 0, 0.04),
           desc="Silicone diaphragm – flexes with pressure to keep flow constant (pressure compensation).")
    cap = MB()
    cap.lathe([(0, 0.0), (0.0108, 0.0), (0.0108, 0.0035), (0.009, 0.006), (0.0, 0.0065)], "plastic_black", segs=40)
    cap.cyl(0.0021, 0.008, "plastic_black", segs=12, z0=0.006)
    c.part("cap", cap, loc=(0, 0, 0.012), explode=(0, 0, 0.056), desc="Top cover with outlet barb.")
    mt = MB()
    pts = [(0, 0, 0.026), (0, 0, 0.04), (0.03, 0, 0.06), (0.1, 0, 0.05), (0.16, 0, 0.0), (0.18, 0, -0.03)]
    mt.sweep(fillet_path(pts, 0.03), 0.002, "pe_black", segs=10)
    c.part("microtube", mt, explode=(0, 0, 0.07), desc="4 mm micro-tube to the plant.")
    st = MB()
    rib = [(0.0035, 0.0), (0.0005, -0.11), (-0.0005, -0.11), (-0.0035, 0.0)]
    for a in (0, 90):
        st.prism(rib, 0.0012, "plastic_green", z0=-0.0006, M=xform(rot=(0, 0, a)) @ xform(rot=(90, 0, 0)))
    st.cyl(0.0045, 0.012, "plastic_green", segs=16, z0=0.0)
    st.cyl(0.0024, 0.01, "plastic_green", segs=12, z0=0.012)
    c.part("stake", st, loc=(0.185, 0, -0.045), rot=(0, 20, 0), explode=(0.05, 0, 0.02),
           desc="Arrow stake – pushed into the plant's cube so water lands at the roots.")
    return c


# ─────────────────────────────── disc filter ───────────────────────────────
def disc_filter(cid="disc_filter", title="Disc filter (1\", 120 mesh)"):
    c = Component(
        cid, title, "Irrigation",
        summary="Stops sand, algae and fertiliser particles before they reach the drippers.",
        how=("Water flows from outside the stack of grooved discs to the inside. The crossing grooves trap particles "
             "down to ~130 µm (120 mesh). Rising pressure drop across the filter = dirty; the twin compares pressure "
             "before/after and tells the farmer when to clean it."),
        sensors=("pressure before/after (Δp)",),
        control="Passive. Δp alarm from pressure readings.",
        state={"dp_bar": 0.15, "clean_in_days": 9},
        real="Amiad / Azud 1\" disc filter, 120 mesh (red discs)", cost="₹1–2k")
    b = MB()
    b.tube(0.019, 0.0145, 0.2, "plastic_black", segs=36, axis="X")
    for sx in (-1, 1):
        b.tube(0.0225, 0.0145, 0.024, "plastic_black", segs=6, axis="X", loc=(sx * 0.09, 0, 0), rot=(30, 0, 0))
        b.cyl(0.006, 0.012, "plastic_black", segs=16, z0=0.0, loc=(sx * 0.045, 0, 0.016))
        b.cyl(0.0045, 0.006, "brass", segs=6, z0=0.012, loc=(sx * 0.045, 0, 0.016))
    b.lathe([(0.0, 0.03), (0.05, 0.03), (0.058, 0.02), (0.06, 0.0), (0.06, -0.035), (0.052, -0.04), (0, -0.04)],
            "plastic_black", segs=48)
    b.text("IN →", 0.009, "sticker_white", loc=(-0.075, -0.0192, 0), rot=(90, 0, 0))
    c.part("body", b, desc="Filter head: inlet, outlet and the seat for the housing.")
    bowl = MB()
    bowl.lathe([(0.0, -0.2), (0.03, -0.2), (0.05, -0.19), (0.058, -0.17), (0.058, -0.01), (0.062, -0.005),
                (0.062, 0.0), (0.0, 0.0)], "plastic_red", segs=48)
    for k in range(12):
        a = TAU * k / 12
        bowl.box((0.006, 0.006, 0.05), "plastic_red", bevel=0.002,
                 loc=(0.06 * math.cos(a), 0.06 * math.sin(a), -0.03), rot=(0, 0, math.degrees(a)))
    bowl.cyl(0.009, 0.014, "plastic_black", segs=6, z0=-0.214)
    c.part("housing", bowl, loc=(0, 0, -0.04), explode=(0, 0, -0.22),
           desc="Housing (bowl). Unscrew to take out the disc stack for cleaning.")
    ds = MB()
    for k in range(34):
        ds.tube(0.042, 0.022, 0.0034, "plastic_red" if k % 2 == 0 else "pvc_red", segs=40, z0=-0.004 * k)
    c.part("disc_stack", ds, loc=(0, 0, -0.05), explode=(0, 0, -0.12),
           desc="Stack of thin grooved discs – the filter element (red = 120 mesh / 130 µm).")
    sp = MB()
    sp.cyl(0.02, 0.15, "plastic_dark", segs=8, z0=-0.15)
    sp.cyl(0.03, 0.006, "plastic_dark", segs=32, z0=0.0)
    c.part("spine", sp, loc=(0, 0, -0.045), explode=(0, 0, -0.05), desc="Central spine that holds the discs.")
    orr = MB()
    orr.torus(0.058, 0.0025, "rubber", segs=48, rsegs=10)
    c.part("o_ring", orr, loc=(0, 0, -0.04), explode=(0, 0, -0.02), desc="O-ring seal between head and housing.")
    return c


# ─────────────────────────────── flow meter ───────────────────────────────
def flow_meter(cid="flow_meter", title="Water meter (25 mm multi-jet, pulse output)"):
    """FEDREL-type 25 mm multi-jet water meter with reed pulse output. ISO 4064 DN25 lay length 260 mm,
    brass body, dry dial register, pulse module clipped on the register. Flow along +X."""
    c = Component(
        cid, title, "Irrigation",
        summary="Counts every litre that goes to the crop – proves a valve really opened.",
        how=("Water enters the brass bowl through several angled jets and spins a small impeller. A magnet on the "
             "impeller turns the dial gears through the sealed wall (the dial stays dry). A magnet on the last dial "
             "closes a reed switch once per litre: that pulse goes to the PLC. If a valve is ON but the pulses stay at "
             "zero, the pump or valve has failed."),
        sensors=("self (1 pulse per litre → PLC high-speed input)",),
        control="Read by PLC (fast counter) and the ESP32 node.",
        state={"flow_l_min": 0.0, "total_l_today": 212.4, "litres_per_pulse": 1},
        real="FEDREL 25 mm brass multi-jet water meter, Class B, reed pulse output (1 L/pulse)",
        cost="₹1.4–1.7k (IndiaMART)")
    b = MB()
    b.cyl(0.021, 0.2, "brass", segs=32, axis="X")
    b.lathe([(0.0, -0.04), (0.036, -0.04), (0.044, -0.03), (0.046, 0.0), (0.044, 0.025), (0.047, 0.03),
             (0.0, 0.03)], "brass", segs=48)
    for sx in (-1, 1):
        b.cyl(0.024, 0.02, "brass", segs=6, axis="X", loc=(sx * 0.095, 0, 0))            # hex union nut
        b.cyl(0.0165, 0.035, "brass", segs=32, axis="X", loc=(sx * 0.12, 0, 0))            # 1" tail piece
        for k in range(5):
            b.torus(0.0167, 0.0009, "brass", segs=32, rsegs=6, axis="X", loc=(sx * (0.11 + 0.005 * k), 0, 0))
    b.text("→", 0.024, "plastic_black", depth=0.0006, loc=(0, -0.0212, 0), rot=(90, 0, 0))
    c.part("brass_body", b, desc="Brass meter body: flow straight through, a bowl in the middle holds the impeller.")
    ip = MB()
    ip.cyl(0.004, 0.03, "plastic_black", segs=12)
    for k in range(8):
        ip.box((0.03, 0.002, 0.022), "plastic_black", rot=(0, 0, 22.5 * k))
    c.part("impeller", ip, loc=(0, 0, -0.012), explode=(0, 0, -0.12), desc="Multi-jet impeller with a drive magnet.")
    rg = MB()
    rg.tube(0.05, 0.043, 0.024, "plastic_black", segs=48, z0=0.0)
    rg.cyl(0.043, 0.004, "plastic_white", segs=48, z0=0.004)
    rg.cyl(0.043, 0.004, "glass", segs=48, z0=0.02)
    for k, x in enumerate((-0.016, -0.005, 0.006, 0.017)):
        rg.cyl(0.0048, 0.0006, "plastic_white", segs=20, loc=(x, -0.018, 0.0085))
        rg.box((0.004, 0.0008, 0.0006), "plastic_red", loc=(x + 0.0016, -0.018, 0.0092), rot=(0, 0, 40 * k))
    rg.box((0.036, 0.009, 0.0006), "plastic_black", loc=(0, 0.01, 0.0085))
    rg.text("00212", 0.0075, "sticker_white", depth=0.0003, loc=(0, 0.01, 0.0089))
    c.part("dial_register", rg, loc=(0, 0, 0.03), explode=(0, 0, 0.1), desc="Dry dial register: m³ counter + litre dials.")
    ld = MB()
    ld.cyl(0.05, 0.005, "plastic_blue", segs=48, z0=0.0, loc=(0, -0.05, 0))
    c.part("lid", ld, loc=(0, 0.05, 0.054), rot=(-105, 0, 0), explode=(0, 0.06, 0.08), desc="Hinged dust lid (open).")
    pm = MB()
    pm.box((0.028, 0.02, 0.022), "plastic_dark", bevel=0.003)
    cable(pm, [(0.0, 0.0, -0.011), (0.0, 0.0, -0.04), (0.04, 0.02, -0.09), (0.09, 0.02, -0.12)], r=0.0022)
    c.part("pulse_module", pm, loc=(0.052, 0, 0.042), explode=(0.08, 0, 0.05),
           desc="Reed-switch pulse module: 1 pulse per litre to the PLC counter input.")
    return c


# ─────────────────────────────── pressure transmitter + gauge ───────────────────────────────
def pressure_transmitter(cid="pressure_tx", title="Pressure transmitter (0–10 bar, 4–20 mA)"):
    c = Component(
        cid, title, "Irrigation",
        summary="Measures line pressure. Confirms the pump is really pushing water and the filter is not blocked.",
        how=("Water pressure bends a thin ceramic diaphragm. A strain bridge on it changes resistance; the electronics "
             "turn that into a 4–20 mA current (4 mA = 0 bar, 20 mA = 10 bar). Current loops ignore long-cable noise."),
        sensors=("self",),
        control="PLC analog input. Used for pump-running check, leak check (pressure drop) and filter Δp.",
        state={"pressure_bar": 2.1},
        real="Stainless 1/4\" BSP ceramic-cell transmitter, 4–20 mA, M12", cost="₹1.5–3k")
    th = MB()
    th.cyl(0.0065, 0.012, "stainless", segs=24, z0=-0.012)
    for k in range(5):
        th.torus(0.0066, 0.0007, "stainless", segs=24, rsegs=6, loc=(0, 0, -0.0105 + 0.0022 * k))
    th.cyl(0.013, 0.01, "stainless", segs=6, bevel=0.001, z0=0.0)
    c.part("process_thread", th, desc="1/4\" BSP thread + hex – screws into the pipe tee.")
    cell = MB()
    cell.cyl(0.009, 0.004, "plastic_white", segs=32, z0=0)
    cell.box((0.006, 0.006, 0.0006), "gold", loc=(0, 0, 0.0042))
    c.part("sensing_cell", cell, loc=(0, 0, 0.011), explode=(0, 0, 0.03),
           desc="Ceramic diaphragm with strain bridge – bends with pressure.")
    pcb = MB()
    pcb.cyl(0.0095, 0.0016, "pcb", segs=32, z0=0)
    pcb.box((0.005, 0.004, 0.0012), "chip", loc=(0.002, 0, 0.0016))
    pcb.box((0.002, 0.003, 0.0012), "chip", loc=(-0.004, 0.002, 0.0016))
    c.part("amplifier_pcb", pcb, loc=(0, 0, 0.02), explode=(0, 0, 0.05),
           desc="Amplifier board – converts the bridge signal to 4–20 mA.")
    hs = MB()
    hs.lathe([(0.0105, 0.0), (0.011, 0.0), (0.011, 0.048), (0.009, 0.052), (0.0085, 0.052), (0.0085, 0.001)],
             "stainless", segs=40, closed=True)
    hs.text("0-10 bar", 0.004, "plastic_black", depth=0.0003, loc=(0, -0.0111, 0.03), rot=(90, 0, 0))
    c.part("housing", hs, loc=(0, 0, 0.01), explode=(0, 0, 0.075), desc="Stainless housing (IP65).")
    cn = MB()
    cn.cyl(0.0075, 0.012, "plastic_black", segs=24, z0=0)
    cn.cyl(0.0085, 0.008, "plastic_black", segs=6, z0=0.012)
    cable(cn, [(0, 0, 0.02), (0, 0, 0.04), (0.03, 0, 0.07), (0.07, 0, 0.08)], r=0.0025)
    c.part("m12_connector", cn, loc=(0, 0, 0.062), explode=(0, 0, 0.1), desc="M12 connector + 2-wire cable to the PLC.")
    return c


def pressure_gauge(cid="pressure_gauge", title="Pressure gauge (63 mm, glycerine)"):
    c = Component(
        cid, title, "Irrigation",
        summary="Analogue backup the farmer can read without any electronics.",
        how=("Pressure enters a curved 'Bourdon' tube. The tube tries to straighten under pressure; a small gear "
             "movement turns that into needle rotation. Glycerine fill damps pump pulsation."),
        sensors=("none (manual reading)",), control="none", state={"pressure_bar": 2.1},
        real="63 mm stainless glycerine gauge 0–10 bar, 1/4\" bottom entry", cost="₹400–800")
    st = MB()
    st.cyl(0.0065, 0.012, "brass", segs=24, z0=-0.052)
    st.cyl(0.0075, 0.01, "brass", segs=6, z0=-0.04)
    st.box((0.012, 0.012, 0.012), "brass", bevel=0.001, loc=(0, 0.004, -0.026))
    c.part("socket", st, desc="Brass socket + thread.")
    bt = MB()
    pts = [(0.0, 0.0, -0.024)] + [(0.017 * math.cos(math.radians(a)), 0.0, 0.017 * math.sin(math.radians(a)))
                                   for a in range(-80, 200, 10)]
    bt.sweep(fillet_path(pts, 0.004), 0.0022, "copper", segs=10, flat=(0.006, 0.0025))
    c.part("bourdon_tube", bt, loc=(0, 0.004, 0), explode=(0, 0.05, 0),
           desc="Bourdon tube – curved tube that uncurls under pressure (the actual sensor).")
    case = MB()
    case.lathe([(0.0, 0.0), (0.03, 0.0), (0.0315, 0.002), (0.0315, 0.022), (0.029, 0.022), (0.029, 0.002),
                (0.0, 0.002)], "stainless", segs=48, axis="-Y", loc=(0, 0.013, 0))
    c.part("case", case, desc="Stainless case filled with glycerine.")
    dl = MB()
    dial(dl, 0.028, (0, 0, 0), "-Y")
    dl.text("bar", 0.005, "plastic_black", loc=(0, -0.0012, -0.01), rot=(90, 0, 0))
    c.part("dial", dl, loc=(0, -0.0065, 0), explode=(0, -0.03, 0), desc="Dial (0–10 bar).")
    nd = MB()
    nd.box((0.022, 0.0008, 0.0015), "plastic_red", loc=(0.008, 0, 0.004), rot=(0, -40, 0))
    nd.cyl(0.002, 0.002, "plastic_black", segs=16, axis="-Y")
    c.part("needle", nd, loc=(0, -0.0085, 0), explode=(0, -0.05, 0), desc="Needle.")
    gl = MB()
    gl.cyl(0.03, 0.002, "acrylic", segs=48, axis="-Y")
    gl.tube(0.032, 0.029, 0.004, "stainless", segs=48, axis="-Y", loc=(0, -0.001, 0))
    c.part("window", gl, loc=(0, -0.0105, 0), explode=(0, -0.07, 0), desc="Window + bezel ring.")
    return c


# ─────────────────────────────── irrigation pump ───────────────────────────────
def irrigation_pump(cid="irrigation_pump", title="Irrigation pump (Grundfos CM 3-4)"):
    c = Component(
        cid, title, "Irrigation",
        summary="Pushes nutrient water from the mix tank through filter, meter and valves to the drippers (~2 bar).",
        how=("A 0.5 kW motor spins a stainless shaft carrying 4 impellers (the \"-4\" in CM 3-4). Each impeller flings "
             "water outward; the diffuser after it turns speed into pressure, and the next stage adds more: about 4 bar "
             "in total. Water enters at the end, leaves from the top port. The same pump also feeds the fog line; the PLC "
             "never runs fog and a watering shot at the same time."),
        sensors=("pressure transmitter", "flow meter", "motor current (CT on contactor)", "tank level (dry-run)"),
        control=("PLC contactor + motor-protection breaker. HARD-WIRED float switch cuts the coil if the tank is empty "
                 "(no software involved)."),
        state={"running": False, "current_a": 0.0, "run_hours": 412},
        real="Grundfos CM 3-4 A-R-I-E-AQQE, 1~230 V, 0.5 kW, Rp 1\" ports, 11.6 kg",
        cost="₹34–39k (IndiaMART)")
    R = 0.062
    mh = MB()
    motor_x(mh, R, 0.2, m="grundfos_black")
    c.part("motor_housing", mh, loc=(-0.1, 0, 0), explode=(0, 0, 0.16),
           desc="Motor frame (finned for cooling) with feet.")
    tb = MB()
    tb.box((0.075, 0.075, 0.04), "grundfos_black", bevel=0.004)
    tb.cyl(0.007, 0.012, "plastic_black", segs=6, axis="Y", loc=(0.02, -0.043, 0))
    tb.cyl(0.009, 0.014, "plastic_black", segs=6, axis="X", loc=(0.044, 0.0, 0.0))
    tb.text("GRUNDFOS", 0.0085, "sticker_white", depth=0.0004, bold=True, loc=(0.0, 0.0, 0.0205))
    c.part("terminal_box", tb, loc=(-0.1, 0, R + 0.028), explode=(0, 0, 0.28),
           desc="Terminal box + run capacitor (single-phase motor).")
    stt = MB()
    stt.tube(0.058, 0.036, 0.13, "steel_dark", segs=40, axis="X")
    for sx in (-1, 1):
        stt.torus(0.047, 0.012, "copper", segs=40, rsegs=10, axis="X", loc=(sx * 0.068, 0, 0))
    c.part("stator", stt, loc=(-0.1, 0, 0), explode=(0, 0, 0.1),
           desc="Stator: steel laminations + copper windings. AC current here makes a rotating magnetic field.")
    rs = MB()
    rs.cyl(0.034, 0.12, "steel_dark", segs=32, axis="X")
    for k in range(16):
        a = TAU * k / 16
        rs.box((0.12, 0.003, 0.003), "alu", loc=(0, 0.034 * math.cos(a), 0.034 * math.sin(a)))
    rs.cyl(0.008, 0.42, "stainless", segs=16, axis="X", loc=(0.08, 0, 0))
    c.part("rotor_shaft", rs, loc=(-0.1, 0, 0), explode=(-0.02, 0, -0.14),
           desc="Rotor + stainless shaft – the only moving part, carries the impellers.")
    fn = MB()
    fn.cyl(0.02, 0.012, "plastic_dark", segs=24, axis="X")
    for k in range(8):
        a = math.degrees(TAU * k / 8)
        fn.box((0.012, 0.05, 0.002), "plastic_dark", M=xform(rot=(a, 0, 0)) @ xform((0, 0.03, 0)))
    c.part("cooling_fan", fn, loc=(-0.215, 0, 0), explode=(-0.1, 0, 0), desc="Cooling fan on the motor shaft.")
    cw = MB()
    cw.lathe([(0.0, 0.0), (0.03, 0.0), (0.03, 0.002), (0.064, 0.004), (0.066, 0.055), (0.063, 0.055),
              (0.061, 0.006), (0.0, 0.004)], "grundfos_black", segs=48, axis="-X")
    cw.cyl(0.064, 0.004, "grundfos_black", segs=48, axis="X", loc=(-0.057, 0, 0))   # end cap with the logo
    face = xform((-0.0595, 0, 0)) @ xform(rot=(0, -90, 0)) @ xform(rot=(0, 0, -90))
    cw.text("GRUNDFOS", 0.0105, "sticker_white", depth=0.0005, bold=True, M=face @ xform((0, -0.012, 0)))
    cw.text("X", 0.022, "sticker_white", depth=0.0005, bold=True, M=face @ xform((0, 0.022, 0)))
    c.part("fan_cowl", cw, loc=(-0.2, 0, 0), explode=(-0.18, 0, 0), desc="Fan cowl (guard).")
    pc = MB()
    pc.lathe([(0.049, 0.02), (0.052, 0.02), (0.052, 0.13), (0.049, 0.13)], "stainless", segs=48, closed=True, axis="X")
    for k in range(9):                      # the ribbed sleeve: one chamber ring per half-stage
        pc.torus(0.052, 0.0022, "stainless", segs=48, rsegs=8, axis="X", loc=(0.03 + 0.0115 * k, 0, 0))
    pc.box((0.05, 0.11, 0.1), "grundfos_black", bevel=0.01, loc=(0.0, 0, 0))            # motor-side bracket
    pc.tube(0.02, 0.0145, 0.03, "grundfos_black", segs=32, z0=0.045, loc=(0.0, 0, 0))    # outlet Rp 1" on top
    pc.lathe([(0.0, 0.13), (0.058, 0.13), (0.06, 0.135), (0.06, 0.168), (0.05, 0.175), (0.0, 0.175)],
             "grundfos_black", segs=6, axis="X")                                          # cast pump head (hex)
    pc.tube(0.02, 0.0145, 0.022, "grundfos_black", segs=32, axis="X", loc=(0.185, 0, 0))  # inlet Rp 1" axial
    pc.cyl(0.007, 0.008, "stainless", segs=6, z0=0.058, loc=(0.152, 0, 0))              # vent / priming plug
    pc.cyl(0.006, 0.008, "stainless", segs=6, z0=-0.066, loc=(0.152, 0, 0))             # drain plug
    pc.box((0.035, 0.12, 0.008), "grundfos_black", loc=(0.152, 0, -R - 0.012))           # foot under the head
    pc.box((0.03, 0.03, 0.03), "grundfos_black", loc=(0.152, 0, -R + 0.008))
    c.part("pump_casing", pc, explode=(0.2, 0, 0.06),
           desc="Ribbed stainless sleeve between a black motor bracket (outlet on top) and a black cast head (inlet at the end).")
    im = c.group("impeller_stack", explode=(0.09, 0, -0.12), desc="4 impellers + diffusers (4 stages).")
    for k in range(4):
        g = MB()
        g.cyl(0.045, 0.003, "stainless", segs=40, axis="X")
        g.tube(0.045, 0.02, 0.002, "stainless", segs=40, axis="X", loc=(0.009, 0, 0))
        for v in range(6):
            g.prism(vane(0.012, 0.043, 70, 0.0022), 0.008, "stainless", z0=0.0015,
                    M=xform(rot=(math.degrees(TAU * v / 6), 0, 0)) @ xform(rot=(0, 90, 0)))
        c.part(f"impeller_{k + 1}", g, parent=im, loc=(0.03 + 0.024 * k, 0, 0), explode=(0.04 * k, 0, 0),
               desc=f"Stage {k + 1} impeller – throws water outward to build pressure.")
        dfz = MB()
        dfz.tube(0.05, 0.012, 0.004, "plastic_dark", segs=40, axis="X")
        for v in range(8):
            a = TAU * v / 8
            dfz.box((0.01, 0.002, 0.018), "plastic_dark", loc=(0.006, 0.032 * math.cos(a), 0.032 * math.sin(a)),
                    rot=(math.degrees(a) - 90, 0, 25))
        c.part(f"diffuser_{k + 1}", dfz, parent=im, loc=(0.042 + 0.024 * k, 0, 0), explode=(0.04 * k + 0.02, 0, 0),
               desc="Diffuser – slows the water and turns speed into pressure.")
    ms = MB()
    ms.tube(0.018, 0.009, 0.01, "plastic_black", segs=32, axis="X")
    ms.tube(0.017, 0.009, 0.004, "plastic_white", segs=32, axis="X", loc=(0.007, 0, 0))
    c.part("mechanical_seal", ms, loc=(0.008, 0, 0), explode=(0.02, 0, 0.12),
           desc="Mechanical seal – stops water leaking along the shaft into the motor.")
    return c
