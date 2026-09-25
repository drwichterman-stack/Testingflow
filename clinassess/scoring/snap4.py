"""SNAP-IV 26: Teacher and Parent Rating Scale, J. M. Swanson (UC Irvine).

Form (verified against the July 2022 SNAP-IV-26 form): 26 items rated
Not at all (0), Just a little (1), Quite a bit (2), Very much (3).
  Items 1-9   ADHD Inattention
  Items 10-18 ADHD Hyperactivity/Impulsivity
  Items 19-26 Oppositional Defiant
Item wording follows DSM criteria and is not reproduced.

Scoring (Swanson's SNAP-IV scoring instructions; the form itself prints
no scoring rule, so status VERIFY):
  * Subscale score = average item rating (sum / items answered).
  * 5% cutoffs for the average rating (score at or above = clinically
    significant):
                     Teacher   Parent
      Inattention      2.56     1.78
      Hyperactivity    1.78     1.44
      Combined (1-18)  2.00     1.67
      ODD              1.38     1.88
  * DSM-style symptom count: items rated Quite a bit or Very much.
"""

from __future__ import annotations

from .base import VERIFY, Field, Instrument, ScoreResult, ScoreRow

RESPONSES = [(0, "Not at all"), (1, "Just a little"), (2, "Quite a bit"), (3, "Very much")]
SUBSCALES = [
    ("inatt", "ADHD Inattention", list(range(1, 10))),
    ("hyper", "ADHD Hyperactivity/Impulsivity", list(range(10, 19))),
    ("comb", "ADHD Combined (items 1-18)", list(range(1, 19))),
    ("odd", "Oppositional Defiant", list(range(19, 27))),
]
CUTOFFS = {
    "teacher": {"inatt": 2.56, "hyper": 1.78, "comb": 2.00, "odd": 1.38},
    "parent": {"inatt": 1.78, "hyper": 1.44, "comb": 1.67, "odd": 1.88},
}
SECTION_OF = {i: "Items 1-9: Inattention" if i <= 9 else
              "Items 10-18: Hyperactivity/Impulsivity" if i <= 18 else
              "Items 19-26: Oppositional Defiant" for i in range(1, 27)}


def fields_for(variant: str) -> list[Field]:
    return [Field(f"item{i}", f"Item {i}", "choice", RESPONSES, section=SECTION_OF[i])
            for i in range(1, 27)]


def score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=VERIFY)
    parts = []
    for key, label, items in SUBSCALES:
        vals = [responses.get(f"item{i}") for i in items]
        ans = [v for v in vals if v not in (None, "")]
        if not ans:
            continue
        avg = sum(ans) / len(ans)
        cut = CUTOFFS[variant][key]
        band = (f"At or above {variant} 5% cutoff ({cut:.2f})" if avg >= cut
                else f"Below {variant} 5% cutoff ({cut:.2f})")
        missing = len(items) - len(ans)
        note = f"{missing} unanswered" if missing else ""
        res.rows.append(ScoreRow("Average item score", label, f"{avg:.2f}", band, note))
        if key != "comb":
            present = sum(1 for v in ans if v >= 2)
            res.rows.append(ScoreRow("Symptom count (rated 2-3)", label,
                                     f"{present}/{len(items)}"))
        parts.append(f"{label.replace('ADHD ', '')} {avg:.2f}")
    res.summary = "Averages: " + "; ".join(parts) + "." if parts else ""
    return res


INSTRUMENT = Instrument(
    key="snap4", name="SNAP-IV 26 Teacher and Parent Rating Scale", short="SNAP-IV",
    flows=("A",), version="snap4-26-1", verification=VERIFY,
    variants=[("parent", "Parent"), ("teacher", "Teacher")],
    fields_for=fields_for, score=score,
    description="26 items (0-3). Subscale averages compared with Swanson's 5% cutoffs.",
    paper_form=True,
)
