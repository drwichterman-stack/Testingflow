"""Child and Adolescent Trauma Screen (CATS), Sachser et al. (2017).

The CATS is freely available (public domain). Item wording is not
reproduced here; enter responses by item number from the form.

Structure implemented:
  * Part 1: trauma-event checklist. The clinician enters the number of
    endorsed events and lists them. Symptom items are completed only if
    at least one event is endorsed.
  * Part 2: symptom items coded 0 Never, 1 Once in a while,
    2 Half the time, 3 Almost always.
      Ages 7-17 (self or caregiver report): 20 items, total 0-60.
      Ages 3-6 (caregiver report): 16 items, total 0-48.
  * Part 3: impairment items (Yes/No), reported as a count.

Severity bands (ages 7-17), CATS scoring sheet:
    0-14  Normal range
    15-20 Moderate trauma-related distress
    21+   Probable PTSD
Status VERIFY: confirm these cutoffs against the version of the CATS form
you use. The app gives no bands for the 3-6 caregiver version; enter the
interpretation from the scoring sheet.
"""

from __future__ import annotations

from .base import VERIFY, Field, Instrument, ScoreResult, ScoreRow, band

RESPONSES = [(0, "Never"), (1, "Once in a while"), (2, "Half the time"), (3, "Almost always")]
YESNO = [(0, "No"), (1, "Yes")]

VARIANTS = [
    ("self_7_17", "Self-report, ages 7-17"),
    ("caregiver_7_17", "Caregiver report, ages 7-17"),
    ("caregiver_3_6", "Caregiver report, ages 3-6"),
]
N_ITEMS = {"self_7_17": 20, "caregiver_7_17": 20, "caregiver_3_6": 16}
N_IMPAIRMENT = 5
CUTOFFS_7_17 = [(0, 14, "Normal range"), (15, 20, "Moderate trauma-related distress"),
                (21, 60, "Probable PTSD")]


def fields_for(variant: str) -> list[Field]:
    fs = [Field("events_count", "Number of trauma events endorsed", "int",
                minimum=0, maximum=30, section="Part 1: Events"),
          Field("events_list", "Events endorsed (brief)", "line", section="Part 1: Events")]
    fs += [Field(f"item{i}", f"Symptom item {i}", "choice", RESPONSES,
                 section=f"Part 2: Symptoms (items 1-{N_ITEMS[variant]})")
           for i in range(1, N_ITEMS[variant] + 1)]
    fs += [Field(f"impair{i}", f"Impairment item {i}", "choice", YESNO,
                 section="Part 3: Impairment")
           for i in range(1, N_IMPAIRMENT + 1)]
    return fs


def score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=VERIFY)
    n = N_ITEMS[variant]
    vals = [responses.get(f"item{i}") for i in range(1, n + 1)]
    answered = [v for v in vals if v not in (None, "")]
    events = responses.get("events_count")
    if events not in (None, ""):
        res.rows.append(ScoreRow("Events", "Trauma events endorsed", str(events)))
        if int(events) == 0 and answered:
            res.warnings.append("No events endorsed, but symptom items were entered.")
    total = sum(answered)
    missing = n - len(answered)
    note = f"{missing} of {n} items unanswered" if missing else ""
    b = band(total, CUTOFFS_7_17) if variant != "caregiver_3_6" else ""
    if missing and variant != "caregiver_3_6":
        # A band is only reported if missing items could not change it.
        best, worst = band(total, CUTOFFS_7_17), band(total + 3 * missing, CUTOFFS_7_17)
        if best != worst:
            b = "Indeterminate (missing items)"
    res.rows.append(ScoreRow("Symptoms", f"Symptom total (0-{3 * n})", str(total), b, note))
    res.rows.append(ScoreRow("Symptoms", "Items rated Half the time or more",
                             str(sum(1 for v in answered if v >= 2))))
    imp = [responses.get(f"impair{i}") for i in range(1, N_IMPAIRMENT + 1)]
    imp_ans = [v for v in imp if v not in (None, "")]
    if imp_ans:
        res.rows.append(ScoreRow("Impairment", f"Areas impaired (of {N_IMPAIRMENT})",
                                 str(sum(imp_ans))))
    if variant == "caregiver_3_6":
        res.warnings.append("Ages 3-6 version: no bands applied. Use the CATS scoring sheet.")
    res.summary = f"Symptom total {total}" + (f" ({b})." if b else ".")
    return res


INSTRUMENT = Instrument(
    key="cats", name="Child and Adolescent Trauma Screen", short="CATS",
    flows=("A",), version="cats-1", verification=VERIFY,
    variants=VARIANTS, fields_for=fields_for, score=score,
    description="Trauma events, symptom items (0-3), and impairment items.",
)
