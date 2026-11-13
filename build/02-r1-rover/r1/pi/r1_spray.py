"""Spray one spot, only if every lock passes. Starter code, untested on hardware. Test with WATER first.
Stop r1_drive.py first: in this starter version the scripts take turns on the Mega's USB port.

  python3 r1_spray.py --house 1 --valve R2 --product "Water (test)" --approved-by "Ravi"

The locks (all must pass, or nothing opens):
  1. a person approved this spray (name is logged). The rover's photo score never counts as approval
  2. the product is listed for this house's crop in config.yaml (copied from its label)
  3. the product's waiting period ends before the house's next picking
  4. nobody is in the house (door/PIR sensor file says "0")
  5. the I/O board says: e-stop chain closed, not tripped, water in the tank, battery not low
  6. the I/O board really armed (it refuses on its own if any of 5 changed in between)
Every spray (or refusal) is appended to ~/r1/spray_log.csv.

13 Nov 2026: the locks are a function (spray_locks) so the laptop tests can try to break each one, and the script now
checks that the board really armed before it opens a valve (v1 logged "SPRAYED" even if the board had refused).
"""
import argparse
import csv
import datetime as dt
import sys
import time
from pathlib import Path


def spray_locks(cfg, house_id, valve, product_name, approved_by, today, occupied_text):
    """Every reason NOT to spray, from the request and the farm's config. Empty list = these locks pass."""
    reasons = []
    house = next((h for h in cfg["houses"] if h["id"] == house_id), None)
    product = next((p for p in cfg["products"] if p["name"] == product_name), None)
    if not (approved_by or "").strip():
        reasons.append("no approval: a person's name is needed for every spray")
    if house is None:
        reasons.append("unknown house")
    if product is None:
        reasons.append("product not in config (copy it from the label first)")
    if house and product and house["crop"] not in product["crops"]:
        reasons.append(f"{product['name']} is not approved for {house['crop']}")
    if house and product:
        picking = dt.date.fromisoformat(str(house["next_picking"]))
        safe_from = today + dt.timedelta(days=int(product["wait_days"]))
        if safe_from > picking:
            reasons.append(f"waiting period ends {safe_from}, after the next picking {picking}")
    if occupied_text is None or occupied_text.strip() != "0":
        reasons.append("someone may be inside (door sensor not 0)")
    if valve not in cfg["valves"]:
        reasons.append("unknown valve")
    return reasons


def board_locks(estop_ok, tripped, tank_ok, batt_low):
    """Reasons from the I/O board's status line."""
    reasons = []
    if not estop_ok:
        reasons.append("e-stop chain open")
    if tripped:
        reasons.append("tripped: check the rover and press the green RESET first")
    if not tank_ok:
        reasons.append("tank empty")
    if batt_low:
        reasons.append("battery low")
    return reasons


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--house", type=int, required=True)
    ap.add_argument("--valve", required=True, help="L1 R1 L2 R2 L3 R3")
    ap.add_argument("--product", required=True)
    ap.add_argument("--approved-by", required=True)
    args = ap.parse_args(argv)

    from r1_link import Link, load_config
    cfg = load_config()
    occ = Path(cfg["door_sensor_file"])
    reasons = spray_locks(cfg, args.house, args.valve, args.product, args.approved_by, dt.date.today(),
                          occ.read_text() if occ.exists() else None)
    link = Link(cfg)
    time.sleep(0.3)                              # wait for a status line
    reasons += board_locks(link.estop_ok, link.tripped, link.tank_ok, link.batt_low)

    log = Path.home() / "r1" / "spray_log.csv"
    log.parent.mkdir(parents=True, exist_ok=True)
    row = [dt.datetime.now().isoformat(), args.house, args.valve, args.product, args.approved_by]

    def refuse(why):
        with open(log, "a", newline="") as f:
            csv.writer(f).writerow(row + ["REFUSED: " + "; ".join(why)])
        print("REFUSED:", *why, sep="\n  ")
        link.close()
        sys.exit(1)

    if reasons:
        refuse(reasons)
    n = cfg["valves"].index(args.valve)
    link.send("L a")                             # amber: spraying, keep out
    link.send("E 1")                             # the pump and valves are fed from after the contactor
    link.set_drive(0, 0)                         # the neutral the board waits for; the rover stays still
    time.sleep(0.3)
    link.send("A 1")
    time.sleep(0.2)
    if not link.armed:
        refuse(["the I/O board refused to arm (status flags: " + str(link.flags) + ")"])
    link.send(f"V {n} 1")
    time.sleep(float(cfg["spray_seconds"]))      # the board closes it after 4 s on its own anyway
    link.send(f"V {n} 0")
    link.send("A 0")
    link.send("L g")
    with open(log, "a", newline="") as f:
        csv.writer(f).writerow(row + ["SPRAYED", cfg["spray_seconds"]])
    print("sprayed", args.valve, "for", cfg["spray_seconds"], "s")
    link.close()


if __name__ == "__main__":
    main()
