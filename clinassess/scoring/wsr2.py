"""Weiss Symptom Record II (WSR-II), M. D. Weiss.

The WSR-II lists DSM-5 symptoms for many disorders, each rated 0 to 3.
Item wording is not reproduced here.

Implemented (status VERIFY):
  * Sections implemented: ADHD Inattention (9 items), ADHD
    Hyperactivity-Impulsivity (9 items), Oppositional Defiant (8 items).
  * Ratings: 0 Never/Not at all, 1 Sometimes/Somewhat, 2 Often/Pretty much,
    3 Very often/Very much.
  * A symptom counts as present when rated 2 or 3.
  * DSM-5 symptom-count thresholds:
      ADHD (each domain): 6 or more if age < 17; 5 or more if age >= 17
      ODD: 4 or more
    A count at or above threshold means only "symptom count meets the DSM-5
    threshold". DSM-5 also requires onset, duration, settings, and
    impairment criteria, which are clinical judgments.
  * Mean item rating is reported for each section.
  * Other WSR-II sections (anxiety, mood, and others) are recorded as
    clinician summary text.

VERIFY: confirm the item ranges and the "2 or 3 = present" convention
against the WSR-II form and scoring instructions you use.
"""

from __future__ import annotations

from .base import VERIFY, Field, Instrument, ScoreResult, ScoreRow

RESPONSES = [(0, "Never / Not at all"), (1, "Sometimes / Somewhat"),
             (2, "Often / Pretty much"), (3, "Very often / Very much")]

SECTIONS = [
    ("adhd_in", "ADHD: Inattention", 9),
    ("adhd_hi", "ADHD: Hyperactivity-Impulsivity", 9),
    ("odd", "Oppositional Defiant", 8),
]

VARIANTS = [("self", "Self-report"), ("parent", "Parent report"),
            ("teacher", "Teacher report"), ("clinician", "Clinician-rated")]


def threshold(section: str, age: int | None) -> int:
    if section == "odd":
        return 4
    return 5 if age is not None and age >= 17 else 6


def fields_for(variant: str) -> list[Field]:
    fs = []
    for key, label, n in SECTIONS:
        fs += [Field(f"{key}_{i}", f"{label} {i}", "choice", RESPONSES, section=label)
               for i in range(1, n + 1)]
    fs.append(Field("other_sections", "Other WSR-II sections (clinician summary)", "text",
                    section="Other sections"))
    return fs


def score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=VERIFY)
    age = context.get("age")
    parts = []
    for key, label, n in SECTIONS:
        vals = [responses.get(f"{key}_{i}") for i in range(1, n + 1)]
        ans = [v for v in vals if v not in (None, "")]
        if not ans:
            continue
        count = sum(1 for v in ans if v >= 2)
        th = threshold(key, age)
        missing = n - len(ans)
        if count >= th:
            b = f"Meets DSM-5 symptom count ({th}+)"
        elif count + missing >= th:
            b = "Indeterminate (missing items)"
        else:
            b = f"Below DSM-5 symptom count ({th}+)"
        note = f"{missing} unanswered" if missing else ""
        res.rows.append(ScoreRow(label, "Symptoms present (rated 2-3)", f"{count}/{n}", b, note))
        res.rows.append(ScoreRow(label, "Mean item rating (0-3)", f"{sum(ans) / len(ans):.2f}"))
        parts.append(f"{label} {count}/{n}")
    if age is None and any(r.section.startswith("ADHD") for r in res.rows):
        res.warnings.append("Age unknown; ADHD threshold of 6 applied.")
    other = (responses.get("other_sections") or "").strip()
    if other:
        res.rows.append(ScoreRow("Other sections", "Clinician summary", other))
    res.summary = "; ".join(parts) + ("." if parts else "")
    return res


INSTRUMENT = Instrument(
    key="wsr2", name="Weiss Symptom Record II", short="WSR-II",
    flows=("A", "B"), version="wsr2-1", verification=VERIFY,
    variants=VARIANTS, fields_for=fields_for, score=score,
    description="DSM-5 symptom ratings (0-3). ADHD and ODD sections are scored.",
)
