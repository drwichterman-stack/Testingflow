"""Child and Adolescent Trauma Screen (CATS), Sachser et al. (2017).

Verified against the official CATS Youth Report form (ages 7-17). The
form states the CATS is freely accessible with no copyright or licensing
fees. Item wording is still entered by number only.

Form structure:
  * Events: 15 Yes/No items (item 15 = other, with description).
  * Symptoms: 20 items in the last two weeks, 0 Never, 1 Once in a while,
    2 Half the time, 3 Almost always. Total 0-60.
    Item order follows DSM-5 PTSD criteria:
      1-5   B Intrusion        6-7  C Avoidance
      8-14  D Negative alterations in cognition and mood
      15-20 E Arousal and reactivity
  * Impairment: 5 Yes/No items (getting along with others, hobbies/fun,
    school or work, family relationships, general happiness).

Severity bands printed on the form (ages 7-17):
    < 15   Normal. Not clinically elevated.
    15-20  Moderate trauma-related distress.
    21+    Probable PTSD.

Also reported (supplementary, status VERIFY): cluster sums and whether
the DSM-5 symptom pattern is met (B >= 1, C >= 1, D >= 2, E >= 2), with a
symptom counted as present when rated 2 or 3.

The caregiver 3-6 form (16 items) gets no automatic band.
"""

from __future__ import annotations

from .base import PUBLISHED, VERIFY, Field, Instrument, ScoreResult, ScoreRow, band

RESPONSES = [(0, "Never"), (1, "Once in a while"), (2, "Half the time"), (3, "Almost always")]
YESNO = [(0, "No"), (1, "Yes")]

VARIANTS = [
    ("self_7_17", "Youth report, ages 7-17"),
    ("caregiver_7_17", "Caregiver report, ages 7-17"),
    ("caregiver_3_6", "Caregiver report, ages 3-6"),
]
N_EVENTS = 15
N_ITEMS = {"self_7_17": 20, "caregiver_7_17": 20, "caregiver_3_6": 16}
IMPAIRMENT = ["Getting along with others", "Hobbies/Fun", "School or work",
              "Family relationships", "General happiness"]
CUTOFFS_7_17 = [(0, 14, "Normal. Not clinically elevated."),
                (15, 20, "Moderate trauma-related distress."),
                (21, 60, "Probable PTSD.")]
CLUSTERS = [("B", "B Intrusion (items 1-5)", range(1, 6), 1),
            ("C", "C Avoidance (items 6-7)", range(6, 8), 1),
            ("D", "D Cognition/mood (items 8-14)", range(8, 15), 2),
            ("E", "E Arousal/reactivity (items 15-20)", range(15, 21), 2)]


def fields_for(variant: str) -> list[Field]:
    fs = [Field(f"event{i}", f"Event {i}" + (" (other)" if i == N_EVENTS else ""),
                "choice", YESNO, section="Stressful or scary events")
          for i in range(1, N_EVENTS + 1)]
    fs.append(Field("event_describe", "Event 15 description", "line",
                    section="Stressful or scary events"))
    n = N_ITEMS[variant]
    fs += [Field(f"item{i}", f"Symptom item {i}", "choice", RESPONSES,
                 section=f"Symptoms, last two weeks (items 1-{n})")
           for i in range(1, n + 1)]
    fs += [Field(f"impair{i}", label, "choice", YESNO,
                 section="Interference (problems interfered with...)")
           for i, label in enumerate(IMPAIRMENT, start=1)]
    return fs


def score(variant: str, responses: dict, context: dict) -> ScoreResult:
    is_young = variant == "caregiver_3_6"
    res = ScoreResult(verification=PUBLISHED if variant == "self_7_17" else VERIFY)
    n = N_ITEMS[variant]
    ev = [responses.get(f"event{i}") for i in range(1, N_EVENTS + 1)]
    if any(v not in (None, "") for v in ev):
        yes = [str(i) for i, v in enumerate(ev, start=1) if v == 1]
        res.rows.append(ScoreRow("Events", "Events endorsed", str(len(yes)), "",
                                 ("items " + ", ".join(yes)) if yes else ""))
        desc = (responses.get("event_describe") or "").strip()
        if desc:
            res.rows.append(ScoreRow("Events", "Other event", desc))
        if not yes and any(responses.get(f"item{i}") not in (None, "") for i in range(1, n + 1)):
            res.warnings.append("No events endorsed, but symptom items were entered.")

    r = {i: responses.get(f"item{i}") for i in range(1, n + 1)}
    answered = [v for v in r.values() if v not in (None, "")]
    total = sum(answered)
    missing = n - len(answered)
    b = ""
    if not is_young and answered:
        b = band(total, CUTOFFS_7_17)
        if missing and band(total + 3 * missing, CUTOFFS_7_17) != b:
            b = "Indeterminate (missing items)"
    res.rows.append(ScoreRow("Symptoms", f"Symptom total (0-{3 * n})", str(total), b,
                             f"{missing} of {n} unanswered" if missing else ""))

    if not is_young and answered:
        met = []
        for key, label, items, need in CLUSTERS:
            vals = [r[i] for i in items if r[i] not in (None, "")]
            present = sum(1 for v in vals if v >= 2)
            ok = present >= need
            met.append(ok)
            res.rows.append(ScoreRow("DSM-5 clusters", label, f"sum {sum(vals)}; "
                                     f"{present} present", "criterion met" if ok else "",
                                     f"needs {need}+ rated 2-3"))
        res.rows.append(ScoreRow("DSM-5 clusters", "Symptom pattern B1+C1+D2+E2",
                                 "met" if all(met) else "not met", "",
                                 "screening only; not a diagnosis"))
    imp = [responses.get(f"impair{i}") for i in range(1, len(IMPAIRMENT) + 1)]
    if any(v not in (None, "") for v in imp):
        areas = [IMPAIRMENT[i] for i, v in enumerate(imp) if v == 1]
        res.rows.append(ScoreRow("Interference", f"Areas affected (of {len(IMPAIRMENT)})",
                                 str(len(areas)), "", ", ".join(areas)))
    if is_young:
        res.warnings.append("Ages 3-6 version: no bands applied. Use the CATS scoring sheet.")
    if variant == "caregiver_7_17":
        res.warnings.append("Caregiver 7-17 bands use the youth-form cutoffs; confirm on "
                            "the caregiver form.")
    res.warnings.append("DSM-5 cluster pattern is supplementary (item rated 2-3 = present).")
    res.summary = f"Symptom total {total}" + (f" ({b.rstrip('.')})." if b else ".")
    return res


INSTRUMENT = Instrument(
    key="cats", name="Child and Adolescent Trauma Screen", short="CATS",
    flows=("A",), version="cats-form-2", verification=PUBLISHED,
    variants=VARIANTS, fields_for=fields_for, score=score,
    description="15 events (Yes/No), symptom items (0-3), and 5 interference items.",
    paper_form=True,
)
