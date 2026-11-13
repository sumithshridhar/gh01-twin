"""Putting a name on what the rover flagged, the way a plant clinic does it: not from the photo alone.
Pure logic, laptop-tested (tests/test_r1_pi.py). Added 13 Nov 2026 (ISSUES.md S3, DISEASE-NAMES.md).

A photo of a spot can't tell early blight from bacterial spot, and the best field-photo apps are right about 3 times
in 4. A person at the plant can: turn the leaf, rub it, hold it to the light. So the name comes from three things:
  1. the crop (only that crop's problems are candidates),
  2. up to 5 one-tap questions answered at the plant ("white powder underneath that rubs off?"),
  3. the house's climate over the last day (wet-leaf hours and temperature from the heat-and-dew alarm).
It answers "likely X" only when one candidate clearly wins AND its tell-tale sign was seen. Otherwise it says
"not sure", lists the 2-3 candidates, and says how to settle it (a lab or an agronomist). It never names a chemical:
products come from the label and a person.

THE TABLE BELOW IS A STARTING KEY written from general plant-pathology knowledge. It has NOT been checked by an
agronomist or tried on a farm. Have one review it for your crops and region before anyone acts on it.

  python r1_diagnose.py tomato        try it: answer the questions with y / n / Enter (= don't know)
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

# First question: one tap that splits the candidates into small groups.
LOOKS = {
    "powder": "Powder or fuzzy mould",
    "spots": "Spots or blotches on leaves",
    "yellow": "Yellowing or a colour pattern",
    "curl": "Curled, stunted or deformed growth",
    "insects": "Insects, fine dots, webbing or tunnels",
    "fruit": "Damage on the fruit or flowers",
}

SIGNS = {
    "white_powder_under": "White powder UNDER the leaf that rubs off with a finger?",
    "white_powder_top": "White powder patches on TOP of the leaf?",
    "leaf_curl_up": "Leaf edges curling upward?",
    "grey_fuzz": "Grey fuzzy mould on fruit or flowers?",
    "sunken_fruit_spot": "Dark, sunken, firm spots on the fruit?",
    "round_pale_centre": "Small round purple spots with a pale centre?",
    "angular_watery": "Angular spots between the veins that look see-through against the light?",
    "stipple": "Fine pale dots all over the leaf (like sandpaper marks)?",
    "webbing": "Fine webbing under the leaf?",
    "bronze_fruit": "Bronzed or silvery-scarred fruit?",
    "thrips_seen": "Tiny slim insects fall out when you tap a flower on your palm?",
    "interveinal_young": "Yellow between green veins on the YOUNGEST leaves?",
    "interveinal_old": "Yellow between green veins on the OLDEST leaves?",
    "whole_bed": "The same look on most plants in the bed (not one patch)?",
    "rings": "Brown spots with rings inside, like a target?",
    "lower_first": "Did it start on the oldest, lowest leaves?",
    "big_watery_blotch": "Large dark greasy blotches that grew within 2-3 days?",
    "white_fringe_under": "White fuzz at the blotch edge underneath, in the morning?",
    "olive_velvet_under": "Olive-green or brown velvet UNDER pale yellow patches?",
    "small_dark_greasy": "Many small dark greasy spots with a yellow halo?",
    "spots_black_dots": "Small round spots with a grey centre and tiny black dots inside?",
    "whitefly": "Tiny white flies fly up when you shake the plant?",
    "stunted_yellow_top": "Top of the plant stunted, yellow, with small curled leaves?",
    "mosaic": "Light and dark green mosaic pattern on the leaves?",
    "rough_brown_fruit": "Fruit with brown wrinkled patches or yellow blotches?",
    "mines": "Winding or blotchy tunnels inside the leaf?",
    "fruit_bottom_black": "Black leathery patch on the BOTTOM of the fruit?",
}


@dataclass
class Problem:
    name: str
    crops: tuple
    kind: str                      # fungus | bacteria | virus | pest | not_disease
    looks: tuple
    signs: dict                    # sign id -> weight (2 = the tell-tale sign)
    climate: str = "any"           # wet | dry | humid | any
    temp: tuple = (5, 40)          # degrees C where it is active
    contact_spread: bool = False   # spreads on hands, tools and the rover
    fast: bool = False             # can take a house in days
    confirm: str = ""
    first_step: str = ""           # what to do today that needs no chemical


P = Problem
PROBLEMS = [
    # ---- strawberry
    P("powdery mildew", ("strawberry",), "fungus", ("powder", "curl"), {"white_powder_under": 2, "leaf_curl_up": 1},
      "humid", (15, 28), confirm="the powder rubs off; a hand lens shows chains of spores",
      first_step="more air between plants, remove the worst leaves into a bag"),
    P("grey mould (botrytis)", ("strawberry",), "fungus", ("powder", "fruit"), {"grey_fuzz": 2}, "wet", (10, 25), fast=True,
      confirm="grey dust puffs off when touched", first_step="pick off every mouldy fruit into a bag, vent in the morning"),
    P("anthracnose", ("strawberry",), "fungus", ("fruit", "spots"), {"sunken_fruit_spot": 2}, "wet", (22, 32),
      confirm="lab: spores from the spot", first_step="remove spotted fruit, stop overhead water"),
    P("common leaf spot", ("strawberry",), "fungus", ("spots",), {"round_pale_centre": 2}, "wet", (15, 28),
      confirm="round spots, purple edge, pale centre", first_step="remove old spotted leaves"),
    P("angular leaf spot (bacterial)", ("strawberry",), "bacteria", ("spots",), {"angular_watery": 2}, "wet", (10, 22),
      contact_spread=True, confirm="see-through against the light; lab test", first_step="don't work the bed while leaves are wet"),
    P("spider mites", ("strawberry", "tomato"), "pest", ("insects", "yellow"), {"stipple": 2, "webbing": 2}, "dry", (25, 40),
      confirm="tap a leaf over white paper: moving dots", first_step="mark the patch; mites start in hot dry corners"),
    P("thrips", ("strawberry",), "pest", ("insects", "fruit"), {"bronze_fruit": 2, "thrips_seen": 2}, "dry", (20, 35),
      confirm="count on a blue sticky card", first_step="blue sticky cards at flower height"),
    P("iron shortage (not a disease)", ("strawberry",), "not_disease", ("yellow",), {"interveinal_young": 2, "whole_bed": 1},
      confirm="check water pH and EC", first_step="test the irrigation water pH"),
    # ---- tomato
    P("early blight", ("tomato",), "fungus", ("spots",), {"rings": 2, "lower_first": 1}, "wet", (20, 32),
      confirm="target rings in the spot", first_step="strip the lowest spotted leaves"),
    P("late blight", ("tomato",), "fungus", ("spots", "powder", "fruit"), {"big_watery_blotch": 2, "white_fringe_under": 1},
      "wet", (10, 25), fast=True, confirm="white fringe underneath at dawn; lab", first_step="call an agronomist TODAY; bag and remove hit plants"),
    P("leaf mould", ("tomato",), "fungus", ("powder", "yellow"), {"olive_velvet_under": 2}, "humid", (18, 28),
      confirm="olive velvet under the yellow patch", first_step="vent and thin leaves to drop humidity"),
    P("powdery mildew (tomato)", ("tomato",), "fungus", ("powder",), {"white_powder_top": 2}, "humid", (18, 30),
      confirm="powder rubs off", first_step="remove the worst leaves into a bag"),
    P("bacterial spot", ("tomato",), "bacteria", ("spots",), {"small_dark_greasy": 2}, "wet", (24, 32), contact_spread=True,
      confirm="lab test (looks like other spots)", first_step="don't touch plants while wet; clean tools"),
    P("septoria leaf spot", ("tomato",), "fungus", ("spots",), {"spots_black_dots": 2, "lower_first": 1}, "wet", (18, 28),
      confirm="black dots in the spot under a hand lens", first_step="strip the lowest spotted leaves"),
    P("leaf curl virus (from whitefly)", ("tomato",), "virus", ("curl", "yellow", "insects"),
      {"stunted_yellow_top": 2, "leaf_curl_up": 1, "whitefly": 1}, confirm="lab test",
      first_step="pull and bag the plant; yellow sticky cards; check the insect net"),
    P("mosaic / brown rugose virus", ("tomato",), "virus", ("yellow", "curl", "fruit"), {"mosaic": 2, "rough_brown_fruit": 1},
      contact_spread=True, fast=True, confirm="lab test (ELISA / PCR)",
      first_step="stop all work in that row; wash hands and tools; call an agronomist"),
    P("whitefly", ("tomato",), "pest", ("insects",), {"whitefly": 2}, confirm="count on a yellow sticky card",
      first_step="yellow sticky cards; check the insect net and the door"),
    P("leaf miner (Tuta)", ("tomato",), "pest", ("insects", "spots"), {"mines": 2}, confirm="a small caterpillar inside the tunnel",
      first_step="remove mined leaves; pheromone trap"),
    P("blossom end rot (not a disease)", ("tomato",), "not_disease", ("fruit",), {"fruit_bottom_black": 2},
      confirm="only on the fruit's bottom, no mould at first", first_step="even out the watering; check calcium"),
    P("magnesium shortage (not a disease)", ("tomato",), "not_disease", ("yellow",),
      {"interveinal_old": 2, "whole_bed": 1, "lower_first": 1}, confirm="leaf or soil test", first_step="soil or leaf test"),
]


@dataclass
class Climate:
    wet_hours_24h: float = 0.0     # hours with the dew-point gap under 2 C (the heat-and-dew alarm's sum)
    mean_c: float = 25.0


def climate_factor(p: Problem, c: Climate):
    f = 1.0
    if p.climate == "wet":
        f = 1.5 if c.wet_hours_24h >= 6 else 1.0 if c.wet_hours_24h >= 2 else 0.6
    elif p.climate == "dry":
        f = 1.4 if c.wet_hours_24h < 2 and c.mean_c >= 27 else 0.8
    elif p.climate == "humid":
        f = 1.2 if c.wet_hours_24h < 10 else 0.9
    if p.climate != "any" and not (p.temp[0] <= c.mean_c <= p.temp[1]):
        f *= 0.6
    return f


@dataclass
class Result:
    verdict: str                   # "likely" | "unsure"
    name: str                      # the likely problem, or ""
    shares: list                   # [(name, share)], best first
    confirm: str = ""
    first_step: str = ""
    warnings: list = field(default_factory=list)
    next_question: tuple = None    # (id, text) or None when finished


def candidates(crop):
    return [p for p in PROBLEMS if crop in p.crops]


def scores(crop, answers, climate):
    """answers: {"look": one of LOOKS, sign_id: True / False}. Missing = not asked or don't know."""
    out = []
    for p in candidates(crop):
        s = math.log(climate_factor(p, climate))
        look = answers.get("look")
        if look and look not in p.looks:
            s -= 2.0
        for sid, ans in answers.items():
            if sid == "look" or ans is None:
                continue
            w = p.signs.get(sid)
            if ans:
                s += w if w else -1.0          # seen and explained / seen but this problem doesn't cause it
            elif w:
                s -= w                         # its sign was looked for and is not there
        out.append((p, s))
    z = sum(math.exp(s) for _, s in out)
    return sorted(((p, math.exp(s) / z) for p, s in out), key=lambda x: -x[1])


def next_question(crop, answers, ranked, max_questions=5):
    if "look" not in answers:
        return ("look", "What do you see most? " + " / ".join(LOOKS.values()))
    if len(answers) >= max_questions:
        return None
    best, best_v = None, 0.0
    for sid in SIGNS:
        if sid in answers:
            continue
        p_yes = sum(sh for p, sh in ranked if sid in p.signs)
        weight = max((p.signs[sid] for p, sh in ranked if sid in p.signs and sh > 0.03), default=0)
        v = p_yes * (1 - p_yes) * weight + 0.2 * p_yes * weight     # split the field, and prefer the leaders' signs
        if v > best_v:
            best, best_v = sid, v
    return (best, SIGNS[best]) if best else None


def diagnose(crop, answers, climate=None, likely_share=0.6, max_questions=5):
    climate = climate or Climate()
    if not candidates(crop):
        return Result("unsure", "", [], warnings=[f"no key for '{crop}' yet: send the photo to an agronomist"])
    ranked = scores(crop, answers, climate)
    top, share = ranked[0]
    seen_key = any(answers.get(sid) is True and w >= 2 for sid, w in top.signs.items())
    shares = [(p.name, round(sh, 2)) for p, sh in ranked[:3]]
    warn = []
    for p, sh in ranked[:3]:
        if sh >= 0.2 and p.contact_spread:
            warn.append(f"{p.name} spreads on hands, tools and the rover: visit this house LAST, and wash before the next")
        if sh >= 0.2 and p.fast:
            warn.append(f"{p.name} can take a house in days: don't wait for the lab to tell someone")
    # Before naming it, rule out the runner-up: its tell-tale sign must have been looked for. (Whiteflies on a plant
    # don't mean "just whitefly" until someone has checked for the virus they carry.)
    rival = next(((sid, SIGNS[sid]) for p, sh in ranked[1:] if sh >= 0.12
                  for sid, w in p.signs.items() if w >= 2 and sid not in answers), None)
    if share >= likely_share and seen_key and rival and len(answers) < max_questions:
        return Result("unsure", "", shares, warnings=warn, next_question=rival)
    if share >= likely_share and seen_key and not rival:
        if top.kind in ("virus", "bacteria"):
            warn.append("a lab test is the only sure name for a virus or bacteria")
        return Result("likely", top.name, shares, top.confirm, top.first_step, warn)
    q = next_question(crop, answers, ranked, max_questions)
    if q is None:
        warn.append("not sure: send the photo and these answers to an agronomist or a plant clinic")
    return Result("unsure", "", shares, warnings=warn, next_question=q)


def ask_until_done(crop, answer_fn, climate=None, max_questions=5):
    """answer_fn(question_id) -> a LOOKS key for "look", else True / False / None. Returns (Result, n_questions)."""
    answers = {}
    while True:
        r = diagnose(crop, answers, climate, max_questions=max_questions)
        if r.next_question is None:
            return r, len(answers)
        answers[r.next_question[0]] = answer_fn(r.next_question[0])


def record_case(path, crop, where, answers, climate, result, confirmed_name=None, confirmed_by=None, photo=None):
    """Every case becomes one line of the farm's own labelled data (the thing no app has). `confirmed_name` is
    filled in later by the lab, the agronomist or the grower; until then the case does not count as a label."""
    row = {"crop": crop, "where": where, "answers": answers, "wet_hours_24h": climate.wet_hours_24h,
           "mean_c": climate.mean_c, "verdict": result.verdict, "guess": result.name, "shares": result.shares,
           "confirmed_name": confirmed_name, "confirmed_by": confirmed_by, "photo": photo}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def key_accuracy(path):
    """Of the confirmed cases where the key said "likely", how many did it name right? The number to watch."""
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    done = [r for r in rows if r["confirmed_name"] and r["verdict"] == "likely"]
    return (sum(r["guess"] == r["confirmed_name"] for r in done), len(done), len(rows))


if __name__ == "__main__":
    import sys
    crop = sys.argv[1] if len(sys.argv) > 1 else "tomato"

    def ask(qid):
        if qid == "look":
            keys = list(LOOKS)
            for i, k in enumerate(keys, 1):
                print(f"  {i}. {LOOKS[k]}")
            return keys[int(input("What do you see most? number: ")) - 1]
        a = input(SIGNS[qid] + " y/n/Enter: ").strip().lower()
        return True if a == "y" else False if a == "n" else None
    res, n = ask_until_done(crop, ask, Climate(wet_hours_24h=4, mean_c=24))
    print(f"\n{res.verdict.upper()}: {res.name or 'not sure'}  {res.shares}")
    for line in (res.confirm and "confirm: " + res.confirm, res.first_step and "today: " + res.first_step, *res.warnings):
        if line:
            print(" ", line)
