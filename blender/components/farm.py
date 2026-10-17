"""The farm around the greenhouse (6 Oct 2026): what a real Kolar / Chikkaballapur polyhouse farm needs next to the
house. Every item maps to a real, buyable product in tools/products.py.

  entry_room      double-door insect-net entry with a disinfectant footbath (stops whitefly = leaf-curl virus)
  shade_net       retractable external aluminet shade net above the roof (gearmotor + cables)
  packhouse       4 × 6 m packhouse west of the house; its roof carries the solar array
  solar_array     6 × Waaree 540 W mono-PERC panels (3.24 kWp), facing south at 13° (Kolar latitude)
  hybrid_inverter MuscleGrid 3.6 kW 48 V hybrid inverter        battery_bank  5.12 kWh LiFePO4 (48 V 100 Ah)
  power_panel     AC/DC distribution boxes + surge protection
  cool_chamber    IARI zero-energy cool chamber (brick + wet sand, no power) for harvested tomatoes
  pack_station    sorting table, platform scale, crates
  farm_pond       8 × 8 × 3 m farm pond, 500 µm HDPE liner (Karnataka Krishi Bhagya design), ~85 m³
  pond_fence      chain-link safety fence + gate round the pond     pond_pump  Kirloskar Chhotu pond → tank
  level_pond      ultrasonic level sensor over the pond             rain_harvest  gutters → first-flush → pond
  borewell        the farm's existing borewell head + starter panel (not part of the kit's bill)
  farm_sign       GH-01 sign at the gate

World frame as the greenhouse: x = length (0 front gable … 9 back gable), y = width. Compass (same as the web twin's sun):
+x = north, −x = south (the noon sun), −y = east, +y = west.
"""
import math
import random

import bmesh

from gh import MB, Component, xform
from parts import cable, kirloskar_chhotu, pvc_run
from greenhouse import GH, L, RH, W, roof_z

# ─────────────────────────── site layout (metres) ───────────────────────────
POND_C, POND_TOP, POND_BOT, POND_D = (5.0, -10.5), 4.0, 1.0, 3.0   # centre, top half-size, bottom half-size, depth
POND_WATER_Z = -1.2                                                  # water 1.8 m deep (about 2/3 full)
FENCE = (-0.9, 10.9, -16.4, -4.6)                                    # pond fence x0, x1, y0, y1
PH = dict(x0=1.5, x1=5.5, y0=5.5, y1=11.5, zl=2.6, tilt=13.0)        # packhouse; roof low at the south (x0) edge
ENTRY = dict(x0=-2.1, x1=-0.08, y=0.95, h=2.4)
BORE = (-4.6, -3.6)
TANK_INLET = (1.6, -1.95, 1.08)


def pond_half(z):
    """Half-size of the (square) pond at height z (0 = ground, −POND_D = bottom)."""
    return POND_BOT + (POND_TOP - POND_BOT) * (1 + z / POND_D)


def ph_roof_z(x):
    """Packhouse roof height: 13° up from the south (low) edge to the north (high) edge."""
    return PH["zl"] + (x - PH["x0"]) * math.tan(math.radians(PH["tilt"]))


def quad(mb, pts, m):
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in pts]
    bm.faces.new(v)
    mb.add(bm, m)


def sign_rot_facing(direction):
    """Euler rot (deg) that turns flat bm_text (reads +X, up +Y, faces +Z) upright, facing `direction`."""
    return {"-x": (90, 0, -90), "+x": (90, 0, 90), "+y": (90, 0, 180), "-y": (90, 0, 0)}[direction]


# ═══════════════════════════ entry room (anteroom + footbath) ═══════════════════════════
def entry_room(cid="entry_room", title="Double-door entry room with footbath"):
    c = Component(
        cid, title, "Structure",
        summary="A small insect-net room in front of the greenhouse door: you close the outer door before you open the inner one.",
        how=("Whitefly and thrips ride in on people. With two doors and a room between them, the greenhouse is never open "
             "straight to the outside. The footbath (disinfectant) cleans boots, so soil-borne disease stays out. In Karnataka "
             "whitefly spreads tomato leaf curl virus, which can wipe out a crop."),
        sensors=("door contact switches (both doors)",),
        control="PLC logs every opening; an alarm if both doors stay open together.",
        state={"outer_door": "closed", "inner_door": "closed", "footbath_changed": "2 days ago"})
    x0, x1, hy, h = ENTRY["x0"], ENTRY["x1"], ENTRY["y"], ENTRY["h"]
    fl = MB()
    fl.box((x1 - x0 + 0.1, 2 * hy + 0.1, 0.12), "concrete", loc=((x0 + x1) / 2, 0, 0.06))
    c.part("floor", fl, desc="Concrete floor and kerb.")
    fb = MB()
    fb.box((0.9, 0.95, 0.05), "pvc_grey", bevel=0.01, loc=(x0 + 0.75, 0, 0.12 + 0.025))
    fb.box((0.84, 0.89, 0.002), "disinfectant", loc=(x0 + 0.75, 0, 0.12 + 0.042))
    c.part("footbath", fb, explode=(0, 0, 0.35), desc="Footbath tray (90 × 95 cm) with disinfectant – step through it on the way in.")
    fr = MB()
    zt = lambda x: h + (x - x0) / (x1 - x0) * 0.15          # mono roof, higher at the greenhouse side
    for x in (x0, x1):
        for y in (-hy, hy):
            fr.box((0.05, 0.05, zt(x)), "galv", loc=(x, y, zt(x) / 2 + 0.12))
    for y in (-0.5, 0.5):                                     # outer door jambs
        fr.box((0.05, 0.05, zt(x0)), "galv", loc=(x0, y, zt(x0) / 2 + 0.12))
    fr.box((0.05, 1.0, 0.05), "galv", loc=(x0, 0, 2.2))      # door header
    for y in (-hy, hy):
        for z in (0.72, 1.6):
            fr.box((x1 - x0, 0.04, 0.04), "galv", loc=((x0 + x1) / 2, y, z))
        fr.box((x1 - x0, 0.05, 0.05), "galv", loc=((x0 + x1) / 2, y, (zt(x0) + zt(x1)) / 2 + 0.12), rot=(0, -math.degrees(math.atan2(0.15, x1 - x0)), 0))
    c.part("frame", fr, desc="Galvanised tube frame.")
    wl = MB()
    for y in (-hy, hy):                                        # side walls: film apron below, 40-mesh insect net above
        wl.box((x1 - x0, 0.006, 0.6), "uv_film", loc=((x0 + x1) / 2, y * 1.01, 0.42))
        wl.box((x1 - x0, 0.004, zt(x0) - 0.6), "net", loc=((x0 + x1) / 2, y * 1.01, 0.72 + (zt(x0) - 0.6) / 2))
    for y0, y1 in ((-hy, -0.53), (0.53, hy)):                 # outer wall beside the door
        wl.box((0.006, y1 - y0, 0.6), "uv_film", loc=(x0 - 0.02, (y0 + y1) / 2, 0.42))
        wl.box((0.004, y1 - y0, zt(x0) - 0.6), "net", loc=(x0 - 0.02, (y0 + y1) / 2, 0.72 + (zt(x0) - 0.6) / 2))
    wl.box((0.004, 1.06, zt(x0) - 2.2), "net", loc=(x0 - 0.02, 0, 2.2 + (zt(x0) - 2.2) / 2 + 0.12))
    c.part("walls", wl, desc="40-mesh insect net walls with a film apron at the bottom.")
    rf = MB()
    quad(rf, [(x0 - 0.06, -hy - 0.06, zt(x0) + 0.15), (x1, -hy - 0.06, zt(x1) + 0.15),
              (x1, hy + 0.06, zt(x1) + 0.15), (x0 - 0.06, hy + 0.06, zt(x0) + 0.15)], "uv_film")
    c.part("roof", rf, explode=(0, 0, 0.6), desc="UV film roof.")
    dr = MB()                                                  # outer door, hinged at y = −0.5, shown a little open
    dr.box((0.04, 0.98, 2.04), "alu", loc=(0, 0.49, 1.02))
    dr.box((0.012, 0.9, 0.95), "net", loc=(0, 0.49, 1.52))
    dr.box((0.012, 0.9, 0.95), "uv_film", loc=(0, 0.49, 0.53))
    dr.box((0.03, 0.06, 0.18), "plastic_black", loc=(-0.03, 0.88, 1.05))
    for z in (0.35, 1.7):
        dr.cyl(0.012, 0.08, "steel_dark", segs=12, loc=(0, 0.0, z))
    c.part("outer_door", dr, loc=(x0 - 0.03, -0.5, 0.12), rot=(0, 0, 22), explode=(-0.6, 0, 0),
           desc="Outer door with a self-closing spring – it must be shut before the inner (greenhouse) door opens.")
    sg = MB()
    sg.box((0.006, 0.5, 0.32), "sticker_yellow", loc=(0, 0, 0))
    sg.text("CLOSE THIS DOOR", 0.045, "plastic_black", bold=True, M=xform((-0.004, 0, 0.08), sign_rot_facing("-x")))
    sg.text("BEFORE OPENING", 0.045, "plastic_black", bold=True, M=xform((-0.004, 0, 0.02), sign_rot_facing("-x")))
    sg.text("THE NEXT ONE", 0.045, "plastic_black", bold=True, M=xform((-0.004, 0, -0.04), sign_rot_facing("-x")))
    sg.text("DIP YOUR FEET", 0.04, "plastic_red", bold=True, M=xform((-0.004, 0, -0.11), sign_rot_facing("-x")))
    c.part("sign", sg, loc=(x0 - 0.03, -0.75, 1.55), explode=(-0.3, 0, 0), desc="Door rule sign.")
    sw = MB()
    for y in (-0.47, 0.47):
        sw.box((0.03, 0.02, 0.06), "plastic_white", loc=(0, y, 0))
    c.part("door_switches", sw, loc=(x0 + 0.02, 0, 2.05), desc="Magnetic door contacts → PLC (an alarm if both doors are open).")
    return c


# ═══════════════════════════ external shade net ═══════════════════════════
def shade_net(cid="shade_net", title="Retractable shade net (aluminet, 50 %)"):
    c = Component(
        cid, title, "Climate",
        summary="A silver shade net on wires 35 cm above the roof. It rolls out on hot, bright afternoons and rolls back in wind.",
        how=("The aluminised net reflects about half of the sunlight before it reaches the film, so the house heats up less "
             "and the fans and wet pad work less (less power, less water). It is outside the roof, so the hot air never gets "
             "in. The weather station's wind sensor pulls it in above 8 m/s so it doesn't tear."),
        sensors=("pyranometer (weather station)", "PAR sensor (inside)", "wind speed"),
        control="AI suggests; PLC runs the gearmotor between limit switches; wind > 8 m/s always retracts.",
        state={"deployed_pct": 100, "shade_pct": 50})
    off = 0.38
    xs = [1.5 * i for i in range(7)]
    fr = MB()
    lines_y = (-2.62, -1.667, 0.0, 1.0, 1.667, 2.62)
    clampy = lambda y: max(-W / 2, min(W / 2, y))
    for x in xs:
        for y in lines_y:
            z0 = GH + 0.06 if abs(y) > W / 2 else roof_z(y) + 0.05
            z1 = roof_z(clampy(y)) + off + 0.03
            fr.box((0.04, 0.04, z1 - z0), "galv", loc=(x, y, (z0 + z1) / 2))
    for y in lines_y:                                          # support wires along the house
        fr.sweep([(-0.25, y, roof_z(clampy(y)) + off + 0.02), (L + 0.25, y, roof_z(clampy(y)) + off + 0.02)], 0.003,
                 "stainless", segs=6)
    c.part("frame", fr, desc="Galvanised posts on every arch and stainless support wires above the roof.")
    sides = (((-2.62, -0.04), "east slope"), ((1.0, 2.62), "west slope (gap over the ridge vent)"))
    for bay in range(6):
        nb = MB()
        xa, xb = xs[bay] + 0.03, xs[bay + 1] - 0.03
        for (ya, yb), _ in sides:
            za = roof_z(max(-2.5, min(2.5, ya))) + off
            zb = roof_z(max(-2.5, min(2.5, yb))) + off
            quad(nb, [(xa, ya, za), (xb, ya, za), (xb, yb, zb), (xa, yb, zb)], "aluminet")
            nb.sweep([(xb, ya, za + 0.01), (xb, yb, zb + 0.01)], 0.012, "alu", segs=10)   # lead bar
        c.part(f"net_bay_{bay + 1}", nb, explode=(0, 0, 1.0 + 0.15 * bay),
               desc=f"Net, bay {bay + 1} of 6 (50 % aluminet, knitted + aluminised).")
    dv = MB()                                                  # gearmotor + cable drum at the front gable apex
    dv.box((0.2, 0.3, 0.2), "paint_motor", loc=(-0.35, 0.0, RH + 0.45))
    dv.cyl(0.08, 0.26, "paint_motor", segs=24, axis="Y", loc=(-0.35, 0.3, RH + 0.45))
    dv.cyl(0.06, 0.5, "steel_dark", segs=24, axis="Y", loc=(-0.35, -0.35, RH + 0.45))
    dv.box((0.05, 0.05, 0.6), "galv", loc=(-0.35, 0.0, RH + 0.05))
    for y in (-1.667, 1.667):
        dv.sweep([(-0.35, -0.35, RH + 0.45), (-0.2, y, roof_z(y) + off + 0.02)], 0.003, "stainless", segs=6)
    c.part("drive", dv, explode=(-0.6, 0, 0.4), desc="370 W gearmotor + cable drum (same family as the vent motor), with limit switches.")
    return c


# ═══════════════════════════ packhouse (+ solar roof) ═══════════════════════════
def packhouse(cid="packhouse", title="Packhouse (4 × 6 m, solar roof)"):
    c = Component(
        cid, title, "Farm",
        summary="Where tomatoes are sorted, weighed, crated and kept cool. Its roof carries the solar panels; the inverter and battery live inside.",
        how=("Harvest goes straight from the greenhouse into the shade here: sorting by size and colour, weighing (the twin "
             "logs kg per plant row), and the zero-energy cool chamber keeps them fresh for 1–2 weeks so the farmer can wait "
             "for a better price instead of selling the same day. Under MIDH a 9 × 6 m packhouse (₹4 L norm) gets 50 % subsidy."),
        sensors=("platform scale (harvest kg)", "cool-chamber T/RH"), control="—",
        state={"harvest_today_kg": 6.4, "crates_in_store": 7})
    x0, x1, y0, y1 = PH["x0"], PH["x1"], PH["y0"], PH["y1"]
    rz = ph_roof_z
    tl = PH["tilt"]
    fl = MB()
    fl.box((x1 - x0 + 0.3, y1 - y0 + 0.3, 0.15), "concrete", loc=((x0 + x1) / 2, (y0 + y1) / 2, 0.075))
    c.part("floor", fl, desc="Raised concrete floor (15 cm plinth keeps rain water out).")
    fr = MB()
    ym = (y0 + y1) / 2
    for y in (y0, ym, y1):
        for x in (x0, x1):
            fr.box((0.1, 0.1, rz(x) - 0.22), "galv", loc=(x, y, 0.15 + (rz(x) - 0.22) / 2))
        ln = (x1 - x0 + 0.5) / math.cos(math.radians(tl))
        fr.box((ln, 0.08, 0.12), "galv", loc=((x0 + x1) / 2, y, rz((x0 + x1) / 2) - 0.13), rot=(0, -tl, 0))
    for k in range(5):                                         # purlins
        x = x0 - 0.2 + k * (x1 - x0 + 0.4) / 4
        fr.box((0.06, y1 - y0 + 0.4, 0.06), "galv", loc=(x, ym, rz(x) - 0.05))
    c.part("frame", fr, desc="Galvanised steel columns, rafters and purlins.")
    rf = MB()
    xa, xb = x0 - 0.25, x1 + 0.25
    ln = (xb - xa) / math.cos(math.radians(tl))
    rf.box((ln, y1 - y0 + 0.5, 0.006), "galv", loc=((xa + xb) / 2, ym, rz((xa + xb) / 2)), rot=(0, -tl, 0))
    for k in range(int((y1 - y0 + 0.5) / 0.15)):               # corrugation ribs run down the slope
        y = y0 - 0.25 + 0.075 + 0.15 * k
        rf.box((ln, 0.03, 0.018), "galv", loc=((xa + xb) / 2, y, rz((xa + xb) / 2) + 0.009), rot=(0, -tl, 0))
    rf.prism([(-0.06, 0.0), (0.06, 0.0), (0.06, 0.08), (0.05, 0.08), (0.05, 0.01), (-0.05, 0.01), (-0.05, 0.08), (-0.06, 0.08)],
             y1 - y0 + 0.5, "galv", z0=-(y1 - y0 + 0.5) / 2,
             M=xform((xa - 0.04, ym, rz(xa) - 0.09)) @ xform(rot=(90, 0, 0)))                  # rain gutter at the low edge
    c.part("roof", rf, explode=(0, 0, 0.9), desc="Corrugated galvanised roof, 13° down to the south; gutter at the low edge.")
    wl = MB()
    t = 0.15
    wl.box((t, y1 - y0, rz(x1) - 0.15), "plaster_white", loc=(x1 - t / 2, ym, 0.15 + (rz(x1) - 0.15) / 2))   # north wall
    for y in (y0, y1):                                         # east + west: brick to 1 m, insect mesh up to the roof
        wl.box((x1 - x0 - t, t, 1.0), "brick", loc=((x0 + x1 - t) / 2, y + (t / 2 if y == y0 else -t / 2), 0.65))
        yy = y + (t / 2 if y == y0 else -t / 2)
        quad(wl, [(x0, yy, 1.15), (x1 - t, yy, 1.15), (x1 - t, yy, rz(x1 - t) - 0.1), (x0, yy, rz(x0) - 0.1)], "net")
    for ya_, yb_ in ((y0, y0 + 0.7), (y1 - 0.7, y1)):         # south side: open front with short returns
        wl.box((t, yb_ - ya_, 1.0), "brick", loc=(x0 + t / 2, (ya_ + yb_) / 2, 0.65))
    c.part("walls", wl, desc="Plastered north wall (holds the electrics), brick half-walls with insect mesh above for air.")
    sh = MB()                                                  # rolling shutter, rolled up, in a hood under the low eave
    sh.box((0.32, y1 - y0 - 1.3, 0.3), "galv_dull", bevel=0.01, loc=(x0 - 0.1, ym, rz(x0) - 0.4))
    for y in (y0 + 0.7, y1 - 0.7):
        sh.box((0.05, 0.06, rz(x0) - 0.7), "galv", loc=(x0 - 0.03, y, 0.15 + (rz(x0) - 0.7) / 2))
    c.part("shutter", sh, explode=(-0.5, 0, 0), desc="Rolling shutter (open) on the south side.")
    return c


def solar_array(cid="solar_array", title="Solar array (6 × 540 W = 3.24 kWp)"):
    c = Component(
        cid, title, "Power",
        summary="Six 540 W panels on the packhouse roof, facing south at 13°. About 14–15 kWh on a clear Kolar day.",
        how=("Karnataka gives farm pump-set feeders 7 hours of three-phase power a day (sometimes much less in a drought), "
             "but a greenhouse needs its fans all afternoon. The panels run the house by day and charge the battery; the grid "
             "is the backup, not the other way round."),
        sensors=("inverter: PV watts, battery %, grid status",),
        control="Hybrid inverter (MPPT). The PLC sheds non-critical loads (robot charger, dosing) when the battery runs low.",
        state={"pv_kw": 2.6, "today_kwh": 9.8})
    tl = PH["tilt"]
    tilt = math.radians(tl)
    pw, ph_, pt = 2.279, 1.134, 0.035
    xh = PH["x1"] + 0.25                                       # high (north) edge of the roof sheet
    slope = (xh - (PH["x0"] - 0.25)) / math.cos(tilt)
    margin = (slope - 3 * ph_ - 0.04) / 2
    yc = (PH["y0"] + PH["y1"]) / 2
    nrm = (-math.sin(tilt), 0.0, math.cos(tilt))               # panels face south (−x), tilted 13°
    R = xform(rot=(0, -tl, 0)) @ xform(rot=(0, 0, 90))         # panel local x → along y, local y → down the slope
    n = 0
    rails = MB()
    for row in range(3):
        s = margin + ph_ / 2 + row * (ph_ + 0.02)              # distance down the slope from the high edge
        x = xh - s * math.cos(tilt)
        z = ph_roof_z(xh) - s * math.sin(tilt) + 0.012
        for col in (-1, 1):
            n += 1
            cy = yc + col * (pw / 2 + 0.01)
            cen = (x + nrm[0] * 0.075, cy, z + nrm[2] * 0.075)
            M = xform(cen) @ R
            p = MB()
            fw = 0.035
            for sx, sy, lx, ly in ((pw, fw, 0, ph_ / 2 - fw / 2), (pw, fw, 0, -ph_ / 2 + fw / 2),
                                   (fw, ph_, pw / 2 - fw / 2, 0), (fw, ph_, -pw / 2 + fw / 2, 0)):
                p.box((sx, sy, pt), "alu", M=M @ xform((lx, ly, 0)))
            p.box((pw - 2 * fw, ph_ - 2 * fw, 0.012), "solar_cell", M=M @ xform((0, 0, 0.008)))
            cw = (pw - 2 * fw - 0.02) / 24
            for k in range(1, 24):                             # 144 half-cut cells: 24 × 6 grid, split in the middle
                p.box((0.004 if k != 12 else 0.012, ph_ - 2 * fw, 0.001), "cell_line",
                      M=M @ xform((-pw / 2 + fw + 0.01 + k * cw, 0, 0.0145)))
            ch = (ph_ - 2 * fw) / 6
            for k in range(1, 6):
                p.box((pw - 2 * fw, 0.003, 0.001), "cell_line", M=M @ xform((0, -ph_ / 2 + fw + k * ch, 0.0145)))
            p.box((0.16, 0.1, 0.02), "plastic_black", M=M @ xform((0.2 * col, 0, -0.03)))  # junction box underneath
            c.part(f"panel_{n}", p, explode=(0.5 * nrm[0], 0, 0.5 + 0.35 * n),
                   desc=f"Panel {n}: Waaree 540 W mono-PERC half-cut (2.28 × 1.13 m, 144 half cells).")
        for dx in (-ph_ / 4, ph_ / 4):                         # 2 rails under every row
            xx = xh - (s + dx) * math.cos(tilt)
            zz = ph_roof_z(xh) - (s + dx) * math.sin(tilt) + 0.035
            rails.box((0.04, 2 * pw + 0.3, 0.04), "alu", loc=(xx, yc, zz), rot=(0, -tl, 0))
    c.part("rails", rails, desc="Aluminium mounting rails on L-feet through the roof sheet.")
    cb = MB()
    xw = PH["x1"] - 0.16                                       # down the inside face of the north wall to the DC box
    for k, m_ in enumerate(("cable", "wire_red")):
        y = PH["y0"] + 0.55 + 0.08 * k
        cable(cb, [(PH["x1"] + 0.1, y, ph_roof_z(PH["x1"]) + 0.05), (xw, y, ph_roof_z(PH["x1"]) - 0.3), (xw, y, 1.85)], r=0.008, m=m_)
    c.part("dc_cables", cb, desc="4 mm² DC solar cables down to the DC box.")
    return c


def hybrid_inverter(cid="hybrid_inverter", title="Hybrid solar inverter (3.6 kW, 48 V)"):
    c = Component(
        cid, title, "Power",
        summary="Turns solar DC into 230 V AC, charges the battery, and switches to battery in under 20 ms when grid power goes.",
        how="MPPT charger + inverter + grid charger in one box. Its RS485 port reports PV, battery and grid to the PLC.",
        sensors=("PV power", "battery %", "grid on/off"), control="Hybrid mode: solar first, battery second, grid last.",
        state={"mode": "solar", "load_w": 1240})
    b = MB()
    w, d, h = 0.33, 0.13, 0.45
    b.box((w, d, h), "plastic_white", bevel=0.01, loc=(0, d / 2, 0))
    b.box((w - 0.02, 0.004, 0.16), "plastic_black", loc=(0, d + 0.001, 0.09))
    b.box((0.09, 0.003, 0.05), "screen", loc=(-0.06, d + 0.004, 0.11))
    for k, m in enumerate(("led_green", "led_green", "led_amber")):
        b.cyl(0.005, 0.004, m, segs=12, axis="Y", loc=(0.06 + 0.025 * k, d + 0.004, 0.12))
    b.text("FOCUS 3.6 kW", 0.016, "plastic_white", M=xform((-0.02, d + 0.004, 0.05), sign_rot_facing("+y")))
    for k in range(5):
        b.cyl(0.011, 0.03, "plastic_black", segs=12, loc=(-0.12 + 0.06 * k, d / 2, -h / 2 - 0.015))
    c.part("inverter", b, explode=(0, 0.4, 0), desc="MuscleGrid Focus 3.6 kW, 48 V hybrid (MPPT + inverter + charger).")
    return c


def battery_bank(cid="battery_bank", title="LiFePO4 battery (48 V 100 Ah, 5.12 kWh)"):
    c = Component(
        cid, title, "Power",
        summary="Keeps the fans, pad pump and controller running through a power cut: about 3–4 hours of full cooling.",
        how=("LiFePO4 cells (safe, 4,000+ cycles) with a built-in BMS. The PLC keeps 30 % in reserve for the safety systems "
             "(controller, alarms, the hard-wired thermostat's fan) and sheds the robot charger first."),
        sensors=("BMS: state of charge, cell temperatures",), control="BMS + inverter; PLC load shedding.",
        state={"soc_pct": 86, "temp_c": 29})
    b = MB()
    w, d, h = 0.46, 0.2, 0.64
    b.box((w, d, h), "anthracite", bevel=0.012, loc=(0, d / 2, h / 2))
    b.box((w - 0.04, 0.004, 0.05), "plastic_black", loc=(0, d + 0.001, h - 0.09))
    for k in range(5):
        b.box((0.06, 0.004, 0.012), "accent_green" if k < 4 else "plastic_dark", loc=(-0.14 + 0.07 * k, d + 0.003, h - 0.09))
    b.text("LiFePO4  48 V  100 Ah", 0.018, "plastic_white", M=xform((0, d + 0.004, h - 0.16), sign_rot_facing("+y")))
    for x in (-0.15, 0.15):
        b.box((0.04, 0.03, 0.03), "wire_red" if x > 0 else "wire_black", loc=(x, d / 2, h + 0.015))
    c.part("battery", b, explode=(0, 0.45, 0), desc="Hykon HiLIFE 48 V 100 Ah LiFePO4 (5.12 kWh, 5-year warranty).")
    return c


def power_panel(cid="power_panel", title="AC/DC distribution boxes"):
    c = Component(cid, title, "Power", summary="DC box (fuses + surge arrester for the panels) and AC box (breakers, surge arrester, earth).",
                  how="Every circuit can be isolated for safe work; surge arresters protect against lightning on the long DC run.",
                  sensors=(), control="Manual isolators.", state={})
    b = MB()
    for k, lab in enumerate(("DC", "AC")):
        x = -0.2 + 0.4 * k
        b.box((0.3, 0.12, 0.34), "ral7035", bevel=0.008, loc=(x, 0.06, 0))
        b.box((0.24, 0.004, 0.08), "acrylic", loc=(x, 0.121, 0.04))
        b.text(lab, 0.04, "plastic_red" if lab == "DC" else "plastic_black", bold=True, M=xform((x, 0.124, -0.09), sign_rot_facing("+y")))
    cable(b, [(-0.2, 0.06, -0.17), (-0.2, 0.06, -0.35), (0.2, 0.06, -0.35), (0.2, 0.06, -0.17)], r=0.008)
    c.part("boxes", b, explode=(0, 0.4, 0), desc="IP65 DC + AC distribution boxes with MCBs and type-2 surge arresters.")
    return c


def cool_chamber(cid="cool_chamber", title="Zero-energy cool chamber (IARI design)"):
    c = Component(
        cid, title, "Farm",
        summary="A double brick wall with wet sand between: water evaporating from the sand keeps tomatoes 10–15 °C cooler, with no power.",
        how=("Developed at IARI, New Delhi. Wet the sand twice a day; the inside stays humid (90 %+) and cool. Tomatoes keep "
             "about 2 weeks instead of 1 – enough to skip a price crash. It costs about ₹7,000 to build."),
        sensors=("T/RH sensor inside (shared node)",), control="Farmer wets the sand (the app reminds).",
        state={"inside_c": 21.5, "outside_c": 33.0, "rh_pct": 93})
    b = MB()
    ow, od, h, gap, t = 1.65, 1.15, 0.675, 0.075, 0.115
    b.box((ow, od, 0.075), "brick", loc=(0, 0, 0.0375))
    for (sx, sy, lx, ly) in ((ow, t, 0, od / 2 - t / 2), (ow, t, 0, -od / 2 + t / 2),
                              (t, od - 2 * t, ow / 2 - t / 2, 0), (t, od - 2 * t, -ow / 2 + t / 2, 0)):
        b.box((sx, sy, h), "brick", loc=(lx, ly, 0.075 + h / 2))
    iw, idp = ow - 2 * (t + gap), od - 2 * (t + gap)
    for (sx, sy, lx, ly) in ((iw, t, 0, idp / 2 - t / 2), (iw, t, 0, -idp / 2 + t / 2),
                              (t, idp - 2 * t, iw / 2 - t / 2, 0), (t, idp - 2 * t, -iw / 2 + t / 2, 0)):
        b.box((sx, sy, h), "brick", loc=(lx, ly, 0.075 + h / 2))
    for (sx, sy, lx, ly) in ((ow - 2 * t, gap, 0, od / 2 - t - gap / 2), (ow - 2 * t, gap, 0, -od / 2 + t + gap / 2),
                              (gap, od - 2 * t - 2 * gap, ow / 2 - t - gap / 2, 0), (gap, od - 2 * t - 2 * gap, -ow / 2 + t + gap / 2, 0)):
        b.box((sx, sy, h - 0.02), "sand_wet", loc=(lx, ly, 0.075 + (h - 0.02) / 2))
    c.part("walls", b, desc="Double brick wall (165 × 115 × 67.5 cm) with a 7.5 cm wet-sand cavity.")
    lid = MB()
    lid.box((ow - 0.05, od - 0.05, 0.03), "straw", loc=(0, 0, 0))
    for k in range(5):
        lid.cyl(0.012, ow - 0.05, "straw", segs=8, axis="X", loc=(0, -od / 2 + 0.1 + k * (od - 0.2) / 4, 0.02))
    c.part("lid", lid, loc=(0.0, 0.0, 0.075 + h + 0.02), explode=(0, 0, 0.5), desc="Lid: khus/straw mat on a bamboo frame, kept wet.")
    return c


def crate(mb, loc, m="plastic_blue", fill=False, rng=None):
    x, y, z = loc
    w, d, h, t = 0.6, 0.4, 0.3, 0.012
    mb.box((w, d, 0.015), m, loc=(x, y, z + 0.0075))
    for k in range(3):
        zz = z + 0.05 + k * 0.1
        mb.box((w, t, 0.06), m, loc=(x, y - d / 2 + t / 2, zz))
        mb.box((w, t, 0.06), m, loc=(x, y + d / 2 - t / 2, zz))
        mb.box((t, d, 0.06), m, loc=(x - w / 2 + t / 2, y, zz))
        mb.box((t, d, 0.06), m, loc=(x + w / 2 - t / 2, y, zz))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((0.03, 0.03, h), m, loc=(x + sx * (w / 2 - 0.015), y + sy * (d / 2 - 0.015), z + h / 2))
    if fill:
        rng = rng or random.Random(4)
        for i in range(7):
            for j in range(5):
                tint = (1.0, 0.75 + 0.25 * rng.random(), 1.0)
                mb.sphere(0.035, "tomato", segs=14, rings=8, squash=0.85, tint=tint,
                          loc=(x - 0.24 + i * 0.08 + rng.uniform(-0.01, 0.01), y - 0.15 + j * 0.075, z + h - 0.03))


def pack_station(cid="pack_station", title="Packing station (table · scale · crates)"):
    c = Component(
        cid, title, "Farm",
        summary="Sort, weigh and crate the harvest. Every crate's weight goes into the twin, so yield per row is real data.",
        how="Stainless sorting table, a 100 kg platform scale with a serial output, and ventilated plastic crates (no bruising).",
        sensors=("platform scale (RS232 → node)",), control="—", state={"last_crate_kg": 12.4})
    tb = MB()
    tb.box((2.0, 0.9, 0.035), "stainless", loc=(0, 0, 0.85))
    tb.box((1.9, 0.8, 0.02), "galv_dull", loc=(0, 0, 0.25))
    for sx in (-1, 1):
        for sy in (-1, 1):
            tb.box((0.04, 0.04, 0.83), "stainless", loc=(sx * 0.95, sy * 0.4, 0.415))
    rng = random.Random(7)
    for i in range(18):
        tint = (1.0, 0.7 + 0.3 * rng.random(), 1.0)
        tb.sphere(0.036, "tomato", segs=14, rings=8, squash=0.85, tint=tint,
                  loc=(-0.7 + rng.uniform(0, 0.9), rng.uniform(-0.3, 0.3), 0.9))
    c.part("table", tb, desc="Stainless steel sorting table (2.0 × 0.9 m) with a lower shelf.")
    sc = MB()
    sc.box((0.45, 0.45, 0.08), "stainless", bevel=0.005, loc=(0, 0, 0.04))
    sc.cyl(0.015, 0.75, "steel_dark", segs=12, z0=0.08, loc=(0, -0.2, 0))
    sc.box((0.22, 0.08, 0.13), "ral7035", bevel=0.01, loc=(0, -0.2, 0.9))
    sc.box((0.14, 0.004, 0.04), "screen", loc=(0, -0.159, 0.93))
    sc.text("12.40", 0.03, "led_red", M=xform((0, -0.156, 0.93), sign_rot_facing("+y")))
    crate(sc, (0, 0, 0.08), "plastic_red", fill=True, rng=random.Random(11))
    c.part("scale", sc, loc=(1.45, 0.0, 0.0), explode=(0.4, 0, 0), desc="Phoenix NEP-100 platform scale (100 kg) with a crate on it.")
    cr = MB()
    rng = random.Random(3)
    for k, (dx, dy) in enumerate(((0, 0), (0.65, 0.0), (0.0, 0.45))):
        for lvl in range(3 - k):
            crate(cr, (dx, dy, 0.31 * lvl), ("plastic_blue", "plastic_green", "plastic_blue")[k],
                  fill=(lvl == 2 - k), rng=rng)
    c.part("crates", cr, loc=(-0.55, 1.05, 0.0), explode=(0, 0.5, 0), desc="Ventilated plastic crates (Nilkamal-type, ~20 kg each).")
    return c


# ═══════════════════════════ farm pond ═══════════════════════════
def farm_pond(cid="farm_pond", title="Farm pond (8 × 8 × 3 m, HDPE-lined)"):
    c = Component(
        cid, title, "Water",
        summary="Stores rain from the roofs and the field: about 85 m³ when full. The greenhouse draws from here first, the borewell only when it runs low.",
        how=("Kolar and Chikkaballapur borewells are very deep and many are drying up. A lined farm pond (Karnataka's Krishi "
             "Bhagya scheme pays up to 80 % of a 12 × 12 × 3 m pond) catches the monsoon. In summer the wet pad alone can "
             "evaporate a few hundred litres a day, so stored water decides how hot a month the crop can survive."),
        sensors=("ultrasonic level sensor over the water", "depth staff (manual check)"),
        control="PLC picks the source: pond first, borewell when the pond is below 20 %.",
        state={"level_m": round(POND_D + POND_WATER_Z, 2), "volume_m3": 34, "pct": 40})
    cx, cy = POND_C
    T, B, D = POND_TOP, POND_BOT, POND_D
    ln = MB()
    bm = bmesh.new()
    top = [bm.verts.new((cx + sx * T, cy + sy * T, 0.0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bot = [bm.verts.new((cx + sx * B, cy + sy * B, -D)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(list(reversed(bot)))
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((top[i], top[j], bot[j], bot[i]))
    ln.add(bm, "hdpe_liner", smooth=False)
    a = 0.6                                                    # liner laid flat over the top edge into the anchor trench
    for sx, sy, lx, ly in ((2 * T + 2 * a, a, 0, T + a / 2), (2 * T + 2 * a, a, 0, -T - a / 2),
                           (a, 2 * T, T + a / 2, 0), (a, 2 * T, -T - a / 2, 0)):
        ln.box((sx, sy, 0.012), "hdpe_liner", loc=(cx + lx, cy + ly, 0.006))
    c.part("liner", ln, desc="500-micron HDPE geomembrane liner (≈125 m²), anchored in a trench round the top.")
    bm_ = MB()
    for sx, sy, lx, ly in ((2 * T + 2 * a + 0.8, 0.4, 0, T + a + 0.2), (2 * T + 2 * a + 0.8, 0.4, 0, -T - a - 0.2),
                           (0.4, 2 * T + 2 * a, T + a + 0.2, 0), (0.4, 2 * T + 2 * a, -T - a - 0.2, 0)):
        bm_.box((sx, sy, 0.18), "gravel", bevel=0.08, loc=(cx + lx, cy + ly, 0.05))
    c.part("berm", bm_, desc="Soil berm over the anchor trench (keeps field mud out).")
    wt = MB()
    hw = pond_half(POND_WATER_Z)
    wt.box((2 * hw, 2 * hw, 0.01), "pond_water", loc=(cx, cy, POND_WATER_Z - 0.005))
    c.part("water", wt, desc="Stored water (shown 1.8 m deep, ≈34 m³ – 40 %).")
    st = MB()                                                  # depth staff on the west slope
    sxp = cx - 2.5
    zb = -D * (T - 2.5) / (T - B)                               # the slope's height 2.5 m from the centre
    st.box((0.05, 0.05, 0.5 - zb), "galv", loc=(sxp, cy, (0.5 + zb) / 2))
    for k in range(int((0.5 - zb) / 0.25)):
        z = zb + 0.125 + 0.25 * k
        st.box((0.012, 0.12, 0.24), "plastic_red" if k % 2 else "plastic_white", loc=(sxp + 0.031, cy, z))
    c.part("depth_staff", st, explode=(0, 0, 0.6), desc="Painted depth staff, 25 cm bands (a manual check of the sensor).")
    rr = MB()                                                  # stone apron under the rain inlet (north-east)
    rng = random.Random(9)
    for i in range(26):
        s = rng.uniform(0.12, 0.24)
        u = rng.uniform(0.0, 1.0)
        x = 8.4 + rng.uniform(-0.35, 0.35)
        y = cy + T - u * (T - B) * 0.5
        z = -u * D * 0.5 + 0.03
        rr.box((s, s * 0.8, s * 0.5), "concrete", bevel=0.03, loc=(x, y, z), rot=(rng.uniform(-20, 20), 45, rng.uniform(0, 90)))
    c.part("inlet_apron", rr, desc="Stone apron where the rain pipe spills in (stops the inflow tearing the liner).")
    return c


def pond_fence(cid="pond_fence", title="Pond safety fence (chain-link, 1.8 m)"):
    c = Component(cid, title, "Water",
                  summary="A farm pond is a drowning risk for children and animals: a fence with a closed gate is a must.",
                  how="GI chain-link on cement posts every 2.5 m, with a lockable gate on the greenhouse side.",
                  sensors=(), control="—", state={})
    x0, x1, y0, y1 = FENCE
    h = 1.8
    po, mesh = MB(), MB()
    gate = (4.4, 5.6)
    for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        L_ = math.hypot(bx - ax, by - ay)
        n = max(1, round(L_ / 2.5))
        for k in range(n + 1):
            u = k / n
            px, py = ax + (bx - ax) * u, ay + (by - ay) * u
            po.box((0.1, 0.1, h + 0.1), "concrete", loc=(px, py, (h + 0.1) / 2))
        segs = [(0.0, 1.0)]
        if ay == y1 and by == y1:                              # gate gap on the north side
            ua, ub = sorted(((gate[0] - ax) / (bx - ax), (gate[1] - ax) / (bx - ax)))
            segs = [(0.0, ua), (ub, 1.0)]
        for ua, ub in segs:
            pa = (ax + (bx - ax) * ua, ay + (by - ay) * ua)
            pb = (ax + (bx - ax) * ub, ay + (by - ay) * ub)
            ln_ = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
            ang = math.degrees(math.atan2(pb[1] - pa[1], pb[0] - pa[0]))
            mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            mesh.box((ln_, 0.004, h - 0.1), "chainlink", loc=(mid[0], mid[1], 0.05 + (h - 0.1) / 2), rot=(0, 0, ang))
            for z in (0.08, h - 0.02):
                mesh.box((ln_, 0.012, 0.012), "galv", loc=(mid[0], mid[1], z), rot=(0, 0, ang))
    c.part("posts", po, desc="Cement fence posts.")
    c.part("chain_link", mesh, desc="GI chain-link mesh with top and bottom wires.")
    gt = MB()
    gw = gate[1] - gate[0]
    gt.box((gw - 0.05, 0.035, 0.035), "galv", loc=(gw / 2, 0, 0.1))
    gt.box((gw - 0.05, 0.035, 0.035), "galv", loc=(gw / 2, 0, h - 0.1))
    for x in (0.03, gw - 0.08):
        gt.box((0.035, 0.035, h - 0.15), "galv", loc=(x, 0, h / 2))
    gt.box((gw - 0.1, 0.004, h - 0.25), "chainlink", loc=(gw / 2, 0, h / 2))
    gt.box((0.06, 0.05, 0.12), "plastic_red", loc=(gw - 0.12, 0, 1.0))
    c.part("gate", gt, loc=(gate[0], y1, 0.0), rot=(0, 0, 0), explode=(0, 0.8, 0), desc="Lockable gate.")
    return c


def pond_pump(cid="pond_pump", title="Pond pump (Kirloskar Chhotu 0.5 HP) → water tank"):
    c = Component(
        cid, title, "Water",
        summary="Lifts pond water into the greenhouse's 500 L tank through a screen filter.",
        how=("The tank's float switch calls for water; the PLC runs this pump if the pond is above 20 %, otherwise it "
             "switches to the borewell. A foot valve with a strainer keeps the pipe primed and stops leaves."),
        sensors=("pump current", "tank float"), control="PLC relay; dry-run cut-off from the pond level sensor.",
        state={"running": False, "source": "pond"})
    px, py = 6.2, -5.15
    pl = MB()
    pl.box((0.55, 0.4, 0.15), "concrete", loc=(px, py, 0.075))
    c.part("plinth", pl, desc="Concrete pump plinth.")
    pm = MB()
    kirloskar_chhotu(pm)
    c.part("pump", pm, loc=(px, py, 0.15), rot=(0, 0, -90), explode=(0, 0.5, 0.4), desc="Kirloskar Chhotu 0.5 HP monoblock pump.")
    pp = MB()
    zin = 0.15 + 0.055
    edge = POND_C[1] + pond_half(POND_WATER_Z)                 # where the water meets the north slope
    pp.sweep([(px, py - 0.105, zin), (px, -5.65, 0.26), (px, -6.5, 0.04), (px, edge, POND_WATER_Z + 0.06),
              (px, edge - 0.5, -1.55)], 0.021, "pe_black", segs=12, fillet=0.25)
    pp.cyl(0.05, 0.16, "steel_dark", segs=16, loc=(px, edge - 0.5, -1.62))                   # foot valve + strainer
    top = 0.15 + 0.21
    pvc_run(pp, [(px, py - 0.09, top), (px, py - 0.09, 0.45), (px, py + 0.3, 0.45), (px, py + 0.3, 0.05),
                 (px, -2.95, 0.05), (2.2, -2.95, 0.05)], 0.016)
    c.part("pipes", pp, desc="32 mm suction (with foot valve) and 32 mm PVC delivery to the tank line.")
    return c


def level_pond(cid="level_pond", title="Pond level sensor (ultrasonic)"):
    c = Component(cid, title, "Sensors",
                  summary="Measures the water level from above (no contact), so the twin always knows how many days of water are left.",
                  how="Same DFRobot ultrasonic sensor as the tank, on an arm over the water, read by a small solar-powered node.",
                  sensors=("ultrasonic distance",), control="—", state={"level_m": 1.8, "pct": 40})
    px, py = -0.35, -9.0
    m = MB()
    m.box((0.06, 0.06, 1.3), "galv", loc=(px, py, 0.65))
    m.box((2.85, 0.04, 0.04), "galv", loc=(px + 1.4, py, 1.25))
    m.box((0.18, 0.1, 0.24), "plastic_white", bevel=0.01, loc=(px, py - 0.08, 1.0))
    m.box((0.32, 0.22, 0.02), "solar_cell", loc=(px, py, 1.38), rot=(0, 0, 0))
    m.box((0.34, 0.24, 0.015), "alu", loc=(px, py, 1.365))
    cable(m, [(px + 0.05, py - 0.08, 1.12), (px + 0.2, py, 1.22), (px + 2.7, py, 1.22)], r=0.004)
    c.part("mast", m, desc="Post, arm, node box (ESP32 + battery) with a small solar panel.")
    s = MB()
    s.cyl(0.03, 0.05, "plastic_black", segs=20, z0=0.0)
    s.cyl(0.02, 0.006, "plastic_dark", segs=20, z0=-0.006)
    c.part("sensor", s, loc=(px + 2.75, py, 1.2), explode=(0, 0, -0.3), desc="DFRobot A02YYUW ultrasonic sensor looking down at the water.")
    return c


def rain_harvest(cid="rain_harvest", title="Rainwater harvesting (gutters → first flush → pond)"):
    c = Component(
        cid, title, "Water",
        summary="The roof's gutters send rain to the pond. The first dirty litres of each shower go to a first-flush chamber, not the pond.",
        how=("About 50 m² of greenhouse roof × Kolar's ~750 mm a year ≈ 30–35 m³ a year from the roof alone; the pond also "
             "catches field runoff. The first-flush chamber fills first with the dust and bird droppings, then clean water "
             "overflows to the pond."),
        sensors=(), control="—", state={"this_year_m3": 21})
    p = MB()
    r = 0.055
    for sy in (-1, 1):
        y = sy * (W / 2 + 0.12)
        pvc_run(p, [(L + 0.1, y, GH + 0.02), (L + 0.1, y, 0.2)], r, m="pvc_white")
    pvc_run(p, [(L + 0.1, W / 2 + 0.12, 0.2), (L + 0.45, W / 2 + 0.12, 0.08), (L + 0.45, -W / 2 - 0.12, 0.08)], r, m="pvc_white")
    pvc_run(p, [(L + 0.1, -W / 2 - 0.12, 0.2), (L + 0.1, -W / 2 - 0.12, 0.08), (L + 0.1, -5.0, 0.08), (8.4, -5.7, 0.08),
                (8.4, -6.45, 0.08)], r, m="pvc_white")
    ff = MB()                                                  # first-flush chamber (90 mm, 1.1 m) beside the south downpipe
    fx, fy = L + 0.1, -W / 2 - 0.32
    ff.cyl(0.045, 1.1, "pvc_white", segs=20, z0=0.12, loc=(fx, fy, 0))
    ff.cyl(0.055, 0.05, "pvc_grey", segs=20, z0=0.07, loc=(fx, fy, 0))
    ff.sweep([(fx, -W / 2 - 0.12, 1.25), (fx, fy, 1.25)], 0.04, "pvc_white", segs=16)
    c.part("pipes", p, desc="110 mm downpipes from both eave gutters, run along the ground to the pond.")
    c.part("first_flush", ff, explode=(0.4, 0, 0), desc="First-flush diverter chamber with a slow-drain cap.")
    return c


def borewell(cid="borewell", title="Borewell head (existing) + pump starter"):
    c = Component(
        cid, title, "Water",
        summary="The farm's existing borewell: a submersible pump hundreds of feet down. Now only the backup water source.",
        how=("In Kolar, borewells often go 1,000+ ft deep and yield less every year. The PLC only starts it when the pond is "
             "low, and logs every litre, so the farmer sees exactly how much groundwater the crop takes."),
        sensors=("flow (shared meter)", "starter: running/tripped"), control="PLC contact into the starter panel.",
        state={"running": False, "litres_today": 0},
        real="The farm's own borewell + submersible pump (not part of the GH-01 bill)", cost="already on the farm")
    bx, by = BORE
    m = MB()
    m.box((0.8, 0.8, 0.15), "concrete", loc=(bx, by, 0.075))
    m.cyl(0.0889, 0.45, "steel_dark", segs=28, z0=0.15, loc=(bx, by, 0))
    m.cyl(0.11, 0.03, "steel_dark", segs=28, z0=0.6, loc=(bx, by, 0))
    pvc_run(m, [(bx, by, 0.63), (bx, by, 0.95), (bx + 0.45, by, 0.95), (bx + 0.45, by, 0.06)], 0.021, m="galv")
    m.box((0.1, 0.07, 0.12), "brass", loc=(bx + 0.25, by, 0.95))                              # gate valve body
    m.cyl(0.05, 0.015, "pvc_red", segs=16, axis="Z", loc=(bx + 0.25, by, 1.05))
    pvc_run(m, [(bx + 0.45, by, 0.06), (bx + 0.45, -2.95, 0.01), (1.2, -2.95, 0.01)], 0.016)   # half-buried across the path
    c.part("head", m, desc="7\" casing with well cap, 1¼\" GI riser, gate valve, and the pipe to the tank.")
    sp = MB()
    sp.box((0.05, 0.05, 1.4), "galv", loc=(0, 0, 0.7))
    sp.box((0.3, 0.16, 0.4), "ral7035", bevel=0.01, loc=(0, -0.11, 1.15))
    for k, m_ in enumerate(("plastic_green", "plastic_red")):
        sp.cyl(0.018, 0.02, m_, segs=16, axis="-Y", loc=(-0.05 + 0.1 * k, -0.2, 1.1))
    sp.box((0.08, 0.004, 0.05), "screen", loc=(0, -0.191, 1.25))
    cable(sp, [(0, -0.11, 0.95), (0.1, 0.1, 0.3), (0.5, 0.35, 0.12)], r=0.007)
    c.part("starter", sp, loc=(bx - 0.6, by + 0.5, 0.0), explode=(-0.4, 0, 0), desc="Submersible pump starter panel (dry-run + phase protection).")
    return c


def tank_valves(cid="source_valves", title="Water source valves (pond / borewell)"):
    c = Component(cid, title, "Water", summary="Two motorised ball valves pick which source fills the tank: pond first, borewell as backup.",
                  how="The PLC opens one at a time; the tank's float switch decides when to fill.",
                  sensors=("valve end switches",), control="PLC.", state={"open": "pond"})
    m = MB()
    pvc_run(m, [(2.2, -2.95, 0.05), (2.2, -2.95, 0.3)], 0.016)
    pvc_run(m, [(1.2, -2.95, 0.01), (1.2, -2.95, 0.3), (2.2, -2.95, 0.3)], 0.016)
    for x in (1.45, 2.0):
        m.box((0.07, 0.06, 0.06), "brass", loc=(x, -2.95, 0.3))
        m.box((0.08, 0.08, 0.07), "plastic_black", loc=(x, -2.95, 0.37))
    pvc_run(m, [(1.6, -2.95, 0.3), (1.6, -2.95, 1.08), (1.6, -2.6, 1.08), (TANK_INLET[0], TANK_INLET[1] - 0.3, TANK_INLET[2])], 0.016)
    c.part("valves", m, desc="2 × 1\" motorised ball valves (24 V) + tee into the tank inlet.")
    return c


def farm_sign(cid="farm_sign", title="GH-01 sign"):
    c = Component(cid, title, "Farm", summary="The sign at the entrance.", sensors=(), control="—", state={},
                  real="Powder-coated steel sign on two posts", cost="≈₹4k")
    m = MB()
    w, h = 1.6, 0.8
    for y in (-0.7, 0.7):
        m.box((0.06, 0.06, 2.0), "anthracite", loc=(0, y, 1.0))
    m.box((0.04, w, h), "signboard", bevel=0.01, loc=(0, 0, 1.55))
    m.box((0.01, w - 0.1, 0.012), "accent_green", loc=(-0.021, 0, 1.55 - h / 2 + 0.07))
    m.text("GH-01", 0.26, "plastic_white", bold=True, M=xform((-0.022, 0, 1.68), sign_rot_facing("-x")))
    m.text("AI + ROBOTICS TOMATO GREENHOUSE", 0.052, "plastic_white", M=xform((-0.022, 0, 1.47), sign_rot_facing("-x")))
    m.text("DIGITAL TWIN · SOLAR · RAIN-FED", 0.045, "accent_green", M=xform((-0.022, 0, 1.39), sign_rot_facing("-x")))
    c.part("board", m, desc="Powder-coated sign on two posts.")
    return c


# ═══════════════════════════ farm v4 (11 Oct 2026): close the loops, shelter the house ═══════════════════════════
DRAIN_SKID = (-1.15, 1.95)            # outside the front (south) gable, west of the entry room
MAST = (0.6, 4.3)                     # between the house and the packhouse
VERMI = dict(x0=7.0, y0=6.6)          # north of the packhouse
BELT_W, BELT_N = 24.0, 52.0           # windbreak: west row line (y), north row line (x), outside GH-02 (x 13…45, y ±16)


def drain_recycle(cid="drain_recycle", title="Drain recycling: sump → screen filter → UV-C → back to the mix tank"):
    c = Component(
        cid, title, "Fertigation",
        summary=("Every day about a quarter of the water given to the slabs drains out, still full of fertiliser. This skid "
                 "collects it, filters it, kills pathogens with UV-C and sends it back into the mix tank."),
        how=("The three gutter outlets feed a 32 mm header to a buried 200 L sump. A float starts a small pump that pushes "
             "the drain water through a 120-mesh screen filter and a 55 W UV-C steriliser (tomato growers dose about "
             "250 mJ/cm²; at ~35 L a day it gets far more) into the mix tank. The PLC lets it make up at most 30 % of each "
             "new batch, and only while the drain EC is below 5.5 mS/cm and the UV lamp is on; otherwise the drain goes "
             "to the soak pit as before."),
        sensors=("sump float", "drain EC + pH probe (in line)", "UV lamp current"),
        control="PLC: recycle share ≤ 30 % of each batch; blocked if UV is off or drain EC > 5.5.",
        state={"recycled_today_L": 31, "drain_ec": 4.6, "uv": "on", "share_pct": 24})
    sx, sy = DRAIN_SKID
    h = MB()
    yy = (-1.6, 0.0, 1.6)
    # 14 Oct 2026: the header runs in a channel 6 cm below the floor (under the robot's handover plates), not across the
    # aisle mouths on top of it
    for y in yy:
        pvc_run(h, [(2.22, y, 0.1), (2.22, y, -0.06)], 0.02)
    pvc_run(h, [(2.22, yy[0], -0.06), (2.22, 2.3, -0.06), (0.08, 2.3, -0.06), (sx + 0.35, 2.3, -0.06), (sx + 0.35, sy, -0.06)], 0.02)
    c.part("drain_header", h, desc="32 mm PVC drain header from the three gutter outlets to the sump (in a floor channel, under the robot's path).")
    s = MB()
    s.cyl(0.34, 0.08, "concrete", segs=32, z0=0.0, loc=(sx, sy, 0))
    s.cyl(0.29, 0.02, "hdpe_blue", segs=32, z0=0.08, loc=(sx, sy, 0))
    s.cyl(0.015, 0.25, "pvc_white", segs=12, z0=0.08, loc=(sx - 0.2, sy + 0.18, 0))
    c.part("sump", s, explode=(0, 0, 0.3), desc="200 L HDPE drum buried as a sump, concrete ring + lid, vent pipe.")
    k = MB()
    cx0, cy0 = sx - 0.75, sy - 0.55
    for dx in (0, 1.5):
        for dy in (0, 1.1):
            k.box((0.05, 0.05, 2.0), "galv", loc=(cx0 + dx, cy0 + dy, 1.0))
    k.box((1.75, 1.35, 0.03), "galv_dull", loc=(cx0 + 0.75, cy0 + 0.55, 2.02), rot=(0, 6, 0))
    k.box((1.5, 0.5, 0.04), "steel_dark", loc=(cx0 + 0.75, cy0 + 0.2, 0.45))
    for dx in (0.02, 1.48):
        k.box((0.04, 0.04, 0.45), "steel_dark", loc=(cx0 + dx, cy0 + 0.2, 0.225))
    c.part("canopy", k, desc="GI frame + sheet canopy over the skid (keeps sun off the UV unit and electronics).")
    p = MB()
    kirloskar_chhotu(p)
    c.part("pump", p, loc=(cx0 + 0.3, cy0 + 0.2, 0.47), explode=(0, -0.3, 0.1), desc="0.5 HP transfer pump (sump → filter → UV).")
    f = MB()
    f.cyl(0.055, 0.32, "pvc_grey", segs=24, z0=0.0)
    f.cyl(0.062, 0.05, "plastic_black", segs=24, z0=0.3)
    f.cyl(0.03, 0.08, "plastic_blue", segs=16, axis="X", loc=(0.0, 0, 0.2))
    c.part("screen_filter", f, loc=(cx0 + 0.62, cy0 + 0.2, 0.47), explode=(0, -0.3, 0.2),
           desc="120-mesh screen filter (stops coco fibre before the UV).")
    u = MB()
    u.cyl(0.045, 0.9, "stainless", segs=28, axis="X", loc=(0, 0, 0))
    for x in (-0.47, 0.47):
        u.cyl(0.05, 0.04, "stainless", segs=28, axis="X", loc=(x, 0, 0))
    for x in (-0.35, 0.35):
        u.cyl(0.016, 0.07, "stainless", segs=12, loc=(x, 0, 0.06))
    u.box((0.22, 0.08, 0.14), "plastic_white", bevel=0.01, loc=(0, 0.11, -0.02))
    u.cyl(0.008, 0.004, "led_blue", segs=12, axis="Y", loc=(0.06, 0.152, 0.0))
    u.cyl(0.012, 0.006, "plastic_purple", segs=16, axis="X", loc=(0.497, 0, 0))
    c.part("uv_steriliser", u, loc=(cx0 + 0.75, cy0 + 0.75, 1.05), explode=(0, 0.3, 0.25),
           desc="55 W UV-C steriliser, 304 stainless chamber with quartz sleeve (~2,000 L/h).")
    ec = MB()
    ec.cyl(0.02, 0.12, "pvc_grey", segs=16, axis="X", loc=(0, 0, 0))
    ec.cyl(0.012, 0.14, "plastic_black", segs=12, z0=0.0, loc=(0.0, 0, 0.0))
    c.part("drain_ec_probe", ec, loc=(cx0 + 1.15, cy0 + 0.2, 0.62), explode=(0, -0.2, 0.2), desc="In-line EC + pH probe on the recycled water.")
    r = MB()
    pvc_run(r, [(cx0 + 0.39, cy0 + 0.2, 0.68), (cx0 + 0.62, cy0 + 0.2, 0.68)], 0.016)
    pvc_run(r, [(cx0 + 0.62, cy0 + 0.2, 0.84), (cx0 + 0.62, cy0 + 0.75, 0.84), (cx0 + 0.3, cy0 + 0.75, 0.84),
                (cx0 + 0.3, cy0 + 0.75, 1.05)], 0.016)
    pvc_run(r, [(cx0 + 1.2, cy0 + 0.75, 1.05), (cx0 + 1.2, cy0 + 0.2, 1.05), (cx0 + 1.2, cy0 + 0.2, 0.62)], 0.016)
    pvc_run(r, [(cx0 + 1.27, cy0 + 0.2, 0.62), (0.1, cy0 + 0.2, 0.62), (0.1, cy0 + 0.2, 2.4), (0.1, -1.95, 2.4), (0.45, -1.95, 2.4),
                (0.45, -1.95, 1.08)], 0.016, m="pvc_blue")
    c.part("return_line", r, desc="25 mm pipework: pump → filter → UV → EC probe → overhead (blue) to the mix tank.")
    return c


def _casuarina(mb, x, y, h, seed):
    """A young casuarina: thin grey-brown trunk and a tall, narrow, feathery crown (layered cones)."""
    rnd = random.Random(seed)
    mb.cyl(0.07, h * 0.55, "stem_old", segs=8, z0=0.0, loc=(x, y, 0))
    z = h * 0.25
    for k in range(4):
        rr = (0.9 - 0.18 * k) * (0.9 + 0.2 * rnd.random())
        hh = h * (0.34 - 0.04 * k)
        mb.cyl(rr, hh, "leaf", segs=9, r_top=0.05, z0=z, loc=(x + rnd.uniform(-0.05, 0.05), y + rnd.uniform(-0.05, 0.05), 0))
        z += hh * 0.62


def windbreak(cid="windbreak", title="Casuarina windbreak (west + north, 2 staggered rows, 76 trees)"):
    c = Component(
        cid, title, "Farm",
        summary=("Karnataka's strong winds come from the west / south-west before the monsoon and the north-west in winter. "
                 "Two staggered rows of casuarina on those sides slow the wind before it reaches the film."),
        how=("A belt about half see-through (40-60 % porosity) works best: a solid wall makes turbulence behind it. It "
             "shelters roughly 10x its height downwind, and the house should sit 2-5 heights behind it. Casuarina grows "
             "fast (~6 m in 2-3 years, 15 m mature) and is the usual South Indian choice. Planted 3 m apart, 2 rows."),
        sensors=("weather station wind (outside the belt)",), control="—",
        state={"trees": 76, "height_m": 6.0, "wind_cut_pct": 45})
    for row, off in enumerate((0.0, 2.2)):
        m = MB()
        n = 0
        for x in [-14.0 + 3.0 * i + (1.5 if row else 0) for i in range(22)]:
            _casuarina(m, x, BELT_W + off, 6.0 + 0.8 * math.sin(x * 1.7), seed=int(100 * x) + row)
            n += 1
        for y in [-22.0 + 3.0 * i + (1.5 if row else 0) for i in range(16)]:
            _casuarina(m, BELT_N + off, y, 6.0 + 0.8 * math.sin(y * 1.3), seed=int(100 * y) + 7 + row)
            n += 1
        c.part(f"row_{row + 1}", m, desc=f"Row {row + 1}: {n} casuarina, 3 m apart (staggered with the other row).")
    return c


def comms_mast(cid="comms_mast", title="Comms mast: 4G router + antenna + lightning rod"):
    c = Component(
        cid, title, "Control",
        summary=("Every alert to the farmer leaves the farm over 4G. The mast lifts the antenna above the packhouse for a "
                 "usable signal, and its lightning rod protects the solar array and the house."),
        how=("A 6 m GI mast with guy wires. At the top: a copper lightning rod tied to its own earth pit by a 25 x 3 mm "
             "copper strip. Below it: an outdoor 4G omni antenna and an IP65 box with an industrial 4G router (Teltonika "
             "RUT241) on a SIM with a data plan. The twin's Telegram alerts and an SMS fallback go out through it."),
        sensors=("4G signal (RSRP)", "router heartbeat"), control="—", state={"signal": "-95 dBm (good)", "alerts_today": 0})
    mx, my = MAST
    m = MB()
    m.box((0.5, 0.5, 0.12), "concrete", loc=(mx, my, 0.06))
    m.cyl(0.038, 6.0, "galv", segs=20, z0=0.12, loc=(mx, my, 0))
    for a in (0, 120, 240):
        ex, ey = mx + 2.6 * math.cos(math.radians(a)), my + 2.6 * math.sin(math.radians(a))
        cable(m, [(mx, my, 4.6), (ex, ey, 0.05)], r=0.003, m="galv", fillet=0.0)
        m.box((0.12, 0.12, 0.1), "concrete", loc=(ex, ey, 0.05))
    m.box((0.26, 0.12, 0.32), "plastic_white", bevel=0.01, loc=(mx, my - 0.09, 2.2))
    m.cyl(0.006, 0.006, "led_green", segs=10, axis="-Y", loc=(mx + 0.06, my - 0.152, 2.3))
    c.part("mast", m, desc="6 m GI mast on a concrete footing, 3 guy wires, IP65 box with the 4G router (Teltonika RUT241).")
    a = MB()
    a.cyl(0.03, 0.75, "plastic_white", segs=16, z0=0.0, loc=(mx, my - 0.12, 5.2))
    a.box((0.04, 0.12, 0.04), "galv", loc=(mx, my - 0.06, 5.25))
    cable(a, [(mx, my - 0.12, 5.2), (mx + 0.04, my - 0.1, 4.0), (mx + 0.02, my - 0.1, 2.36)], r=0.005)
    c.part("antenna", a, explode=(0, -0.4, 0.3), desc="Outdoor 4G omni antenna (8 dBi) + LMR cable down to the router.")
    lr = MB()
    lr.cyl(0.009, 1.0, "copper", segs=12, z0=6.1, loc=(mx, my, 0), r_top=0.002)
    lr.box((0.025, 0.004, 6.0), "copper", loc=(mx + 0.045, my, 3.1))
    lr.cyl(0.18, 0.06, "concrete", segs=20, z0=0.0, loc=(mx + 0.9, my + 0.4, 0))
    lr.box((0.9, 0.025, 0.004), "copper", loc=(mx + 0.47, my + 0.2, 0.01), rot=(0, 0, 24))
    c.part("lightning_rod", lr, explode=(0, 0, 0.6), desc="Copper lightning rod + 25 x 3 mm copper down-conductor to its own earth pit.")
    # 12 Oct 2026: when 4G drops, alerts still need a way out, and someone on the farm needs to hear them
    sm = MB()
    sm.box((0.16, 0.08, 0.2), "plastic_white", bevel=0.01, loc=(mx, my - 0.09, 1.82))
    sm.cyl(0.006, 0.18, "plastic_black", segs=10, z0=1.92, loc=(mx + 0.05, my - 0.09, 0))
    sm.cyl(0.004, 0.004, "led_amber", segs=10, axis="-Y", loc=(mx - 0.04, my - 0.132, 1.86))
    c.part("sms_modem", sm, explode=(0, -0.3, 0), desc="Backup 2G SMS modem on a second operator's SIM (sends alerts when 4G data is down).")
    bc = MB()
    bc.box((0.12, 0.14, 0.04), "galv", loc=(mx, my - 0.1, 2.62))
    bc.cyl(0.07, 0.03, "plastic_black", segs=20, z0=2.64, loc=(mx, my - 0.12, 0))
    bc.cyl(0.06, 0.11, "plastic_orange", segs=20, z0=2.67, loc=(mx, my - 0.12, 0), r_top=0.045)
    bc.cyl(0.05, 0.05, "plastic_black", segs=16, axis="-Y", loc=(mx + 0.11, my - 0.12, 2.6))
    c.part("beacon_siren", bc, explode=(0, -0.3, 0.3), desc="12 V amber beacon + 110 dB siren: critical alarms while the farm is offline.")
    return c


def vermicompost(cid="vermicompost", title="Vermicompost: 2 HDPE vermibeds under a shade roof"):
    c = Component(
        cid, title, "Farm",
        summary=("Pruned leaves, old plants after each crop and spoilt fruit go to two worm beds instead of being burnt. "
                 "Out comes vermicompost for the farm's field crops, and vermiwash."),
        how=("Two 12 x 4 x 2 ft HDPE vermibeds (about 1 tonne each) under a 50 % shade-net roof, kept moist. Diseased "
             "material (e.g. blight leaves) is bagged and removed instead of composted."),
        sensors=(), control="—", state={"beds": 2, "next_harvest": "in 6 weeks"})
    x0, y0 = VERMI["x0"], VERMI["y0"]
    s = MB()
    for dx in (0, 4.4):
        for dy in (0, 3.0):
            s.box((0.05, 0.05, 2.2), "galv", loc=(x0 + dx, y0 + dy, 1.1))
    s.box((4.6, 3.2, 0.01), "net", loc=(x0 + 2.2, y0 + 1.5, 2.2))
    c.part("shade_roof", s, desc="GI posts + 50 % green shade-net roof.")
    for k, yb in enumerate((y0 + 0.75, y0 + 2.25)):
        b = MB()
        b.box((3.66, 1.22, 0.61), "plastic_green", loc=(x0 + 2.2, yb, 0.305))
        b.box((3.56, 1.12, 0.02), "soil", loc=(x0 + 2.2, yb, 0.5))
        b.box((3.4, 1.0, 0.04), "straw", loc=(x0 + 2.2, yb, 0.52))
        c.part(f"bed_{k + 1}", b, explode=(0, 0, 0.3), desc="12 x 4 x 2 ft HDPE vermibed: crop waste + dung + earthworms, straw cover.")
    return c
