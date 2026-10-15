#!/usr/bin/env python3
"""GH-01 edge computer (Raspberry Pi 5 + AI HAT+): receives sticky-trap photos and counts the new insects on the Hailo-8.

  POST /trap   body = JPEG, headers X-Trap: trap-2, X-Taken: unix time   (sent by trap_cam.py)

For every photo it:
1. cuts the 4608 x 2592 photo into overlapping 640 x 640 tiles (~40) and runs the detector on each tile;
2. merges boxes across tile edges;
3. matches the boxes with the same trap's last photo: stuck insects don't move, so an unmatched box is a NEW catch;
4. stores everything in SQLite;
5. raises an alert when the new whiteflies in this hour reach 3x the trap's usual hourly rate (and at least 5).
A big drop in the total means the card was changed: the baseline starts again.

The model is a small detector (YOLOv8s / YOLOX-s) trained on 640 px tiles of sticky-card photos and compiled for the
Hailo-8 with NMS on the chip; picamera2's Hailo helper runs it (output: one list per class of [y0, x0, y1, x1, score]).
Written for the bench build; not yet run on hardware (14 Oct 2026).
"""
import json
import os
import sqlite3
import statistics
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np
from picamera2.devices import Hailo

MODEL = os.environ.get("GH_MODEL", "/home/pi/models/sticky_traps_yolov8s.hef")
CLASSES = ["whitefly", "thrips", "macrolophus", "nesidiocoris", "fungus_gnat"]
FRIENDS = {"macrolophus", "nesidiocoris"}          # predatory bugs: they eat whitefly, never a reason to spray
TILE, OVERLAP, THRESH = 640, 96, 0.40
SAME_INSECT_PX = 18                                 # ~1 mm at 20 cm: the same stuck insect in the next photo
DATA = Path(os.environ.get("GH_DATA", "/home/pi/traps"))
DATA.mkdir(parents=True, exist_ok=True)
DB = sqlite3.connect(DATA / "traps.db", check_same_thread=False)
DB.execute("CREATE TABLE IF NOT EXISTS photos (trap TEXT, taken INTEGER, file TEXT, boxes TEXT, new TEXT, card INTEGER)")
HAILO = Hailo(MODEL)
H_IN, W_IN, _ = HAILO.get_input_shape()


def tiles(img):
    h, w = img.shape[:2]
    step = TILE - OVERLAP
    ys = list(range(0, max(1, h - TILE), step)) + [h - TILE]
    xs = list(range(0, max(1, w - TILE), step)) + [w - TILE]
    for y in sorted(set(ys)):
        for x in sorted(set(xs)):
            yield x, y, img[y:y + TILE, x:x + TILE]


def iou(a, b):
    ix = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    iy = max(0, min(a[4], b[4]) - max(a[2], b[2]))
    inter = ix * iy
    ua = (a[3] - a[1]) * (a[4] - a[2]) + (b[3] - b[1]) * (b[4] - b[2]) - inter
    return inter / ua if ua > 0 else 0.0


def detect(img):
    boxes = []                                       # (class, x0, y0, x1, y1, score) in photo pixels
    for x, y, t in tiles(img):
        rgb = cv2.cvtColor(cv2.resize(t, (W_IN, H_IN)), cv2.COLOR_BGR2RGB)
        for c, dets in enumerate(HAILO.run(rgb)):
            for d in dets:
                if d[4] >= THRESH:
                    boxes.append((c, x + d[1] * TILE, y + d[0] * TILE, x + d[3] * TILE, y + d[2] * TILE, float(d[4])))
    boxes.sort(key=lambda b: -b[5])                  # merge duplicates from overlapping tiles (greedy, per class)
    keep = []
    for b in boxes:
        if all(k[0] != b[0] or iou(k, b) < 0.4 for k in keep):
            keep.append(b)
    return keep


def centre(b):
    return ((b[1] + b[3]) / 2, (b[2] + b[4]) / 2)


def new_since(boxes, prev):
    if not prev:
        return boxes
    pc = np.array([centre(p) for p in prev])
    return [b for b in boxes if np.min(np.hypot(*(pc - np.array(centre(b))).T)) > SAME_INSECT_PX]


def alert(trap, text, photo):
    # hook your notifier here (MQTT to the GH-01 dashboard, Telegram, SMS); the dashboard shows the photo
    print(f"[ALERT] {trap}: {text} ({photo})", flush=True)


def handle(trap, taken, jpeg):
    path = DATA / f"{trap}_{taken}.jpg"
    path.write_bytes(jpeg)
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    t0 = time.time()
    boxes = detect(img)
    row = DB.execute("SELECT boxes, card FROM photos WHERE trap=? ORDER BY taken DESC LIMIT 1", (trap,)).fetchone()
    prev, card = (json.loads(row[0]), row[1]) if row else ([], 1)
    if prev and len(boxes) < 0.2 * len(prev):        # most insects gone: a fresh card
        card, prev = card + 1, []
    new = new_since(boxes, prev)
    DB.execute("INSERT INTO photos VALUES (?,?,?,?,?,?)", (trap, taken, path.name, json.dumps(boxes), json.dumps(new), card))
    DB.commit()
    counts = {CLASSES[c]: sum(1 for b in new if b[0] == c) for c in range(len(CLASSES))}
    # usual rate: new whiteflies per photo on this trap over the last 7 days
    week = DB.execute("SELECT new FROM photos WHERE trap=? AND taken>? AND card=? ORDER BY taken", (trap, taken - 7 * 86400, card)).fetchall()
    hist = [sum(1 for b in json.loads(r[0]) if b[0] == 0) for r in week[:-1]]
    usual = statistics.median(hist) if len(hist) >= 6 else None
    wf = counts["whitefly"]
    if usual is not None and wf >= 5 and wf >= 3 * max(usual, 1):
        alert(trap, f"whitefly +{wf} in 1 hour ({wf / max(usual, 1):.0f}x usual)", path.name)
    return {"trap": trap, "new": counts, "on_card": len(boxes), "seconds": round(time.time() - t0, 2),
            "friends": sum(counts[k] for k in FRIENDS)}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/trap":
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length", 0))
        res = handle(self.headers.get("X-Trap", "trap-?"), int(self.headers.get("X-Taken", time.time())), self.rfile.read(n))
        body = json.dumps(res).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(res, flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8088), Handler).serve_forever()
