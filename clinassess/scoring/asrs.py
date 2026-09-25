"""Adult ADHD Self-Report Scale (ASRS v1.1), WHO / Kessler et al. (2005).

Source: ASRS-v1.1 Symptom Checklist and scoring instructions (World Health
Organization; Harvard Medical School National Comorbidity Survey).

Rules implemented:
  * 18 items, coded 0 Never, 1 Rarely, 2 Sometimes, 3 Often, 4 Very Often.
  * An item is "shaded" (counted) when it reaches its threshold. Verified
    box by box against the shaded cells of the official WHO checklist:
      Sometimes or higher: items 1, 2, 3, 9, 12, 16, 18
      Often or higher:     items 4, 5, 6, 7, 8, 10, 11, 13, 14, 15, 17
  * Part A screener (items 1 to 6): 4 or more shaded = symptoms highly
    consistent with adult ADHD; further investigation warranted.
  * Part B (items 7 to 18): shaded count reported. There is no official
    Part B cutoff; it gives added information on symptoms.
  * Raw symptom totals (0 to 72, and 0 to 36 per subscale) are also given:
      Inattentive: items 1-4, 7-11
      Hyperactive-Impulsive: items 5, 6, 12-18
    These raw totals have no official WHO cutoff.

The ASRS is designed for adults (18+). Use with adolescents is a clinical
decision; Flow A shows this measure only when enabled for the client.
"""

from __future__ import annotations

from .base import PUBLISHED, Field, Instrument, ScoreResult, ScoreRow

RESPONSES = [(0, "Never"), (1, "Rarely"), (2, "Sometimes"), (3, "Often"), (4, "Very Often")]
THRESHOLD_SOMETIMES = {1, 2, 3, 9, 12, 16, 18}
INATTENTIVE = [1, 2, 3, 4, 7, 8, 9, 10, 11]
HYPERACTIVE = [5, 6, 12, 13, 14, 15, 16, 17, 18]


def threshold(item: int) -> int:
    return 2 if item in THRESHOLD_SOMETIMES else 3


def fields_for(variant: str) -> list[Field]:
    return [Field(f"item{i}", f"Item {i} (shaded at {'Sometimes' if threshold(i) == 2 else 'Often'}+)",
                  "choice", RESPONSES,
                  section="Part A (items 1-6)" if i <= 6 else "Part B (items 7-18)")
            for i in range(1, 19)]


def score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=PUBLISHED)
    r = {i: responses.get(f"item{i}") for i in range(1, 19)}
    missing = [i for i, v in r.items() if v in (None, "")]
    if missing:
        res.warnings.append(f"Unanswered items: {', '.join(map(str, missing))}. "
                            "Counts use answered items only.")
    shaded = {i for i, v in r.items() if v not in (None, "") and v >= threshold(i)}
    part_a = len([i for i in shaded if i <= 6])
    part_b = len([i for i in shaded if i > 6])
    a_missing = [i for i in missing if i <= 6]
    if part_a >= 4:
        a_band = "Positive screen: highly consistent with adult ADHD"
    elif a_missing and part_a + len(a_missing) >= 4:
        a_band = "Indeterminate (missing Part A items)"
    else:
        a_band = "Negative screen"
    res.rows.append(ScoreRow("Screener", "Part A shaded items (of 6)", str(part_a), a_band,
                             "cutoff: 4 or more"))
    res.rows.append(ScoreRow("Checklist", "Part B shaded items (of 12)", str(part_b), "",
                             "no official cutoff"))

    def total(items):
        return sum(r[i] for i in items if r[i] not in (None, ""))
    res.rows.append(ScoreRow("Raw totals", "Inattentive raw (items 1-4, 7-11; 0-36)",
                             str(total(INATTENTIVE)), "", "no official cutoff"))
    res.rows.append(ScoreRow("Raw totals", "Hyperactive-Impulsive raw (items 5-6, 12-18; 0-36)",
                             str(total(HYPERACTIVE)), "", "no official cutoff"))
    res.rows.append(ScoreRow("Raw totals", "Total raw (0-72)",
                             str(total(range(1, 19))), "", "no official cutoff"))
    res.rows.append(ScoreRow("Checklist", "Inattentive items shaded (of 9)",
                             str(len(shaded & set(INATTENTIVE)))))
    res.rows.append(ScoreRow("Checklist", "Hyperactive-Impulsive items shaded (of 9)",
                             str(len(shaded & set(HYPERACTIVE)))))
    age = context.get("age")
    if age is not None and age < 18:
        res.warnings.append(f"Client age {age}: ASRS v1.1 is normed for adults (18+).")
    res.summary = f"Part A: {part_a}/6 shaded ({a_band.lower()})."
    return res


INSTRUMENT = Instrument(
    key="asrs", name="Adult ADHD Self-Report Scale v1.1", short="ASRS v1.1",
    flows=("A", "B"), version="asrs-1.1-2", verification=PUBLISHED,
    variants=[("self", "Self-report")], fields_for=fields_for, score=score,
    description="18 items. Part A (1-6) is the screener; Part B (7-18) adds detail.",
    gated=True, paper_form=True,
)
