"""Tutorial bench parts (14 Oct 2026): real products at real size, for the "Build GH-01" tutorial videos.
Episode 1 = the sticky-trap pest camera: Raspberry Pi Zero 2 W, Camera Module 3, Adafruit TPL5110 power timer,
MT3608 boost board, 18650 cell + holder, 5 V white LED ring, IRLZ44N MOSFET + resistors on a 170-point breadboard,
a multimeter, an IP65 box, a Raspberry Pi 5 + AI HAT+ (the farm computer) and the card frame.

Sizes come from the makers' drawings where they exist:
- Pi Zero 2 W: 65 x 30 mm, holes 3.5 mm in (58 x 23), mini-HDMI at 12.4 mm, USB at 41.4, PWR at 54
  (RP-008358-DS-1 mechanical drawing); parts placed as in the drawing (SoC, shield can, SD, CSI connector).
- Camera Module 3: 25 x 23.862 x 1.12 mm board, holes 2.2 mm 2 mm from the sides, lens centre 14.4 mm up,
  19.61 mm FPC connector on the back, 11.3 mm total height (RP-008151-DS-1).
Everything else is measured from typical listings (marked ~).

Each part is a component (an Empty + parts) like the greenhouse library, so the web side finds parts by
userData gh_id / part_name. Every board lies flat: bottom of the PCB at z = 0, origin at the board centre, x = long side.
"""
import math
import random

import gh
from gh import MB, Component

MM = 0.001

gh.SPEC.update({
    "pcb_rpi": dict(color=(0.035, 0.27, 0.07), rough=0.32, coat=0.35),
    "pcb_black": dict(color=(0.012, 0.012, 0.014), rough=0.35, coat=0.3),
    "pcb_mt": dict(color=(0.02, 0.09, 0.34), rough=0.35, coat=0.3),
    "silk": dict(color=(0.88, 0.88, 0.85), rough=0.6),
    "chip_mark": dict(color=(0.36, 0.36, 0.37), rough=0.6),
    "smd_tan": dict(color=(0.55, 0.42, 0.26), rough=0.45),
    "tin": dict(color=(0.78, 0.78, 0.76), metal=1, rough=0.3),
    "shield": dict(color=(0.74, 0.74, 0.72), metal=1, rough=0.36),
    "fpc_beige": dict(color=(0.86, 0.80, 0.66), rough=0.5),
    "kapton": dict(color=(0.80, 0.45, 0.07), rough=0.25, coat=0.6),
    "pad_yellow": dict(color=(0.95, 0.82, 0.08), rough=0.4),
    "trim_blue": dict(color=(0.04, 0.24, 0.75), rough=0.4),
    "trim_white": dict(color=(0.9, 0.9, 0.88), rough=0.45),
    "ferrite": dict(color=(0.07, 0.07, 0.075), rough=0.6),
    "cell_wrap": dict(color=(0.04, 0.32, 0.68), rough=0.3, coat=0.5),
    "resistor_body": dict(color=(0.80, 0.70, 0.50), rough=0.5),
    "band_brown": dict(color=(0.28, 0.12, 0.04), rough=0.5),
    "band_black": dict(color=(0.02, 0.02, 0.02), rough=0.5),
    "band_red": dict(color=(0.65, 0.04, 0.02), rough=0.5),
    "band_yellow": dict(color=(0.95, 0.75, 0.05), rough=0.5),
    "band_gold": dict(color=(0.9, 0.7, 0.3), metal=1, rough=0.3),
    "breadboard": dict(color=(0.93, 0.93, 0.91), rough=0.55),
    "hole_dark": dict(color=(0.035, 0.035, 0.035), rough=0.9),
    "meter_yellow": dict(color=(0.95, 0.60, 0.02), rough=0.6),
    "meter_face": dict(color=(0.07, 0.07, 0.08), rough=0.5),
    "abs_grey": dict(color=(0.56, 0.58, 0.59), rough=0.5),
    "led_ring": dict(color=(1.0, 0.92, 0.6), rough=0.3, emit=(1, 0.95, 0.85), emit_strength=0.0),
    "phosphor": dict(color=(1.0, 0.85, 0.35), rough=0.3),
    "usb_blue": dict(color=(0.03, 0.2, 0.65), rough=0.4),
    "nylon_white": dict(color=(0.9, 0.89, 0.85), rough=0.6),
    "foam_black": dict(color=(0.03, 0.03, 0.03), rough=0.95),
})


def rrect(w, h, r, n=5):
    """Rounded rectangle, CCW, centred (metres)."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def bx(mb, m, cx, cy, sx, sy, sz, z0=0.0, bevel=0.0, rot=(0, 0, 0)):
    """Box in millimetres: centre (cx, cy), bottom at z0."""
    mb.box((sx * MM, sy * MM, sz * MM), m, bevel=bevel * MM, loc=(cx * MM, cy * MM, (z0 + sz / 2) * MM), rot=rot)


def txt(mb, s, cx, cy, z, size, m="silk", rot=0.0, bold=False, depth=0.02, align="CENTER"):
    mb.text(s, size * MM, m, depth=depth * MM, align=align, bold=bold, loc=(cx * MM, cy * MM, (z + depth / 2) * MM), rot=(0, 0, rot))


def ring_pad(mb, cx, cy, z, r_out, r_in, m="gold"):
    mb.tube(r_out * MM, r_in * MM, 0.04 * MM, m, segs=20, z0=0, loc=(cx * MM, cy * MM, z * MM))
    mb.cyl(r_in * MM, 0.05 * MM, "hole_dark", segs=16, z0=0, loc=(cx * MM, cy * MM, z * MM))


def sprinkle(mb, rnd, n, zones, avoid, z, kinds=((1.0, 0.5, 0.35, "smd_tan"), (1.6, 0.8, 0.45, "smd_tan"), (1.0, 0.5, 0.35, "chip"))):
    """Small SMD passives in free areas (zones / avoid are [x0, y0, x1, y1] in mm, board-centred)."""
    k = 0
    tries = 0
    while k < n and tries < n * 40:
        tries += 1
        x0, y0, x1, y1 = rnd.choice(zones)
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if any(a0 - 0.8 < x < a1 + 0.8 and b0 - 0.8 < y < b1 + 0.8 for a0, b0, a1, b1 in avoid):
            continue
        L, W, H, m = rnd.choice(kinds)
        rot = rnd.choice((0, 90))
        bx(mb, m, x, y, L, W, H, z, rot=(0, 0, rot))
        ex = (L / 2 - 0.12) if rot == 0 else 0
        ey = (L / 2 - 0.12) if rot == 90 else 0
        for s in (-1, 1):
            bx(mb, "tin", x + s * ex, y + s * ey, 0.24 if rot == 0 else W, W if rot == 0 else 0.24, H + 0.02, z - 0.01)
        avoid.append((x - L / 2, y - L / 2, x + L / 2, y + L / 2))
        k += 1


# ═══════════════════════════════ Raspberry Pi Zero 2 W ═══════════════════════════════
ZW, ZH, ZT = 65.0, 30.0, 1.0


def zero_xy(X, Y):
    """Drawing coords (mm from the top-left corner, header edge at the top) -> board-centred mm."""
    return X - ZW / 2, ZH / 2 - Y


def zero_pin(n):
    """Centre of GPIO header pin n (1-40), board-centred mm. Odd pins are the inner row, pin 1 at the SD-card end."""
    c = (n - 1) // 2
    X = 8.37 + 2.54 * c
    Y = 4.77 if n % 2 else 2.23
    return zero_xy(X, Y)


HEADER_TOP = ZT + 2.5 + 6.0       # top of the header pins above the board bottom (mm)


def pi_zero_2w(cid="bp_zero", title="Raspberry Pi Zero 2 W (with header)"):
    c = Component(cid, title, "Bench", summary="65 x 30 mm, quad-core 1 GHz, 512 MB, Wi-Fi. ₹1,770.",
                  real="Raspberry Pi Zero 2 W(H)")
    rnd = random.Random(2)
    pcb = MB()
    pcb.prism(rrect(ZW * MM, ZH * MM, 3.0 * MM), ZT * MM, "pcb_rpi", z0=0.0)
    for X, Y in ((3.5, 3.5), (61.5, 3.5), (3.5, 26.5), (61.5, 26.5)):
        x, y = zero_xy(X, Y)
        ring_pad(pcb, x, y, ZT, 3.0, 1.375)
        ring_pad(pcb, x, y, -0.06, 3.0, 1.375)
    # silkscreen: header outline, labels
    x0, y0 = zero_xy(6.6, 0.6)
    x1, y1 = zero_xy(58.4, 6.4)
    for (a, b, w, h) in (((x0 + x1) / 2, y0, x1 - x0, 0.18), ((x0 + x1) / 2, y1, x1 - x0, 0.18),
                         (x0, (y0 + y1) / 2, 0.18, y0 - y1), (x1, (y0 + y1) / 2, 0.18, y0 - y1)):
        bx(pcb, "silk", a, b, w, h, 0.02, ZT)
    txt(pcb, "GPIO", *zero_xy(39.5, 8.0), ZT, 1.3)
    txt(pcb, "USB", *zero_xy(37.0, 22.6), ZT, 1.2)
    txt(pcb, "PWR IN", *zero_xy(57.6, 20.5), ZT, 1.1, rot=90)
    c.part("pcb", pcb, desc="The board: 65 x 30 mm.")

    top = MB()
    # SoC RP3A0 (SiP: quad Cortex-A53 + 512 MB) and the Wi-Fi shield can
    x, y = zero_xy((19.8 + 34.9) / 2, (8.3 + 23.5) / 2)
    bx(top, "chip", x, y, 15.1, 15.2, 1.2, ZT, bevel=0.25)
    txt(top, "RP3A0-AU", x, y - 1.6, ZT + 1.2, 1.5, m="chip_mark", bold=True)
    txt(top, "2041", x, y - 3.6, ZT + 1.2, 1.1, m="chip_mark")
    for k in range(7):                     # a small raspberry: 7 dots
        a = k * math.tau / 6
        top.cyl(0.55 * MM, 0.02 * MM, "chip_mark", segs=12, z0=0,
                loc=((x + (0 if k == 6 else 0.95 * math.cos(a))) * MM, (y + 3.0 + (0 if k == 6 else 0.95 * math.sin(a))) * MM, (ZT + 1.2) * MM))
    x, y = zero_xy((37.6 + 50.0) / 2, (10.2 + 22.4) / 2)
    bx(top, "shield", x, y, 12.4, 12.2, 1.5, ZT, bevel=0.2)
    bx(top, "shield", x, y, 11.2, 11.0, 0.05, ZT + 1.5)
    # microSD slot, crystal, small ICs, inductor
    x, y = zero_xy((1.5 + 13.0) / 2, (7.1 + 19.1) / 2)
    bx(top, "shield", x, y, 11.5, 12.0, 1.4, ZT, bevel=0.1)
    for k in range(8):
        bx(top, "gold", x + 4.4, y + 4.2 - k * 1.1, 2.2, 0.55, 0.05, ZT + 1.4)
    bx(top, "shield", *zero_xy(15.0, 13.75), 2.4, 3.3, 0.8, ZT, bevel=0.1)
    for X0, Y0, X1, Y1, h in ((52.2, 6.5, 54.3, 8.1, 0.8), (55.9, 11.8, 58.5, 13.8, 0.9), (54.0, 15.0, 57.0, 18.0, 0.9),
                              (20.7, 25.3, 22.6, 28.2, 1.0), (13.8, 12.1, 16.2, 15.4, 0.8)):
        bx(top, "chip", *zero_xy((X0 + X1) / 2, (Y0 + Y1) / 2), X1 - X0, Y1 - Y0, h, ZT, bevel=0.08)
    x, y = zero_xy(52.85, 22.0)
    top.prism([(math.cos(math.radians(22.5 + 45 * k)) * 2.3 * MM, math.sin(math.radians(22.5 + 45 * k)) * 2.3 * MM) for k in range(8)],
              2.0 * MM, "ferrite", z0=ZT * MM, loc=(x * MM, y * MM, 0))
    # connectors: mini-HDMI, 2 x micro-USB
    x, y = zero_xy(12.4, 26.7)
    bx(top, "shield", x, y, 11.2, 7.5, 3.2, ZT, bevel=0.3)
    bx(top, "hole_dark", x, y - 3.7, 9.8, 0.1, 2.0, ZT + 0.6)
    for X in (41.4, 54.0):
        x, y = zero_xy(X, 27.2)
        bx(top, "shield", x, y, 7.6, 5.9, 2.6, ZT, bevel=0.25)
        bx(top, "shield", x, y - 3.0, 8.4, 0.3, 3.0, ZT - 0.2)
        bx(top, "hole_dark", x, y - 3.05, 6.4, 0.12, 1.6, ZT + 0.5)
    # GPIO header (black base 2.5 mm, 40 gold pins 6 mm above, 3 mm below)
    hx, hy = zero_xy(32.5, 3.5)
    bx(top, "plastic_black", hx, hy, 50.8, 5.08, 2.5, ZT, bevel=0.2)
    for n in range(1, 41):
        px, py = zero_pin(n)
        bx(top, "gold", px, py, 0.64, 0.64, 6.0 + 2.5 + 3.0 + ZT, -3.0, bevel=0.08)
        bx(top, "tin", px, py, 1.6, 1.6, 0.6, -0.6, bevel=0.3)     # solder fillets underneath
    # passives
    avoid = [(-31, 9, 26, 15), (-31, -5, -19, 8), (-13, -9, 3, 7), (5, -8, 18, 5), (-26, -16, -14, -8), (5, -16, 13, -8),
             (18, -16, 26, -8), (28, -9, 33, 9), (17, -10, 23, -4), (19, 3, 26, 9)]
    sprinkle(top, rnd, 46, [(-30, -14, 30, 8)], avoid, ZT)
    c.part("parts", top, desc="RP3A0 (CPU + 512 MB), Wi-Fi under the metal can, microSD, mini-HDMI, USB, PWR IN.")

    # CSI camera connector (22-pin, 0.5 mm): beige body, black latch that slides out 1 mm to open
    x, y = zero_xy(62.8, 14.95)
    csi = MB()
    bx(csi, "fpc_beige", 0, 0, 2.4, 16.3, 1.2, 0.0, bevel=0.1)
    for k in range(22):
        bx(csi, "gold", -0.6, -5.25 + k * 0.5, 0.9, 0.22, 0.05, 1.2)
    c.part("csi", csi, loc=(x * MM, y * MM, ZT * MM), desc="Camera connector (22-pin, 0.5 mm pitch).")
    lt = MB()
    bx(lt, "plastic_black", 0, 0, 0.9, 16.0, 1.25, 0.0, bevel=0.1)
    c.part("csi_latch", lt, loc=((x + 1.6) * MM, y * MM, ZT * MM), desc="Latch: pull out to open, push in to lock.")
    return c


# ═══════════════════════════════ Camera Module 3 ═══════════════════════════════
CW, CH, CT = 25.0, 23.862, 1.12
LENS_Y = 14.4 - CH / 2          # lens centre, board-centred (mm)
LENS_TOP = CT + 7.8             # lens tip above the board bottom (mm); + 2.4 mm connector behind = 11.3 total


def camera_module_3(cid="bp_cam3", title="Raspberry Pi Camera Module 3"):
    c = Component(cid, title, "Bench", summary="Sony IMX708, 12 MP, autofocus 10 cm to infinity, 66 x 41 deg view. ₹3,158.",
                  real="Raspberry Pi Camera Module 3 (standard)")
    pcb = MB()
    pcb.prism(rrect(CW * MM, CH * MM, 1.5 * MM), CT * MM, "pcb_rpi", z0=0.0)
    for sx in (-1, 1):
        for y in (2.0 - CH / 2, 14.5 - CH / 2):
            ring_pad(pcb, sx * 10.5, y, CT, 2.375, 1.1, m="pad_yellow")
            ring_pad(pcb, sx * 10.5, y, -0.06, 2.375, 1.1, m="pad_yellow")
    txt(pcb, "Camera Module 3", 10.9, 0.5, CT, 1.15, rot=90)
    txt(pcb, "Raspberry Pi", -10.9, -2.0, CT, 1.15, rot=90)
    for k in range(7):
        a = k * math.tau / 6
        pcb.cyl(0.45 * MM, 0.02 * MM, "silk", segs=10, z0=0,
                loc=((-9.6 + (0 if k == 6 else 0.8 * math.cos(a))) * MM, (8.6 + (0 if k == 6 else 0.8 * math.sin(a))) * MM, CT * MM))
    c.part("pcb", pcb, desc="25 x 24 mm board, same holes as Camera Module 2.")
    opt = MB()
    # sensor base, autofocus actuator (silver, chamfered), lens barrel
    bx(opt, "chip", 0, LENS_Y, 10.4, 10.4, 0.9, CT, bevel=0.1)
    a, b_ = 4.4, 3.3                                   # square VCM housing, 8.8 mm, corners chamfered 1.1 mm
    sq = [(a, b_), (b_, a), (-b_, a), (-a, b_), (-a, -b_), (-b_, -a), (b_, -a), (a, -b_)]
    opt.prism([(x * MM, y * MM) for x, y in sq], 3.6 * MM, "shield", z0=(CT + 0.9) * MM, loc=(0, LENS_Y * MM, 0), bevel=0.25 * MM)
    opt.prism([(x * 0.86 * MM, y * 0.86 * MM) for x, y in sq], 0.5 * MM, "shield", z0=(CT + 4.5) * MM, loc=(0, LENS_Y * MM, 0))
    opt.cyl(2.875 * MM, 2.4 * MM, "plastic_black", segs=40, bevel=0.3 * MM, z0=(CT + 4.9) * MM, loc=(0, LENS_Y * MM, 0))
    opt.tube(2.875 * MM, 2.0 * MM, 0.5 * MM, "plastic_black", segs=40, z0=(CT + 7.3) * MM, loc=(0, LENS_Y * MM, 0))
    opt.cyl(2.0 * MM, 0.1 * MM, "lens", segs=32, z0=(CT + 7.0) * MM, loc=(0, LENS_Y * MM, 0))
    opt.cyl(0.9 * MM, 0.05 * MM, "lens", segs=24, z0=(CT + 7.1) * MM, loc=(0, LENS_Y * MM, 0))
    # sensor flex + gold stiffener + QR at the top edge
    bx(opt, "kapton", -1.2, 9.4, 3.6, 3.0, 0.3, CT)
    bx(opt, "gold", -1.2, 9.4, 3.0, 2.4, 0.05, CT + 0.3)
    bx(opt, "sticker_white", 2.6, 9.4, 3.0, 3.0, 0.15, CT)
    rnd = random.Random(5)
    for i in range(6):
        for j in range(6):
            if rnd.random() < 0.5:
                bx(opt, "chip", 1.4 + i * 0.45, 8.2 + j * 0.45, 0.4, 0.4, 0.03, CT + 0.15)
    sprinkle(opt, rnd, 14, [(-11, -11, 11, -5), (6, -4, 11, 8)], [(-6, -9, 6, 8), (-12, -12, -8.5, 12), (8.5, -12, 12, 12)], CT)
    c.part("optics", opt, desc="Autofocus lens (4.74 mm, f/1.8) over the 12 MP Sony IMX708.")
    con = MB()                           # 15-pin, 1 mm FPC connector on the back, at the bottom edge
    bx(con, "plastic_black", 0, -CH / 2 + 2.6, 19.61, 4.0, 2.4, -2.4, bevel=0.15)
    for k in range(15):
        bx(con, "gold", -7.0 + k * 1.0, -CH / 2 + 0.4, 0.4, 0.8, 0.1, -0.8)
    c.part("connector", con, desc="15-pin, 1 mm ribbon connector (back side).")
    return c


# ═══════════════════════════════ Adafruit TPL5110 power timer ═══════════════════════════════
TPL_W, TPL_H = 20.3, 17.8
TPL_PADS = ["VDD", "GND", "DRV", "DONE", "DLY"]


def tpl_pad(name):
    k = TPL_PADS.index(name)
    return (-5.08 + 2.54 * k, -TPL_H / 2 + 1.6)


def tpl5110(cid="bp_tpl", title="Adafruit TPL5110 power timer"):
    c = Component(cid, title, "Bench", summary="Wakes the project every 100 ms to 2 h (trimpot), cuts its power on DONE. ~20 µA idle.",
                  real="Adafruit 3435 TPL5110 Low Power Timer Breakout")
    b = MB()
    b.prism(rrect(TPL_W * MM, TPL_H * MM, 1.8 * MM), 1.6 * MM, "pcb_black", z0=0.0)
    for nm in TPL_PADS:
        x, y = tpl_pad(nm)
        ring_pad(b, x, y, 1.6, 0.95, 0.5)
        txt(b, nm, x, y + 2.0, 1.6, 0.85, bold=True)
    for sx in (-1, 1):
        ring_pad(b, sx * 7.6, 5.9, 1.6, 1.6, 1.25)
    txt(b, "TPL5110", 0, 6.6, 1.6, 1.2, bold=True)
    bx(b, "chip", -2.2, 2.4, 2.9, 1.6, 1.0, 1.6, bevel=0.1)                     # TPL5110 (SOT-23-6)
    bx(b, "chip", 1.9, 2.4, 2.9, 1.3, 1.0, 1.6, bevel=0.1)                      # P-MOSFET (SOT-23)
    bx(b, "trim_white", 5.4, 1.2, 3.6, 3.6, 1.4, 1.6, bevel=0.2)               # delay trimpot
    b.cyl(1.25 * MM, 0.5 * MM, "trim_blue", segs=20, z0=3.0 * MM, loc=(5.4 * MM, 1.2 * MM, 0))
    bx(b, "plastic_black", 5.4, 1.2, 2.0, 0.35, 0.2, 3.45)
    bx(b, "shield", -6.3, 1.8, 3.6, 3.0, 1.0, 1.6, bevel=0.1)                   # tactile switch
    b.cyl(0.8 * MM, 0.5 * MM, "plastic_black", segs=16, z0=2.6 * MM, loc=(-6.3 * MM, 1.8 * MM, 0))
    rnd = random.Random(11)
    sprinkle(b, rnd, 7, [(-9, -3, 9, 4)], [(-8.5, 0, -4, 3.6), (-4, 1.4, 4, 3.4), (3.4, -1, 7.4, 3.2), (-9, -9, 9, -2.7)], 1.6)
    c.part("board", b, desc="Timer chip + MOSFET switch, DELAY trimpot (fully right = every 2 h), manual-on button.")
    return c


# ═══════════════════════════════ MT3608 boost board ═══════════════════════════════
MT_W, MT_H = 36.0, 17.0
MT_PADS = {"VIN+": (-15.6, 5.6), "VIN-": (-15.6, -5.6), "VOUT+": (15.6, 5.6), "VOUT-": (15.6, -5.6)}


def mt3608(cid="bp_boost", title="MT3608 boost board"):
    c = Component(cid, title, "Bench", summary="Steps the 3.7 V cell up to 5.1 V. Set the trimpot BEFORE connecting the Pi.",
                  real="MT3608 2 A DC-DC step-up module (~₹50)")
    b = MB()
    b.prism(rrect(MT_W * MM, MT_H * MM, 0.8 * MM), 1.6 * MM, "pcb_mt", z0=0.0)
    for nm, (x, y) in MT_PADS.items():
        ring_pad(b, x, y, 1.6, 1.3, 0.6)
        ring_pad(b, x, y, -0.06, 1.3, 0.6)
        txt(b, nm, x + (4.3 if x < 0 else -4.3), y, 1.6, 1.1, bold=True)
    bx(b, "ferrite", -2.6, -2.2, 6.0, 6.0, 4.5, 1.6, bevel=0.6)                 # 22 µH inductor
    bx(b, "chip", 3.6, -4.0, 2.9, 1.6, 1.0, 1.6, bevel=0.1)                     # MT3608
    bx(b, "chip", 3.6, 1.4, 4.3, 2.6, 2.1, 1.6, bevel=0.15)                     # SS34 diode
    bx(b, "chip_mark", 2.1, 1.4, 0.5, 2.6, 2.12, 1.6)
    for x in (-9.0, 8.8):
        bx(b, "smd_tan", x, -1.0, 3.2, 1.6, 1.4, 1.6, bevel=0.1)                 # 22 µF caps
        for s in (-1, 1):
            bx(b, "tin", x + s * 1.45, -1.0, 0.35, 1.65, 1.45, 1.6)
    bx(b, "trim_blue", -3.4, 5.4, 9.5, 4.8, 10.0, 1.6, bevel=0.3)              # 3296W 100k multi-turn trimpot
    c.part("board", b, desc="Boost converter: inductor, MT3608 chip, diode, caps.")
    sc = MB()                                                                   # brass adjusting screw (turns in the video)
    sc.cyl(1.1 * MM, 0.9 * MM, "brass", segs=20, z0=0.0)
    bx(sc, "steel_dark", 0, 0, 2.0, 0.35, 0.2, 0.75)
    c.part("trim_screw", sc, loc=(-6.6 * MM, 5.4 * MM, 11.6 * MM), desc="Turn to set the output voltage.")
    return c


# ═══════════════════════════════ 18650 cell in a holder ═══════════════════════════════
def cell_holder(cid="bp_cell", title="18650 Li-ion cell + holder"):
    c = Component(cid, title, "Bench", summary="3.7 V, 3000 mAh (11 Wh). Charged between card changes.", real="18650 3000 mAh + 1-cell holder")
    h = MB()
    L, W = 77.0, 21.0
    bx(h, "plastic_black", 0, 0, L, W, 1.5, 0.0, bevel=0.3)
    for sy in (-1, 1):
        bx(h, "plastic_black", 0, sy * (W / 2 - 0.75), L - 6, 1.5, 11.0, 0.0, bevel=0.3)
    for sx in (-1, 1):
        bx(h, "plastic_black", sx * (L / 2 - 1.0), 0, 2.0, W, 17.0, 0.0, bevel=0.4)
    # spring (- end) and plate (+ end)
    from parts import helix
    pts = helix(4.0 * MM, 1.6 * MM, 4.0)
    h.sweep([(p[2] - (L / 2 - 2.0) * MM, p[0], p[1] + 10.5 * MM) for p in pts], 0.35 * MM, "tin", segs=6)
    bx(h, "tin", L / 2 - 2.3, 0, 0.5, 9.0, 9.0, 6.0)
    txt(h, "+", L / 2 - 6.0, -W / 2 + 3.0, 1.5, 3.0, m="silk", bold=True)
    txt(h, "-", -L / 2 + 6.0, -W / 2 + 3.0, 1.5, 3.0, m="silk", bold=True)
    c.part("holder", h, desc="Single 18650 holder with leads.")
    ce = MB()
    R, CL = 9.2, 65.0
    ce.cyl(R * MM, (CL - 1.0) * MM, "cell_wrap", segs=40, bevel=0.6 * MM, axis="X")
    ce.cyl(3.0 * MM, 1.2 * MM, "tin", segs=24, axis="X", loc=((CL / 2 - 0.2) * MM, 0, 0))
    ce.cyl(8.0 * MM, 0.4 * MM, "tin", segs=32, axis="X", loc=((-CL / 2 + 0.6) * MM, 0, 0))
    ce.text("18650  3000mAh  3.7V", 3.6 * MM, "silk", depth=0.05 * MM, bold=True, loc=(0, 0, R * MM + 0.02 * MM))
    c.part("cell", ce, loc=(0.6 * MM, 0, 10.8 * MM), desc="18650 lithium-ion cell.")
    return c


# ═══════════════════════════════ 5 V white LED ring ═══════════════════════════════
RING_R0, RING_R1, RING_N = 13.0, 22.0, 12


def led_ring(cid="bp_ring", title="5 V white LED ring (12 LEDs)"):
    c = Component(cid, title, "Bench", summary="Even light on the card for every photo, ~150 mA at 5 V. Switched by a MOSFET.",
                  real="5 V white LED ring, 44 mm (or a USB ring light with the plug cut off)")
    b = MB()
    b.tube(RING_R1 * MM, RING_R0 * MM, 1.6 * MM, "pcb_black", segs=64, z0=0.0)
    for k in range(RING_N):
        a = k * math.tau / RING_N
        r = (RING_R0 + RING_R1) / 2
        x, y = r * math.cos(a), r * math.sin(a)
        bx(b, "plastic_white", x, y, 5.0, 5.0, 1.5, 1.6, bevel=0.2, rot=(0, 0, math.degrees(a)))
        b.cyl(2.0 * MM, 0.06 * MM, "phosphor", segs=20, z0=3.1 * MM, loc=(x * MM, y * MM, 0))
        for s in (-1, 1):
            bx(b, "tin", x + 2.9 * math.cos(a + s * 0.24), y + 2.9 * math.sin(a + s * 0.24), 0.6, 0.6, 0.3, 1.6)
    for nm, a in (("+", -100), ("-", -80)):
        x, y = 20.0 * math.cos(math.radians(a)), 20.0 * math.sin(math.radians(a))
        ring_pad(b, x, y, 1.6, 0.9, 0.45)
    txt(b, "5V", 20.0 * math.cos(math.radians(-118)), 20.0 * math.sin(math.radians(-118)), 1.6, 1.6, bold=True, rot=-28)
    c.part("pcb", b, desc="Ring PCB with 12 white LEDs.")
    em = MB()
    for k in range(RING_N):
        a = k * math.tau / RING_N
        r = (RING_R0 + RING_R1) / 2
        em.cyl(1.7 * MM, 0.08 * MM, "led_ring", segs=20, z0=3.17 * MM, loc=(r * math.cos(a) * MM, r * math.sin(a) * MM, 0))
    c.part("leds", em, desc="The LED emitters (they light up).")
    return c


# ═══════════════════════════════ breadboard with the MOSFET switch ═══════════════════════════════
BB_W, BB_H, BB_T = 46.5, 34.5, 8.5
ROWS = "abcdefghij"


def bb_hole(col, row):
    """170-point mini breadboard: columns 1-17, rows a-j (a-e and f-j are joined per column). mm, board-centred."""
    ri = ROWS.index(row)
    y = (3.81 + (4 - ri) * 2.54) if ri < 5 else -(3.81 + (ri - 5) * 2.54)
    return ((col - 9) * 2.54, y)


def resistor(mb, a, b, bands, z_top, lift=3.0):
    """Axial 1/4 W resistor with its legs in breadboard holes a and b (mm, board-centred); body bridged above."""
    (x0, y0), (x1, y1) = a, b
    L = math.hypot(x1 - x0, y1 - y0)
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    zc = z_top + lift
    body = min(6.0, L - 1.6)
    mb.cyl(1.15 * MM, body * MM, "resistor_body", segs=20, bevel=0.5 * MM, axis="X", loc=(cx * MM, cy * MM, zc * MM), rot=(0, 0, ang))
    for k, bm in enumerate(bands):
        off = -body / 2 + 1.0 + k * 0.95 if k < 3 else body / 2 - 1.0
        dx, dy = off * math.cos(math.radians(ang)), off * math.sin(math.radians(ang))
        mb.cyl(1.2 * MM, 0.45 * MM, bm, segs=20, axis="X", loc=((cx + dx) * MM, (cy + dy) * MM, zc * MM), rot=(0, 0, ang))
    for (x, y), s in (((x0, y0), -1), ((x1, y1), 1)):
        ex, ey = cx + s * (body / 2) * math.cos(math.radians(ang)), cy + s * (body / 2) * math.sin(math.radians(ang))
        mb.sweep([(ex * MM, ey * MM, zc * MM), (x * MM, y * MM, zc * MM), (x * MM, y * MM, (z_top - 2.0) * MM)], 0.3 * MM, "tin",
                 segs=6, fillet=0.0)


def breadboard(cid="bp_bread", title="Mini breadboard: MOSFET light switch"):
    c = Component(cid, title, "Bench", summary="IRLZ44N logic-level MOSFET, 1 kΩ gate resistor, 100 kΩ pull-down.",
                  real="170-point mini breadboard + IRLZ44N + 1/4 W resistors")
    b = MB()
    bx(b, "breadboard", 0, 0, BB_W, BB_H, BB_T, 0.0, bevel=0.6)
    bx(b, "hole_dark", 0, 0, BB_W - 4, 1.6, 0.4, BB_T - 0.38)                   # centre channel
    for col in range(1, 18):
        for row in ROWS:
            x, y = bb_hole(col, row)
            bx(b, "hole_dark", x, y, 0.8, 0.8, 0.3, BB_T - 0.28)
    for col in (1, 5, 10, 15):
        txt(b, str(col), bb_hole(col, "a")[0], 16.0, BB_T, 1.3, m="chip_mark")
    for row in "aej":
        txt(b, row, -22.0, bb_hole(1, row)[1], BB_T, 1.3, m="chip_mark")
    c.part("board", b, desc="170 holes; each column of 5 is one wire inside.")
    # IRLZ44N in a8 (gate) a9 (drain) a10 (source), tab towards the back
    m = MB()
    gx, gy = bb_hole(9, "a")
    zb = BB_T + 2.5
    bx(m, "epoxy_black", gx, gy + 0.5, 10.1, 4.5, 9.2, zb, bevel=0.2)
    bx(m, "tin", gx, gy + 2.1, 10.1, 1.3, 15.5, zb)
    m.cyl(1.8 * MM, 1.4 * MM, "hole_dark", segs=20, axis="Y", loc=(gx * MM, (gy + 2.1) * MM, (zb + 12.3) * MM))
    txt(m, "IRLZ44N", gx, gy - 1.76, zb + 5.2, 1.3, m="chip_mark", depth=0.03)
    for k in (-1, 0, 1):
        x = gx + k * 2.54
        bx(m, "tin", x, gy, 0.8, 0.5, 2.5 + 2.0, BB_T - 2.0)
    c.part("mosfet", m, desc="IRLZ44N: fully on at 3.3 V on the gate (an IRF520 is not).")
    r = MB()
    resistor(r, bb_hole(5, "d"), bb_hole(8, "d"), ["band_brown", "band_black", "band_red", "band_gold"], BB_T, lift=2.0)     # 1 kΩ
    resistor(r, bb_hole(8, "e"), bb_hole(10, "e"), ["band_brown", "band_black", "band_yellow", "band_gold"], BB_T, lift=1.4)  # 100 kΩ
    c.part("resistors", r, desc="1 kΩ (brown-black-red) gate resistor, 100 kΩ (brown-black-yellow) gate-to-source pull-down.")
    return c


# ═══════════════════════════════ multimeter ═══════════════════════════════
def multimeter(cid="bp_meter", title="Digital multimeter"):
    c = Component(cid, title, "Bench", summary="Set the boost output to 5.1 V before connecting anything.", real="Any DMM, DC volts")
    b = MB()
    W, H, T = 75.0, 145.0, 30.0
    b.prism(rrect(W * MM, H * MM, 9.0 * MM), T * MM, "meter_yellow", z0=0.0, bevel=2.0 * MM)
    b.prism(rrect((W - 9) * MM, (H - 12) * MM, 6.0 * MM), 1.0 * MM, "meter_face", z0=(T - 0.4) * MM)
    bx(b, "screen", 0, 42.0, 50.0, 25.0, 0.6, T + 0.4, bevel=0.5)                # LCD window (digits drawn on the web)
    b.cyl(17.0 * MM, 3.5 * MM, "plastic_black", segs=48, bevel=0.8 * MM, z0=(T + 0.6) * MM, loc=(0, 0, 0))
    bx(b, "plastic_white", 0, 0, 3.0, 26.0, 1.2, T + 4.1, bevel=0.4)             # dial knob ridge / pointer
    bx(b, "plastic_red", 0, 11.0, 2.0, 4.0, 0.4, T + 5.3)
    for k, (x, col) in enumerate(((-22.0, "plastic_red"), (0.0, "plastic_black"), (22.0, "plastic_red"))):
        b.tube(4.0 * MM, 2.0 * MM, 2.0 * MM, col, segs=24, z0=(T + 0.6) * MM, loc=(x * MM, -50.0 * MM, 0))
        b.cyl(2.0 * MM, 0.2 * MM, "hole_dark", segs=16, z0=(T + 0.8) * MM, loc=(x * MM, -50.0 * MM, 0))
    for k, s in enumerate(("V", "Ω", "A", "OFF")):
        a = math.radians(90 + 50 * (k - 1.5))
        txt(b, s, 23.0 * math.cos(a), 23.0 * math.sin(a), T + 0.6, 3.2, m="silk", bold=True)
    c.part("body", b, desc="Meter body, dial on DC volts.")
    for nm, col, x in (("probe_red", "plastic_red", 0.0), ("probe_black", "plastic_black", 0.0)):
        p = MB()
        p.cyl(4.0 * MM, 95.0 * MM, col, segs=24, bevel=1.0 * MM, z0=0.0)
        p.cyl(5.0 * MM, 3.0 * MM, col, segs=24, bevel=0.8 * MM, z0=-3.0 * MM)
        p.cyl(1.0 * MM, 14.0 * MM, "stainless", segs=12, r_top=0.15 * MM, z0=-17.0 * MM)
        c.part(nm, p, loc=(x, -0.2, 0.0), desc="Test probe (tip down).")
    return c


# ═══════════════════════════════ IP65 box ═══════════════════════════════
BOX_W, BOX_D, BOX_H, BOX_WALL = 115.0, 90.0, 55.0, 2.5
WIN_R = 25.0          # round window over the lens + LED ring


def ip65_box(cid="bp_box", title="IP65 box with a window"):
    c = Component(cid, title, "Bench", summary="ABS IP65 box, 115 x 90 x 55 mm. A 50 mm acrylic window glued over a hole for the camera and light.",
                  real="ABS IP65 junction box ~₹300 + 3 mm acrylic disc")
    b = MB()
    W, D, H, t = BOX_W, BOX_D, BOX_H, BOX_WALL
    b.prism(rrect(W * MM, D * MM, 6.0 * MM), t * MM, "abs_grey", z0=0.0, bevel=0.8 * MM)
    for sx in (-1, 1):
        bx(b, "abs_grey", sx * (W / 2 - t / 2), 0, t, D - 8, H - 3, t, bevel=0.6)
    for sy in (-1, 1):
        bx(b, "abs_grey", 0, sy * (D / 2 - t / 2), W - 8, t, H - 3, t, bevel=0.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(5.0 * MM, (H - 3) * MM, "abs_grey", segs=24, z0=t * MM, loc=(sx * (W / 2 - 5.0) * MM, sy * (D / 2 - 5.0) * MM, 0))
            b.cyl(1.6 * MM, 0.3 * MM, "hole_dark", segs=12, z0=(H - 0.2) * MM, loc=(sx * (W / 2 - 5.0) * MM, sy * (D / 2 - 5.0) * MM, 0))
    c.part("base", b, desc="Box base.")
    pl = MB()                                       # mounting plate for the camera + ring, 37.5 mm up
    bx(pl, "plastic_black", 0, 0, W - 8, D - 8, 2.0, 0.0)
    bx(pl, "hole_dark", -20.0, 0, 3.0, 20.0, 0.1, 2.0)                           # ribbon slot
    c.part("plate", pl, loc=(0, 0, 37.5 * MM), desc="Black mounting plate for the camera and LED ring.")
    ld = MB()
    from parts import polygon_plate_with_hole
    polygon_plate_with_hole(ld, "abs_grey", rrect(W * MM, D * MM, 6.0 * MM), WIN_R * MM, 3.0 * MM, M=gh.xform((0, 0, 3.0 * MM)), per=6)
    ld.cyl((WIN_R + 1.5) * MM, 3.0 * MM, "acrylic", segs=64, z0=1.5 * MM)
    ld.torus((WIN_R + 0.2) * MM, 0.8 * MM, "plastic_black", segs=64, rsegs=8, loc=(0, 0, 4.6 * MM))
    for sx in (-1, 1):
        for sy in (-1, 1):
            ld.cyl(2.6 * MM, 1.0 * MM, "stainless", segs=16, bevel=0.3 * MM, z0=6.0 * MM, loc=(sx * (W / 2 - 5.0) * MM, sy * (D / 2 - 5.0) * MM, 0))
            bx(ld, "steel_dark", sx * (W / 2 - 5.0), sy * (D / 2 - 5.0), 2.6, 0.4, 0.2, 7.0)
    c.part("lid", ld, loc=(0, 0, BOX_H * MM), desc="Lid with a clear window over the lens.")
    sg = MB()
    bx(sg, "sticker_white", 0, 0, 30, 22, 4.0, 0.0, bevel=1.5)
    txt(sg, "SILICA GEL", 0, 2.0, 4.0, 2.4, m="chip_mark", bold=True)
    txt(sg, "DO NOT EAT", 0, -2.5, 4.0, 2.0, m="chip_mark")
    c.part("silica", sg, loc=(30.0 * MM, -25.0 * MM, BOX_WALL * MM), desc="Silica gel: keeps the window from fogging.")
    return c


# ═══════════════════════════════ Raspberry Pi 5 + AI HAT+ ═══════════════════════════════
def pi5_ai_hat(cid="bp_pi5", title="Raspberry Pi 5 + AI HAT+ (26 TOPS)"):
    c = Component(cid, title, "Bench", summary="The farm computer in the control cabinet: counts insects on its Hailo-8 AI chip, offline.",
                  real="Raspberry Pi 5 8 GB + Raspberry Pi AI HAT+ 26 TOPS")
    W, H = 85.0, 56.0
    pcb = MB()
    pcb.prism(rrect(W * MM, H * MM, 3.0 * MM), 1.4 * MM, "pcb_rpi", z0=0.0)
    holes = [(-W / 2 + 3.5, H / 2 - 3.5), (-W / 2 + 3.5 + 58, H / 2 - 3.5), (-W / 2 + 3.5, H / 2 - 3.5 - 49), (-W / 2 + 3.5 + 58, H / 2 - 3.5 - 49)]
    for x, y in holes:
        ring_pad(pcb, x, y, 1.4, 3.0, 1.375)
    bx(pcb, "shield", -14.0, 3.0, 17.0, 17.0, 1.6, 1.4, bevel=0.3)               # BCM2712 (lid)
    txt(pcb, "RASPBERRY PI", -14.0, 4.0, 3.0, 1.4, m="chip_mark", bold=True)
    bx(pcb, "chip", 9.0, 3.0, 9.0, 13.0, 1.0, 1.4, bevel=0.2)                    # RAM
    bx(pcb, "chip", 14.0, -14.0, 7.0, 7.0, 0.9, 1.4, bevel=0.15)                 # RP1
    txt(pcb, "RP1", 14.0, -14.0, 2.3, 1.4, m="chip_mark", bold=True)
    for k, y in enumerate((-18.5, 0.5)):                                         # 2 x stacked USB-A
        bx(pcb, "shield", W / 2 - 8.0, y, 17.5, 13.2, 15.6, 1.4, bevel=0.3)
        for z, col in ((4.3, "usb_blue" if k == 0 else "plastic_black"), (11.6, "usb_blue" if k == 0 else "plastic_black")):
            bx(pcb, col, W / 2 + 0.6, y, 0.2, 10.0, 2.0, 1.4 + z - 1.0)
    bx(pcb, "shield", W / 2 - 9.0, 19.0, 21.0, 16.0, 13.5, 1.4, bevel=0.3)       # Ethernet
    bx(pcb, "hole_dark", W / 2 + 1.6, 19.0, 0.2, 11.0, 8.0, 4.0)
    bx(pcb, "plastic_black", -W / 2 + 3.5 + 29.0, H / 2 - 3.5, 50.8, 5.08, 2.5, 1.4, bevel=0.2)  # GPIO header
    for k in range(40):
        bx(pcb, "gold", -W / 2 + 3.5 + 29.0 - 24.13 + (k // 2) * 2.54, H / 2 - 3.5 + (1.27 if k % 2 else -1.27), 0.64, 0.64, 8.5, 1.4)
    for x in (-W / 2 + 3.5 + 7.7 + 3.5, -W / 2 + 3.5 + 7.7 + 3.5 + 13.5 + 3.0):  # 2 x micro-HDMI, USB-C
        bx(pcb, "shield", x, -H / 2 + 3.5, 7.5, 7.0, 3.6, 1.4, bevel=0.3)
    bx(pcb, "shield", -W / 2 + 11.2, -H / 2 + 3.6, 9.0, 7.2, 3.3, 1.4, bevel=0.6)
    bx(pcb, "fpc_beige", -W / 2 + 3.0, -4.0, 3.2, 17.0, 1.5, 1.4)                 # PCIe FFC
    rnd = random.Random(3)
    sprinkle(pcb, rnd, 40, [(-40, -22, 25, 20)], [(-23, -6, -5, 12), (4, -4, 14, 10), (10, -18, 18, -10), (-42, -13, -38, 5),
                                                (-40, -28, 0, -20), (-14, 20, 40, 28), (25, -28, 43, 28)], 1.4)
    c.part("pi5", pcb, desc="Raspberry Pi 5 (8 GB): the farm computer.")
    hat = MB()
    HW, HH, HZ = 65.0, 56.5, 1.4 + 16.0
    x0 = -W / 2 + 3.5 + 29.0                                     # HAT centred on the 58 mm hole pattern
    hat.prism(rrect(HW * MM, HH * MM, 3.0 * MM), 1.6 * MM, "pcb_rpi", z0=HZ * MM, loc=(x0 * MM, (H / 2 - 3.5 - 24.5) * MM, 0))
    for x, y in holes:
        hat.cyl(2.75 * MM, 16.0 * MM, "brass", segs=6, z0=1.4 * MM, loc=(x * MM, y * MM, 0))
        hat.cyl(2.75 * MM, 1.4 * MM, "brass", segs=6, z0=(HZ + 1.6) * MM, loc=(x * MM, y * MM, 0))
    hy = H / 2 - 3.5 - 24.5
    bx(hat, "chip", x0 - 6.0, hy - 2.0, 15.0, 15.0, 1.4, HZ + 1.6, bevel=0.3)       # Hailo-8
    txt(hat, "HAILO-8", x0 - 6.0, hy - 2.0, HZ + 3.0, 1.9, m="chip_mark", bold=True)
    txt(hat, "AI HAT+  26 TOPS", x0 + 12.0, hy + 14.0, HZ + 1.6, 2.0, m="silk", bold=True)
    bx(hat, "plastic_black", x0, H / 2 - 3.5, 50.8, 5.08, 8.5, HZ - 8.5, bevel=0.2)   # stacking header
    bx(hat, "fpc_beige", x0 - HW / 2 + 3.0, hy - 6.0, 3.2, 17.0, 1.5, HZ + 1.6)
    sprinkle(hat, rnd, 24, [(x0 - 30, hy - 25, x0 + 30, hy + 10)], [(x0 - 14.5, hy - 10.5, x0 + 2.5, hy + 6.5), (x0 - 32, hy - 16, x0 - 28, hy + 4)], HZ + 1.6)
    c.part("hat", hat, desc="AI HAT+: Hailo-8, 26 trillion operations a second, on the Pi's PCIe lane.")
    return c


# ═══════════════════════════════ card frame (trap stand) ═══════════════════════════════
CARD_W, CARD_H = 250.0, 100.0
CAM_DIST = 200.0
LENS_IN_BOX = 51.4      # lens tip above the box bottom (camera on the 38 mm plate, 3 mm standoffs)
BOX_BACK = CAM_DIST + LENS_IN_BOX


def trap_frame(cid="bp_frame", title="Sticky card frame + camera arm"):
    """Card plane = XZ at y = 0 (camera side = -y); card centre at z = 0. The box mounts on the arm end, its lid facing +y."""
    c = Component(cid, title, "Bench", summary="Holds the card flat, the camera 20 cm away: the whole card fills the picture.",
                  real="Aluminium flat bar + binder clips (DIY)")
    f = MB()
    W, H = CARD_W + 16, CARD_H + 16
    for sz in (-1, 1):
        bx(f, "alu", 0, 4.0, W, 3.0, 8.0, sz * (H / 2 - 4.0) - 4.0)
    for sx in (-1, 1):
        bx(f, "alu", sx * (W / 2 - 4.0), 4.0, 8.0, 3.0, H, -H / 2)
    for sx in (-0.33, 0.33):                                                     # clips
        bx(f, "plastic_black", sx * W, 1.0, 14.0, 6.0, 9.0, H / 2 - 12.0, bevel=0.8)
    bx(f, "alu", 0, -(BOX_BACK + 13.0) / 2, 20.0, BOX_BACK - 13.0, 4.0, -H / 2 - 4.0)   # arm under the card, out to the box
    bx(f, "alu", 0, -BOX_BACK - 2.0, 60.0, 4.0, H / 2 + 24.0, -H / 2 - 4.0)               # box mounting plate (behind the box)
    f.torus(10.0 * MM, 1.6 * MM, "stainless", segs=24, rsegs=8, axis="Y", loc=(0, 4.0 * MM, (H / 2 + 12.0) * MM))
    bx(f, "alu", 0, 4.0, 4.0, 3.0, 6.0, H / 2)
    c.part("frame", f, desc="Frame, clips, arm and the box mount.")
    return c


ALL = [pi_zero_2w, camera_module_3, tpl5110, mt3608, cell_holder, led_ring, breadboard, multimeter, ip65_box, pi5_ai_hat, trap_frame]
