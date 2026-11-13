"""What R1 does with photos that look wrong. Pure logic, laptop-tested (tests/test_r1_pi.py). Starter code.
Added 13 Nov 2026 (ISSUES.md S3: "we still don't know how we identify the diseases").

R1 does NOT name diseases, and it never sprays on its own judgement:
  1. The model on the rover only scores "how different is this leaf from this farm's healthy leaves" (0..1). It is
     trained on healthy photos first, so it works without a disease dataset (docs: rover/SOLUTIONS.md).
  2. A person names it: the farmer, or an agronomist from the photo. A second-opinion app may suggest a name, shown
     as a guess (field-photo apps are right about 3 times in 4).
  3. The climate sets the urgency: a spot in a house whose leaves stayed wet for hours (dew-point gap under 2 C, the
     heat-and-dew alarm's sum) matters more than the same spot after a dry week.
  4. Alerts are rationed: one morning summary with at most 10 photos, plus the list of places the cameras could not
     see well (a person checks those by hand). The phone rings in between only when the photo, the climate and
     "new since last week" all agree.
  5. Every tap (Real / Not disease / Don't know) is a label. If the farmer's taps say fewer than 8 alerts in 10 are
     real, the bar goes up and it sends fewer alerts, not more.
  6. Spraying stays behind r1_spray.py's locks, which need a person's name every time.
"""
from dataclasses import dataclass, field


@dataclass
class Flag:
    house: int
    bed: int
    metre: float
    side: str
    height: float
    score: float                  # 0..1, how unlike this farm's healthy leaves
    new: bool = True              # not flagged at this plant last week
    photo: str = ""


def house_risk(wet_hours_24h, warm=True):
    """Leaf-wet hours in the last 24 h (dew-point gap < 2 C) -> green / amber / red. `warm` = the hours were in the
    range most leaf fungi like (roughly 15-28 C); cold or hot wet hours count less."""
    h = wet_hours_24h if warm else wet_hours_24h / 2
    return "red" if h >= 6 else "amber" if h >= 2 else "green"


@dataclass
class Triage:
    threshold: float = 0.60       # below this score a flag is only logged
    urgent: float = 0.85          # score needed to ring the phone (with red risk and new)
    max_summary: int = 10
    target_precision: float = 0.80
    labels: list = field(default_factory=list)   # True = the farmer said real, False = not disease

    def priority(self, f: Flag, risk):
        return f.score * {"green": 0.6, "amber": 0.8, "red": 1.0}[risk] * (1.0 if f.new else 0.5)

    def decide(self, flags, risks, unseen=()):
        """flags: today's Flags; risks: {house: green/amber/red}; unseen: places the cameras couldn't see.
        Returns {'ring': [...], 'summary': [...], 'logged': n, 'check_by_hand': [...]}"""
        keep = [f for f in flags if f.score >= self.threshold]
        first = {}                                   # at most one ring per house: its highest-scoring flag
        for f in sorted(keep, key=lambda f: -f.score):
            if f.score >= self.urgent and f.new and risks.get(f.house) == "red":
                first.setdefault(f.house, f)
        ring = list(first.values())
        rest = sorted((f for f in keep if all(f is not r for r in ring)),
                      key=lambda f: -self.priority(f, risks.get(f.house, "green")))
        summary = rest[: self.max_summary]
        return {"ring": ring, "summary": summary, "logged": len(flags) - len(ring) - len(summary),
                "check_by_hand": list(unseen)}

    def tap(self, real: bool):
        """The farmer's answer on one alert. Keeps the last 30 and moves the bar."""
        self.labels = (self.labels + [bool(real)])[-30:]
        if len(self.labels) < 10:
            return self.threshold
        precision = sum(self.labels) / len(self.labels)
        if precision < self.target_precision:
            self.threshold = min(0.95, round(self.threshold + 0.05, 2))
        elif precision > 0.9:
            self.threshold = max(0.60, round(self.threshold - 0.02, 2))
        return self.threshold
