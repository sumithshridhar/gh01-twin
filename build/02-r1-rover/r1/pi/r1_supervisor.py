"""R1's in-row driver: it keeps to the middle of the path and decides what to do about anything in the way.
Pure logic with no hardware imports, so the same code runs on the rover and in the laptop simulator (r1_sim.py,
tests/test_r1_pi.py). Starter code, untested on hardware. Added 13 Nov 2026 (ISSUES.md, S1 S4 E5 E6 E8).

The rule it follows: an obstacle is a pause, never a crash.
  - It stops before it touches anything that stands in the path, and waits: a person or a dog usually moves on.
  - It crosses what is low enough (a drip hose), slowly. It stops in front of what isn't (a header pipe).
  - It notices when the wheels turn but the ground doesn't move (mud), stops before it digs in, backs out once and
    tries again slowly.
  - For everything else it stops, tells a person exactly where and why, and carries on from the same metre after
    they tap Resume (or Skip). It never drives on by itself after a bumper or e-stop trip.

Sensors (one reading every 0.1 s):
  pts        2-D lidar points in the rover frame (x forward, y left, metres). The lidar is mounted LOW at the front,
             under the bed tops, so it sees the soil walls of the beds, which don't change, instead of the leaves.
  step_l/r   two small ToF sensors at the front corners aimed down at the ground ahead: the height of anything low
             (a hose, a pipe) or the depth of a hole. The lidar can't see below its own height.
  ground_v   speed over the ground from a downward optical-flow sensor. The wheels slip in mud; this doesn't.
  wheel_v    speed from the wheel pulses.
  tripped, batt_low, batt_flat   flags from the I/O board (r1_io.ino status line).
  box_c      temperature inside the electronics box.
"""
import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Cfg:
    half_w: float = 0.18          # half the rover's width (36 cm body)
    front_x: float = 0.38         # front bumper, measured from the rover centre
    track: float = 0.29           # left wheel centre to right wheel centre
    v_cruise: float = 0.30        # m/s in a clear path
    v_slow: float = 0.12          # m/s near something, or after a slip
    v_cross: float = 0.08         # m/s over a low step
    pct_per_mps: float = 133.0    # D-command % per m/s (40 % = 0.30 m/s): measure on the bench
    stop_gap: float = 0.30        # stop when something in the way is this close to the bumper
    slow_gap: float = 0.80        # slow down when something is this close
    side_margin: float = 0.02     # the corridor the rover sweeps = its width + this on each side
    persist: int = 3              # scans in a row before a thing counts (lidar noise, the scan dipping on a bump)
    clear_scans: int = 20         # 2 s clear before it drives on after a stop
    wait_s: float = 30.0          # wait this long for something to move before calling a person
    step_max: float = 0.020       # m: highest step it may cross on dry soil (80 % of the 27 mm limit, r1_calcs.py)
    step_max_wet: float = 0.011   # m: the same after any slip on this path (80 % of 15 mm)
    step_seen: float = 0.010      # m: below this the ground counts as flat
    hole_max: float = 0.06        # m: a hole or rut deeper than this = stop
    cross_len: float = 1.0        # m of slow driving after a step is seen (front wheels, then rear)
    slip_stuck: float = 0.6       # (wheel - ground) / wheel above this ...
    slip_s: float = 1.5           # ... for this long = stuck: stop before it digs in
    slip_soft: float = 0.12       # steady slip above this ...
    soft_scans: int = 8           # ... for 0.8 s = soft ground: use step_max_wet for the rest of the path
    backoff_m: float = 0.15       # one try: back out this far, then try again slowly
    backoff_s: float = 3.0        # give up backing out after this long
    box_hot_c: float = 60.0       # electronics box: stop and call a person
    end_margin: float = 0.30      # stop this far before the end of the path
    photo_every: float = 0.25     # m of ground travel between photo stations
    capture_s: float = 0.0        # seconds stopped at each station (0 = photos on the move)
    k_y: float = 3.0              # centring: turn rate (rad/s) per metre off-centre
    k_psi: float = 1.5            # turn rate per radian of heading error
    max_turn: float = 0.6         # rad/s
    min_wall_pts: int = 4
    no_wall_scans: int = 15       # 1.5 s without seeing a bed wall = call a person
    near_x: tuple = (0.30, 0.65)  # lidar points used for the near wall estimate (x range, rover frame)
    far_x: tuple = (0.65, 1.20)   # and the far one (heading)


@dataclass
class Sense:
    t: float
    pts: np.ndarray               # (N, 2) lidar points, rover frame
    step_l: float = 0.0
    step_r: float = 0.0
    ground_v: float = 0.0
    wheel_v: float = 0.0
    tripped: bool = False
    batt_low: bool = False
    batt_flat: bool = False
    box_c: float = 35.0
    resume: bool = False          # a person tapped Resume on the phone
    skip: bool = False            # a person tapped "Skip the rest of this path"


@dataclass
class Out:
    left: float
    right: float
    state: str
    events: list = field(default_factory=list)   # (kind, metre, message)


@dataclass
class Walls:
    ok: bool = False
    d_left: float = math.nan      # distance from the rover centre line to each wall, at the rover centre
    d_right: float = math.nan
    psi: float = 0.0              # heading error (+ = pointing towards the left wall)
    slope_l: float = 0.0
    slope_r: float = 0.0


def scan_to_points(angles_rad, ranges_m, lidar_x=0.30):
    """Lidar readings (angle 0 = straight ahead, + = left) to rover-frame points. Drops missing returns."""
    a = np.asarray(angles_rad, float)
    r = np.asarray(ranges_m, float)
    ok = np.isfinite(r) & (r > 0.05)
    return np.stack([lidar_x + r[ok] * np.cos(a[ok]), r[ok] * np.sin(a[ok])], 1)


def estimate_walls(pts, c: Cfg) -> Walls:
    """Both bed walls from the lidar points beside the rover. Plants and things in the path only make points
    CLOSER than the wall, so each side uses a high percentile of the lateral distance: a few leaves or a stake don't
    move the wall."""
    w = Walls()
    if pts is None or len(pts) == 0:
        return w
    x, y = pts[:, 0], pts[:, 1]
    res = {}
    for side, sign in (("l", 1.0), ("r", -1.0)):
        lat = sign * y
        on_side = (lat > 0.08) & (lat < 0.80)
        vals = []
        for lo, hi in (c.near_x, c.far_x):
            m = on_side & (x >= lo) & (x < hi)
            if m.sum() >= c.min_wall_pts:
                vals.append((float(np.mean(x[m])), float(np.percentile(lat[m], 75))))
            else:
                vals.append(None)
        res[side] = vals
    slopes, d0 = {}, {}
    for side in ("l", "r"):
        near, far = res[side]
        if near and far:
            slopes[side] = (far[1] - near[1]) / max(1e-3, far[0] - near[0])
        if near:
            d0[side] = near
    if "l" not in d0 or "r" not in d0:
        return w
    # left wall distance falls as x grows when the rover points left: slope_l = -tan(psi), slope_r = +tan(psi)
    if "l" in slopes and "r" in slopes:
        tan_psi = (slopes["r"] - slopes["l"]) / 2.0
    elif "l" in slopes:
        tan_psi = -slopes["l"]
    elif "r" in slopes:
        tan_psi = slopes["r"]
    else:
        tan_psi = 0.0
    w.psi = math.atan(tan_psi)
    w.slope_l, w.slope_r = -tan_psi, tan_psi
    xl, dl = d0["l"]
    xr, dr = d0["r"]
    w.d_left = dl - w.slope_l * xl                # extrapolate back to the rover centre (x = 0)
    w.d_right = dr - w.slope_r * xr
    w.ok = True
    return w


def gap_ahead(pts, walls: Walls, c: Cfg):
    """Distance from the bumper to the nearest thing inside the corridor the rover will sweep, not counting the
    bed walls themselves. inf = clear."""
    if pts is None or len(pts) == 0:
        return math.inf
    x, y = pts[:, 0], pts[:, 1]
    half = c.half_w + c.side_margin
    m = (x > c.front_x - 0.02) & (x < c.front_x + 1.2) & (np.abs(y) < half)
    if walls.ok:                                  # a point on (or behind) a wall line is the wall, not an obstacle
        wall_l = walls.d_left + walls.slope_l * x
        wall_r = -(walls.d_right + walls.slope_r * x)
        m &= (y < wall_l - 0.04) & (y > wall_r + 0.04)
    if not m.any():
        return math.inf
    return float(np.min(x[m]) - c.front_x)


class Supervisor:
    """One path at a time. Call step() every 0.1 s with the latest Sense; send Out.left/right to the I/O board."""

    def __init__(self, cfg: Cfg = None, path_len: float = 30.0, label: str = ""):
        self.c = cfg or Cfg()
        self.path_len = path_len
        self.label = label                      # "house 2 · bed 5", used in messages
        self.state = "FOLLOW"
        self.dist = 0.0                         # metres along the path, from the ground sensor
        self.reason = ""
        self.last_t = None
        self.block = 0
        self.near = 0
        self.clear = 0
        self.wait_since = None
        self.cross_until = -1.0
        self.step_count = 0
        self.wet = False
        self.soft = 0
        self.slip_since = None
        self.retry_until = -1.0                 # after one back-off: slow until past the bad spot
        self.backoff_from = None
        self.backoff_t = None
        self.no_wall = 0
        self.next_photo = 0.0
        self.station_until = None
        self.cmd_v = 0.0
        self.unscanned = []                     # (from_m, to_m) left out when a person chose Skip

    # ---- helpers
    def _where(self):
        return f"{self.label + ' · ' if self.label else ''}metre {self.dist:.1f}"

    def _ask(self, why, msg, ev):
        if self.state != "ASK_HUMAN" or self.reason != why:
            ev.append(("ask", round(self.dist, 2), f"{msg} ({self._where()})"))
        self.state, self.reason = "ASK_HUMAN", why
        self.cmd_v = 0.0
        return Out(0.0, 0.0, self.state, ev)

    def _stop(self, ev):
        self.cmd_v = 0.0
        return Out(0.0, 0.0, self.state, ev)

    def _drive(self, v, turn, ev):
        self.cmd_v = v
        c = self.c
        left = (v - turn * c.track / 2) * c.pct_per_mps
        right = (v + turn * c.track / 2) * c.pct_per_mps
        lim = 100.0
        return Out(max(-lim, min(lim, left)), max(-lim, min(lim, right)), self.state, ev)

    # ---- the decision, every 0.1 s
    def step(self, s: Sense) -> Out:
        c = self.c
        ev = []
        dt = 0.1 if self.last_t is None else max(1e-3, s.t - self.last_t)
        self.last_t = s.t
        self.dist += s.ground_v * dt

        if self.state == "DONE":
            return self._stop(ev)

        # 1. things only a person can sort out, whatever else is going on
        if s.tripped:
            return self._ask("tripped", "Bumper or e-stop pressed. Check the rover, press the green RESET, then Resume", ev)
        if s.batt_flat:
            return self._ask("battery", "Battery flat. Push it to the charger", ev)
        if s.box_c >= c.box_hot_c:
            return self._ask("hot", f"Electronics box at {s.box_c:.0f} °C. Stopped to cool down; move it to shade", ev)

        # 2. waiting for a person
        if self.state == "ASK_HUMAN":
            if s.skip:
                self.unscanned.append((round(self.dist, 2), self.path_len))
                self.state = "DONE"
                ev.append(("skipped", round(self.dist, 2), f"Rest of the path not scanned ({self._where()})"))
                return self._stop(ev)
            if not s.resume:
                return self._stop(ev)
            ev.append(("resumed", round(self.dist, 2), f"Resumed after: {self.reason}"))
            self.state, self.reason = "FOLLOW", ""
            self.block = self.near = self.clear = self.step_count = 0
            self.wait_since = self.slip_since = None
            self.backoff_from = None
            self.no_wall = 0

        # 3. the end of the path
        if self.dist >= self.path_len - c.end_margin:
            self.state = "DONE"
            ev.append(("done", round(self.dist, 2), f"Path finished ({self._where()})"))
            return self._stop(ev)

        walls = estimate_walls(s.pts, c)
        gap = gap_ahead(s.pts, walls, c)

        # 4. backing out of mud (one try)
        if self.state == "BACKOFF":
            backed = self.backoff_from - self.dist
            if backed >= c.backoff_m:
                self.state = "FOLLOW"
                self.retry_until = self.backoff_from + 0.5
                self.slip_since = None
                ev.append(("retry", round(self.dist, 2), "Backed out of the soft patch, trying again slowly"))
            elif s.t - self.backoff_t > c.backoff_s or (s.t - self.backoff_t > 1.5 and backed < 0.02):
                return self._ask("stuck", "Stuck in mud: the wheels turn but it doesn't move, even backwards", ev)
            else:
                return self._drive(-c.v_slow, 0.0, ev)

        # 5. stuck: the wheels turn, the ground doesn't. Any steady slip = soft ground: lower step limit from here on
        if self.cmd_v > 0.05 and s.wheel_v > 0.06:
            slip = (s.wheel_v - s.ground_v) / s.wheel_v
            self.soft = self.soft + 1 if slip > c.slip_soft else 0
            if self.soft >= c.soft_scans and not self.wet:
                self.wet = True
                ev.append(("soft", round(self.dist, 2), "Soft, slippery ground: it now crosses only very low things"))
            if slip > c.slip_stuck:
                if self.slip_since is None:
                    self.slip_since = s.t
                elif s.t - self.slip_since >= c.slip_s:
                    self.wet = True
                    if self.dist < self.retry_until:
                        return self._ask("stuck", "Stuck in mud. It backed out once and stuck again here; it needs a board or a push", ev)
                    self.state, self.backoff_from, self.backoff_t = "BACKOFF", self.dist, s.t
                    ev.append(("slip", round(self.dist, 2), "Wheels slipping: stopped before digging in, backing out"))
                    return self._drive(-c.v_slow, 0.0, ev)
            else:
                self.slip_since = None
        else:
            self.slip_since = None

        # 6. low things the lidar can't see: steps and holes
        step = max(s.step_l, s.step_r)
        hole = min(s.step_l, s.step_r)
        limit = c.step_max_wet if self.wet else c.step_max
        if step > c.step_seen or hole < -c.hole_max:
            self.step_count += 1
        else:
            self.step_count = 0
        if self.step_count >= 2:
            if step > limit:
                return self._ask("step", f"Something {step * 1000:.0f} mm high across the path: too high to cross "
                                         f"(limit {limit * 1000:.0f} mm). Lay a ramp over it or move it", ev)
            if hole < -c.hole_max:
                return self._ask("hole", f"A hole or rut {-hole * 1000:.0f} mm deep ahead. Fill it or lay a board", ev)
            if self.cross_until < self.dist:
                ev.append(("cross", round(self.dist, 2), f"Low step {step * 1000:.0f} mm: crossing slowly"))
            self.cross_until = self.dist + c.cross_len

        # 7. the bed walls (centring), and a path too narrow for the rover
        if walls.ok:
            self.no_wall = 0
            width = walls.d_left + walls.d_right
            if width < 2 * (c.half_w + 0.01):
                return self._ask("narrow", f"The path is only {width * 100:.0f} cm wide here; R1 needs "
                                           f"{2 * (c.half_w + 0.01) * 100:.0f} cm. Trim or tie back the plants", ev)
            e = (walls.d_right - walls.d_left) / 2.0      # + = rover is left of the centre line
            turn = -c.k_y * e - c.k_psi * walls.psi
            turn = max(-c.max_turn, min(c.max_turn, turn))
        else:
            self.no_wall += 1
            if self.no_wall >= c.no_wall_scans:
                return self._ask("walls", "Can't see both bed walls. Is it in a path?", ev)
            turn = 0.0

        # 8. something standing in the path
        self.block = self.block + 1 if gap < c.stop_gap else 0
        self.near = self.near + 1 if gap < c.slow_gap else 0
        if self.state == "STOP_WAIT":
            self.clear = self.clear + 1 if gap > c.stop_gap + 0.10 else 0
            if self.clear >= c.clear_scans:
                self.state = "FOLLOW"
                self.block = self.clear = 0
                ev.append(("clear", round(self.dist, 2), "Path clear again, driving on"))
            elif s.t - self.wait_since >= c.wait_s:
                return self._ask("blocked", f"Something has blocked the path for {c.wait_s:.0f} s, "
                                            f"{max(0.0, gap) * 100:.0f} cm in front of the bumper. Photo attached", ev)
            else:
                return self._stop(ev)
        elif self.block >= c.persist:
            self.state, self.wait_since, self.clear = "STOP_WAIT", s.t, 0
            ev.append(("wait", round(self.dist, 2), f"Stopped {max(0.0, gap) * 100:.0f} cm before something in the path; waiting for it to move"))
            return self._stop(ev)

        # 9. photo stations
        if self.state == "STATION":
            if s.t < self.station_until:
                return self._stop(ev)
            self.state = "FOLLOW"
        if self.dist >= self.next_photo:
            ev.append(("photo", round(self.dist, 2), ""))
            self.next_photo += c.photo_every
            if self.next_photo <= self.dist:     # never stack stations up after a jump
                self.next_photo = self.dist + c.photo_every
            if c.capture_s > 0:
                self.state, self.station_until = "STATION", s.t + c.capture_s
                return self._stop(ev)

        # 10. speed
        v = c.v_cruise
        if self.near >= 2:
            v = min(v, c.v_slow)
        if self.dist < self.retry_until:
            v = min(v, c.v_slow)
        if self.dist < self.cross_until:
            v = min(v, c.v_cross)
        if s.batt_low:
            v = min(v, c.v_slow)
        return self._drive(v, turn, ev)
