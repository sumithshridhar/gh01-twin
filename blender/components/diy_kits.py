"""Two beginner builds for the "Build GH-01" tutorial videos (17 Oct 2026), real parts at real size:

  Part 3, "Plants that water themselves": ESP32 DevKit V1 on a 30-pin expansion board (DC jack 6.5-16 V), capacitive soil
  moisture sensor v1.2, 5 V 1-channel relay, 12 V 1/2" normally-closed solenoid valve, 12 V 2 A adapter + DC splitter +
  DC screw-terminal jack, IP65 box with a clear lid, 16 mm drip line, button drippers, 4 mm micro tube, arrow stakes.

  Part 4, "A box that warns you before plant disease": ESP32 on the same expansion board (jumper on 3.3 V), SHT30 humidity
  probe in a sintered metal cap, a sun shield made of 6 white plant saucers on 3 threaded rods, a pipe stand, an IP65 box,
  5 V phone charger + long USB cable.

Sizes (mm) from listings / datasheets: ESP32 DevKit V1 30-pin ~51.5 x 28.5, headers 25.4 apart at 2.54 pitch; WROOM-32
module 25.5 x 18; soil sensor v1.2 ~98 x 23; 1-channel relay module ~50 x 26 with a 19 x 15.5 x 15 SRD-05VDC relay;
1/2" plastic solenoid valve ~83 x 45 x 70; 16 mm LDPE drip pipe; SHT30 probe ~16 mm diameter.

World frame shared by both videos (metres, z up, studio floor at 0): a tap riser at (0, -0.40), three grow bags in a column
at x = 0.17, y = 0, 0.33, 0.66, the drip line along x = 0. Part 3's box hangs on a wooden post at (-0.25, -0.38);
Part 4's stand is at (0.46, 0.165), beside the bags.
"""
import math
import random

from mathutils import Matrix, Vector

import gh
from gh import MB, AXIS_ROT, bm_box, bm_cyl, bm_text, xform
from parts import cable

from components import bench  # noqa: F401  (registers pcb / silk / chip materials)
from components import soilhouse as SH
from components.rover_kit import Kit, Piece  # noqa: F401

MM = 0.001
gh.SPEC.update({
    "pcb_exp": dict(color=(0.02, 0.12, 0.42), rough=0.35, coat=0.3),
    "module_pcb": dict(color=(0.03, 0.06, 0.16), rough=0.35, coat=0.3),
    "relay_blue": dict(color=(0.05, 0.22, 0.72), rough=0.35),
    "pcb_relay": dict(color=(0.02, 0.18, 0.5), rough=0.35, coat=0.3),
    "term_blue": dict(color=(0.08, 0.32, 0.75), rough=0.45),
    "header_white": dict(color=(0.92, 0.92, 0.88), rough=0.45),
    "wire_red3": dict(color=(0.78, 0.05, 0.03), rough=0.4),
    "wire_black3": dict(color=(0.03, 0.03, 0.03), rough=0.4),
    "wire_yellow3": dict(color=(0.95, 0.75, 0.02), rough=0.4),
    "wire_green3": dict(color=(0.05, 0.6, 0.18), rough=0.4),
    "wire_orange3": dict(color=(0.95, 0.42, 0.03), rough=0.4),
    "wire_blue3": dict(color=(0.05, 0.3, 0.85), rough=0.4),
    "dupont": dict(color=(0.05, 0.05, 0.055), rough=0.45),
    "valve_body": dict(color=(0.86, 0.86, 0.83), rough=0.38),
    "valve_coil": dict(color=(0.04, 0.04, 0.045), rough=0.4),
    "ball_red": dict(color=(0.8, 0.05, 0.03), rough=0.35),
    "dripper_purple": dict(color=(0.42, 0.12, 0.62), rough=0.4),
    "stake_green": dict(color=(0.1, 0.5, 0.15), rough=0.45),
    "growbag": dict(color=(0.88, 0.88, 0.85), rough=0.75, sheen=0.3, noise=("fibre", 300.0, 0.15)),
    "growbag_in": dict(color=(0.03, 0.03, 0.03), rough=0.7),
    "wood_post": dict(color=(0.55, 0.38, 0.2), rough=0.8, noise=("coco", 30.0, 0.2)),
    "box_grey": dict(color=(0.6, 0.62, 0.63), rough=0.45),
    "box_lid": dict(color=(0.86, 0.9, 0.93), rough=0.05, alpha=0.09, coat=1.0),
    "socket_white": dict(color=(0.9, 0.9, 0.88), rough=0.4),
    "sintered": dict(color=(0.62, 0.62, 0.6), metal=0.8, rough=0.75, noise=("concrete", 900.0, 0.4)),
    "saucer": dict(color=(0.93, 0.93, 0.91), rough=0.4, subsurface=0.05),
    "stand_paint": dict(color=(0.12, 0.13, 0.14), rough=0.5),
    "wet_patch": dict(color=(0.07, 0.035, 0.018), rough=0.35, alpha=0.85),
    "water_drop": dict(color=(0.75, 0.85, 0.9), rough=0.02, alpha=0.5, coat=1.0),
    "relay_led": dict(color=(0.1, 0.9, 0.2), rough=0.3, emit=(0.1, 1, 0.2), emit_strength=0.0),
    "pwr_led": dict(color=(0.9, 0.05, 0.02), rough=0.3, emit=(1, 0.05, 0.02), emit_strength=0.0),
    "esp_led": dict(color=(0.1, 0.3, 1.0), rough=0.3, emit=(0.1, 0.35, 1.0), emit_strength=0.0),
})


# ─────────────────────────────── helpers (mm, inside a frame M) ───────────────────────────────
def B(mb, M, m, cx, cy, z0, sx, sy, sz, bevel=0.0, rot=(0, 0, 0)):
    mb.add(bm_box(sx * MM, sy * MM, sz * MM, bevel=bevel * MM), m, M=M @ xform((cx * MM, cy * MM, (z0 + sz / 2) * MM), rot))


def C(mb, M, m, cx, cy, z0, r, h, segs=24, axis="Z", bevel=0.0, r_top=None):
    """Cylinder of radius r, length h (mm). axis Z: from z0 up. Other axes: (cx, cy, z0) is the centre of the start face."""
    mb.add(bm_cyl(r * MM, h * MM, segs, bevel * MM, None if r_top is None else r_top * MM, z0=0.0), m,
           M=M @ xform((cx * MM, cy * MM, z0 * MM)) @ xform(rot=AXIS_ROT[axis]))


def T(mb, M, s, cx, cy, z, size, m="silk", rot=0.0, bold=False):
    mb.add(bm_text(s, size * MM, 0.03 * MM, "CENTER", bold), m, M=M @ xform((cx * MM, cy * MM, (z + 0.015) * MM), (0, 0, rot)), smooth=False)


def rrect(w, h, r, n=4):
    return bench.rrect(w, h, r, n)


def P(M, x, y, z):
    """mm point in frame M -> world Vector (metres)."""
    return M @ Vector((x * MM, y * MM, z * MM))


def wire(mb, pts, m, r=0.7, fillet=4.0, ends=(True, True)):
    """A jumper wire through mm points already in world metres (Vectors). Black DuPont housings on the ends."""
    mb.sweep([tuple(p) for p in pts], r * MM, m, segs=8, fillet=fillet * MM)
    for i, flag in ((0, ends[0]), (-1, ends[1])):
        if not flag:
            continue
        a, b = pts[i], pts[1 if i == 0 else -2]
        d = (b - a).normalized()
        c = a + d * 7 * MM
        q = d.to_track_quat("Z", "Y")
        mb.add(bm_box(2.6 * MM, 2.6 * MM, 14 * MM), "dupont", M=Matrix.Translation(c) @ q.to_matrix().to_4x4())


# ─────────────────────────────── ESP32 DevKit V1 (30 pin) ───────────────────────────────
ESP_W, ESP_H = 51.5, 28.5
ESP_L = ["EN", "VP", "VN", "D34", "D35", "D32", "D33", "D25", "D26", "D27", "D14", "D12", "D13", "GND", "VIN"]
ESP_R = ["D23", "D22", "TX0", "RX0", "D21", "D19", "D18", "D5", "TX2", "RX2", "D4", "D2", "D15", "GND", "3V3"]


def esp_pin(name, side="L"):
    """Board-centred mm (x, y) of a header pin; +x = antenna end, left column (+y) when the antenna points up."""
    if side == "L" and name in ESP_L:
        return 17.78 - 2.54 * ESP_L.index(name), 12.7
    return 17.78 - 2.54 * ESP_R.index(name), -12.7


def esp32_devkit(mb, M):
    """Black ESP32 DevKit V1: WROOM-32 module with its PCB antenna at +x, micro-USB at -x, pins pointing down.
    Origin: board centre, PCB bottom at z = 0."""
    mb.prism(rrect(ESP_W * MM, ESP_H * MM, 1.0 * MM), 1.6 * MM, "pcb_black", M=M)
    B(mb, M, "module_pcb", 13.0, 0, 1.6, 25.5, 18.0, 0.8)
    B(mb, M, "shield", 9.65, 0, 2.4, 17.6, 15.8, 2.4, bevel=0.2)
    T(mb, M, "ESP-WROOM-32", 9.65, 2.0, 4.8, 1.7, m="chip_mark", bold=True)
    T(mb, M, "ESPRESSIF", 9.65, -2.4, 4.8, 1.3, m="chip_mark")
    for i in range(5):                                                     # meander antenna trace
        B(mb, M, "gold", 20.0 + 1.2 * i, 0, 2.4, 0.45, 13.0, 0.04)
    B(mb, M, "gold", 22.4, 6.5, 2.4, 5.3, 0.45, 0.04)
    B(mb, M, "shield", -23.4, 0, 1.6, 5.9, 7.6, 2.9, bevel=0.3)            # micro-USB
    B(mb, M, "hole_dark", -26.3, 0, 2.1, 0.2, 6.0, 1.8)
    B(mb, M, "chip", -12.5, 0, 1.6, 5.0, 5.0, 0.9, bevel=0.1)              # CP2102
    B(mb, M, "chip", -6.0, -7.5, 1.6, 6.5, 3.5, 1.6, bevel=0.1)            # AMS1117
    B(mb, M, "tin", -6.0, -10.0, 1.6, 6.5, 1.4, 0.3)
    for y in (7.8, -7.8):                                                  # EN / BOOT buttons
        B(mb, M, "shield", -21.0, y, 1.6, 4.6, 3.6, 1.4)
        B(mb, M, "plastic_black", -21.0, y, 3.0, 2.0, 1.6, 0.9)
    T(mb, M, "EN", -21.0, 10.3, 1.6, 1.2, rot=0)
    T(mb, M, "BOOT", -21.0, -10.3, 1.6, 1.2, rot=0)
    B(mb, M, "pwr_led", -16.0, 3.5, 1.6, 1.6, 0.8, 0.6)
    B(mb, M, "esp_led", -16.0, -3.5, 1.6, 1.6, 0.8, 0.6)
    T(mb, M, "ESP32 DEVKIT V1", -1.0, 5.6, 1.6, 1.9, bold=True)
    for side, names, y in (("L", ESP_L, 12.7), ("R", ESP_R, -12.7)):
        B(mb, M, "plastic_black", 0, y, -2.5, 38.1, 2.5, 2.5)
        for k, nm in enumerate(names):
            x = 17.78 - 2.54 * k
            B(mb, M, "gold", x, y, -8.5, 0.64, 0.64, 11.1)
            mb.tube(0.85 * MM, 0.45 * MM, 0.05 * MM, "tin", segs=12, z0=0.0, M=M @ xform((x * MM, y * MM, 1.6 * MM)))
            T(mb, M, nm, x, y - math.copysign(2.6, y), 1.6, 0.85, rot=90)
    return mb


# ─────────────────────────────── 30-pin expansion board ───────────────────────────────
EXP_W, EXP_H, EX0 = 68.0, 55.0, 5.0
ESP_ON_EXP_Z = 12.6        # ESP32 PCB bottom above the expansion board bottom (female header 8.5 + pin spacer 2.5 + PCB 1.6)


def gvs(name, row, side="L"):
    """Expansion-board mm (x, y) of the G / V / S pin beside ESP32 pin `name` (row 'S', 'V' or 'G')."""
    x, y = esp_pin(name, side)
    s = 1 if y > 0 else -1
    return EX0 + x, s * (17.6 + 2.54 * "SVG".index(row))


GVS_TOP = 1.6 + 2.5 + 6.0


def expansion_board(mb, M):
    """Blue 30-pin expansion board: two female headers for the ESP32, a G-V-S pin trio beside every ESP32 pin,
    a DC jack (6.5-16 V) with its regulator, a 3.3 V / 5 V jumper for the V pins, a power LED. Origin: board centre."""
    mb.prism(rrect(EXP_W * MM, EXP_H * MM, 2.0 * MM), 1.6 * MM, "pcb_exp", M=M)
    for y in (12.7, -12.7):
        B(mb, M, "plastic_black", EX0, y, 1.6, 38.1, 2.54, 8.5)
        for k in range(15):
            B(mb, M, "hole_dark", EX0 + 17.78 - 2.54 * k, y, 10.1, 1.0, 1.0, 0.05)
    for s in (1, -1):
        for j, row in enumerate("SVG"):
            y = s * (17.6 + 2.54 * j)
            B(mb, M, "plastic_black", EX0, y, 1.6, 38.1, 2.54, 2.5)
            for k in range(15):
                B(mb, M, "gold", EX0 + 17.78 - 2.54 * k, y, 1.6, 0.64, 0.64, 8.5)
            T(mb, M, row, EX0 - 21.6, y, 1.6, 1.6, bold=True)
    B(mb, M, "plastic_black", -27.0, -16.0, 1.6, 14.0, 9.0, 11.0, bevel=0.4)            # DC jack
    C(mb, M, "hole_dark", -34.05, -16.0, 7.1, 3.0, 2.0, axis="X")
    T(mb, M, "DC 6.5-16V", -26.0, -24.0, 1.6, 1.4, bold=True)
    for y in (-3.0, 4.5):                                                                # regulators
        B(mb, M, "chip", -26.0, y, 1.6, 6.5, 3.5, 1.6, bevel=0.1)
        B(mb, M, "tin", -26.0, y + 2.4, 1.6, 6.5, 1.3, 0.3)
    for x in (-31.0, -21.0):
        B(mb, M, "sticker_yellow", x, 0.8, 1.6, 3.2, 1.7, 1.6, bevel=0.2)                 # tantalum caps
    for i in range(3):                                                                    # V-pin jumper
        B(mb, M, "gold", -24.5 + 2.54 * i, 17.0, 1.6, 0.64, 0.64, 8.5)
    B(mb, M, "plastic_black", -24.5 + 1.27 * 3, 17.0, 4.1, 5.1, 2.5, 6.0)
    T(mb, M, "5V", -24.5, 20.3, 1.6, 1.3)
    T(mb, M, "3V3", -19.4, 20.3, 1.6, 1.3)
    B(mb, M, "pwr_led", -31.0, 9.5, 1.6, 1.6, 0.8, 0.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.tube(2.6 * MM, 1.6 * MM, 0.05 * MM, "tin", segs=16, z0=0.0, M=M @ xform((sx * (EXP_W / 2 - 3.4) * MM, sy * (EXP_H / 2 - 3.4) * MM, 1.6 * MM)))
    return mb


# ─────────────────────────────── sensors / relay / power ───────────────────────────────
def soil_sensor(mb, M):
    """Capacitive soil moisture sensor v1.2: black board with a pointed tip (-x), electronics + 3-pin JST at +x,
    a white line = how deep it may go. Origin: board centre, bottom at z = 0."""
    outline = [(49 * MM, -11.5 * MM), (49 * MM, 11.5 * MM), (-37 * MM, 11.5 * MM), (-49 * MM, 0), (-37 * MM, -11.5 * MM)]
    mb.prism(outline, 1.6 * MM, "pcb_black", M=M)
    B(mb, M, "chip", 33.0, 4.0, 1.6, 5.0, 4.0, 1.5, bevel=0.1)        # TLC555
    for i in range(4):
        for s in (-1, 1):
            B(mb, M, "tin", 31.1 + 1.27 * i, 4.0 + s * 2.6, 1.6, 0.4, 1.2, 0.4)
    B(mb, M, "chip", 37.5, -5.0, 1.6, 3.0, 1.6, 1.0)                  # 662K regulator
    for x, y in ((27.0, -4.0), (28.5, 6.5), (39.5, 3.0), (25.0, 2.0)):
        B(mb, M, "smd_tan", x, y, 1.6, 1.6, 0.8, 0.5)
    B(mb, M, "header_white", 45.5, 0, 1.6, 4.5, 8.0, 6.0, bevel=0.3)  # JST PH 3-pin
    B(mb, M, "hole_dark", 47.8, 0, 2.6, 0.3, 6.6, 3.6)
    B(mb, M, "silk", 21.0, 0, 1.6, 0.6, 21.0, 0.03)                   # depth line
    T(mb, M, "Capacitive Soil Moisture Sensor v1.2", -8.0, 0.0, 1.6, 2.0, rot=0, bold=True)
    T(mb, M, "GND VCC AOUT", 40.5, -8.6, 1.6, 1.2)
    return mb


SOIL_JST = (48.0, 0.0, 4.6)


def relay_module(mb, M):
    """5 V 1-channel relay module (optocoupler): blue relay cube, blue screw terminal (NO / COM / NC) at +x,
    3-pin header (DC+ / DC- / IN) at -x pointing up, red power + green status LEDs. Origin: board centre."""
    mb.prism(rrect(50 * MM, 26 * MM, 1.0 * MM), 1.6 * MM, "pcb_relay", M=M)
    B(mb, M, "relay_blue", 4.0, 0, 1.6, 19.0, 15.5, 15.0, bevel=0.3)
    T(mb, M, "SRD-05VDC-SL-C", 4.0, 3.0, 16.6, 1.6, m="plastic_white", bold=True)
    T(mb, M, "SONGLE", 4.0, -2.0, 16.6, 2.0, m="plastic_white", bold=True)
    B(mb, M, "term_blue", 20.5, 0, 1.6, 8.0, 15.0, 10.0, bevel=0.3)
    for i in range(3):
        C(mb, M, "stainless", 20.5, -5.0 + 5.0 * i, 11.6, 1.6, 0.6, segs=16)
        B(mb, M, "steel_dark", 20.5, -5.0 + 5.0 * i, 12.2, 2.4, 0.4, 0.15)
        B(mb, M, "hole_dark", 24.55, -5.0 + 5.0 * i, 3.0, 0.2, 3.2, 3.2)
    for i, lab in enumerate(("NO", "COM", "NC")):
        T(mb, M, lab, 14.2, -5.0 + 5.0 * i, 1.6, 1.3, rot=90, bold=True)
    B(mb, M, "plastic_black", -22.0, 0, 1.6, 2.5, 7.6, 2.5)
    for i, lab in enumerate(("DC+", "DC-", "IN")):
        y = 2.54 - 2.54 * i
        B(mb, M, "gold", -22.0, y, 1.6, 0.64, 0.64, 8.5)
        T(mb, M, lab, -17.6, y, 1.6, 1.2, bold=True)
    B(mb, M, "header_white", -11.0, 6.0, 1.6, 4.6, 6.4, 3.6)          # optocoupler
    B(mb, M, "chip", -11.0, -3.0, 1.6, 2.9, 1.6, 1.0)
    B(mb, M, "pwr_led", -16.0, -9.0, 1.6, 1.6, 0.8, 0.6)
    B(mb, M, "relay_led", -11.5, -9.0, 1.6, 1.6, 0.8, 0.6)
    return mb


RELAY_PIN = {"DC+": (-22.0, 2.54), "DC-": (-22.0, 0.0), "IN": (-22.0, -2.54)}
RELAY_TERM = {"NO": (24.6, -5.0), "COM": (24.6, 0.0), "NC": (24.6, 5.0)}


def dc_terminal(mb, M):
    """DC female jack to 2-way screw terminal (no soldering). Origin: centre, jack opening at -x."""
    C(mb, M, "plastic_black", -10.0, 0, 5.0, 5.0, 12.0, axis="X")
    C(mb, M, "hole_dark", -10.05, 0, 5.0, 3.0, 2.0, axis="X")
    B(mb, M, "term_green", 6.0, 0, 0.0, 9.0, 10.0, 10.0, bevel=0.3)
    for y in (-2.5, 2.5):
        C(mb, M, "stainless", 6.0, y, 10.0, 1.5, 0.6, segs=14)
        B(mb, M, "hole_dark", 10.55, y, 2.5, 0.2, 3.0, 3.0)
    T(mb, M, "+  -", 6.0, 0.0, 10.6, 1.8, m="plastic_white", bold=True, rot=90)
    return mb


def solenoid_valve(mb, M, face=-1):
    """12 V 1/2" normally-closed plastic solenoid valve: water flows along +x (arrow), black coil on top with two
    spade terminals. Origin: centre of the body bottom."""
    B(mb, M, "valve_body", 0, 0, 0, 45.0, 40.0, 32.0, bevel=3.0)
    for sx in (-1, 1):
        C(mb, M, "valve_body", sx * 22.0, 0, 16.0, 10.3, 21.0, segs=32, axis="X" if sx > 0 else "-X")
        for k in range(7):
            mb.torus(10.3 * MM, 0.55 * MM, "valve_body", segs=32, rsegs=6,
                     M=M @ xform(((sx * (25.0 + 2.4 * k)) * MM, 0, 16.0 * MM), (0, 90, 0)))
    B(mb, M, "valve_coil", 0, 0, 32.0, 34.0, 31.0, 36.0, bevel=1.5)
    C(mb, M, "valve_coil", 0, 0, 68.0, 7.0, 3.0, segs=6)
    for x in (-7.0, 7.0):
        B(mb, M, "tin", x, 0, 68.0, 6.3, 0.8, 8.0)
    f = face                                              # which side shows the label + flow arrow (-1: -y, +1: +y)
    B(mb, M, "sticker_white", 0, f * 15.6, 44.0, 22.0, 0.3, 12.0, rot=(0, 0, 0))
    mb.add(bm_text("12V DC", 4.0 * MM, 0.2 * MM, "CENTER", True), "plastic_black",
           M=M @ xform((0, f * 15.9 * MM, 50.0 * MM), (90, 0, 0 if f < 0 else 180)), smooth=False)
    arrow = [(-12 * MM, -2 * MM), (6 * MM, -2 * MM), (6 * MM, -5 * MM), (14 * MM, 0), (6 * MM, 5 * MM), (6 * MM, 2 * MM), (-12 * MM, 2 * MM)]
    mb.prism(list(reversed(arrow)) if f < 0 else arrow, 0.8 * MM, "plastic_dark", M=M @ xform((0, f * 20.0 * MM, 14.0 * MM), (90 if f < 0 else -90, 0, 0)))
    return mb


VALVE_SPADES = [(-7.0, 0.0, 76.0), (7.0, 0.0, 76.0)]


def adapter_12v(mb, M):
    """12 V 2 A wall adapter (round 2-pin), standing on the socket board. Origin: bottom centre."""
    B(mb, M, "plastic_black", 0, 0, 0, 62.0, 44.0, 36.0, bevel=4.0)
    B(mb, M, "sticker_white", 0, -22.1, 10.0, 34.0, 0.2, 14.0)
    mb.add(bm_text("12V 2A", 5.0 * MM, 0.2 * MM, "CENTER", True), "plastic_black", M=M @ xform((0, -22.4 * MM, 17.0 * MM), (90, 0, 0)), smooth=False)
    C(mb, M, "plastic_black", 31.0, 0, 18.0, 4.0, 8.0, axis="X")
    return mb


def socket_board(mb, M):
    """4-socket extension board lying on the floor, switch lit; its cable runs off to -x. Origin: bottom centre."""
    B(mb, M, "socket_white", 0, 0, 0, 260.0, 70.0, 38.0, bevel=5.0)
    for i in range(4):
        x = -90.0 + 60.0 * i
        B(mb, M, "plastic_white", x, 0, 38.0, 44.0, 44.0, 1.0, bevel=2.0)
        for dx, dy in ((-6, -6), (6, -6), (0, 8)):
            C(mb, M, "hole_dark", x + dx, dy, 38.8, 2.4, 0.4, segs=12)
    B(mb, M, "ball_red", 112.0, 0, 38.0, 14.0, 22.0, 5.0, bevel=1.5)
    return mb


# ─────────────────────────────── boxes ───────────────────────────────
def ip65_base(mb, M, W, H, D, glands=()):
    """Grey IP65 box base: back plate at z = 0, opening at +z, walls t = 3 mm, corner bosses; cable glands on the bottom
    wall (y = -H/2) at the given x. Local y = up when mounted."""
    t = 3.0
    mb.prism(rrect(W * MM, H * MM, 6.0 * MM), t * MM, "box_grey", M=M)
    for sx in (-1, 1):
        B(mb, M, "box_grey", sx * (W / 2 - t / 2), 0, t, t, H - 8, D - t, bevel=0.6)
    for sy in (-1, 1):
        B(mb, M, "box_grey", 0, sy * (H / 2 - t / 2), t, W - 8, t, D - t, bevel=0.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            C(mb, M, "box_grey", sx * (W / 2 - 6.0), sy * (H / 2 - 6.0), t, 5.5, D - t, segs=20)
            C(mb, M, "hole_dark", sx * (W / 2 - 6.0), sy * (H / 2 - 6.0), D - 0.1, 1.6, 0.2, segs=10)
    for gx in glands:
        C(mb, M, "plastic_black", gx, -H / 2, D / 2, 9.5, 5.0, segs=6, axis="-Y")
        C(mb, M, "plastic_black", gx, -H / 2 - 5.0, D / 2, 8.0, 9.0, segs=24, axis="-Y", r_top=5.5)
    return mb


def ip65_lid(mb, M, W, H):
    """Clear polycarbonate lid with 4 screws. Local origin: the lid's inner face centre."""
    gh.mat("box_lid").surface_render_method = "DITHERED"      # blended + raytracing showed things behind the back plate
    mb.prism(rrect(W * MM, H * MM, 6.0 * MM), 4.0 * MM, "box_lid", M=M)
    for sx in (-1, 1):
        for sy in (-1, 1):
            C(mb, M, "stainless", sx * (W / 2 - 6.0), sy * (H / 2 - 6.0), 4.0, 3.0, 1.2, segs=16, bevel=0.4)
            B(mb, M, "steel_dark", sx * (W / 2 - 6.0), sy * (H / 2 - 6.0), 5.0, 3.6, 0.5, 0.25)
    return mb


# ─────────────────────────────── plumbing ───────────────────────────────
PIPE_R = 0.008                     # 16 mm LDPE lateral
MT_R = 0.002                       # 4 mm micro tube


def dripper(mb, loc, up=(0, 0, 1)):
    """Online button dripper pressed into the lateral at loc (top of the pipe)."""
    M = Matrix.Translation(Vector(loc)) @ Vector(up).to_track_quat("Z", "Y").to_matrix().to_4x4()
    C(mb, M, "dripper_purple", 0, 0, 0.0, 10.0, 7.0, segs=24, bevel=1.2)
    C(mb, M, "dripper_purple", 0, 0, 7.0, 6.0, 3.0, segs=20)
    C(mb, M, "dripper_purple", 0, 0, 10.0, 2.4, 6.0, segs=12, r_top=1.8)
    return mb


def arrow_stake(mb, tip, top_z):
    """Green arrow dripper stake pushed into the soil: tip (in the soil) to its top with the micro-tube barb."""
    x, y, z = tip
    h = top_z - z
    for rz in (0, 90):
        prof = [(-1.2 * MM, 0), (1.2 * MM, 0), (4.0 * MM, h * 0.75), (4.0 * MM, h), (-4.0 * MM, h), (-4.0 * MM, h * 0.75)]
        mb.prism(list(reversed(prof)), 1.2 * MM, "stake_green", M=xform((x, y, z), (90, 0, rz)) @ xform((0, 0, -0.6 * MM)))
    mb.cyl(2.4 * MM, 8 * MM, "stake_green", segs=12, z0=0.0, loc=(x, y, top_z))
    return mb


# ─────────────────────────────── the garden set (both videos) ───────────────────────────────
BAG_X, BAGS_Y, BAG_R, BAG_H, SOIL_Z = 0.17, (0.0, 0.33, 0.66), 0.14, 0.26, 0.24
RISER = (0.0, -0.40)
VALVE_Z = 0.30


def garden(coll):
    """Grow bags with soil + strawberry plants, and the tap riser (GI pipe + brass ball valve). Returns soil objects."""
    soils = []
    for i, y in enumerate(BAGS_Y):
        mb = MB()
        prof = [(BAG_R * 0.96, 0.0), (BAG_R, 0.03), (BAG_R * 1.02, BAG_H * 0.5), (BAG_R, BAG_H - 0.01), (BAG_R + 0.004, BAG_H),
                (BAG_R - 0.004, BAG_H + 0.006), (BAG_R - 0.008, BAG_H - 0.004)]
        mb.lathe(prof, "growbag", segs=48, loc=(BAG_X, y, 0))
        mb.tube(BAG_R - 0.007, BAG_R - 0.009, BAG_H - 0.004 - SOIL_Z + 0.002, "growbag_in", segs=48, z0=SOIL_Z - 0.002, loc=(BAG_X, y, 0))
        mb.add(bm_cyl(BAG_R * 0.96, 0.002, 48, z0=0.0), "growbag", loc=(BAG_X, y, 0))
        ob = mb.build(f"bag_{i + 1}")
        coll.objects.link(ob)
        sm = MB()
        sm.add(bm_cyl(BAG_R - 0.009, 0.006, 48, z0=SOIL_Z - 0.006), SH.soil_material("bag_soil"), loc=(BAG_X, y, 0))
        so = sm.build(f"soil_{i + 1}")
        coll.objects.link(so)
        soils.append(so)
        p = SH.strawberry_plant(cid=f"sb_bag{i + 1}", seed=11 + 7 * i, ripe=3 + (i % 2), green=2, flowers=1 + (i % 2), outward=-1 if i % 2 else 1)
        objs = [p.root] + gh.descendants(p.root)
        for o in objs:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            coll.objects.link(o)
        p.root.location = (BAG_X, y, SOIL_Z)
        p.root.scale = (1.3, 1.3, 1.3)
        p.root.rotation_euler = (0, 0, math.radians(40 + 70 * i))
    mb = MB()
    rx, ry = RISER
    mb.box((0.12, 0.12, 0.012), "concrete", bevel=0.003, loc=(rx, ry, 0.006))
    mb.cyl(0.0107, VALVE_Z - 0.012, "galv", segs=24, z0=0.012, loc=(rx, ry, 0))
    mb.sphere(0.0135, "galv", segs=20, rings=10, loc=(rx, ry, VALVE_Z))                   # elbow
    mb.cyl(0.0107, 0.03, "galv", segs=24, z0=0.0, loc=(rx, ry, VALVE_Z), axis="Y")
    mb.cyl(0.013, 0.05, "brass", segs=24, z0=0.0, loc=(rx, ry + 0.03, VALVE_Z), axis="Y")   # ball valve
    for yy in (ry + 0.03, ry + 0.068):
        mb.cyl(0.0145, 0.012, "brass", segs=6, z0=0.0, loc=(rx, yy, VALVE_Z), axis="Y")
    mb.cyl(0.004, 0.012, "brass", segs=12, z0=0.0, loc=(rx, ry + 0.055, VALVE_Z + 0.012))
    mb.box((0.075, 0.012, 0.004), "ball_red", bevel=0.0015, loc=(rx + 0.03, ry + 0.055, VALVE_Z + 0.025))
    ob = mb.build("riser")
    coll.objects.link(ob)
    return soils


VALVE_Y0 = RISER[1] + 0.08 + 0.0425            # solenoid body centre (inlet thread screws into the ball valve)


# ─────────────────────────────── Part 3: the watering kit ───────────────────────────────
BOXA = dict(W=150.0, H=110.0, D=70.0, origin=(-0.25, -0.40, 0.33))
POST = (-0.25, -0.38)


def box_frame(origin):
    """Box-local frame: local z (out of the box) -> world -y, local y -> world z."""
    return xform(origin, (90, 0, 0))


def water_kit(coll):
    """Part 3 pieces, assembled (steps: 1 water line, 2 sensor, 3 box + brain + relay, 4 power + wires)."""
    k = Kit(coll)
    info = {}
    rx, ry = RISER
    # ── step 1: the water line ──
    mb = MB()
    Mv = xform((rx, VALVE_Y0, VALVE_Z - 0.016), (0, 0, 90))                 # flow along +y
    solenoid_valve(mb, Mv)
    k.add("valve", 1, mb, "12 V water valve", "normally closed · arrow → plants · ₹250")
    info["valve_M"] = Mv
    mb = MB()
    y0 = VALVE_Y0 + 0.030
    mb.cyl(0.013, 0.018, "plastic_black", segs=6, z0=0.0, loc=(rx, y0, VALVE_Z), axis="Y")
    mb.cyl(0.0085, 0.022, "plastic_black", segs=20, z0=0.0, loc=(rx, y0 + 0.018, VALVE_Z), axis="Y", r_top=0.007)
    k.add("connector", 1, mb, "½\" → 16 mm connector", "screws on, pipe pushes on")
    lat_end = BAGS_Y[-1] + 0.15
    pts = [(rx, y0 + 0.03, VALVE_Z), (rx, y0 + 0.07, VALVE_Z), (rx, y0 + 0.11, PIPE_R + 0.001), (rx, lat_end, PIPE_R + 0.001)]
    mb = MB()
    mb.sweep(pts, PIPE_R, "drip_black", segs=14, fillet=0.05)
    mb.cyl(0.009, 0.022, "plastic_black", segs=20, z0=0.0, loc=(rx, lat_end, PIPE_R + 0.001), axis="Y")
    k.add("lateral", 1, mb, "16 mm drip pipe", "₹15 a metre · end cap")
    info["lateral_pts"] = pts
    stakes = []
    for i, y in enumerate(BAGS_Y):
        mb = MB()
        dpos = (rx, y - 0.05, 2 * PIPE_R + 0.001)
        dripper(mb, dpos)
        tip = (BAG_X - 0.075, y - 0.035, SOIL_Z - 0.06)
        top_z = SOIL_Z + 0.03
        arrow_stake(mb, tip, top_z)
        mt = [(rx, y - 0.05, 2 * PIPE_R + 0.016), (rx + 0.01, y - 0.05, 0.03), (BAG_X - BAG_R - 0.012, y - 0.04, 0.05),
              (BAG_X - BAG_R - 0.012, y - 0.04, BAG_H + 0.02), (BAG_X - 0.09, y - 0.036, BAG_H + 0.03), (tip[0], tip[1], top_z + 0.008)]
        mb.sweep(mt, MT_R, "drip_black", segs=8, fillet=0.03)
        k.add(f"drip_{i + 1}", 1, mb, "Dripper + stake", "punch a hole · push in · 1 per pot")
        stakes.append((tip[0], tip[1], SOIL_Z))
    info["stakes"] = stakes
    # ── step 2: the soil sensor in bag 2 ──
    sx, sy = BAG_X + 0.07, BAGS_Y[1] + 0.03
    Ms = xform((sx, sy, SOIL_Z - 0.019), (0, -90, 0)) @ xform((0, 0, -0.8 * MM))       # tip down, connector up
    mb = MB()
    soil_sensor(mb, Ms)
    k.add("sensor", 2, mb, "Soil sensor", "capacitive · nothing to rust · ₹60")
    info["sensor_top"] = P(Ms, *SOIL_JST)
    # ── step 3: post, box, expansion board, ESP32, relay ──
    mb = MB()
    px, py = POST
    mb.box((0.04, 0.04, 0.55), "wood_post", bevel=0.003, loc=(px, py, 0.275))
    for a in (0, 90):
        mb.box((0.26, 0.04, 0.025), "wood_post", bevel=0.003, loc=(px, py, 0.0125), rot=(0, 0, a))
    k.add("post", 3, mb, "Wooden post", "the box hangs on it")
    MB_ = box_frame(BOXA["origin"])
    W, H, D = BOXA["W"], BOXA["H"], BOXA["D"]
    mb = MB()
    ip65_base(mb, MB_, W, H, D, glands=(-45.0, 0.0, 45.0))
    k.add("box", 3, mb, "IP65 box", "150 × 110 × 70 · clear lid")
    Me = MB_ @ xform((-30 * MM, 14 * MM, 8 * MM))
    mb = MB()
    expansion_board(mb, Me)
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            C(mb, Me, "plastic_white", sx_ * (EXP_W / 2 - 3.4), sy_ * (EXP_H / 2 - 3.4), -5.0, 2.5, 5.0, segs=12)
    k.add("expansion", 3, mb, "Expansion board", "12 V in · a G-V-S pin for every pin · ₹120")
    info["exp_M"] = Me
    Mesp = Me @ xform((EX0 * MM, 0, ESP_ON_EXP_Z * MM))
    mb = MB()
    esp32_devkit(mb, Mesp)
    k.add("esp32", 3, mb, "ESP32", "a ₹450 computer with Wi-Fi")
    Mr = MB_ @ xform((42 * MM, 26 * MM, 8 * MM))
    mb = MB()
    relay_module(mb, Mr)
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            C(mb, Mr, "plastic_white", sx_ * 21.0, sy_ * 9.0, -5.0, 2.0, 5.0, segs=12)
    k.add("relay", 3, mb, "Relay", "a switch the ESP32 can press · ₹40")
    info["relay_M"] = Mr
    Mt = MB_ @ xform((30 * MM, -28 * MM, 8 * MM), (0, 0, 180))
    mb = MB()
    dc_terminal(mb, Mt)
    k.add("dc_term", 4, mb, "DC screw terminal", "12 V for the valve · no soldering")
    # ── step 4: power: socket board + adapter, power cable + splitter, all wires ──
    mb = MB()
    Msock = xform((-0.62, -0.56, 0.0), (0, 0, 0))
    socket_board(mb, Msock)
    mb.sweep([(-0.75, -0.56, 0.015), (-0.85, -0.5, 0.004), (-1.6, -0.3, 0.004)], 0.0035, "socket_white", segs=10, fillet=0.06)
    k.add("socket", 4, mb, "Socket board", "")
    mb = MB()
    Mad = xform((-0.71, -0.56, 0.039))
    adapter_12v(mb, Mad)
    k.add("adapter", 4, mb, "12 V 2 A adapter", "₹200 · powers everything")
    # wires (drawn by the video): power cable, inner wires, valve wires, sensor cable
    gl = {g: P(MB_, g, -H / 2 - 13.0, D / 2) for g in (-45.0, 0.0, 45.0)}
    glin = {g: P(MB_, g, -H / 2 + 6.0, D / 2) for g in (-45.0, 0.0, 45.0)}
    jack = P(Me, -36.0, -16.0, 7.1)
    term_in = P(Mt, -18.0, 0, 5.0)
    split = P(MB_, -45.0, -30.0, 30.0)
    mb = MB()
    mb.sweep([tuple(P(Mad, 35.0, 0, 18.0)), (-0.6, -0.52, 0.02), (-0.4, -0.47, 0.004), (BOXA["origin"][0] - 0.045, -0.44, 0.004),
              (BOXA["origin"][0] - 0.045, -0.44, 0.2), tuple(gl[-45.0]), tuple(glin[-45.0]), tuple(split)], 0.0018, "cable", segs=10, fillet=0.03)
    mb.add(bm_box(0.012, 0.016, 0.012), "plastic_black", M=Matrix.Translation(split))
    mb.sweep([tuple(split), tuple(split + Vector((-0.004, 0.0, 0.0))), tuple(jack + Vector((-0.01, 0, 0))), tuple(jack)], 0.0015, "cable", segs=10, fillet=0.012)
    mb.sweep([tuple(split), tuple(split + Vector((0.01, 0.0, 0.0))), tuple(term_in + Vector((-0.012, 0, 0))), tuple(term_in)], 0.0015, "cable", segs=10, fillet=0.012)
    k.add("power_wires", 4, mb, "12 V cable", "one plug for the ESP32 · one for the valve")
    # inner jumper wires (box-local mm -> world)
    mb = MB()
    def gw(name, row, side="L"):
        x, y = gvs(name, row, side)
        return P(Me, x, y, GVS_TOP + 1.0)
    rp = {kk: P(Mr, v[0], v[1], 1.6 + 8.5 + 1.0) for kk, v in RELAY_PIN.items()}
    for (pin, row), rk, m in ((("D26", "V"), "DC+", "wire_red3"), (("D26", "G"), "DC-", "wire_black3"), (("D26", "S"), "IN", "wire_yellow3")):
        a, b = gw(pin, row), rp[rk]
        wire(mb, [a, a + Vector((0, -0.012, 0)), (a + b) / 2 + Vector((0, -0.03, 0.004)), b + Vector((0, -0.012, 0)), b], m)
    # relay terminals -> valve (via the screw terminal +) and the valve's other wire to the terminal -
    tp = P(Mt, 6.0, 2.5, 10.0)
    tm = P(Mt, 6.0, -2.5, 10.0)
    com = P(Mr, *RELAY_TERM["COM"], 6.0)
    no = P(Mr, *RELAY_TERM["NO"], 6.0)
    mb.sweep([tuple(tp), tuple(tp + Vector((0, -0.01, 0))), tuple(com + Vector((0.012, -0.01, 0))), tuple(com)], 0.0009, "wire_red3", segs=8, fillet=0.006)
    info["relay_no"] = no
    k.add("box_wires", 4, mb, "3 short wires", "ESP32 pin D26 → relay")
    # valve wires: relay NO -> valve spade 1, terminal - -> valve spade 2 (through the right gland)
    mb = MB()
    sp = [P(Mv, *s) for s in VALVE_SPADES]
    for a, s, m in ((no, sp[0], "wire_red3"), (tm, sp[1], "wire_black3")):
        pts = [a, a + Vector((0.012, -0.004, 0)), glin[45.0] + Vector((0.003 if m == "wire_red3" else -0.003, 0, 0)),
               gl[45.0], gl[45.0] + Vector((0.01, -0.02, -0.04)), s + Vector((-0.02, -0.03, 0.03)), s + Vector((0, 0, 0.012)), s]
        mb.sweep([tuple(p) for p in pts], 0.0011, m, segs=8, fillet=0.015)
    k.add("valve_wires", 4, mb, "Valve wires", "through the relay's NO and COM")
    # sensor cable: JST -> right side of the bags -> floor -> post -> middle gland -> D34 G/V/S
    mb = MB()
    st = info["sensor_top"]
    path = [st, st + Vector((0, 0, 0.01)), Vector((BAG_X + BAG_R + 0.012, sy, BAG_H + 0.02)), Vector((BAG_X + BAG_R + 0.012, sy, 0.004)),
            Vector((BAG_X + BAG_R + 0.04, -0.25, 0.004)), Vector((0.12, -0.55, 0.004)), Vector((px + 0.05, -0.5, 0.004)), Vector((px + 0.05, -0.45, 0.2)), gl[0.0], glin[0.0]]
    mb.sweep([tuple(p) for p in path], 0.0016, "cable", segs=8, fillet=0.03)
    c0 = glin[0.0]
    for row, m in (("G", "wire_black3"), ("V", "wire_red3"), ("S", "wire_yellow3")):
        b = gw("D34", row)
        wire(mb, [c0, c0 + Vector((0, -0.006, 0.01)), (c0 + b) / 2 + Vector((0, -0.02, 0.0)), b + Vector((0, -0.012, 0)), b], m, ends=(False, True))
    k.add("sensor_cable", 4, mb, "Sensor cable", "G-V-S onto pin D34")
    # lid last
    mb = MB()
    ip65_lid(mb, MB_ @ xform((0, 0, D * MM)), W, H)
    k.add("lid", 4, mb, "Clear lid", "rain stays out · you can see the lights")
    info["box_M"] = MB_
    return k, info


# ─────────────────────────────── Part 4: the climate / disease-warning kit ───────────────────────────────
STAND = (0.46, 0.165)
SHIELD = dict(x=0.34, y=0.165, top=0.50, n=6, gap=0.024, r=0.075)
BOXB = dict(W=115.0, H=90.0, D=55.0)


def saucer(mb, loc, hole):
    """A 15 cm white plant saucer, upside down: flat face on top, rim flaring down. hole = centre hole radius (m)."""
    r0, r1, h = 0.062, 0.075, 0.02
    if hole:
        prof = [(hole, h), (r0, h), (r1, 0.0), (r1 - 0.002, 0.0), (r0 - 0.002, h - 0.002), (hole, h - 0.002)]
        mb.lathe(prof, "saucer", segs=48, closed=True, loc=loc)
    else:
        prof = [(0, h), (r0, h), (r1, 0.0), (r1 - 0.002, 0.0), (r0 - 0.002, h - 0.002), (0, h - 0.002)]
        mb.lathe(prof, "saucer", segs=48, loc=loc)


def sht30_probe(mb, M):
    """SHT30 probe: sintered metal cap (air in, water drops out) on a black sleeve; origin = cable end, cap up."""
    C(mb, M, "plastic_black", 0, 0, 0, 5.0, 10.0, segs=20, r_top=7.0)
    C(mb, M, "stainless", 0, 0, 10.0, 8.0, 14.0, segs=28, bevel=0.6)
    C(mb, M, "sintered", 0, 0, 24.0, 8.0, 22.0, segs=28, bevel=2.0)
    return mb


def climate_kit(coll):
    """Part 4 pieces (steps: 1 stand, 2 shield, 3 sensor, 4 box + wires)."""
    k = Kit(coll)
    info = {}
    sx_, sy_ = STAND
    # step 1: the stand (leaf height)
    mb = MB()
    mb.box((0.2, 0.2, 0.006), "stand_paint", bevel=0.002, loc=(sx_, sy_, 0.003))
    mb.cyl(0.03, 0.012, "stand_paint", segs=24, z0=0.006, loc=(sx_, sy_, 0))
    mb.cyl(0.0127, SHIELD["top"] + 0.06, "galv", segs=24, z0=0.006, loc=(sx_, sy_, 0))
    mb.cyl(0.014, 0.006, "plastic_black", segs=24, z0=SHIELD["top"] + 0.06, loc=(sx_, sy_, 0))
    k.add("stand", 1, mb, "Stand", "25 mm pipe on a flat base · leaf height")
    # step 2: the shield: arm + 3 rods + 6 saucers + spacers
    S = SHIELD
    top = S["top"]
    mb = MB()
    mb.box((sx_ - S["x"], 0.03, 0.005), "alu", loc=((sx_ + S["x"]) / 2, S["y"], top + 0.026))
    mb.box((0.004, 0.05, 0.045), "alu", loc=(sx_ - 0.016, sy_, top + 0.02))
    mb.torus(0.0145, 0.002, "stainless", segs=24, rsegs=6, loc=(sx_, sy_, top + 0.005))
    mb.torus(0.0145, 0.002, "stainless", segs=24, rsegs=6, loc=(sx_, sy_, top + 0.035))
    rods = []
    for a in (90, 210, 330):
        rx_ = S["x"] + 0.055 * math.cos(math.radians(a))
        ry_ = S["y"] + 0.055 * math.sin(math.radians(a))
        rods.append((rx_, ry_))
        mb.cyl(0.0025, S["n"] * S["gap"] + 0.03, "stainless", segs=10, z0=top + 0.03 - (S["n"] * S["gap"] + 0.03), loc=(rx_, ry_, 0))
    k.add("arm_rods", 2, mb, "Arm + 3 threaded rods", "M5 · nuts hold each plate")
    for i in range(S["n"]):
        z = top - i * S["gap"] - 0.02
        mb = MB()
        saucer(mb, (S["x"], S["y"], z), None if i == 0 else 0.032)
        for rx_, ry_ in rods:
            mb.cyl(0.0045, 0.004, "stainless", segs=6, z0=z + 0.02, loc=(rx_, ry_, 0))
            if i > 0:
                mb.tube(0.004, 0.0026, S["gap"] - 0.002, "pvc_white", segs=12, z0=z + 0.02, loc=(rx_, ry_, 0))
        k.add(f"plate_{i + 1}", 2, mb, "White plant saucer" if i else "Top plate (no hole)", "₹20 each · gaps let air through")
    info["shield_mid"] = Vector((S["x"], S["y"], top - 0.5 * S["n"] * S["gap"]))
    # step 3: the probe inside, cable down
    pz = top - (S["n"] - 1) * S["gap"] - 0.01
    Mp = xform((S["x"], S["y"], pz))
    mb = MB()
    sht30_probe(mb, Mp)
    k.add("probe", 3, mb, "SHT30 humidity probe", "±2 % · metal cap keeps drops out · ₹900")
    info["probe_top"] = Vector((S["x"], S["y"], pz + 0.046))
    # step 4: the box on the stand + board + ESP32 + cables + lid
    W, H, D = BOXB["W"], BOXB["H"], BOXB["D"]
    origin = (sx_, sy_ - 0.0127 - 0.003, 0.22)
    MB_ = box_frame(origin)
    mb = MB()
    ip65_base(mb, MB_, W, H, D, glands=(-30.0, 30.0))
    for z in (0.18, 0.26):
        mb.torus(0.0145, 0.002, "stainless", segs=24, rsegs=6, loc=(sx_, sy_, z))
    k.add("box", 4, mb, "IP65 box", "115 × 90 × 55 · 2 hose clips")
    Me = MB_ @ xform((0, 6 * MM, 8 * MM))
    mb = MB()
    expansion_board(mb, Me)
    k.add("expansion", 4, mb, "Expansion board", "jumper on 3.3 V for this sensor")
    Mesp = Me @ xform((EX0 * MM, 0, ESP_ON_EXP_Z * MM))
    mb = MB()
    esp32_devkit(mb, Mesp)
    k.add("esp32", 4, mb, "ESP32", "reads it every 5 min · Wi-Fi to your phone")
    gl = {g: P(MB_, g, -H / 2 - 13.0, D / 2) for g in (-30.0, 30.0)}
    glin = {g: P(MB_, g, -H / 2 + 6.0, D / 2) for g in (-30.0, 30.0)}
    # probe cable: down out of the shield, into the right gland, 4 wires to the G-V-S pins
    mb = MB()
    pc = Vector((S["x"], S["y"], pz))
    path = [pc, pc + Vector((0, 0, -0.03)), Vector((S["x"] + 0.02, S["y"] - 0.03, 0.33)), gl[30.0] + Vector((0.0, -0.03, -0.05)), gl[30.0], glin[30.0]]
    mb.sweep([tuple(p) for p in path], 0.0022, "cable", segs=8, fillet=0.03)

    def gw(name, row, side):
        x, y = gvs(name, row, side)
        return P(Me, x, y, GVS_TOP + 1.0)
    c0 = glin[30.0]
    for (pin, row, side), m in ((("D23", "V", "R"), "wire_red3"), (("D23", "G", "R"), "wire_black3"),
                                (("D21", "S", "R"), "wire_yellow3"), (("D22", "S", "R"), "wire_green3")):
        b = gw(pin, row, side)
        wire(mb, [c0, c0 + Vector((0, -0.006, 0.008)), (c0 + b) / 2 + Vector((0, -0.016, 0.0)), b + Vector((0, -0.012, 0)), b], m, ends=(False, True))
    k.add("probe_wires", 4, mb, "4 wires", "power · ground · SDA → D21 · SCL → D22")
    # USB: charger cable in through the left gland to the ESP32's micro-USB; outside down the stand to the floor, off +x
    mb = MB()
    usb = P(Mesp, -27.0, 0, 3.0)
    path = [Vector((1.2, 0.5, 0.004)), Vector((0.7, 0.25, 0.004)), Vector((sx_ - 0.03, sy_ - 0.05, 0.004)), gl[-30.0] + Vector((0, -0.01, -0.12)),
            gl[-30.0], glin[-30.0], usb + Vector((-0.02, -0.004, 0)), usb]
    mb.sweep([tuple(p) for p in path], 0.0016, "cable", segs=8, fillet=0.03)
    mb.add(bm_box(0.012, 0.008, 0.0045), "plastic_black", M=Matrix.Translation(usb + Vector((-0.006, 0, 0))))
    k.add("usb", 4, mb, "USB cable", "5 V from any phone charger")
    mb = MB()
    ip65_lid(mb, MB_ @ xform((0, 0, D * MM)), W, H)
    k.add("lid", 4, mb, "Clear lid", "")
    info["box_M"] = MB_
    return k, info


# ─────────────────────────────── Part 3 in a real polyhouse (17 Oct 2026) ───────────────────────────────
def zone_kit(coll, corner=(0.0, 16.0), inward=1.0, header_end=(0.97, 16.325), bed_y=16.85, bed_h=0.40, sensor_x=2.0):
    """Part 3 installed in a soil-bed polyhouse (stories/gh01-rover/world.py, house B): the 12 V valve on the feed pipe
    into one zone's sub-main header (after a hand ball valve on a riser), the box + a weatherproof socket on a plank
    clamped to the corner GI column, the soil sensor in the first bed of the zone between the two drip rows.
    The beds' own drip laterals do the watering. Steps: 1 valve + outlet pipe, 2 sensor, 3 plank + box + brain + relay,
    4 power + wires (+ lid, hidden in the video)."""
    k = Kit(coll)
    info = {}
    cx, cy = corner
    s = inward                                             # +1: the house is on the +y side of this wall
    W, H, D = BOXA["W"], BOXA["H"], BOXA["D"]
    plank_y = cy + s * 0.135
    face_x = cx + 0.038                                    # the column's inside face
    # ── static: riser + ball valve (the farm's existing feed), weatherproof socket + conduit ──
    rx, ry = cx + 0.55, header_end[1] + s * 0.075
    mb = MB()
    mb.box((0.12, 0.12, 0.03), "concrete", bevel=0.004, loc=(rx, ry, 0.015))
    mb.cyl(0.0107, VALVE_Z - 0.03, "galv", segs=24, z0=0.03, loc=(rx, ry, 0))
    mb.sphere(0.0135, "galv", segs=20, rings=10, loc=(rx, ry, VALVE_Z))
    mb.cyl(0.0107, 0.03, "galv", segs=24, z0=0.0, loc=(rx, ry, VALVE_Z), axis="X")
    mb.cyl(0.013, 0.05, "brass", segs=24, z0=0.0, loc=(rx + 0.03, ry, VALVE_Z), axis="X")
    for xx in (rx + 0.03, rx + 0.068):
        mb.cyl(0.0145, 0.012, "brass", segs=6, z0=0.0, loc=(xx, ry, VALVE_Z), axis="X")
    mb.cyl(0.004, 0.012, "brass", segs=12, z0=0.0, loc=(rx + 0.055, ry, VALVE_Z + 0.012))
    mb.box((0.012, 0.075, 0.004), "ball_red", bevel=0.0015, loc=(rx + 0.055, ry + s * 0.03, VALVE_Z + 0.025))
    sock = (face_x + 0.025 + 0.035, plank_y, 0.78)
    mb.box((0.07, 0.12, 0.12), "box_grey", bevel=0.006, loc=sock)
    for dz in (-0.028, 0.028):
        mb.box((0.004, 0.05, 0.045), "plastic_white", bevel=0.003, loc=(sock[0] + 0.036, sock[1], sock[2] + dz))
    mb.cyl(0.009, 2.6, "pvc_grey", segs=14, z0=sock[2] + 0.06, loc=(face_x + 0.02, plank_y + s * 0.04, 0))     # conduit
    ob = mb.build("zone_static")
    coll.objects.link(ob)
    info["riser"] = (rx, ry)
    # ── step 1: the valve, its outlet pipe into the header ──
    VX = rx + 0.08 + 0.0425
    Mv = xform((VX, ry, VALVE_Z - 0.016))                  # flow along +x, into the house
    mb = MB()
    solenoid_valve(mb, Mv, face=1 if s > 0 else -1)          # label + arrow towards the house
    k.add("valve", 1, mb, "12 V water valve", "normally closed · arrow → beds · ₹250")
    info["valve_M"] = Mv
    mb = MB()
    x0 = VX + 0.03
    mb.cyl(0.013, 0.018, "pvc_grey", segs=6, z0=0.0, loc=(x0, ry, VALVE_Z), axis="X")
    hx, hy = header_end
    pts = [(x0 + 0.018, ry, VALVE_Z), (x0 + 0.08, ry, VALVE_Z), (hx - 0.12, ry, 0.12), (hx - 0.06, hy, 0.025), (hx - 0.02, hy, 0.02)]
    mb.sweep(pts, 0.0105, "pvc_grey", segs=14, fillet=0.06)
    mb.cyl(0.037, 0.05, "pvc_grey", segs=24, z0=0.0, loc=(hx - 0.03, hy, 0.005), axis="X")         # reducer onto the header
    k.add("outlet", 1, mb, "1/2 inch pipe to the zone header", "1 valve = 1 zone (~4 beds)")
    # ── step 2: the sensor between the drip rows of the zone's first bed ──
    Ms = xform((sensor_x, bed_y, bed_h + 0.004 - 0.019), (0, -90, 0)) @ xform((0, 0, -0.8 * MM))
    mb = MB()
    soil_sensor(mb, Ms)
    k.add("sensor", 2, mb, "Soil sensor", "capacitive · nothing to rust · ₹60")
    info["sensor_top"] = P(Ms, *SOIL_JST)
    # ── step 3: plank on the column, box, expansion board, ESP32, relay ──
    mb = MB()
    mb.box((0.025, 0.24, 0.8), "wood_post", bevel=0.003, loc=(face_x + 0.0125, plank_y, 0.98))
    for z in (0.72, 1.28):
        mb.box((0.115, 0.30, 0.03), "steel_dark", loc=(cx + 0.012, cy + s * 0.105, z))
    k.add("plank", 3, mb, "Plank on the column", "2 steel straps · no drilling")
    rot = (90, 0, 90 if s > 0 else -90)
    origin = (face_x + 0.025, plank_y, 1.2)
    MB_ = xform(origin, rot)
    mb = MB()
    ip65_base(mb, MB_, W, H, D, glands=(-45.0, 0.0, 45.0))
    k.add("box", 3, mb, "IP65 box", "150 × 110 × 70 · on the column")
    Me = MB_ @ xform((-30 * MM, 14 * MM, 8 * MM))
    mb = MB()
    expansion_board(mb, Me)
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            C(mb, Me, "plastic_white", sx_ * (EXP_W / 2 - 3.4), sy_ * (EXP_H / 2 - 3.4), -5.0, 2.5, 5.0, segs=12)
    k.add("expansion", 3, mb, "Expansion board", "12 V in · a G-V-S pin for every pin · ₹120")
    Mesp = Me @ xform((EX0 * MM, 0, ESP_ON_EXP_Z * MM))
    mb = MB()
    esp32_devkit(mb, Mesp)
    k.add("esp32", 3, mb, "ESP32", "a ₹450 computer with Wi-Fi")
    Mr = MB_ @ xform((42 * MM, 26 * MM, 8 * MM))
    mb = MB()
    relay_module(mb, Mr)
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            C(mb, Mr, "plastic_white", sx_ * 21.0, sy_ * 9.0, -5.0, 2.0, 5.0, segs=12)
    k.add("relay", 3, mb, "Relay", "a switch the ESP32 can press · ₹40")
    Mt = MB_ @ xform((30 * MM, -28 * MM, 8 * MM), (0, 0, 180))
    mb = MB()
    dc_terminal(mb, Mt)
    k.add("dc_term", 4, mb, "DC screw terminal", "12 V for the valve · no soldering")
    # ── step 4: adapter in the socket, cables ──
    mb = MB()
    Mad = Matrix.Translation((sock[0] + 0.036, sock[1], sock[2] - 0.028)) @ Matrix(((0, 0, 1, 0), (0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 0, 1)))  # pins into the lower socket, cable up
    adapter_12v(mb, Mad)
    k.add("adapter", 4, mb, "12 V 2 A adapter", "₹200 · in the house's socket")
    gl = {g: P(MB_, g, -H / 2 - 13.0, D / 2) for g in (-45.0, 0.0, 45.0)}
    glin = {g: P(MB_, g, -H / 2 + 6.0, D / 2) for g in (-45.0, 0.0, 45.0)}
    jack = P(Me, -36.0, -16.0, 7.1)
    term_in = P(Mt, -18.0, 0, 5.0)
    split = P(MB_, -45.0, -30.0, 30.0)
    ad_out = P(Mad, 35.0, 0, 18.0)
    mb = MB()
    mb.sweep([tuple(ad_out), tuple(ad_out + Vector((0.01, 0, 0.04))), tuple(gl[-45.0] + Vector((0.01, 0, -0.12))), tuple(gl[-45.0]),
              tuple(glin[-45.0]), tuple(split)], 0.0018, "cable", segs=10, fillet=0.03)
    mb.add(bm_box(0.012, 0.016, 0.012), "plastic_black", M=Matrix.Translation(split))
    for tgt in (jack, term_in):
        mb.sweep([tuple(split), tuple((split + tgt) / 2 + Vector((0.008, 0, 0))), tuple(tgt)], 0.0015, "cable", segs=10, fillet=0.012)
    k.add("power_wires", 4, mb, "12 V cable", "one plug for the ESP32 · one for the valve")
    mb = MB()

    def gw(name, row, side="L"):
        x, y = gvs(name, row, side)
        return P(Me, x, y, GVS_TOP + 1.0)
    out_n = (MB_.to_3x3() @ Vector((0, 0, 1))).normalized()     # out of the box (world)
    rp = {kk: P(Mr, v[0], v[1], 1.6 + 8.5 + 1.0) for kk, v in RELAY_PIN.items()}
    for (pin, row), rk, m in ((("D26", "V"), "DC+", "wire_red3"), (("D26", "G"), "DC-", "wire_black3"), (("D26", "S"), "IN", "wire_yellow3")):
        a, b = gw(pin, row), rp[rk]
        wire(mb, [a, a + out_n * 0.012, (a + b) / 2 + out_n * 0.03, b + out_n * 0.012, b], m)
    tp = P(Mt, 6.0, 2.5, 10.0)
    tm = P(Mt, 6.0, -2.5, 10.0)
    com = P(Mr, *RELAY_TERM["COM"], 6.0)
    no = P(Mr, *RELAY_TERM["NO"], 6.0)
    mb.sweep([tuple(tp), tuple(tp + out_n * 0.01), tuple(com + out_n * 0.01), tuple(com)], 0.0009, "wire_red3", segs=8, fillet=0.006)
    k.add("box_wires", 4, mb, "3 short wires", "ESP32 pin D26 → relay")
    mb = MB()
    sp = [P(Mv, *q) for q in VALVE_SPADES]
    for a, q, m, dd in ((no, sp[0], "wire_red3", 0.004), (tm, sp[1], "wire_black3", -0.004)):
        pts = [a, a + out_n * 0.012, glin[45.0] + Vector((0, dd, 0)), gl[45.0], gl[45.0] + Vector((0.01, 0, -0.15)),
               Vector((face_x + 0.05, plank_y + s * 0.13, 0.5)), q + Vector((-0.06, 0, 0.05)), q + Vector((0, 0, 0.012)), q]
        mb.sweep([tuple(p) for p in pts], 0.0011, m, segs=8, fillet=0.02)
    k.add("valve_wires", 4, mb, "Valve wires", "through the relay's NO and COM")
    mb = MB()
    st_ = info["sensor_top"]
    foot_y = bed_y - s * 0.35
    path = [st_, st_ + Vector((0, 0, 0.01)), Vector((sensor_x - 0.05, bed_y - s * 0.31, bed_h + 0.02)), Vector((sensor_x - 0.08, foot_y, 0.012)),
            Vector((sensor_x - 0.3, cy + s * 0.15, 0.008)), Vector((face_x + 0.06, cy + s * 0.15, 0.008)), Vector((face_x + 0.05, cy + s * 0.15, 0.6)),
            gl[0.0] + Vector((0.01, 0, -0.12)), gl[0.0], glin[0.0]]
    mb.sweep([tuple(p) for p in path], 0.0016, "cable", segs=8, fillet=0.03)
    c0 = glin[0.0]
    for row, m in (("G", "wire_black3"), ("V", "wire_red3"), ("S", "wire_yellow3")):
        b = gw("D34", row)
        wire(mb, [c0, c0 + out_n * 0.006 + Vector((0, 0, 0.01)), (c0 + b) / 2 + out_n * 0.02, b + out_n * 0.012, b], m, ends=(False, True))
    k.add("sensor_cable", 4, mb, "Sensor cable", "G-V-S onto pin D34")
    mb = MB()
    ip65_lid(mb, MB_ @ xform((0, 0, D * MM)), W, H)
    k.add("lid", 4, mb, "Clear lid", "")
    info["box_M"] = MB_
    info["box_c"] = P(MB_, 0, 0, D / 2)
    info["sock"] = Vector(sock)
    return k, info
