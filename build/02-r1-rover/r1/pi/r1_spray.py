"""Spray one spot, only if every lock passes. Starter code, untested on hardware. Test with WATER first.
Stop r1_drive.py first: in this starter version the scripts take turns on the Mega's USB port.

  python3 r1_spray.py --house 1 --valve R2 --product "Water (test)" --approved-by "Ravi"

The locks (all must pass, or nothing opens):
  1. a person approved this spray (name is logged)
  2. the product is listed for this house's crop in config.yaml (copied from its label)
  3. the product's waiting period ends before the house's next picking
  4. nobody is in the house (door/PIR sensor file says "0")
  5. the e-stop loop is closed and there is water in the tank (reported by the Mega)
Every spray (or refusal) is appended to ~/r1/spray_log.csv.
"""
import argparse
import csv
import datetime as dt
import sys
import time
from pathlib import Path

from r1_link import Link, load_config

ap = argparse.ArgumentParser()
ap.add_argument("--house", type=int, required=True)
ap.add_argument("--valve", required=True, help="L1 R1 L2 R2 L3 R3")
ap.add_argument("--product", required=True)
ap.add_argument("--approved-by", required=True)
args = ap.parse_args()
cfg = load_config()

house = next((h for h in cfg["houses"] if h["id"] == args.house), None)
product = next((p for p in cfg["products"] if p["name"] == args.product), None)
reasons = []
if not args.approved_by.strip():
    reasons.append("no approval")
if house is None:
    reasons.append("unknown house")
if product is None:
    reasons.append("product not in config (copy it from the label first)")
if house and product and house["crop"] not in product["crops"]:
    reasons.append(f"{product['name']} is not approved for {house['crop']}")
if house and product:
    picking = dt.date.fromisoformat(str(house["next_picking"]))
    safe_from = dt.date.today() + dt.timedelta(days=int(product["wait_days"]))
    if safe_from > picking:
        reasons.append(f"waiting period ends {safe_from}, after the next picking {picking}")
occ = Path(cfg["door_sensor_file"])
if not occ.exists() or occ.read_text().strip() != "0":
    reasons.append("someone may be inside (door sensor not 0)")
if args.valve not in cfg["valves"]:
    reasons.append("unknown valve")

link = Link(cfg)
time.sleep(0.3)                                  # wait for a status line
if not link.estop_ok:
    reasons.append("e-stop loop open")
if not link.tank_ok:
    reasons.append("tank empty")

log = Path.home() / "r1" / "spray_log.csv"
log.parent.mkdir(parents=True, exist_ok=True)
row = [dt.datetime.now().isoformat(), args.house, args.valve, args.product, args.approved_by]
if reasons:
    with open(log, "a", newline="") as f:
        csv.writer(f).writerow(row + ["REFUSED: " + "; ".join(reasons)])
    print("REFUSED:", *reasons, sep="\n  ")
    link.close()
    sys.exit(1)

n = cfg["valves"].index(args.valve)
link.send("L a")                                 # amber: spraying, keep out
link.send("A 1")
time.sleep(0.2)
link.send(f"V {n} 1")
time.sleep(float(cfg["spray_seconds"]))
link.send(f"V {n} 0")
link.send("A 0")
link.send("L g")
with open(log, "a", newline="") as f:
    csv.writer(f).writerow(row + ["SPRAYED", cfg["spray_seconds"]])
print("sprayed", args.valve, "for", cfg["spray_seconds"], "s")
link.close()
