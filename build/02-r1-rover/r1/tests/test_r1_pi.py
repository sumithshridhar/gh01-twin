"""Laptop tests for R1's Pi code (13 Nov 2026). No rover needed: the driving logic runs in the simulator (r1_sim.py),
the cameras, serial port and phone are fakes, and every rule is tried on purpose.

  pip install pytest numpy pyyaml flask opencv-python
  python -m pytest r1/tests -v          (from build/02-r1-rover)

Each test name says what it proves. ISSUES.md lists which issue each one closes.
"""
import datetime as dt
import sqlite3
import sys
import types
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pi"))

from r1_supervisor import Cfg, Sense, Supervisor  # noqa: E402
from r1_sim import CentringOnly, Noise, Sim, Thing, World, photo_stats  # noqa: E402
import r1_mission as M  # noqa: E402
from r1_triage import Flag, Triage, house_risk  # noqa: E402
from r1_spray import board_locks, spray_locks  # noqa: E402
from r1_link import Link, parse_status  # noqa: E402
from r1_capture import Capturer  # noqa: E402
from r1_auto import run_path  # noqa: E402


# ---------------------------------------------------------------- driving one path (r1_supervisor in r1_sim)
def path(width=0.52, things=(), length=12.0):
    w = World(length=length, width=width)
    w.phase = (0.3, 1.1, 2.0, 0.7)
    w.things = list(things)
    return w


def drive(w, seed=0, t_max=900, **kw):
    return Sim(w, seed=seed, **kw).run(t_max=t_max)


def reasons(r):
    return [a[0] for a in r.asks]


def test_clear_path_photos_every_25cm_no_wall_touch():
    r = drive(path())
    ps = photo_stats(r.photos)
    assert r.finished and not r.asks and r.collisions == 0 and r.scrape_m == 0
    assert ps["n"] >= 40 and ps["dupes"] == 0 and ps["holes"] == 0


def test_crate_it_stops_before_touching_waits_then_calls_a_person():
    r = drive(path(things=[Thing("crate", 6.0, 6.3, -0.2, 0.2, 0.3)]))
    assert r.collisions == 0
    assert reasons(r) == ["blocked"]
    _, x_at_ask, msg = r.asks[0]
    assert 6.0 - (x_at_ask + 0.38) >= 0.10, "stopped at least 10 cm before the crate"
    assert "metre" in msg and "Photo" in msg
    assert r.finished, "after the person moved it and tapped Resume, it finished the path"


def test_person_who_walks_away_no_call_needed():
    r = drive(path(things=[Thing("person", 6.0, 6.25, -0.12, 0.12, 1.7, leave_t=25.0)]))
    assert r.collisions == 0 and r.asks == [] and r.finished


def test_drip_hose_is_crossed_slowly_without_a_call():
    r = drive(path(things=[Thing("hose", 5.0, 5.02, h=0.016)]))
    assert r.finished and r.asks == [] and r.into_step == 0


def test_header_pipe_too_high_it_stops_in_front_and_asks_for_a_ramp():
    r = drive(path(things=[Thing("pipe", 5.0, 5.06, h=0.050)]))
    assert reasons(r) == ["step"] and r.into_step == 0
    assert "ramp" in r.asks[0][2]
    assert r.finished


def test_deep_mud_noticed_before_it_digs_in():
    r = drive(path(things=[Thing("mud", 5.0, 6.0, h=0.0, slip=0.95)]))
    assert reasons(r) == ["stuck"]
    assert r.dig_s < 5.0, f"wheels spun in place for {r.dig_s:.1f} s"
    assert r.finished


def test_mild_mud_photos_stay_25cm_apart_because_metres_come_from_the_ground_sensor():
    w = path(things=[Thing("mud", 3.0, 9.0, h=0.0, slip=0.5)])
    r = drive(w)
    assert r.asks == [] and photo_stats(r.photos)["dupes"] == 0
    before = Sim(path(things=[Thing("mud", 3.0, 9.0, h=0.0, slip=0.5)]), seed=0,
                 controller=CentringOnly(Cfg(), path_len=11.5)).run(t_max=900)
    assert photo_stats(before.photos)["dupes"] > 5, "wheel-turn photos bunch up in mud (the v1 way)"


def test_leaves_growing_into_the_path_are_not_brushed():
    r = drive(path(width=0.46, things=[Thing("leaves", 5.0, 5.3, 0.18, 0.30, 0.5)]))
    assert r.brush_m == 0.0 and r.collisions == 0
    assert reasons(r) == ["blocked"] and r.finished


def test_path_narrower_than_the_rover_it_refuses_instead_of_scraping():
    r = drive(path(width=0.37), t_max=120)
    assert reasons(r)[:1] == ["narrow"] and r.scrape_m < 0.05


def test_lidar_dipping_into_the_soil_on_bumps_causes_no_false_stops():
    r = Sim(path(), seed=3, noise=Noise(ground_hit_p=0.3)).run(t_max=600)
    assert r.finished and r.false_stops == 0 and r.asks == []


def test_it_stands_still_at_every_photo_station():
    cfg = Cfg(capture_s=1.2)
    sim = Sim(path(length=6.0), cfg=cfg, seed=1)
    seen = []
    step = sim.sup.step

    def spy(s):
        out = step(s)
        seen.append((out.state, out.left, out.right))
        return out
    sim.sup.step = spy
    r = sim.run(t_max=600)
    assert r.finished
    stations = [x for x in seen if x[0] == "STATION"]
    assert len(stations) > 100 and all(lft == 0 and rgt == 0 for _, lft, rgt in stations)


def test_bumper_trip_it_waits_for_a_person_and_never_drives_on_by_itself():
    sup = Supervisor(Cfg(), path_len=10)
    pts = np.array([[0.5, 0.26], [0.9, 0.26], [0.5, -0.26], [0.9, -0.26]] * 3)
    out = sup.step(Sense(t=0.0, pts=pts, tripped=True))
    assert out.state == "ASK_HUMAN" and (out.left, out.right) == (0, 0) and out.events[0][0] == "ask"
    out = sup.step(Sense(t=0.1, pts=pts, tripped=True, resume=True))
    assert (out.left, out.right) == (0, 0), "Resume is ignored while the bumper/e-stop chain is still tripped"
    out = sup.step(Sense(t=0.2, pts=pts, tripped=False))
    assert out.state == "ASK_HUMAN" and (out.left, out.right) == (0, 0), "released, but no Resume yet: still waiting"
    out = sup.step(Sense(t=0.3, pts=pts, tripped=False, resume=True))
    assert out.state != "ASK_HUMAN"


def test_before_centring_only_drives_into_a_crate_and_never_finishes():
    """The v1 idea ('it drives the row by itself') without obstacle logic: kept as a test so the comparison stays true."""
    w = path(things=[Thing("crate", 6.0, 6.3, -0.2, 0.2, 0.3)])
    r = Sim(w, seed=0, controller=CentringOnly(Cfg(), path_len=11.5), v1_restart=True).run(t_max=300)
    assert r.collisions >= 1 and not r.finished


# ---------------------------------------------------------------- the day plan (r1_mission)
H = M.House


def test_order_healthiest_first_and_refusals_with_reasons():
    houses = [H(1, "tomato", 10, 30, 0.55, "red"), H(2, "tomato", 10, 30, 0.55, "green"),
              H(3, "capsicum", 8, 30, 0.52, "amber"), H(4, "watermelon_ground", 5, 30, 0.6),
              H(5, "strawberry", 15, 30, 0.45)]
    go, refused = M.plan_day(houses)
    assert [h.id for h in go] == [2, 3, 1]
    why = dict(refused)
    assert "vines" in why[4] and "trolley" in why[5]


def test_never_back_into_a_cleaner_house_the_same_day():
    assert not M.may_enter(H(2, "tomato", 1, 30, 0.55, "green"), "red").ok
    assert not M.may_enter(H(2, "tomato", 1, 30, 0.55, "amber"), "red").ok
    assert M.may_enter(H(1, "tomato", 1, 30, 0.55, "red"), "red").ok
    assert M.may_enter(H(1, "tomato", 1, 30, 0.55, "green"), None).ok


def test_wheel_bath_must_be_confirmed_at_the_door_within_10_minutes():
    assert not M.door_ok(2, {}, 1000).ok
    assert not M.door_ok(2, {2: 0}, 1000).ok
    assert M.door_ok(2, {2: 700}, 1000).ok


def test_it_starts_only_from_a_checked_start():
    h = H(1, "tomato", 10, 30, 0.55)
    assert M.start_ok(h, 3, "H1-B3", 0.56).ok
    assert not M.start_ok(h, 3, "H1-B4", 0.56).ok
    assert not M.start_ok(h, 3, "H1-B3", 0.70).ok
    assert not M.start_ok(h, 3, None, None).ok


def test_dew_point_matches_the_alarm_formula():
    assert abs(M.dew_point_c(25.0, 60.0) - 16.69) < 0.05
    assert abs(M.dew_point_c(20.0, 100.0) - 20.0) < 0.01


def test_patrol_gate_wet_leaves_hot_box_short_battery():
    plan = M.bed_wh(H(1, "tomato", 10, 30, 0.55)) * 10
    assert M.patrol_gate(26.0, 70.0, 38.0, 700.0, plan).ok
    wet = M.patrol_gate(22.0, 95.0, 30.0, 700.0, plan)
    assert not wet.ok and "wet" in wet.why[0]
    assert not M.patrol_gate(26.0, 60.0, 55.0, 700.0, plan).ok
    assert not M.patrol_gate(26.0, 60.0, 38.0, plan, plan).ok, "needs a 25 % reserve on top of the plan"


def test_a_stop_is_a_pause_progress_survives_a_restart(tmp_path):
    f = tmp_path / "progress.json"
    p = M.Progress(f)
    h = H(1, "tomato", 3, 30, 0.55)
    p.record(1, 1, 30.0)
    p.record(1, 2, 12.4)
    p2 = M.Progress(f)                                    # the Pi rebooted
    assert p2.next_bed(h) == (2, 12.4)
    p2.skip(1, 2, 12.4, 30.0, "crate left in the path")
    assert M.Progress(f).next_bed(h) == (3, 0.0)
    assert "metre 12.4 to 30.0" in M.Progress(f).check_by_hand()[0]


# ---------------------------------------------------------------- photos that look wrong (r1_triage)
def test_morning_summary_is_rationed_and_rings_only_when_everything_agrees():
    tr = Triage()
    flags = [Flag(1, b, m, "L", 0.6, 0.62 + 0.01 * (m % 30), new=True) for b in range(1, 3) for m in range(20)]
    flags.append(Flag(2, 1, 5.0, "R", 0.6, 0.97, new=True))   # strong, new, in a house that had wet leaves
    flags.append(Flag(1, 9, 1.0, "R", 0.6, 0.97, new=True))   # strong, new, but a dry (green) house
    out = tr.decide(flags, {1: "green", 2: "red"}, unseen=["house 1 bed 4 m 3-5 camera L2 failed"])
    assert [f.house for f in out["ring"]] == [2]
    assert len(out["summary"]) == 10 and out["logged"] == len(flags) - 11
    assert out["check_by_hand"] == ["house 1 bed 4 m 3-5 camera L2 failed"]


def test_when_the_farmer_says_not_disease_too_often_it_sends_fewer_alerts():
    tr = Triage()
    flags = [Flag(1, 1, m, "L", 0.6, 0.6 + 0.012 * m) for m in range(30)]
    before = len(tr.decide(flags, {1: "amber"})["summary"]) + tr.decide(flags, {1: "amber"})["logged"]
    n_before = sum(f.score >= tr.threshold for f in flags)
    for real in [True, False, False, True, False, False, True, False, False, False]:
        tr.tap(real)
    assert tr.threshold > 0.60
    assert sum(f.score >= tr.threshold for f in flags) < n_before
    assert before == 30


def test_house_risk_from_wet_leaf_hours():
    assert house_risk(0) == "green" and house_risk(3) == "amber" and house_risk(7) == "red"
    assert house_risk(7, warm=False) == "amber"


# ---------------------------------------------------------------- the spray locks (r1_spray)
CFG = {"houses": [{"id": 1, "crop": "tomato", "next_picking": "2026-11-20"},
                  {"id": 2, "crop": "strawberry", "next_picking": "2026-11-15"}],
       "products": [{"name": "Water (test)", "crops": ["tomato", "strawberry"], "wait_days": 0},
                    {"name": "Product T", "crops": ["tomato"], "wait_days": 5}],
       "valves": ["L1", "R1", "L2", "R2", "L3", "R3"]}
TODAY = dt.date(2026, 11, 13)


def test_spray_all_locks_pass_with_water():
    assert spray_locks(CFG, 1, "R2", "Water (test)", "Ravi", TODAY, "0") == []


@pytest.mark.parametrize("args,expect", [
    ((1, "R2", "Water (test)", "", TODAY, "0"), "no approval"),
    ((2, "R2", "Product T", "Ravi", TODAY, "0"), "not approved for strawberry"),
    ((1, "R2", "Product T", "Ravi", dt.date(2026, 11, 17), "0"), "waiting period"),
    ((1, "R2", "Water (test)", "Ravi", TODAY, "1"), "someone may be inside"),
    ((1, "R2", "Water (test)", "Ravi", TODAY, None), "someone may be inside"),
    ((1, "R9", "Water (test)", "Ravi", TODAY, "0"), "unknown valve"),
    ((1, "R2", "Mystery", "Ravi", TODAY, "0"), "not in config"),
])
def test_spray_each_lock_refuses(args, expect):
    assert any(expect in r for r in spray_locks(CFG, *args))


def test_spray_board_locks():
    assert board_locks(True, False, True, False) == []
    assert len(board_locks(False, True, False, True)) == 4


# ---------------------------------------------------------------- the serial link (r1_link)
def test_status_line_v2_and_v1():
    s = parse_status("S 10 11 12 13 1 1 0 256 22")
    assert s["battery_v"] == 25.6 and s["latch"] and s["need_neutral"] and not s["tripped"] and s["batt_low"]
    assert parse_status("S 1 2 3 4 1 0 1")["battery_v"] is None
    assert parse_status("S 1 2 3") is None and parse_status("S a b c d e f g h i") is None and parse_status("") is None


class FakeSerial:
    def __init__(self, lines=()):
        self.out = []
        self.inbox = b"".join((x + "\n").encode() for x in lines)

    def write(self, b):
        self.out.append(b.decode().strip())

    def read(self, n):
        import time as _t
        _t.sleep(0.005)
        chunk, self.inbox = self.inbox[:n], self.inbox[n:]
        return chunk


def test_link_sends_a_stop_at_once_and_reads_flags():
    import time as _t
    ser = FakeSerial(["S 0 0 0 0 1 1 0 251 3"])
    link = Link({"wheel": {"diameter_m": 0.254, "pulses_per_rev": 90}}, ser=ser)
    _t.sleep(0.05)
    assert link.tripped and link.latch and link.battery_v == 25.1
    link.set_drive(40, 40)
    n = len(ser.out)
    link.set_drive(0, 0)
    assert "D 0 0" in ser.out[n:], "the stop went out immediately, not at the next 100 ms resend"
    link.resume()
    i = max(k for k, x in enumerate(ser.out) if x == "E 1")
    assert "D 0 0" in ser.out[i + 1:], "after E 1 comes the neutral the board waits for"
    link.close()


# ---------------------------------------------------------------- the cameras (r1_capture), with a fake OpenCV
class FakeCap:
    open_now = max_open = 0
    fail = set()
    props = {}

    def __init__(self, dev, api):
        self.dev, self.ok = dev, dev not in FakeCap.fail
        if self.ok:
            FakeCap.open_now += 1
            FakeCap.max_open = max(FakeCap.max_open, FakeCap.open_now)

    def isOpened(self):
        return self.ok

    def set(self, k, v):
        FakeCap.props[(self.dev, k)] = v
        return True

    def grab(self):
        return True

    def read(self):
        return True, np.zeros((4, 6, 3), np.uint8)       # landscape: 6 wide, 4 tall

    def release(self):
        if self.ok:
            FakeCap.open_now -= 1
            self.ok = False


def fake_cv2(saved):
    def imwrite(p, img, params):
        saved.append((p, img.shape))
        Path(p).write_bytes(b"jpg")
        return True
    return types.SimpleNamespace(
        CAP_V4L2=200, CAP_PROP_FOURCC=6, CAP_PROP_FRAME_WIDTH=3, CAP_PROP_FRAME_HEIGHT=4, CAP_PROP_AUTO_EXPOSURE=21,
        CAP_PROP_EXPOSURE=15, CAP_PROP_AUTO_WB=44, CAP_PROP_WB_TEMPERATURE=45, ROTATE_90_CLOCKWISE=0,
        IMWRITE_JPEG_QUALITY=1, VideoWriter_fourcc=lambda *a: 0, VideoCapture=FakeCap,
        rotate=lambda img, code: np.ascontiguousarray(np.transpose(img, (1, 0, 2))), imwrite=imwrite)


CAMS = {"cameras": [{"name": n, "device": i * 2, "side": "left" if n[0] == "L" else "right", "height": h}
                    for i, (n, h) in enumerate([("L1", .62), ("R1", .62), ("L2", 1.22), ("R2", 1.22), ("L3", 1.82), ("R3", 1.82)])]}


def test_cameras_take_turns_portrait_fixed_exposure(tmp_path):
    FakeCap.open_now = FakeCap.max_open = 0
    FakeCap.fail, FakeCap.props = set(), {}
    saved = []
    cap = Capturer(CAMS, 1, 3, M.CROPS["tomato"]["cameras"], root=tmp_path, cv2=fake_cv2(saved), today=dt.date(2026, 11, 13))
    for m in (0.0, 0.25, 0.5):
        assert cap.shoot(m) == 6
    cap.close()
    assert FakeCap.max_open == 1, "never more than one camera streaming"
    assert all(shape == (6, 4, 3) for _, shape in saved), "saved in portrait"
    assert FakeCap.props[(0, 21)] == 1, "manual exposure"
    rows = sqlite3.connect(tmp_path / "photos.db").execute("SELECT COUNT(*), MIN(metre), MAX(metre) FROM photo").fetchone()
    assert rows == (18, 0.0, 0.5)


def test_strawberry_uses_its_two_cameras_and_a_dead_camera_is_listed_not_skipped(tmp_path):
    FakeCap.open_now = FakeCap.max_open = 0
    FakeCap.fail = {2}                                     # R1 unplugged
    saved = []
    prof = M.CROPS["strawberry"]
    cap = Capturer(CAMS, 2, 1, prof["cameras"], root=tmp_path, cv2=fake_cv2(saved), heights=prof["heights"])
    assert cap.shoot(1.25) == 1
    assert cap.unseen == [(1.25, "R1", "camera did not open")]
    db = sqlite3.connect(tmp_path / "photos.db")
    assert db.execute("SELECT cam FROM unseen").fetchall() == [("R1",)]
    assert db.execute("SELECT cam, height FROM photo").fetchall() == [("L1", 0.85)], "stamped at the strawberry height"
    cap.close()


# ---------------------------------------------------------------- the phone page (r1_drive)
class FakeLink:
    def __init__(self):
        self.tripped = self.latch = self.batt_flat = self.batt_low = False
        self.estop_ok, self.tank_ok, self.battery_v = True, True, 25.6
        self.drives, self.resumed = [], 0

    def distance_m(self):
        return 0.0

    def set_drive(self, a, b):
        self.drives.append((round(a), round(b)))

    def resume(self):
        self.resumed += 1

    def send(self, line):
        pass


def make_app(pin="739154"):
    from r1_drive import create_app
    clock = [1000.0]
    link = FakeLink()
    app = create_app(link, {"pin": pin, "drive_speed_pct": 40}, clock=lambda: clock[0])
    return app, link, clock


@pytest.mark.parametrize("pin", ["CHANGE-ME", "4826", "123456", "999999", "12ab56"])
def test_drive_refuses_to_start_with_a_weak_or_example_pin(pin):
    with pytest.raises(SystemExit):
        make_app(pin)


def test_drive_five_wrong_pins_lock_the_page():
    app, link, clock = make_app()
    phone = app.test_client()
    for _ in range(5):
        assert phone.post("/login", json={"pin": "000001"}).status_code == 403
    assert phone.post("/login", json={"pin": "739154"}).status_code == 429, "locked, even for the right PIN"
    clock[0] += 301
    assert phone.post("/login", json={"pin": "739154"}).status_code == 200


def test_drive_one_driver_at_a_time():
    app, link, clock = make_app()
    a, b = app.test_client(), app.test_client()
    assert a.post("/login", json={"pin": "739154"}).status_code == 200
    assert a.post("/stick", json={"x": 0, "y": 1}).status_code == 200
    assert b.post("/login", json={"pin": "739154"}).status_code == 409
    assert b.post("/stick", json={"x": 0, "y": 1}).status_code == 403
    clock[0] += 6
    assert b.post("/login", json={"pin": "739154"}).status_code == 200
    assert a.post("/stick", json={"x": 0, "y": 1}).status_code == 403, "the first phone lost control"


def test_drive_after_a_trip_the_stick_does_nothing_and_resume_needs_reset():
    app, link, clock = make_app()
    p = app.test_client()
    p.post("/login", json={"pin": "739154"})
    link.tripped = True
    j = p.post("/stick", json={"x": 0, "y": 1}).get_json()
    assert link.drives[-1] == (0, 0) and j["tripped"] and "RESET" in j["msg"]
    assert p.post("/resume").status_code == 409 and link.resumed == 0
    link.latch = True                                      # a person pressed the green RESET on the rover
    assert p.post("/resume").status_code == 200 and link.resumed == 1


# ---------------------------------------------------------------- the whole loop (r1_auto) with the simulator as hardware
def test_auto_loop_with_the_simulator():
    w = path(length=5.0, things=[Thing("person", 2.5, 2.75, -0.12, 0.12, 1.7, leave_t=15.0)])
    sim = Sim(w, seed=2)

    class SimLink:
        def __init__(self):
            self.drive, self.sent = (0, 0), []
            self.batt_low = self.batt_flat = False

        @property
        def tripped(self):
            return sim.tripped

        def set_drive(self, a, b):
            self.drive = (a, b)

        def send(self, line):
            self.sent.append(line)

        def resume(self):
            self.sent.append("E 1")

    link = SimLink()

    class SimSensors:
        def __init__(self):
            self.g = self.wv = 0.0

        def read(self, t):
            g = wv = 0.0
            for _ in range(5):
                a, b = sim.physics(link.drive[0], link.drive[1], 0.02)
                g, wv = g + a / 5, wv + b / 5
            sim.t = t
            tl, tr = sim.tof()
            return Sense(t=t, pts=sim.lidar(), step_l=tl, step_r=tr, ground_v=g, wheel_v=wv)

    shots = []
    cap = types.SimpleNamespace(shoot=lambda m: shots.append(m))
    msgs = []
    phone = types.SimpleNamespace(send=lambda k, m, s: msgs.append(k), poll=lambda: None)
    T = [0.0]
    sup = run_path(link, SimSensors(), Supervisor(Cfg(), path_len=4.5), cap, phone,
                   clock=lambda: T[0], sleep=lambda s: T.__setitem__(0, T[0] + 0.1), max_s=300)
    assert sup.state == "DONE" and sim.res.collisions == 0
    assert "wait" in msgs and "clear" in msgs, "it waited for the person and drove on by itself"
    assert len(shots) >= 15 and link.drive == (0, 0) and link.sent[:2] == ["L g", "F 1"] and link.sent[-1] == "F 0"


# ---------------------------------------------------------------- the sums (r1/calc)
def test_engineering_sums_all_pass(capsys):
    sys.path.insert(0, str(HERE.parent / "calc"))
    import r1_calcs
    r1_calcs.CHECKS.clear()
    assert r1_calcs.main(), capsys.readouterr().out


def test_cost_and_payback_sums_all_pass(capsys, monkeypatch):
    sys.path.insert(0, str(HERE.parent / "calc"))
    import r1_costs
    r1_costs.CHECKS.clear()
    monkeypatch.setattr(sys, "argv", ["r1_costs.py"])
    assert r1_costs.main(), capsys.readouterr().out


# ---------------------------------------------------------------- starting a path (r1_auto.start_checks, read_tag)
def test_bed_tag_is_read_from_a_qr_code():
    import cv2
    from r1_auto import read_tag
    q = cv2.QRCodeEncoder.create().encode("H1-B3")
    img = cv2.copyMakeBorder(cv2.resize(q, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST), 40, 40, 40, 40,
                             cv2.BORDER_CONSTANT, value=255)
    assert read_tag(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)) == "H1-B3"
    assert read_tag(np.full((200, 200, 3), 255, np.uint8)) is None


def test_start_checks_all_rules_in_one_place():
    from r1_auto import path_width, start_checks
    h = H(1, "tomato", 10, 30, 0.55)
    pts = np.array([[x, s * 0.275] for x in np.linspace(0.32, 1.15, 25) for s in (1, -1)])
    w = path_width(pts)
    assert abs(w - 0.55) < 0.01
    plan = M.bed_wh(h)
    assert start_checks(h, 3, "H1-B3", w, {1: 990.0}, 1000.0, 26.0, 70.0, 38.0, 700.0, plan) == []
    why = start_checks(h, 3, "H2-B3", w, {}, 1000.0, 22.0, 95.0, 38.0, 700.0, plan)
    assert len(why) == 3, why        # wrong tag, no wheel bath, wet leaves


def test_hole_or_rut_ahead_it_stops_and_asks():
    sup = Supervisor(Cfg(), path_len=10)
    pts = np.array([[x, s * 0.26] for x in np.linspace(0.32, 1.15, 25) for s in (1, -1)])
    out = None
    for k in range(3):
        out = sup.step(Sense(t=0.1 * k, pts=pts, step_l=-0.08, step_r=0.0, ground_v=0.2, wheel_v=0.2))
    assert out.state == "ASK_HUMAN" and sup.reason == "hole" and (out.left, out.right) == (0, 0)


def test_docs_quote_the_same_prices_as_the_parts_list():
    """The README, ISSUES.md, FAILURES.md and rover/README.md must quote the totals bom.csv adds up to (issue E11)."""
    sys.path.insert(0, str(HERE.parent / "calc"))
    import r1_costs
    rows = r1_costs.load()
    fmt = lambda lo, hi: f"₹{lo / 1e5:.2f}–{hi / 1e5:.2f} lakh"   # noqa: E731
    root = HERE.parent.parent                       # build/02-r1-rover
    readme = (root / "README.md").read_text(encoding="utf-8")
    issues = (root / "ISSUES.md").read_text(encoding="utf-8")
    failures = (root.parent.parent / "FAILURES.md").read_text(encoding="utf-8")
    rover = (root.parent.parent / "rover" / "README.md").read_text(encoding="utf-8")
    for cfg in ("full", "scout", "trolley"):
        (r_lo, r_hi), (s_lo, s_hi) = r1_costs.totals(rows, cfg, doors=3)
        assert fmt(r_lo, r_hi) in readme and fmt(s_lo, s_hi) in readme, cfg
        assert fmt(r_lo, r_hi) in issues, cfg
        assert fmt(r_lo, r_hi) in failures, cfg
    full = fmt(*r1_costs.totals(rows, "full")[0])
    assert full in rover
    for old in ("₹2.0–2.1 lakh", "₹1,82,700"):
        assert old not in readme and old not in rover


def test_runner_remembers_the_sickest_house_today_and_refuses_a_cleaner_one(tmp_path):
    from r1_auto import log_visit, sickest_today, start_checks
    log = tmp_path / "day.json"
    assert sickest_today(log, "2026-11-13") is None
    log_visit(log, "2026-11-13", "green")
    log_visit(log, "2026-11-13", "red")
    assert sickest_today(log, "2026-11-13") == "red" and sickest_today(log, "2026-11-14") is None
    h = H(2, "tomato", 10, 30, 0.55, "green")
    why = start_checks(h, 1, "H2-B1", 0.55, {2: 990.0}, 1000.0, 26.0, 70.0, 38.0, 700.0, M.bed_wh(h),
                       sickest_today(log, "2026-11-13"))
    assert len(why) == 1 and "red house today" in why[0]


def test_on_soft_ground_it_stops_for_a_hose_it_would_cross_on_dry_soil():
    """Found by the 200-path batch on 13 Nov: wet tyres can't climb a 16 mm hose, and mild mud never triggered 'stuck'."""
    r = drive(path(things=[Thing("mud", 3.0, 8.0, h=0.0, slip=0.3), Thing("hose", 6.0, 6.02, h=0.016)]))
    assert r.into_step == 0 and reasons(r) == ["step"] and r.finished


# ---------------------------------------------------------------- naming what was flagged (r1_diagnose)
import r1_diagnose as D  # noqa: E402


def _truthful(p):
    """A grower looking at a plant that has exactly problem p."""
    return lambda q: p.looks[0] if q == "look" else (q in p.signs)


def _good_weather(p):
    return D.Climate(wet_hours_24h={"wet": 8, "dry": 0, "humid": 4, "any": 3}[p.climate], mean_c=sum(p.temp) / 2)


@pytest.mark.parametrize("p", D.PROBLEMS, ids=lambda p: p.name)
def test_every_problem_in_the_key_can_be_named_in_5_taps(p):
    for crop in p.crops:
        r, n = D.ask_until_done(crop, _truthful(p), _good_weather(p))
        assert r.verdict == "likely" and r.name == p.name, (crop, r.shares)
        assert n <= 5 and r.confirm and r.first_step


def test_a_photo_alone_is_never_given_a_name():
    for crop in ("tomato", "strawberry"):
        r = D.diagnose(crop, {}, D.Climate(8, 22))
        assert r.verdict == "unsure" and r.next_question[0] == "look"


def test_dont_know_answers_end_in_not_sure_with_candidates_and_a_clinic():
    r, n = D.ask_until_done("tomato", lambda q: "spots" if q == "look" else None, D.Climate(8, 22))
    assert r.verdict == "unsure" and n <= 5 and len(r.shares) == 3
    assert any("agronomist" in w for w in r.warnings)


def test_two_problems_at_once_is_not_given_one_name():
    seen = {"look": "spots", "rings": True, "small_dark_greasy": True, "spots_black_dots": False, "big_watery_blotch": False}
    r = D.diagnose("tomato", seen, D.Climate(8, 27))
    assert r.verdict == "unsure" and {n for n, _ in r.shares[:2]} == {"early blight", "bacterial spot"}


def test_the_climate_moves_the_odds_before_any_sign_is_seen():
    cool_wet = dict(D.diagnose("tomato", {"look": "spots"}, D.Climate(10, 16)).shares)
    hot_dry = dict(D.diagnose("tomato", {"look": "insects"}, D.Climate(0, 33)).shares)
    assert next(iter(cool_wet)) == "late blight" and next(iter(hot_dry)) == "spider mites"


def test_contagious_and_fast_problems_warn_before_they_are_confirmed():
    r, _ = D.ask_until_done("tomato", _truthful(next(p for p in D.PROBLEMS if p.name.startswith("mosaic"))))
    text = " ".join(r.warnings)
    assert "LAST" in text and "lab test" in text and "days" in text


def test_it_never_names_a_chemical():
    words = ("spray ", "fungicide", "sulphur", "copper", "mancozeb", "azoxystrobin", "neem", "ml/l", "g/l")
    for p in D.PROBLEMS:
        assert not any(w in (p.first_step + p.confirm).lower() for w in words), p.name


def test_unknown_crop_goes_to_a_person():
    r = D.diagnose("capsicum", {})
    assert r.verdict == "unsure" and "agronomist" in r.warnings[0]


def test_cases_become_the_farms_own_labels_and_the_key_is_scored(tmp_path):
    f = tmp_path / "cases.jsonl"
    eb = next(p for p in D.PROBLEMS if p.name == "early blight")
    r, _ = D.ask_until_done("tomato", _truthful(eb), _good_weather(eb))
    D.record_case(f, "tomato", "H1-B3 m12.5 L2", {"rings": True}, D.Climate(8, 26), r, "early blight", "lab")
    D.record_case(f, "tomato", "H1-B4 m3.0 R1", {"rings": True}, D.Climate(8, 26), r, "septoria leaf spot", "agronomist")
    D.record_case(f, "tomato", "H1-B5 m7.0 R1", {}, D.Climate(8, 26), r)            # not confirmed yet: no label
    assert D.key_accuracy(f) == (1, 2, 3)


def test_any_first_answer_any_weather_it_never_gives_the_wrong_name():
    """378 cases: every problem x every first answer x 3 climates, grower answers truthfully. Unsure is allowed;
    a wrong name is not. (13 Nov: it once said 'whitefly' on a plant with the virus whiteflies carry.)"""
    wrong = named = sensible = 0
    for p in D.PROBLEMS:
        for crop in p.crops:
            for look in D.LOOKS:
                for cl in (D.Climate(0, 33), D.Climate(4, 24), D.Climate(10, 16)):
                    r, n = D.ask_until_done(crop, lambda q: look if q == "look" else (q in p.signs), cl)
                    assert n <= 5
                    wrong += r.verdict == "likely" and r.name != p.name
                    if look in p.looks:
                        sensible += 1
                        named += r.verdict == "likely"
    assert wrong == 0 and named / sensible >= 0.9, (wrong, named, sensible)
