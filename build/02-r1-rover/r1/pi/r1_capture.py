"""Take 6 photos every 25 cm while the rover drives down a path, and stamp each one with where it was taken.
Starter code, untested on hardware.

  python3 r1_drive.py --house 1 --bed 3        (capture runs inside the drive server: they share the USB port)

Photos go to ~/r1/photos/<date>/house1_bed3/<metre>_<camera>.jpg, and one row per photo into ~/r1/photos.db (SQLite):
house, bed, metre, side, height, time, file. The bed comes from the tag at the bed end (read by the front camera in the
full version; given on the command line here), the metre from the wheel pulses.
"""
import datetime as dt
import sqlite3
import time
from pathlib import Path

import cv2


class Capturer:
    """Runs inside r1_drive.py (they share the Mega's USB port): 6 photos every 25 cm of wheel travel."""

    def __init__(self, link, cfg, house, bed):
        self.link, self.cfg, self.house, self.bed = link, cfg, house, bed
        root = Path.home() / "r1"
        self.out = root / "photos" / dt.date.today().isoformat() / f"house{house}_bed{bed}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "photos.db"
        self.stop = False

    def run(self):
        db = sqlite3.connect(self.db_path)
        db.execute("CREATE TABLE IF NOT EXISTS photo (house INT, bed INT, metre REAL, side TEXT, height REAL, cam TEXT, t TEXT, file TEXT)")
        cams = []
        for c in self.cfg["cameras"]:
            cap = cv2.VideoCapture(c["device"], cv2.CAP_V4L2)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))   # MJPG keeps 6 cameras inside USB bandwidth
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cams.append((c, cap))
        start = self.link.distance_m()
        next_at = 0.0
        try:
            while not self.stop:
                metre = self.link.distance_m() - start
                if metre >= next_at:
                    self.link.send("F 1")              # flash rings on
                    time.sleep(0.08)
                    for c, cap in cams:
                        for _ in range(2):             # drop stale frames from the buffer
                            cap.grab()
                        ok, img = cap.read()
                        if not ok:
                            print("camera", c["name"], "failed")
                            continue
                        f = self.out / f"{metre:06.2f}_{c['name']}.jpg"
                        cv2.imwrite(str(f), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                        db.execute("INSERT INTO photo VALUES (?,?,?,?,?,?,?,?)",
                                   (self.house, self.bed, round(metre, 2), c["side"], c["height"], c["name"], dt.datetime.now().isoformat(), str(f)))
                    self.link.send("F 0")
                    db.commit()
                    next_at += self.cfg["photo_every_m"]
                    print(f"{metre:5.2f} m: {len(cams)} photos")
                time.sleep(0.01)
        finally:
            for _, cap in cams:
                cap.release()
            db.close()
