"""R1's day plan: which houses, in what order, when, and from where it may start. Pure logic, laptop-tested
(tests/test_r1_pi.py). Starter code, untested on hardware. Added 13 Nov 2026 (ISSUES.md S2 S7 S8 S9 R1).

Moving between greenhouses is NOT autonomous. A worker drives R1 from the phone (r1_drive.py) through the door and the
wheel bath. The rover drives itself only inside a path, and only from a start it has checked: the tag at the bed end
(read by the front camera) and the path width (measured by the lidar) must match what config.yaml says for that bed.

The rules:
  1. Order: the healthiest house first, the riskiest last. Never back into a cleaner house the same day after a
     sicker one: the rover can carry spores, bacteria and viruses on its tyres and body.
  2. Every door: the worker confirms the wheel bath and the mist arch on the phone. No confirmation, no start.
  3. When: only when the leaves are dry (gap between air temperature and dew point >= 2 C, the same sum as the
     heat-and-dew alarm), the electronics box is cool enough to finish, and the battery holds the plan plus a reserve.
  4. Crops it can't do: crops that trail on the ground (field watermelon) have vines across the paths, so it refuses
     them; melons grown up strings are fine. Paths narrower than R1 needs go to the hand-pushed camera trolley.
  5. A stop is a pause: progress is saved per bed and metre. The next run starts where the last one stopped, and every
     metre that was not scanned is listed for a person to check by hand.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

RISK = {"green": 0, "amber": 1, "red": 2}

# Per crop: how the plant grows, and what R1 needs for it. `min_path_m` comes from r1_calcs.py (fit) and r1_sim.py
# (--width-sweep); `cameras` are the names in config.yaml; `capture_s` is the stop at each photo station.
CROPS = {
    "tomato":        {"habit": "upright",  "mast_m": 1.95, "cameras": ["L1", "R1", "L2", "R2", "L3", "R3"], "capture_s": 3.6},
    "capsicum":      {"habit": "upright",  "mast_m": 1.40, "cameras": ["L1", "R1", "L2", "R2"], "capture_s": 2.4},
    "cucumber":      {"habit": "upright",  "mast_m": 1.95, "cameras": ["L1", "R1", "L2", "R2", "L3", "R3"], "capture_s": 3.6},
    "melon_trellis": {"habit": "upright",  "mast_m": 1.95, "cameras": ["L1", "R1", "L2", "R2", "L3", "R3"], "capture_s": 3.6},
    "strawberry":    {"habit": "low_bed",  "mast_m": 0.91, "cameras": ["L1", "R1"], "capture_s": 1.2,
                      "heights": {"L1": 0.85, "R1": 0.85}},   # v1: 0.62 m was below the canopy top (r1_calcs.py)
    "watermelon_ground": {"habit": "trailing"},
}


def dew_point_c(t_c, rh):
    """Magnus formula, the same constants as the heat-and-dew alarm (build/04-heat-dew-alarm/alarm_logic.h)."""
    g = math.log(rh / 100.0) + 17.62 * t_c / (243.12 + t_c)
    return 243.12 * g / (17.62 - g)


@dataclass
class House:
    id: int
    crop: str
    beds: int
    bed_len_m: float
    path_w_m: float
    risk: str = "green"            # from the heat-and-dew alarm, or a confirmed sick plant


@dataclass
class Gate:
    ok: bool
    why: list = field(default_factory=list)


def plan_day(houses, min_path_m=0.48, crops=CROPS):
    """Houses R1 may patrol today, healthiest first, plus the ones it refuses and why."""
    go, refused = [], []
    for h in houses:
        prof = crops.get(h.crop)
        if prof is None:
            refused.append((h.id, f"no crop profile for '{h.crop}' in config"))
        elif prof["habit"] == "trailing":
            refused.append((h.id, f"{h.crop} trails on the ground: vines cross the paths. Grow it up strings, or scout by hand"))
        elif h.path_w_m < min_path_m:
            refused.append((h.id, f"paths {h.path_w_m * 100:.0f} cm < {min_path_m * 100:.0f} cm: use the camera trolley here"))
        else:
            go.append(h)
    go.sort(key=lambda h: (RISK[h.risk], h.id))
    return go, refused


def may_enter(house, sickest_today):
    """sickest_today: the highest risk of any house the rover has been in today (None = none yet)."""
    if sickest_today is not None and RISK[sickest_today] > RISK[house.risk]:
        return Gate(False, [f"it was in a {sickest_today} house today; house {house.id} is {house.risk}. Tomorrow, first"])
    return Gate(True)


def door_ok(house_id, bath_confirmed_at, now_s, max_age_s=600):
    """bath_confirmed_at: {house_id: time the worker tapped 'wheel bath + mist arch done' at that door}."""
    t = bath_confirmed_at.get(house_id)
    if t is None:
        return Gate(False, ["nobody confirmed the wheel bath at this door"])
    if now_s - t > max_age_s:
        return Gate(False, [f"wheel bath confirmed {int((now_s - t) / 60)} min ago; do it again"])
    return Gate(True)


def start_ok(house, bed, tag_read, width_measured, tol_m=0.05):
    """The worker parked it at a bed end. It starts only if the tag says this house + bed and the lidar's path width
    matches the config."""
    why = []
    want = f"H{house.id}-B{bed}"
    if tag_read != want:
        why.append(f"tag reads {tag_read!r}, expected {want!r}: wrong path or no tag")
    if width_measured is None or abs(width_measured - house.path_w_m) > tol_m:
        why.append(f"path measures {width_measured} m, config says {house.path_w_m} m")
    return Gate(not why, why)


def photo_every_for(risk):
    """Look harder where the climate says disease is likely: in an amber or red house the stations are 12.5 cm apart,
    so every leaf is photographed from two positions (a second angle around the leaf in front; r1_calcs.py)."""
    return 0.25 if risk == "green" else 0.125


def bed_wh(house, crops=CROPS, v=0.30, w_moving=114.0, w_stopped=54.0):
    """Energy for one path, from the power budget in r1_calcs.py (R1 full: watts while driving / stopped for photos)."""
    prof = crops[house.crop]
    drive_s = house.bed_len_m / v
    stop_s = house.bed_len_m / photo_every_for(house.risk) * prof["capture_s"]
    return (drive_s * w_moving + stop_s * w_stopped) / 3600.0


def patrol_gate(air_c, rh, box_c, battery_wh_left, plan_wh, reserve=0.25, min_dew_gap=2.0, box_start_max=50.0):
    """May it start now? Leaves dry, box cool enough to finish, and energy for the plan + a reserve to get home."""
    why = []
    gap = air_c - dew_point_c(air_c, rh)
    if gap < min_dew_gap:
        why.append(f"leaves may be wet (dew-point gap {gap:.1f} C < {min_dew_gap} C): driving through wet plants spreads "
                   f"disease, and the camera glass fogs")
    if box_c > box_start_max:
        why.append(f"electronics box already {box_c:.0f} C (start limit {box_start_max:.0f} C): go early morning or late afternoon")
    need = plan_wh * (1 + reserve)
    if battery_wh_left < need:
        why.append(f"battery {battery_wh_left:.0f} Wh < plan {plan_wh:.0f} Wh + {reserve:.0%} reserve: charge first, or plan fewer paths")
    return Gate(not why, why)


class Progress:
    """Where each bed got to, saved to a JSON file so a stop is only a pause."""

    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.done = {}                 # "house-bed" -> metres scanned from the start
        self.gaps = []                 # [house, bed, from_m, to_m, why]
        if self.path and self.path.exists():
            d = json.loads(self.path.read_text())
            self.done, self.gaps = d.get("done", {}), d.get("gaps", [])

    def save(self):
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"done": self.done, "gaps": self.gaps}, indent=1))

    def scanned_to(self, house, bed):
        return self.done.get(f"{house}-{bed}", 0.0)

    def record(self, house, bed, to_m):
        k = f"{house}-{bed}"
        self.done[k] = max(self.done.get(k, 0.0), round(to_m, 2))
        self.save()

    def skip(self, house, bed, from_m, to_m, why):
        self.gaps.append([house, bed, round(from_m, 2), round(to_m, 2), why])
        self.save()

    def next_bed(self, house):
        """First bed of this house that isn't finished, and the metre to start from."""
        for b in range(1, house.beds + 1):
            got = self.scanned_to(house.id, b)
            skipped = any(g[0] == house.id and g[1] == b for g in self.gaps)
            if got < house.bed_len_m - 0.5 and not skipped:
                return b, got
        return None, None

    def check_by_hand(self):
        """The list a person walks with: every stretch the rover could not scan."""
        return [f"house {h} bed {b}: metre {a:.1f} to {z:.1f} ({why})" for h, b, a, z, why in self.gaps]
