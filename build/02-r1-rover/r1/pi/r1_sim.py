"""Laptop simulator for R1 driving one soil-bed path (13 Nov 2026). A MODEL, not the farm: it is only as good as the
terrain and noise numbers in World/Noise below, which are guesses until the bench and one real path measure them.

It answers one question: with the things a real path has (a person walking through, a crate, a fallen stake, a drip
hose, a header pipe, mud, leaves growing in, a crooked soil wall), does the driving logic in r1_supervisor.py stop
before touching anything, cross only what it can, notice mud before digging in, keep its photos 25 cm apart, and
call a person only when it has to?

  python r1_sim.py                       200 random paths, the default mix (the numbers in ISSUES.md)
  python r1_sim.py --runs 50 --seed 7    a different sample
  python r1_sim.py --width-sweep         how narrow a path R1 can drive without brushing the beds
  python r1_sim.py --baseline            the same paths with centring only (no obstacle, step or mud logic)

Rover frame: x forward, y left. World frame: the path runs along +x from x = 0, its centre line is y = 0.
"""
import argparse
import math
from dataclasses import dataclass, field

import numpy as np

from r1_supervisor import Cfg, Out, Sense, Supervisor, estimate_walls

LIDAR_X, LIDAR_FOV, LIDAR_STEP, LIDAR_MAX = 0.30, math.radians(100), math.radians(1.0), 3.0
TOF_X, TOF_Y, TOF_AHEAD = 0.36, 0.12, 0.25          # the two downward ToF sensors and where they look
WHEEL_X, WHEEL_R = 0.24, 0.127                      # axle position, 10" tyre radius
BODY_L, BODY_W = 0.76, 0.36                          # footprint incl. bumpers


@dataclass
class Noise:
    lidar_sigma: float = 0.010          # m, range noise
    lidar_dropout: float = 0.02         # share of rays with no return
    ground_hit_p: float = 0.03          # chance per scan that a bump tips the scan plane into the soil ahead
    tof_sigma: float = 0.003            # m
    flow_sigma: float = 0.05            # share of the true ground speed
    yaw_sigma: float = 0.03             # rad/s of random turning from uneven soil
    yaw_bias: float = 0.02              # rad/s: one side drags more (per run, random sign)


@dataclass
class Thing:
    kind: str
    x0: float
    x1: float
    y0: float = -1.0
    y1: float = 1.0
    h: float = 1.0                      # height; < 0.10 = low (below the lidar plane)
    slip: float = 0.0                   # mud: share of wheel speed lost
    leave_t: float = math.inf           # people walk away
    gone: bool = False

    @property
    def high(self):
        return self.h >= 0.10 and self.kind != "mud"


@dataclass
class World:
    length: float = 20.0
    width: float = 0.52                 # path width at the bottom of the beds
    wall_amp: float = 0.015             # how crooked a soil bed wall is (m, each side)
    things: list = field(default_factory=list)
    phase: tuple = (0.0, 0.0, 0.0, 0.0)
    h_climb: float = 0.026              # what the wheels can really climb on dry soil (r1_calcs.py); wet: x 0.56

    def wall_y(self, x, side):
        """y of the left (+1) or right (-1) bed wall at x."""
        p = self.phase
        a = self.wall_amp * (0.6 * np.sin(2 * np.pi * x / 1.3 + p[0 if side > 0 else 2]) +
                             0.4 * np.sin(2 * np.pi * x / 0.45 + p[1 if side > 0 else 3]))
        return side * (self.width / 2 + a)


def make_world(rng, length=20.0, width=None, obstacles_per_m=0.15, intrusions_per_m=0.05, mix=None):
    w = World(length=length, width=width if width is not None else float(rng.uniform(0.46, 0.60)))
    w.phase = tuple(rng.uniform(0, 2 * np.pi, 4))
    mix = mix or {"person": 0.30, "crate": 0.12, "stake": 0.10, "hose": 0.20, "pipe": 0.05, "mud": 0.15, "deep_mud": 0.08}
    kinds, probs = list(mix), np.array(list(mix.values()), float)
    probs /= probs.sum()
    n = rng.poisson(obstacles_per_m * length)
    for _ in range(n):
        k = kinds[rng.choice(len(kinds), p=probs)]
        x0 = float(rng.uniform(2.0, length - 1.5))
        half = w.width / 2
        if k == "person":
            y = float(rng.uniform(-0.05, 0.05))
            w.things.append(Thing("person", x0, x0 + 0.25, y - 0.12, y + 0.12, 1.7, leave_t=float(rng.uniform(3, 60))))
        elif k == "crate":
            w.things.append(Thing("crate", x0, x0 + 0.30, -0.20, 0.20, 0.30))
        elif k == "stake":                 # a fallen or leaning stake sticking out from one wall
            side = rng.choice([-1, 1])
            reach = float(rng.uniform(0.08, 0.20))
            y0, y1 = (half - reach, half + 0.05) if side > 0 else (-half - 0.05, -half + reach)
            w.things.append(Thing("stake", x0, x0 + 0.03, y0, y1, 0.6))
        elif k == "hose":                  # a 16-20 mm drip lateral across the path
            w.things.append(Thing("hose", x0, x0 + 0.02, h=float(rng.uniform(0.012, 0.020))))
        elif k == "pipe":                  # a 40-63 mm header pipe across the path
            w.things.append(Thing("pipe", x0, x0 + 0.06, h=float(rng.uniform(0.040, 0.063))))
        elif k == "mud":
            w.things.append(Thing("mud", x0, x0 + float(rng.uniform(0.5, 2.0)), h=0.0, slip=float(rng.uniform(0.15, 0.40))))
        elif k == "deep_mud":
            w.things.append(Thing("mud", x0, x0 + float(rng.uniform(0.4, 1.2)), h=0.0, slip=0.95))
    for side in (-1, 1):                   # leaves / trusses reaching down into the lidar plane
        for _ in range(rng.poisson(intrusions_per_m * length)):
            x0 = float(rng.uniform(1.0, length - 1.0))
            depth = float(rng.uniform(0.01, 0.05))
            wy = float(w.wall_y(np.array([x0]), side)[0])
            y0, y1 = (wy - depth, wy + 0.05) if side > 0 else (wy - 0.05, wy + depth)
            w.things.append(Thing("leaves", x0, x0 + float(rng.uniform(0.10, 0.30)), y0, y1, 0.5))
    return w


def box_segments(t: Thing):
    a, b, c, d = (t.x0, t.y0), (t.x1, t.y0), (t.x1, t.y1), (t.x0, t.y1)
    return [(a, b), (b, c), (c, d), (d, a)]


def ray_cast(o, angles, P, Q, max_r):
    """Distance along each ray (angles in the world frame) from o to the nearest segment P[i]-Q[i]; inf = none."""
    d = np.stack([np.cos(angles), np.sin(angles)], 1)
    e = Q - P
    po = P - o
    den = d[:, None, 0] * e[None, :, 1] - d[:, None, 1] * e[None, :, 0]
    num_t = po[None, :, 0] * e[None, :, 1] - po[None, :, 1] * e[None, :, 0]
    num_u = po[None, :, 0] * d[:, None, 1] - po[None, :, 1] * d[:, None, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        t = num_t / den
        u = num_u / den
    ok = (np.abs(den) > 1e-12) & (t > 1e-6) & (u >= 0) & (u <= 1)
    r = np.where(ok, t, np.inf).min(1)
    r[r > max_r] = np.inf
    return r


@dataclass
class Result:
    finished: bool = False
    time_s: float = 0.0
    collisions: int = 0
    into_step: int = 0                  # drove a wheel into a step it could not climb
    dig_s: float = 0.0                  # seconds of wheels spinning in place
    scrape_m: float = 0.0               # metres of travel with the body touching a bed wall
    brush_m: float = 0.0                # metres with the body touching leaves that grow into the path
    asks: list = field(default_factory=list)
    false_stops: int = 0                # stopped for nothing real
    photos: list = field(default_factory=list)   # TRUE x of each photo
    unscanned_m: float = 0.0
    y_err: list = field(default_factory=list)    # how far off the path's centre line, every 0.1 s while moving


class Sim:
    def __init__(self, world: World, cfg: Cfg = None, seed=0, noise: Noise = None, controller=None, human_s=60.0,
                 v1_restart=False):
        self.w, self.c = world, cfg or Cfg()
        self.rng = np.random.default_rng(seed)
        self.n = noise or Noise()
        self.x, self.y = 0.5, float(self.rng.normal(0, 0.02))
        self.th = float(self.rng.normal(0, math.radians(2)))
        self.vl = self.vr = 0.0
        self.bias = float(self.rng.choice([-1, 1]) * self.n.yaw_bias)
        self.tripped = False
        self.v1_restart = v1_restart          # firmware v1: drives on by itself when the bumper springs back
        self._pushing = False
        self.t = 0.0
        self.sup = controller or Supervisor(self.c, path_len=world.length - 0.5)
        self.human_s = human_s
        self.fix_at = None
        self.res = Result()
        # the bed walls as short segments, built once
        xs = np.arange(-1.0, world.length + 2.0, 0.10)
        self.wall_P, self.wall_Q = [], []
        for side in (-1, 1):
            ys = world.wall_y(xs, side)
            self.wall_P.append(np.stack([xs[:-1], ys[:-1]], 1))
            self.wall_Q.append(np.stack([xs[1:], ys[1:]], 1))
        self.wall_P, self.wall_Q = np.concatenate(self.wall_P), np.concatenate(self.wall_Q)

    # ---- the world as the sensors see it
    def high_things(self):
        return [t for t in self.w.things if t.high and not t.gone and not (t.kind == "person" and self.t >= t.leave_t)]

    def lidar(self):
        o = np.array([self.x + LIDAR_X * math.cos(self.th), self.y + LIDAR_X * math.sin(self.th)])
        rel = np.arange(-LIDAR_FOV, LIDAR_FOV + 1e-9, LIDAR_STEP)
        near = (self.wall_P[:, 0] > self.x - 0.6) & (self.wall_P[:, 0] < self.x + LIDAR_MAX + 0.5)
        P, Q = list(self.wall_P[near]), list(self.wall_Q[near])
        for t in self.high_things():
            if t.x1 > self.x - 1 and t.x0 < self.x + LIDAR_MAX:
                for a, b in box_segments(t):
                    P.append(a)
                    Q.append(b)
        r = ray_cast(o, self.th + rel, np.array(P, float), np.array(Q, float), LIDAR_MAX)
        r = r + self.rng.normal(0, self.n.lidar_sigma, r.shape)
        r[self.rng.random(r.shape) < self.n.lidar_dropout] = np.inf
        if self.rng.random() < self.n.ground_hit_p:           # the rover pitched on a bump: soil ahead in the scan
            fwd = (np.abs(rel) < math.radians(20)) & (r > 0.9)
            r[fwd] = self.rng.uniform(0.9, 1.6, fwd.sum())
        ok = np.isfinite(r)
        return np.stack([LIDAR_X + r[ok] * np.cos(rel[ok]), r[ok] * np.sin(rel[ok])], 1)

    def ground_height(self, gx):
        h = 0.0
        for t in self.w.things:
            if not t.gone and t.kind in ("hose", "pipe") and t.x0 - 0.01 <= gx <= t.x1 + 0.01:
                h = max(h, t.h)
        return h

    def tof(self):
        out = []
        for sy in (1, -1):
            px = self.x + (TOF_X + TOF_AHEAD) * math.cos(self.th) - sy * TOF_Y * math.sin(self.th)
            out.append(self.ground_height(px) + float(self.rng.normal(0, self.n.tof_sigma)))
        return out

    def slip_at(self, gx):
        s = 0.0
        for t in self.w.things:
            if not t.gone and t.kind == "mud" and t.x0 <= gx <= t.x1:
                s = max(s, t.slip)
        return s

    # ---- physics, 50 Hz
    def physics(self, left_pct, right_pct, dt):
        tl, tr = left_pct / self.c.pct_per_mps, right_pct / self.c.pct_per_mps
        a = 2.0 * dt
        if self.tripped:
            tl = tr = 0.0
        self.vl += max(-a * 2, min(a, tl - self.vl)) if abs(tl) < abs(self.vl) else max(-a, min(a, tl - self.vl))
        self.vr += max(-a * 2, min(a, tr - self.vr)) if abs(tr) < abs(self.vr) else max(-a, min(a, tr - self.vr))
        wheel_v = (self.vl + self.vr) / 2
        slip = self.slip_at(self.x)
        ground_v = wheel_v * (1 - slip)
        # a wheel meets a step it can't climb: the tyre touches the edge cd before it, and the rover stops there
        lim = self.w.h_climb * (0.56 if slip > 0.1 else 1.0)
        pushing = False
        for wx in (WHEEL_X, -WHEEL_X):
            gx = self.x + wx * math.cos(self.th)
            for t in self.w.things:
                if t.gone or t.kind not in ("hose", "pipe") or t.h <= lim or ground_v <= 0:
                    continue
                cd = math.sqrt(WHEEL_R ** 2 - (WHEEL_R - min(t.h, WHEEL_R)) ** 2)
                stop_x = t.x0 - cd
                if gx <= stop_x + 1e-4 and gx + ground_v * dt > stop_x:
                    ground_v = max(0.0, (stop_x - gx) / dt)
                    pushing = True
        if pushing and not self._pushing:
            self.res.into_step += 1
        self._pushing = pushing
        moving = min(1.0, abs(ground_v) / 0.3)        # uneven soil only turns it while it rolls
        yaw = (self.vr - self.vl) / self.c.track * (1 - slip) + moving * (self.bias + float(self.rng.normal(0, self.n.yaw_sigma)))
        self.th += yaw * dt
        nx = self.x + ground_v * math.cos(self.th) * dt
        ny = self.y + ground_v * math.sin(self.th) * dt
        if self.collides(nx, ny, self.th):
            if not self.tripped:
                self.res.collisions += 1
                self.tripped = True            # the bumper presses: hardware cuts the motors
            self.vl = self.vr = 0.0
            return 0.0, wheel_v
        moved = math.hypot(nx - self.x, ny - self.y)
        self.x, self.y = nx, ny
        if abs(wheel_v) > 0.1 and abs(ground_v) < 0.03:
            self.res.dig_s += dt
        sc, br = self.touching()
        self.res.scrape_m += moved * sc
        self.res.brush_m += moved * br
        return ground_v, wheel_v

    def footprint(self, x, y, th, n=8):
        c, s = math.cos(th), math.sin(th)
        pts = []
        for i in range(n + 1):
            u = -BODY_L / 2 + BODY_L * i / n
            for v in (-BODY_W / 2, BODY_W / 2):
                pts.append((x + u * c - v * s, y + u * s + v * c))
        for v in np.linspace(-BODY_W / 2, BODY_W / 2, 5):
            pts.append((x + BODY_L / 2 * c - v * s, y + BODY_L / 2 * s + v * c))
        return np.array(pts)

    def collides(self, x, y, th):
        fp = self.footprint(x, y, th)
        for t in self.high_things():
            if t.kind == "leaves":
                continue
            if np.any((fp[:, 0] >= t.x0) & (fp[:, 0] <= t.x1) & (fp[:, 1] >= t.y0) & (fp[:, 1] <= t.y1)):
                return True
        return False

    def touching(self):
        fp = self.footprint(self.x, self.y, self.th)
        wall = np.any(fp[:, 1] > self.w.wall_y(fp[:, 0], 1)) or np.any(fp[:, 1] < self.w.wall_y(fp[:, 0], -1))
        leaves = False
        for t in self.w.things:
            if t.kind == "leaves" and not t.gone:
                if np.any((fp[:, 0] >= t.x0) & (fp[:, 0] <= t.x1) & (fp[:, 1] >= t.y0) & (fp[:, 1] <= t.y1)):
                    leaves = True
        return float(wall), float(leaves)

    # ---- a person arriving after a call
    def human_fix(self, reason):
        ahead = [t for t in self.w.things if not t.gone and t.x0 < self.x + 2.0 and t.x1 > self.x - 1.0]
        if reason in ("blocked", "step", "hole", "narrow", "tripped"):
            for t in ahead:
                if t.kind in ("crate", "stake", "pipe", "leaves", "person") or (t.kind == "hose" and reason == "step"):
                    t.gone = True
        if reason == "stuck":
            for t in ahead:
                if t.kind == "mud":
                    t.gone = True            # boards laid over it
        self.tripped = False

    def truly_blocked(self):
        """Is there really something within the stop zone + 1 m ahead of the bumper (for counting false stops)?"""
        fx = self.x + self.c.front_x
        for t in self.high_things():
            if t.x1 > fx - 0.1 and t.x0 < fx + 1.3 and t.y1 > self.y - 0.25 and t.y0 < self.y + 0.25:
                return True
        return False

    def run(self, t_max=1500.0):
        dt_ctrl, sub = 0.1, 5
        resume = False
        out = None
        ground_v = wheel_v = 0.0
        while self.t < t_max:
            if self.fix_at is not None and self.t >= self.fix_at:
                self.human_fix(self.sup.reason)
                self.fix_at, resume = None, True
            if self.v1_restart and self.tripped:     # v1: the bumper springs back once nothing presses on it
                c, s_ = math.cos(self.th), math.sin(self.th)
                if not self.collides(self.x + 0.02 * c, self.y + 0.02 * s_, self.th):
                    self.tripped = False
            tl, tr = self.tof()
            s = Sense(t=self.t, pts=self.lidar(), step_l=tl, step_r=tr,
                      ground_v=ground_v * (1 + float(self.rng.normal(0, self.n.flow_sigma))),
                      wheel_v=wheel_v + float(self.rng.normal(0, 0.005)), tripped=self.tripped, resume=resume)
            resume = False
            out = self.sup.step(s)
            for kind, m, msg in out.events:
                if kind == "photo":
                    self.res.photos.append(self.x)
                elif kind == "ask":
                    self.res.asks.append((self.sup.reason, round(self.x, 2), msg))
                    self.fix_at = self.t + self.human_s
                elif kind == "wait" and not self.truly_blocked():
                    self.res.false_stops += 1
            if out.state == "DONE":
                self.res.finished = True
                self.res.unscanned_m = sum(b - a for a, b in self.sup.unscanned)
                break
            gv_sum = wv_sum = 0.0
            for _ in range(sub):
                g, wv = self.physics(out.left, out.right, dt_ctrl / sub)
                gv_sum += g
                wv_sum += wv
            ground_v, wheel_v = gv_sum / sub, wv_sum / sub
            if ground_v > 0.05 and self.x > 1.5:
                xs = np.array([self.x])
                centre = float((self.w.wall_y(xs, 1)[0] + self.w.wall_y(xs, -1)[0]) / 2)
                self.res.y_err.append(self.y - centre)
            self.t += dt_ctrl
        self.res.time_s = round(self.t, 1)
        return self.res


class CentringOnly(Supervisor):
    """The baseline: the same wall-following, but no obstacle, step or mud logic, photos by wheel turns, and it
    drives on as soon as a bumper springs back (firmware v1). What 'it drives the row by itself' meant before."""

    def __init__(self, cfg=None, path_len=30.0):
        super().__init__(cfg, path_len)
        self.wheel_dist = 0.0

    def step(self, s):
        c, ev = self.c, []
        dt = 0.1 if self.last_t is None else s.t - self.last_t
        self.last_t = s.t
        self.dist += s.ground_v * dt
        self.wheel_dist += s.wheel_v * dt
        if self.wheel_dist >= self.path_len - c.end_margin:
            self.state = "DONE"
            return Out(0.0, 0.0, self.state, ev)
        if s.tripped:                                # v1: wait while pressed, no call to anyone
            self.state = "TRIPPED"
            return self._stop(ev)
        self.state = "FOLLOW"
        walls = estimate_walls(s.pts, c)
        turn = 0.0
        if walls.ok:
            e = (walls.d_right - walls.d_left) / 2.0
            turn = max(-c.max_turn, min(c.max_turn, -c.k_y * e - c.k_psi * walls.psi))
        if self.wheel_dist >= self.next_photo:
            ev.append(("photo", round(self.wheel_dist, 2), ""))
            self.next_photo += c.photo_every
        return self._drive(c.v_cruise, turn, ev)


def photo_stats(xs, every=0.25):
    if len(xs) < 2:
        return {"n": len(xs), "max_gap": math.nan, "dupes": 0, "holes": 0}
    g = np.diff(np.array(xs))
    return {"n": len(xs), "max_gap": float(g.max()), "dupes": int((g < 0.6 * every).sum()), "holes": int((g > 1.4 * every).sum())}


def batch(runs=200, seed=1, width=None, baseline=False, length=20.0, intrusions_per_m=0.05, verbose=False, t_max=1500.0):
    rng = np.random.default_rng(seed)
    tot = {"runs": runs, "metres": 0.0, "finished": 0, "collisions": 0, "into_step": 0, "dig_s": 0.0, "scrape_m": 0.0,
           "brush_m": 0.0, "asks": 0, "false_stops": 0, "photo_dupes": 0, "photo_holes": 0, "photos": 0,
           "max_photo_gap": 0.0, "ask_reasons": {}, "time_s": 0.0, "things": {}}
    for i in range(runs):
        w = make_world(rng, length=length, width=width, intrusions_per_m=intrusions_per_m)
        for t in w.things:
            tot["things"][t.kind] = tot["things"].get(t.kind, 0) + 1
        cfg = Cfg()
        ctrl = CentringOnly(cfg, path_len=w.length - 0.5) if baseline else None
        r = Sim(w, cfg, seed=int(rng.integers(1 << 30)), controller=ctrl, v1_restart=baseline).run(t_max=t_max)
        tot["metres"] += w.length - 1.0
        tot["finished"] += r.finished
        tot["collisions"] += r.collisions
        tot["into_step"] += r.into_step
        tot["dig_s"] += r.dig_s
        tot["scrape_m"] += r.scrape_m
        tot["brush_m"] += r.brush_m
        tot["asks"] += len(r.asks)
        tot["false_stops"] += r.false_stops
        tot["time_s"] += r.time_s
        for why, _, _ in r.asks:
            tot["ask_reasons"][why] = tot["ask_reasons"].get(why, 0) + 1
        ps = photo_stats(r.photos)
        tot["photos"] += ps["n"]
        tot["photo_dupes"] += ps["dupes"]
        tot["photo_holes"] += ps["holes"]
        if not math.isnan(ps["max_gap"]):
            tot["max_photo_gap"] = max(tot["max_photo_gap"], ps["max_gap"])
        if verbose:
            print(i, r.finished, r.collisions, r.into_step, round(r.dig_s, 1), [a[0] for a in r.asks])
    return tot


def show(tot, title):
    per100 = 100.0 / max(1.0, tot["metres"])
    print(f"\n{title}: {tot['runs']} paths, {tot['metres']:.0f} m, things in the paths: {tot['things']}")
    print(f"  finished                      {tot['finished']} of {tot['runs']}")
    print(f"  hit something standing        {tot['collisions']}")
    print(f"  drove into a step too high    {tot['into_step']}")
    print(f"  wheels spinning in place      {tot['dig_s']:.0f} s in total")
    print(f"  touching a bed wall           {tot['scrape_m']:.1f} m of {tot['metres']:.0f} m")
    print(f"  brushing leaves in the path   {tot['brush_m']:.1f} m")
    print(f"  calls to a person             {tot['asks']} ({tot['asks'] * per100:.1f} per 100 m) {tot['ask_reasons']}")
    print(f"  stops for nothing real        {tot['false_stops']}")
    print(f"  photos: {tot['photos']}, spaced < 15 cm {tot['photo_dupes']}, > 35 cm {tot['photo_holes']}, "
          f"largest gap {tot['max_photo_gap'] * 100:.0f} cm")
    print(f"  time per 100 m                {tot['time_s'] * per100 / 60:.0f} min (incl. waiting for people)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--width-sweep", action="store_true")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    if a.width_sweep:
        print("Path width vs touching the beds (no obstacles, leaves growing in at 0.05 per m per side)")
        for wd in (0.40, 0.42, 0.44, 0.46, 0.48, 0.50, 0.55):
            rng = np.random.default_rng(a.seed)
            scr = brush = asks = metres = 0.0
            for i in range(a.runs):
                w = make_world(rng, width=wd, obstacles_per_m=0.0)
                r = Sim(w, seed=int(rng.integers(1 << 30))).run()
                scr += r.scrape_m
                brush += r.brush_m
                asks += len(r.asks)
                metres += w.length - 1.0
            print(f"  {wd * 100:.0f} cm: wall touched on {100 * scr / metres:5.2f} % of the distance, "
                  f"leaves brushed {100 * brush / metres:4.1f} %, calls {100 * asks / metres:.1f} per 100 m")
    else:                                    # the baseline gets stuck for good, so it gets 10 minutes per path, not 25
        show(batch(a.runs, a.seed, baseline=a.baseline, verbose=a.v, t_max=600.0 if a.baseline else 1500.0),
             "CENTRING ONLY (no obstacle / step / mud logic)" if a.baseline else "R1 supervisor")
