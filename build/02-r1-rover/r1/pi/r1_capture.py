"""Photos at each station along a path, each stamped with where it was taken. Starter code, untested on hardware.

13 Nov 2026 (ISSUES.md S5 E7), what changed from v1 and why:
  - ONE camera streams at a time: open, let it settle, grab, close. v1 kept six USB cameras streaming at once through
    one hub, and USB cameras reserve bandwidth when they start, so on one USB 2 bus the 3rd or 4th camera is likely
    to fail ("No space left on device"). The bench test measures how long one camera takes (capture_s in r1_mission).
  - Fixed exposure and white balance, and the LED rings stay ON for the whole path. v1 flashed the rings for 80 ms,
    but a USB camera's auto-exposure takes far longer than that to settle, so photos would have come out with
    different brightness: the opposite of what the light is for.
  - Cameras turned to PORTRAIT: the long side of the picture covers the plant's height. In landscape, three heights
    0.6 m apart left bands between them that no camera saw (r1_calcs.py, camera coverage).
  - Which cameras run comes from the house's crop (r1_mission.CROPS): 2 for strawberry, 6 for tomato.
  - The metre comes from the rover's ground sensor (r1_supervisor), not wheel turns, so mud can't stack photos.
  - A camera that fails marks that metre "not seen" for the check-by-hand list, instead of silently leaving a gap.

Photos go to ~/r1/photos/<date>/house<h>_bed<b>/<metre>_<camera>.jpg, one row per photo in ~/r1/photos.db.
"""
import datetime as dt
import sqlite3
from pathlib import Path

DEFAULT_SETTINGS = {"width": 1920, "height": 1080, "exposure_100us": 10, "wb_kelvin": 5000, "settle_frames": 4}


def open_camera(cv2, device, s):
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, s["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, s["height"])
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)                 # V4L2: 1 = manual
    cap.set(cv2.CAP_PROP_EXPOSURE, s["exposure_100us"])     # 10 x 100 us = 1/1000 s: sharp while the rings light it
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)
    cap.set(cv2.CAP_PROP_WB_TEMPERATURE, s["wb_kelvin"])
    return cap


class Capturer:
    def __init__(self, cfg, house, bed, cameras, root=None, cv2=None, today=None, heights=None):
        """cameras: names from the crop profile, e.g. ["L1", "R1"]; their device, side and height come from config.
        heights: the crop profile's camera heights where the mast is set differently (strawberry: 0.85 m)."""
        if cv2 is None:
            import cv2 as _cv2                                  # on the rover; tests pass a fake
            cv2 = _cv2
        self.cv2, self.cfg, self.house, self.bed = cv2, cfg, house, bed
        byname = {c["name"]: c for c in cfg["cameras"]}
        missing = [n for n in cameras if n not in byname]
        if missing:
            raise ValueError(f"cameras {missing} are not in config.yaml")
        self.cams = [{**byname[n], **({"height": heights[n]} if heights and n in heights else {})} for n in cameras]
        self.settings = {**DEFAULT_SETTINGS, **cfg.get("camera_settings", {})}
        root = Path(root) if root else Path.home() / "r1"
        day = (today or dt.date.today()).isoformat()
        self.out = root / "photos" / day / f"house{house}_bed{bed}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / "photos.db")
        self.db.execute("CREATE TABLE IF NOT EXISTS photo (house INT, bed INT, metre REAL, side TEXT, height REAL, "
                        "cam TEXT, t TEXT, file TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS unseen (house INT, bed INT, metre REAL, cam TEXT, why TEXT, t TEXT)")
        self.taken = 0
        self.unseen = []                                        # (metre, camera, why)

    def shoot(self, metre):
        """All of this crop's cameras at one station, one after the other. Returns how many photos were saved."""
        cv2, s, ok_n = self.cv2, self.settings, 0
        for c in self.cams:
            why = None
            cap = None
            try:
                cap = open_camera(cv2, c["device"], s)
                if cap is None:
                    why = "camera did not open"
                else:
                    for _ in range(s["settle_frames"]):         # let the stream settle at the fixed exposure
                        cap.grab()
                    ok, img = cap.read()
                    if not ok or img is None:
                        why = "no picture"
                    else:
                        if c.get("portrait", True):
                            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                        f = self.out / f"{metre:06.2f}_{c['name']}.jpg"
                        cv2.imwrite(str(f), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                        self.db.execute("INSERT INTO photo VALUES (?,?,?,?,?,?,?,?)",
                                        (self.house, self.bed, round(metre, 2), c["side"], c["height"], c["name"],
                                         dt.datetime.now().isoformat(), str(f)))
                        ok_n += 1
            except Exception as e:                              # a USB camera dropping out must not stop the path
                why = f"error: {e}"
            finally:
                if cap is not None:
                    cap.release()                               # only one camera streams at any moment
            if why:
                self.unseen.append((round(metre, 2), c["name"], why))
                self.db.execute("INSERT INTO unseen VALUES (?,?,?,?,?,?)",
                                (self.house, self.bed, round(metre, 2), c["name"], why, dt.datetime.now().isoformat()))
        self.db.commit()
        self.taken += ok_n
        return ok_n

    def close(self):
        self.db.close()
