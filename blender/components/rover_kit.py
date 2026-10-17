"""R1 rover as a build kit (16 Oct 2026): the same rover as components/rover.py, split into the pieces you actually buy and
bolt together, plus the electronics that rover.py keeps hidden in its box. Used by the "Build R1" tutorial video:
every piece is its own object, assembled in the rover frame (+x forward, z up, ground at 0), tagged with the build step
it belongs to. The video lays them out on the floor, then flies each one into place.

Real parts and sizes (see tutorials/02-r1-rover/README.md for the list and prices):
  2040 V-slot extrusion (20 x 40 mm), 6 mm aluminium wheel plates, 10" hub motors, 24 V 30 Ah LiFePO4,
  ZS-X11H BLDC drivers (~63 x 45 mm board on an aluminium heat plate), Arduino Mega 2560 (101.5 x 53.3 mm),
  Raspberry Pi 5 + AI HAT+, 16-channel 5 V relay module (~180 x 87 mm), potted 24 V DC-DC converters (~46 x 46 x 20 mm),
  MIDI fuse holder, red battery isolator switch, 24 V 100 A DC contactor, 7-port USB 3.0 hub, IP65 box 300 x 220 x 120 mm.
"""
import math

import gh
from gh import MB, bm_box, bm_cyl, xform
from parts import cable, screw

from components import rover as R

gh.SPEC.update({
    "pcb_green": dict(color=(0.03, 0.28, 0.08), rough=0.35, coat=0.3),
    "pcb_blue_ard": dict(color=(0.0, 0.33, 0.55), rough=0.35, coat=0.3),
    "relay_blue": dict(color=(0.05, 0.22, 0.72), rough=0.35),
    "term_blue": dict(color=(0.08, 0.32, 0.75), rough=0.45),
    "term_green": dict(color=(0.08, 0.5, 0.2), rough=0.45),
    "header_white": dict(color=(0.92, 0.92, 0.88), rough=0.45),
    "cap_black": dict(color=(0.04, 0.04, 0.05), rough=0.35, coat=0.4),
    "potted_alu": dict(color=(0.7, 0.71, 0.72), metal=1, rough=0.4),
    "wire_yellow": dict(color=(0.9, 0.75, 0.02), rough=0.4),
    "wire_green2": dict(color=(0.05, 0.55, 0.15), rough=0.4),
    "wire_blue2": dict(color=(0.05, 0.25, 0.75), rough=0.4),
    "wire_red2": dict(color=(0.75, 0.04, 0.03), rough=0.4),
    "isolator_red": dict(color=(0.78, 0.03, 0.02), rough=0.35, coat=0.4),
    "clear_cover": dict(color=(0.85, 0.9, 0.95), rough=0.05, alpha=0.35, coat=1.0),
    "strap_black": dict(color=(0.03, 0.03, 0.03), rough=0.7),
    "wood_block": dict(color=(0.55, 0.38, 0.2), rough=0.8, noise=("coco", 30.0, 0.2)),
})

MM = 0.001
BOX = dict(x0=0.045, x1=0.345, w=0.22, h=0.12)        # IP65 electronics box on the deck front
PANEL_X = (-0.11, 0.11)                               # side panels between the wheels


class Piece:
    def __init__(self, name, step, ob, label="", sub=""):
        self.name, self.step, self.ob, self.label, self.sub = name, step, ob, label, sub


class Kit:
    def __init__(self, coll):
        self.coll = coll
        self.pieces = []

    def add(self, name, step, mb, label="", sub="", loc=(0, 0, 0), rot=(0, 0, 0)):
        ob = mb.build(f"kit.{name}") if isinstance(mb, MB) else mb
        self.coll.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = [math.radians(a) for a in rot]
        p = Piece(name, step, ob, label, sub)
        self.pieces.append(p)
        return p


# ─────────────────────────────── electronics ───────────────────────────────
def zs_x11h(mb, loc, rot=0.0):
    """ZS-X11H BLDC driver: green board on an aluminium heat plate, 2 big capacitors, blue power/motor terminals,
    white Hall header, control pin header."""
    M = xform(loc, (0, 0, rot))
    mb.add(bm_box(0.063, 0.045, 0.004), "potted_alu", M=M @ xform((0, 0, 0.002)))
    mb.add(bm_box(0.063, 0.045, 0.0016), "pcb_green", M=M @ xform((0, 0, 0.0048)))
    for dx in (-0.012, 0.004):
        mb.add(bm_cyl(0.005, 0.02, 16), "cap_black", M=M @ xform((dx, 0.012, 0.0156)))
        mb.add(bm_cyl(0.0052, 0.001, 16), "potted_alu", M=M @ xform((dx, 0.012, 0.0257)))
    for k in range(5):                                    # power + 3 phases: 5-way screw terminal along the front edge
        mb.add(bm_box(0.0075, 0.009, 0.01), "term_blue", M=M @ xform((0.026 - 0.0076 * k + 0.004, -0.017, 0.0106)))
        mb.add(bm_cyl(0.0018, 0.001, 8), "stainless", M=M @ xform((0.026 - 0.0076 * k + 0.004, -0.017, 0.0161)))
    mb.add(bm_box(0.013, 0.006, 0.007), "header_white", M=M @ xform((-0.022, -0.016, 0.0091)))      # Hall
    mb.add(bm_box(0.016, 0.003, 0.009), "plastic_black", M=M @ xform((-0.02, 0.019, 0.0101)))      # control pins
    for k in range(6):
        mb.add(bm_box(0.0006, 0.0006, 0.006), "gold", M=M @ xform((-0.026 + 0.0025 * k, 0.019, 0.0165)))
    for k in range(6):
        mb.add(bm_box(0.007, 0.006, 0.004), "chip", M=M @ xform((0.012 + 0.008 * (k % 3) - 0.008, 0.002 - 0.008 * (k // 3), 0.0076)))
    return mb


def arduino_mega(mb, loc, rot=0.0):
    M = xform(loc, (0, 0, rot))
    mb.add(bm_box(0.1015, 0.0533, 0.0016), "pcb_blue_ard", M=M @ xform((0, 0, 0.0008)))
    mb.add(bm_box(0.016, 0.012, 0.011), "shield", M=M @ xform((-0.047, 0.012, 0.007)))           # USB-B
    mb.add(bm_box(0.014, 0.009, 0.011), "plastic_black", M=M @ xform((-0.047, -0.016, 0.007)))   # barrel jack
    mb.add(bm_box(0.014, 0.014, 0.0012), "chip", M=M @ xform((0.012, 0.0, 0.0022)) @ xform(rot=(0, 0, 45)))
    for y in (0.024, -0.024):
        mb.add(bm_box(0.08, 0.0025, 0.0085), "plastic_black", M=M @ xform((0.005, y, 0.0058)))
    mb.add(bm_box(0.005, 0.045, 0.0085), "plastic_black", M=M @ xform((0.047, 0.0, 0.0058)))     # double header
    mb.add(bm_box(0.012, 0.004, 0.003), "silk", M=M @ xform((-0.02, -0.01, 0.0018)))
    return mb


def relay16(mb, loc, rot=0.0):
    """16-channel 5 V relay module: blue relays in two rows of 8 on a blue board, green screw terminals."""
    M = xform(loc, (0, 0, rot))
    mb.add(bm_box(0.18, 0.087, 0.0016), "pcb_blue_ard", M=M @ xform((0, 0, 0.0008)))
    for r in (-1, 1):
        for k in range(8):
            x = -0.0735 + k * 0.021
            mb.add(bm_box(0.0185, 0.015, 0.0155), "relay_blue", M=M @ xform((x, r * 0.012, 0.0094)))
            mb.add(bm_box(0.0185, 0.009, 0.01), "term_green", M=M @ xform((x, r * 0.037, 0.0066)))
    mb.add(bm_box(0.04, 0.004, 0.0085), "plastic_black", M=M @ xform((0.065, 0.0, 0.0058)))
    return mb


def converter(mb, loc, rot=(0, 0, 0), label="24V>5V 5A"):
    M = xform(loc, rot)
    mb.add(bm_box(0.046, 0.046, 0.02, bevel=0.002), "potted_alu", M=M)
    mb.add(bm_box(0.03, 0.001, 0.008), "sticker_white", M=M @ xform((0, -0.0235, 0.002)))
    for k, m in enumerate(("wire_red2", "wire_black", "wire_red2", "wire_black")):
        mb.add(bm_cyl(0.0012, 0.03, 6), m, M=M @ xform((-0.012 + 0.008 * k, 0.03, 0.0)) @ xform(rot=(90, 0, 0)))
    return mb


def power_panel(kit):
    """Left side panel (between the wheels): fuse, isolator switch, contactor, bus bars."""
    mb = MB()
    y0 = R.RAIL_Y + 0.012
    mb.box((0.22, 0.004, 0.17), "anodised", loc=(0.0, y0, 0.205))
    # MIDI fuse holder
    mb.box((0.06, 0.02, 0.03), "plastic_black", bevel=0.003, loc=(-0.07, y0 + 0.012, 0.25))
    mb.box((0.055, 0.012, 0.025), "clear_cover", bevel=0.003, loc=(-0.07, y0 + 0.028, 0.25))
    mb.box((0.04, 0.004, 0.012), "copper", loc=(-0.07, y0 + 0.023, 0.25))
    # isolator switch: round base + red key knob facing out
    mb.cyl(0.03, 0.02, "plastic_black", segs=32, axis="Y", loc=(0.0, y0 + 0.012, 0.25))
    mb.box((0.012, 0.03, 0.05), "isolator_red", bevel=0.004, loc=(0.0, y0 + 0.034, 0.25))
    mb.cyl(0.02, 0.012, "isolator_red", segs=24, axis="Y", loc=(0.0, y0 + 0.026, 0.25))
    # contactor: cylinder with two copper studs, axis out of the panel
    mb.cyl(0.026, 0.05, "plastic_black", segs=28, axis="Y", loc=(0.07, y0 + 0.027, 0.2))
    for dz in (-0.012, 0.012):
        mb.cyl(0.004, 0.016, "copper", segs=12, axis="Y", loc=(0.07, y0 + 0.058, 0.2 + dz))
    # bus bars (+ red, - black)
    for k, m in enumerate(("pvc_red", "plastic_black")):
        mb.box((0.07, 0.016, 0.016), m, bevel=0.002, loc=(-0.03 + 0.02 * k, y0 + 0.01, 0.15 - 0.022 * k))
    mb.text("POWER", 0.012, "plastic_white", loc=(0.0, y0 + 0.0025, 0.29), rot=(90, 0, 180), bold=True)
    return kit.add("power_panel", 4, mb, "Power panel", "fuse · main switch · heavy relay · bus bars")


def converter_panel(kit):
    """Right side panel: three 24 V converters (for the Pi, the USB hub, the relay board)."""
    mb = MB()
    y0 = -(R.RAIL_Y + 0.012)
    mb.box((0.22, 0.004, 0.17), "anodised", loc=(0.0, y0, 0.205))
    for k, lab in enumerate(("24V>5V 5A", "24V>12V 3A", "24V>5V 3A")):
        converter(mb, (-0.065 + 0.065 * k, y0 - 0.012, 0.25), rot=(90, 0, 0), label=lab)
    return kit.add("converter_panel", 4, mb, "3 converters", "5 V for the Pi · 12 V for the hub · 5 V for relays")


def ebox_base(kit):
    b = BOX
    L = b["x1"] - b["x0"]
    cx = (b["x0"] + b["x1"]) / 2
    mb = MB()
    t = 0.004
    mb.box((L, b["w"], t), "ip65_grey", loc=(cx, 0, R.DECK_Z + t / 2))
    for sy in (-1, 1):
        mb.box((L, t, b["h"]), "ip65_grey", loc=(cx, sy * (b["w"] / 2 - t / 2), R.DECK_Z + b["h"] / 2))
    for sx in (-1, 1):
        mb.box((t, b["w"], b["h"]), "ip65_grey", loc=(cx + sx * (L / 2 - t / 2), 0, R.DECK_Z + b["h"] / 2))
    for k in range(4):                                     # cable glands on the back wall
        mb.cyl(0.008, 0.016, "plastic_black", segs=12, axis="-X", loc=(b["x0"] - 0.006, -0.075 + 0.05 * k, R.DECK_Z + 0.04))
    mb.box((0.26, 0.18, 0.002), "plastic_white", loc=(cx, 0, R.DECK_Z + 0.005))     # mounting plate
    return kit.add("ebox", 5, mb, "IP65 box", "300 × 220 × 120 mm")


def ebox_lid(kit):
    b = BOX
    L = b["x1"] - b["x0"]
    cx = (b["x0"] + b["x1"]) / 2
    mb = MB()
    mb.box((L, b["w"], 0.008), "ip65_grey", bevel=0.004, loc=(cx, 0, R.DECK_Z + b["h"] + 0.004))
    mb.box((0.14, 0.001, 0.035), "plastic_black", loc=(cx, -b["w"] / 2 - 0.0005, R.DECK_Z + b["h"] - 0.02))
    mb.text("GHOST OPS  R1", 0.013, "brand_orange", loc=(cx, -b["w"] / 2 - 0.0012, R.DECK_Z + b["h"] - 0.015), rot=(90, 0, 0), bold=True)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.004, 0.003, "stainless", segs=10, z0=R.DECK_Z + b["h"] + 0.008, loc=(cx + sx * 0.13, sy * 0.095, 0))
    return kit.add("ebox_lid", 6, mb, "Lid", "IP65: rain and spray stay out")


# ─────────────────────────────── the kit ───────────────────────────────
def build(coll):
    """All pieces, assembled. Returns the Kit (kit.pieces in build order)."""
    k = Kit(coll)
    Z = R.RAIL_Z
    # step 1: frame
    for sy, nm in ((1, "rail_L"), (-1, "rail_R")):
        mb = MB()
        R.extrusion(mb, 0.68, 0.02, 0.04, loc=(0, sy * R.RAIL_Y, Z), axis="X")
        k.add(nm, 1, mb, "2040 bar · 680 mm", "the two sides")
    for x, nm in ((0.32, "cross_F"), (-0.02, "cross_M"), (-0.32, "cross_B")):
        mb = MB()
        R.extrusion(mb, 2 * R.RAIL_Y - 0.02, 0.02, 0.02, loc=(x, 0, Z), axis="Y")
        k.add(nm, 1, mb, "2040 bar · 176 mm", "front · middle · back")
    mb = MB()
    for x in (0.32, -0.02, -0.32):
        for sy in (-1, 1):
            mb.box((0.02, 0.02, 0.004), "anodised", loc=(x + 0.016, sy * (R.RAIL_Y - 0.02), Z + 0.018))
            screw(mb, (x + 0.016, sy * (R.RAIL_Y - 0.02), Z + 0.0205), length=0.01, r=0.0025, head_r=0.0042)
    k.add("corners", 1, mb, "Corner brackets", "T-nut + M5 bolt")
    # step 2: wheel plates + hub motors
    for sx in (-1, 1):
        for sy in (-1, 1):
            nm = f"{'F' if sx > 0 else 'R'}{'L' if sy > 0 else 'R'}"
            mb = MB()
            mb.box((0.07, 0.006, 0.09), "anodised", bevel=0.001, loc=(sx * R.WX, sy * (R.WY - 0.04), 0.155))
            mb.box((0.03, 0.03, 0.012), "anodised", loc=(sx * R.WX, sy * (R.WY - 0.055), 0.127))
            for dx in (-0.02, 0.02):
                for dz in (0.17, 0.19):
                    screw(mb, (sx * R.WX + dx, sy * (R.WY - 0.043), dz), axis="Y" if sy > 0 else "-Y", length=0.01)
            k.add(f"plate_{nm}", 2, mb, "Wheel plate", "6 mm aluminium · 4 bolts")
    for sx in (-1, 1):
        for sy in (-1, 1):
            nm = f"{'F' if sx > 0 else 'R'}{'L' if sy > 0 else 'R'}"
            mb = MB()
            R.hub_wheel(mb, (sx * R.WX, sy * R.WY, R.W_R), sy)
            k.add(f"wheel_{nm}", 2, mb, "10\" hub motor", "24 V · 350 W · the motor is inside")
    # step 3: tray, battery, tank, deck
    mb = MB()
    mb.box((0.64, 0.17, 0.004), "anodised", loc=(0, 0, R.TRAY_Z))
    for sy in (-1, 1):
        mb.box((0.64, 0.004, 0.07), "anodised", loc=(0, sy * 0.085, R.TRAY_Z + 0.035))
    k.add("tray", 3, mb, "Tray", "10 cm off the ground")
    mb = MB()
    mb.box((0.20, 0.16, 0.17), "lfp_blue", bevel=0.008, loc=(0.175, 0, R.TRAY_Z + 0.087))
    mb.box((0.12, 0.001, 0.05), "sticker_white", loc=(0.175, -0.0805, R.TRAY_Z + 0.117))
    mb.text("LiFePO4 24V 30Ah", 0.011, "plastic_black", loc=(0.175, -0.081, R.TRAY_Z + 0.122), rot=(90, 0, 0), bold=True)
    mb.cyl(0.008, 0.012, "pvc_red", segs=12, z0=R.TRAY_Z + 0.172, loc=(0.235, 0.05, 0))
    mb.cyl(0.008, 0.012, "plastic_black", segs=12, z0=R.TRAY_Z + 0.172, loc=(0.235, -0.05, 0))
    for dx in (-0.05, 0.05):
        mb.box((0.025, 0.166, 0.002), "strap_black", loc=(0.175 + dx, 0, R.TRAY_Z + 0.175))
    k.add("battery", 3, mb, "Battery", "24 V 30 Ah LiFePO4 · 8 kg")
    mb = MB()
    mb.box((0.38, 0.165, 0.175), "tank_white", bevel=0.02, loc=(-0.13, 0, R.TRAY_Z + 0.09))
    mb.box((0.37, 0.155, 0.1), "spray_liquid", bevel=0.015, loc=(-0.13, 0, R.TRAY_Z + 0.055))
    mb.cyl(0.028, 0.03, "plastic_yellow", segs=24, z0=R.TRAY_Z + 0.1775, loc=(-0.25, 0.022, 0))
    k.add("tank", 3, mb, "15 L tank", "the heavy parts go low")
    mb = MB()
    mb.box((0.70, 0.235, 0.004), "anod_dark", bevel=0.001, loc=(0, 0, R.DECK_Z - 0.002))
    for i in range(9):
        mb.box((0.66, 0.003, 0.0012), "anodised", loc=(0, -0.10 + i * 0.025, R.DECK_Z + 0.0006))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.008, R.DECK_Z - R.RAIL_Z - 0.02, "anodised", segs=12, z0=R.RAIL_Z + 0.02, loc=(sx * 0.30, sy * R.RAIL_Y, 0))
    k.add("deck", 3, mb, "Deck plate", "4 mm aluminium")
    # step 4: power
    power_panel(k)
    converter_panel(k)
    mb = MB()
    mb.box((0.05, 0.12, 0.07), "ip65_grey", bevel=0.006, loc=(-0.325, 0, R.DECK_Z + 0.035))
    mb.cyl(0.02, 0.012, "estop_yellow", segs=24, z0=R.DECK_Z + 0.07, loc=(-0.325, -0.025, 0))
    mb.lathe([(0, 0), (0.019, 0), (0.02, 0.008), (0.018, 0.016), (0, 0.019)], "estop_red", segs=28, loc=(-0.325, -0.025, R.DECK_Z + 0.082))
    k.add("estop", 4, mb, "Emergency stop", "cuts the heavy relay, in hardware")
    mb = MB()
    y0 = R.RAIL_Y + 0.02
    cable(mb, [(0.235, 0.05, R.TRAY_Z + 0.184), (0.235, 0.09, R.TRAY_Z + 0.2), (0.12, y0 + 0.01, 0.26), (-0.07, y0 + 0.02, 0.25)], r=0.005, m="wire_red2", fillet=0.04)
    cable(mb, [(0.235, -0.05, R.TRAY_Z + 0.184), (0.24, -0.02, R.TRAY_Z + 0.2), (0.12, y0 - 0.02, 0.16), (-0.02, y0 + 0.01, 0.128)], r=0.005, m="wire_black", fillet=0.04)
    cable(mb, [(0.07, y0 + 0.06, 0.2), (0.09, y0 + 0.03, 0.29), (0.1, 0.09, R.DECK_Z + 0.03), (BOX["x0"] + 0.02, 0.08, R.DECK_Z + 0.03)], r=0.004, m="wire_red2", fillet=0.03)
    cable(mb, [(-0.325, -0.025, R.DECK_Z + 0.03), (-0.3, 0.06, R.DECK_Z - 0.01), (-0.1, y0, 0.27), (0.06, y0 + 0.03, 0.22)], r=0.0022, m="wire_grey", fillet=0.04)
    k.add("power_cables", 4, mb, "Power wires", "red to red, black to black")
    # step 5: e-box + motor drivers + phase wires
    ebox_base(k)
    mb = MB()
    for i in range(4):
        zs_x11h(mb, (0.29, -0.072 + 0.048 * i, R.DECK_Z + 0.006), rot=0)
    k.add("drivers", 5, mb, "4 × ZS-X11H", "one driver per wheel")
    mb = MB()
    for sx in (-1, 1):
        for sy in (-1, 1):
            start = (BOX["x1"] - 0.01, sy * 0.05 + sx * 0.012, R.DECK_Z + 0.03)
            end = (sx * R.WX, sy * (R.WY - 0.06), R.W_R + 0.01)
            mid = (sx * R.WX * 0.6 + 0.08, sy * 0.1, R.DECK_Z - 0.03)
            for j, m in enumerate(("wire_yellow", "wire_green2", "wire_blue2")):
                o = (j - 1) * 0.004
                cable(mb, [(start[0], start[1] + o, start[2]), (start[0] + 0.02, start[1] + o, R.DECK_Z + 0.02),
                           (mid[0], mid[1] + o, mid[2]), (end[0], end[1] + o, end[2] + o)], r=0.0018, m=m, fillet=0.04)
    k.add("phase_wires", 5, mb, "Motor wires", "3 thick wires + 1 sensor plug per wheel")
    # step 6: brain
    try:
        from components import bench
        pi = bench.pi5_ai_hat(cid="kit_pi5", title="Raspberry Pi 5 + AI HAT+")
        objs = [pi.root] + gh.descendants(pi.root)
        import bpy
        for o in objs:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            coll.objects.link(o)
        pi.root.location = (0.12, -0.05, R.DECK_Z + 0.008)
        pi.root.rotation_euler = (0, 0, math.radians(90))
        k.pieces.append(Piece("pi5", 6, pi.root, "Raspberry Pi 5 + AI HAT+", "the brain · 26 TOPS AI chip"))
    except Exception as e:  # noqa: BLE001
        print("pi5 skipped", e)
    mb = MB()
    arduino_mega(mb, (0.13, 0.055, R.DECK_Z + 0.008), rot=90)
    cable(mb, [(0.13, 0.0, R.DECK_Z + 0.02), (0.11, 0.0, R.DECK_Z + 0.05), (0.1, -0.02, R.DECK_Z + 0.03)], r=0.0028, m="cable", fillet=0.02)
    k.add("mega", 6, mb, "Arduino Mega", "talks to the motor drivers")
    ebox_lid(k)
    # step 7: mast, arms + cameras, USB hub
    mb = MB()
    R.extrusion(mb, 1.05 - R.DECK_Z, 0.04, 0.04, loc=(R.MAST_X, 0, (R.DECK_Z + 1.05) / 2), axis="Z")
    mb.box((0.12, 0.12, 0.008), "anod_dark", loc=(R.MAST_X, 0, R.DECK_Z + 0.004))
    for a in (0, 90, 180, 270):
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        mb.box((0.04, 0.004, 0.04), "anod_dark", loc=(R.MAST_X + dx * 0.04, dy * 0.04, R.DECK_Z + 0.028), rot=(0, 0, a))
    mb.box((0.05, 0.05, 0.04), "anod_dark", bevel=0.003, loc=(R.MAST_X, 0, 1.06))
    k.add("mast_lower", 7, mb, "Mast", "40 × 40 bar + base plate")
    mb = MB()
    R.extrusion(mb, 1.95 - 1.05 + 0.25, 0.03, 0.03, loc=(R.MAST_X, 0, (1.05 - 0.25 + 1.95) / 2), axis="Z")
    k.add("mast_upper", 7, mb, "Upper mast", "slides up, locks · 1.95 m for tomato")
    for zi, (zl, tilt) in enumerate(((0.62, 25.0), (1.22, 0.0), (1.82, -10.0))):
        mb = MB()
        R.extrusion(mb, 0.25, 0.02, 0.02, loc=(R.MAST_X, 0, zl), axis="Y")
        for sy in (-1, 1):
            R.camera_pod(mb, (R.MAST_X, sy * 0.14, zl + 0.03), sy, tilt=tilt)
        cable(mb, [(R.MAST_X + 0.022, 0.0, zl + 0.03), (R.MAST_X + 0.024, 0.0, zl - 0.2), (R.MAST_X + 0.024, 0.0, R.DECK_Z + 0.12)], r=0.003, fillet=0.03)
        k.add(f"arm_{zi + 1}", 7, mb, f"Camera arm {zi + 1}", "2 USB cameras + LED flash rings" + (" · tilted up 25°" if zi == 0 else ""))
    mb = MB()
    mb.box((0.03, 0.12, 0.022), "plastic_black", bevel=0.004, loc=(R.MAST_X - 0.04, 0.0, R.DECK_Z + 0.16), rot=(0, 0, 0))
    for i in range(7):
        mb.box((0.002, 0.012, 0.005), "plastic_blue", loc=(R.MAST_X - 0.0555, -0.048 + 0.016 * i, R.DECK_Z + 0.16))
    k.add("usb_hub", 7, mb, "USB 3.0 hub", "7 ports · one cable to the Pi")
    # step 8: sprayer
    mb = MB()
    mb.box((0.11, 0.085, 0.07), "plastic_black", bevel=0.006, loc=(-0.225, -0.055, R.DECK_Z + 0.035))
    mb.cyl(0.03, 0.08, "steel_dark", segs=24, bevel=0.003, axis="X", loc=(-0.135, -0.055, R.DECK_Z + 0.035))
    mb.cyl(0.018, 0.06, "clear_cover", segs=20, axis="X", loc=(-0.3, -0.055, R.DECK_Z + 0.02))     # inline filter
    k.add("pump", 8, mb, "Pump + filter", "24 V diaphragm pump")
    mb = MB()
    mb.box((0.2, 0.025, 0.025), "anodised", bevel=0.002, loc=(-0.19, 0.07, R.DECK_Z + 0.0125))
    for i in range(6):
        R.solenoid_valve(mb, (-0.275 + i * 0.034, 0.07, R.DECK_Z + 0.037))
    k.add("valves", 8, mb, "6 valves", "one per nozzle: L1 R1 L2 R2 L3 R3")
    mb = MB()
    for zi, zl in enumerate((0.62, 1.22, 1.82)):
        for sy in (-1, 1):
            R.teejet_nozzle(mb, (R.MAST_X, sy * 0.13, zl - 0.03), sy, tilt=-12.0)
            kk = zi * 2 + (0 if sy < 0 else 1)
            vx = -0.19 - 0.085 + kk * 0.034
            ox = R.MAST_X - 0.026 - 0.004 * kk
            pts = [(vx, 0.09, R.DECK_Z + 0.07), (vx, 0.045, R.DECK_Z + 0.03), (ox, 0.022 - 0.003 * kk, R.DECK_Z + 0.03),
                   (ox, 0.022 - 0.003 * kk, zl - 0.03), (R.MAST_X, sy * 0.03, zl - 0.03), (R.MAST_X, sy * 0.115, zl - 0.03)]
            cable(mb, pts, r=0.003, m="pu_tube", fillet=0.03, segs=8)
    k.add("tubes", 8, mb, "Tubes + nozzles", "6 mm push-fit · TeeJet hollow cone")
    mb = MB()
    relay16(mb, (0.0, 0.0, 0.0))
    p = k.add("relays", 8, mb, "16-relay board", "the Mega switches valves, pump, lights", loc=(0.0, -(R.RAIL_Y + 0.016), 0.17), rot=(90, 0, 0))
    # step 9: bumpers, beacon, lidar, front camera, handle
    mb = MB()
    for sx in (-1, 1):
        mb.box((0.025, 0.30, 0.045), "bumper", bevel=0.01, loc=(sx * 0.365, 0, 0.165))
        for sy in (-1, 1):
            mb.box((0.02, 0.012, 0.02), "anodised", loc=(sx * 0.345, sy * 0.1, 0.165))
    for sy in (-1, 1):
        mb.box((0.004, 0.05, 0.024), "copper", loc=(0.3785, sy * 0.06, 0.165))
    k.add("bumpers", 9, mb, "Bumpers", "a touch cuts the motors")
    mb = MB()
    mb.cyl(0.022, 0.01, "plastic_black", segs=24, z0=1.953)
    for kk, m in enumerate(("beacon_red", "beacon_amber", "beacon_green")):
        mb.cyl(0.02, 0.028, m, segs=24, z0=1.965 + kk * 0.03)
    mb.cyl(0.021, 0.008, "plastic_black", segs=24, z0=2.055)
    k.add("beacon", 9, mb, "Warning light", "green scout · amber spray · red stop", loc=(R.MAST_X, 0, 0))
    mb = MB()
    mb.cyl(0.006, 0.05, "anodised", segs=12, z0=R.DECK_Z + BOX["h"] + 0.008, loc=(0.27, 0, 0))
    R.rplidar_c1(mb, (0.27, 0, R.DECK_Z + BOX["h"] + 0.058))
    k.add("lidar", 9, mb, "Lidar", "Slamtec RPLIDAR C1: keeps it centred")
    mb = MB()
    R.camera_pod(mb, (0, 0, 0), 1)
    k.add("front_camera", 9, mb, "Front camera", "reads the bed tags", loc=(0.345, 0, 0.215), rot=(0, 0, -90))
    mb = MB()
    hp = [(-0.33, -0.09, R.DECK_Z), (-0.40, -0.09, R.DECK_Z + 0.28), (-0.42, -0.09, R.DECK_Z + 0.55), (-0.42, 0.09, R.DECK_Z + 0.55),
          (-0.40, 0.09, R.DECK_Z + 0.28), (-0.33, 0.09, R.DECK_Z)]
    mb.sweep(hp, 0.011, "anodised", segs=12, fillet=0.06)
    mb.sweep([(-0.42, -0.06, R.DECK_Z + 0.55), (-0.42, 0.06, R.DECK_Z + 0.55)], 0.015, "rubber", segs=14)
    k.add("handle", 9, mb, "Push handle", "")
    return k
