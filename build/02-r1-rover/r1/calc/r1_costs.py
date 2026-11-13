"""R1's cost and payback from ONE parts list (bom.csv), so the total can't drift between the README, the reels and the
pitch again (ISSUES.md S6, E11). 13 Nov 2026.

  python r1_costs.py                              the farm R1 was designed for: 3 houses of about 1,000 m2
  python r1_costs.py --houses 1 --area 4047       one acre in one house
  python r1_costs.py --chem 2000 --loss 30000     your farm's chemical spend (Rs/acre/month) and crop loss saved (Rs/season)

Three ways to build it:
  full     R1 as designed: drives itself, 6+1 cameras, AI chip, sprayer, drive-on dock
  scout    drives itself and photographs, no sprayer, no AI chip (scores photos overnight), 2+1 cameras, smaller battery
  trolley  the same cameras and brain on a hand-pushed trolley that the worker takes on the daily round

Payback counts only money that is easy to see: the hours of scouting a worker no longer walks (rovers that drive
themselves) and spray saved by spraying only the flagged plants (with the sprayer). It does NOT count crop saved by
catching disease earlier, because nobody has measured that on a real farm; instead it prints how much that saving
would have to be for each way to pay back in one season.
"""
import argparse
import csv
import math
from pathlib import Path

BOM = Path(__file__).resolve().parent / "bom.csv"
CONFIGS = ("full", "scout", "trolley")
ACRE = 4047.0
SEASON_DAYS = 180                         # one strawberry or tomato crop, roughly


def load(path=BOM):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def totals(rows, cfg, doors=3):
    """(low, high) in rupees: the rover itself, and the system = rover + per-door + per-farm items."""
    rover = [0.0, 0.0]
    system = [0.0, 0.0]
    for r in rows:
        q = int(r[f"qty_{cfg}"])
        if not q:
            continue
        mult = q * (doors if r["per"] == "door" else 1)
        lo, hi = float(r["unit_low"]) * mult, float(r["unit_high"]) * mult
        if r["per"] == "rover":
            rover[0] += lo
            rover[1] += hi
        system[0] += lo
        system[1] += hi
    return tuple(rover), tuple(system)


def value_per_day(cfg, area_m2, wage=550.0, scout_h_per_acre=2.0, chem_per_acre_month=750.0, spot_saving=0.5):
    """Rupees a day of easy-to-see value. Defaults = the 4 Nov payback reel's model: 2 h of scouting per acre a day
    (a worker's 8 h day = Rs 550, Karnataka minimum wage), plus spray saved on 1 acre = Rs 12.5 a day."""
    acres = area_m2 / ACRE
    labour = scout_h_per_acre * acres * wage / 8.0 if cfg in ("full", "scout") else 0.0
    spray = chem_per_acre_month * spot_saving * acres / 30.0 if cfg == "full" else 0.0
    return labour + spray


def lakh(x):
    return f"Rs {x / 1e5:.2f} lakh"


def report(area_m2=3000.0, houses=3, chem=750.0, loss=0.0, wage=550.0):
    rows = load()
    out = {}
    print(f"Farm: {houses} house(s), {area_m2:.0f} m2 ({area_m2 / ACRE:.2f} acre). Wage Rs {wage:.0f}/day. "
          f"Chemicals Rs {chem:.0f}/acre/month. Crop saved by earlier warnings: Rs {loss:.0f}/season (not measured)\n")
    for cfg in CONFIGS:
        (r_lo, r_hi), (s_lo, s_hi) = totals(rows, cfg, doors=houses)
        v = value_per_day(cfg, area_m2, wage=wage, chem_per_acre_month=chem) + loss / SEASON_DAYS
        mid = (s_lo + s_hi) / 2
        days = mid / v if v > 0 else math.inf
        need = mid / SEASON_DAYS
        extra = max(0.0, (need - v) * SEASON_DAYS)
        out[cfg] = {"rover": (r_lo, r_hi), "system": (s_lo, s_hi), "value_day": v, "payback_days": days,
                    "need_day": need, "crop_saving_needed": extra}
        pb = "never (only crop saved would pay for it)" if math.isinf(days) else f"{days:,.0f} days ({days / 365:.1f} years)"
        print(f"  {cfg:8s} rover {lakh(r_lo)}-{r_hi / 1e5:.2f} | with doors/farm {lakh(s_lo)}-{s_hi / 1e5:.2f} | "
              f"easy value Rs {v:,.0f}/day | payback {pb}")
        print(f"           to pay back in one season it must bring Rs {need:,.0f}/day: "
              f"that is Rs {extra:,.0f} of crop saved per season on top")
    return out


CHECKS = []


def check(ok, what, detail=""):
    CHECKS.append(bool(ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {what}  {detail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", type=float, default=3000.0, help="m2 the rover covers")
    ap.add_argument("--houses", type=int, default=3, help="doors that need a wheel bath")
    ap.add_argument("--chem", type=float, default=750.0, help="Rs per acre per month on sprays")
    ap.add_argument("--loss", type=float, default=0.0, help="Rs of crop per season saved by earlier warnings")
    ap.add_argument("--wage", type=float, default=550.0)
    a = ap.parse_args()
    res = report(a.area, a.houses, a.chem, a.loss, a.wage)
    rows = load()
    print("\nChecks")
    full = totals(rows, "full")[0]
    check(abs(200000 / 150 - 1333.3) < 0.1, "the 4 Nov reel's sum still holds: Rs 2,00,000 / Rs 150 a day = 1,333 days")
    acre = value_per_day("full", ACRE)
    check(abs(acre - 150.0) < 0.01, "this model gives the reel's Rs 150 a day on one acre", f"(Rs {acre:.1f})")
    check(1.9e5 <= full[0] and full[1] <= 2.2e5, "full R1 parts total is in the README's range", f"({lakh(full[0])}-{full[1] / 1e5:.2f})")
    s, t = totals(rows, "scout")[0], totals(rows, "trolley")[0]
    check(s[1] < full[0], "R1-Scout costs less than full R1 at any price in the ranges", f"({lakh(s[1])} < {lakh(full[0])})")
    reuse = sum(float(r["unit_low"]) * int(r["qty_trolley"]) for r in rows
                if r["per"] == "rover" and int(r["qty_trolley"]) and int(r["qty_scout"]))
    check(reuse / t[0] >= 0.7, "most of the trolley's money carries over into R1-Scout later", f"({reuse / t[0]:.0%})")
    check(res["full"]["payback_days"] > 3 * 365, "on 3 small houses full R1 does not pay back in 3 years on labour + spray "
          "(honest: it is still a concept)", f"({res['full']['payback_days'] / 365:.1f} years)")
    n = sum(CHECKS)
    print(f"\n{'ALL PASSED' if n == len(CHECKS) else 'FAILED'}: {n} of {len(CHECKS)} checks")
    return n == len(CHECKS)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
