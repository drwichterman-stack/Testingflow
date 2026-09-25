"""Strengths and Difficulties Questionnaire (SDQ), Goodman (1997).

Source: "Scoring the Strengths & Difficulties Questionnaire for age 4-17
or 18+", Youth in Mind, sdqinfo.org. Item wording is copyrighted and is
not reproduced; the clinician enters each response by item number from
the paper form.

Rules implemented:
  * Items coded 0 Not True, 1 Somewhat True, 2 Certainly True.
  * Items 7, 11, 14, 21, 25 are reverse scored (2, 1, 0).
  * Five scales of five items each (0 to 10).
  * A scale is scored if at least 3 of its 5 items are answered, prorated
    as round(mean x 5), matching the official SPSS syntax.
  * Total Difficulties = Emotional + Conduct + Hyperactivity + Peer
    (0 to 40), scored only if all four are available.
  * Externalising = Conduct + Hyperactivity; Internalising = Emotional + Peer.
  * Impact supplement: scored only if the respondent reports a difficulty.
    "Not at all" and "Only a little" = 0, "A medium amount" (US) or
    "Quite a lot" (UK) = 1, "A great deal" = 2.
  * Item order and reverse-keyed items verified against the US English
    P4-10 and P/T 11-17 forms (copyright Robert Goodman, 2005).
  * Bands: the original three-band categorisation (Normal / Borderline /
    Abnormal) from sdqinfo.org, separate for parent, teacher, and self.
"""

from __future__ import annotations

from .base import (PUBLISHED, Field, Instrument, ScoreResult, ScoreRow, band,
                   round_half_up)

REVERSED = {7, 11, 14, 21, 25}
SCALES = {
    "emotional": ("Emotional Symptoms", [3, 8, 13, 16, 24]),
    "conduct": ("Conduct Problems", [5, 7, 12, 18, 22]),
    "hyperactivity": ("Hyperactivity/Inattention", [2, 10, 15, 21, 25]),
    "peer": ("Peer Relationship Problems", [6, 11, 14, 19, 23]),
    "prosocial": ("Prosocial Behaviour", [1, 4, 9, 17, 20]),
}

RESPONSES = [(0, "Not True"), (1, "Somewhat True"), (2, "Certainly True")]

# (low, high, band) for each scale by informant. Original 3-band cut-offs.
_N, _B, _A = "Normal", "Borderline", "Abnormal"
CUTOFFS = {
    "parent": {
        "total": [(0, 13, _N), (14, 16, _B), (17, 40, _A)],
        "emotional": [(0, 3, _N), (4, 4, _B), (5, 10, _A)],
        "conduct": [(0, 2, _N), (3, 3, _B), (4, 10, _A)],
        "hyperactivity": [(0, 5, _N), (6, 6, _B), (7, 10, _A)],
        "peer": [(0, 2, _N), (3, 3, _B), (4, 10, _A)],
        "prosocial": [(6, 10, _N), (5, 5, _B), (0, 4, _A)],
        "impact": [(0, 0, _N), (1, 1, _B), (2, 10, _A)],
    },
    "teacher": {
        "total": [(0, 11, _N), (12, 15, _B), (16, 40, _A)],
        "emotional": [(0, 4, _N), (5, 5, _B), (6, 10, _A)],
        "conduct": [(0, 2, _N), (3, 3, _B), (4, 10, _A)],
        "hyperactivity": [(0, 5, _N), (6, 6, _B), (7, 10, _A)],
        "peer": [(0, 3, _N), (4, 4, _B), (5, 10, _A)],
        "prosocial": [(6, 10, _N), (5, 5, _B), (0, 4, _A)],
        "impact": [(0, 0, _N), (1, 1, _B), (2, 6, _A)],
    },
    "self": {
        "total": [(0, 15, _N), (16, 19, _B), (20, 40, _A)],
        "emotional": [(0, 5, _N), (6, 6, _B), (7, 10, _A)],
        "conduct": [(0, 3, _N), (4, 4, _B), (5, 10, _A)],
        "hyperactivity": [(0, 5, _N), (6, 6, _B), (7, 10, _A)],
        "peer": [(0, 3, _N), (4, 5, _B), (6, 10, _A)],
        "prosocial": [(6, 10, _N), (5, 5, _B), (0, 4, _A)],
        "impact": [(0, 0, _N), (1, 1, _B), (2, 10, _A)],
    },
}

VARIANTS = [
    ("parent", "Parent (P4-10 or P/T 11-17)"),
    ("teacher", "Teacher (T4-10 or P/T 11-17)"),
    ("self", "Self-report (S11-17)"),
]

DIFFICULTY_OPTIONS = [(0, "No"), (1, "Yes, minor difficulties"),
                      (2, "Yes, definite difficulties"), (3, "Yes, severe difficulties")]
# US English forms print "A medium amount"; UK forms print "Quite a lot".
# Both occupy the third position and score 1.
IMPACT_OPTIONS = [(0, "Not at all"), (1, "Only a little"),
                  (2, "A medium amount / Quite a lot"), (3, "A great deal")]
CHRONICITY_OPTIONS = [(0, "Less than a month"), (1, "1-5 months"), (2, "6-12 months"),
                      (3, "Over a year")]
IMPACT_ITEMS = {
    "parent": [("imp_distress", "Distress"), ("imp_home", "Interferes: home life"),
               ("imp_friends", "Interferes: friendships"),
               ("imp_class", "Interferes: classroom learning"),
               ("imp_leisure", "Interferes: leisure activities")],
    "self": [("imp_distress", "Distress"), ("imp_home", "Interferes: home life"),
             ("imp_friends", "Interferes: friendships"),
             ("imp_class", "Interferes: classroom learning"),
             ("imp_leisure", "Interferes: leisure activities")],
    "teacher": [("imp_distress", "Distress"),
                ("imp_peers", "Interferes: peer relationships"),
                ("imp_class", "Interferes: classroom learning")],
}


def fields_for(variant: str) -> list[Field]:
    fields = [Field(f"item{i}", f"Item {i}" + (" (reverse scored)" if i in REVERSED else ""),
                    "choice", RESPONSES, section="Items 1-25")
              for i in range(1, 26)]
    fields.append(Field("difficulties", "Overall: any difficulties?", "choice",
                        DIFFICULTY_OPTIONS, section="Impact supplement (optional)"))
    fields.append(Field("chronicity", "How long present (not scored)", "choice",
                        CHRONICITY_OPTIONS, section="Impact supplement (optional)"))
    for key, label in IMPACT_ITEMS.get(variant, []):
        fields.append(Field(key, label, "choice", IMPACT_OPTIONS,
                            section="Impact supplement (optional)"))
    return fields


def _item_score(i: int, raw: int) -> int:
    return 2 - raw if i in REVERSED else raw


def scale_score(items: list[int], responses: dict) -> int | None:
    vals = [_item_score(i, responses[f"item{i}"]) for i in items
            if responses.get(f"item{i}") not in (None, "")]
    if len(vals) < 3:
        return None
    return round_half_up(sum(vals) / len(vals) * 5)


def score(variant: str, responses: dict, context: dict) -> ScoreResult:
    cut = CUTOFFS[variant]
    res = ScoreResult(verification=PUBLISHED)
    scales = {}
    for key, (label, items) in SCALES.items():
        s = scale_score(items, responses)
        scales[key] = s
        answered = sum(responses.get(f"item{i}") not in (None, "") for i in items)
        if s is None:
            res.rows.append(ScoreRow("Scales", label, "not scored",
                                     note=f"only {answered}/5 items answered"))
            res.warnings.append(f"{label}: fewer than 3 items answered; not scored.")
        else:
            note = f"prorated from {answered}/5 items" if answered < 5 else ""
            res.rows.append(ScoreRow("Scales", label, str(s), band(s, cut[key]), note))

    diff = [scales[k] for k in ("emotional", "conduct", "hyperactivity", "peer")]
    if None in diff:
        res.rows.insert(0, ScoreRow("Composite", "Total Difficulties", "not scored"))
    else:
        total = sum(diff)
        res.rows.insert(0, ScoreRow("Composite", "Total Difficulties", str(total),
                                    band(total, cut["total"])))
        res.rows.insert(1, ScoreRow("Composite", "Externalising (Conduct + Hyperactivity)",
                                    str(scales["conduct"] + scales["hyperactivity"])))
        res.rows.insert(2, ScoreRow("Composite", "Internalising (Emotional + Peer)",
                                    str(scales["emotional"] + scales["peer"])))
        res.summary = f"Total Difficulties {total} ({band(total, cut['total'])})."

    d = responses.get("difficulties")
    if d not in (None, ""):
        if d == 0:
            res.rows.append(ScoreRow("Impact", "Impact score", "0", band(0, cut["impact"]),
                                     "no difficulties reported"))
        else:
            imp_items = IMPACT_ITEMS[variant]
            answered = [responses.get(k) for k, _ in imp_items
                        if responses.get(k) not in (None, "")]
            impact = sum({0: 0, 1: 0, 2: 1, 3: 2}[v] for v in answered)
            note = "" if len(answered) == len(imp_items) else \
                f"{len(answered)}/{len(imp_items)} impact items answered"
            res.rows.append(ScoreRow("Impact", "Impact score", str(impact),
                                     band(impact, cut["impact"]), note))
    return res


INSTRUMENT = Instrument(
    key="sdq", name="Strengths and Difficulties Questionnaire", short="SDQ",
    flows=("A",), version="sdq-3band-1", verification=PUBLISHED,
    variants=VARIANTS, fields_for=fields_for, score=score,
    description="25 items, 5 scales. Enter responses from the paper form by item number.",
    paper_form=True,
)
