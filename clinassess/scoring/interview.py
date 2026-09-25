"""Clinical interview notes, organized by domain. Not scored."""

from __future__ import annotations

from .base import PUBLISHED, Field, Instrument, ScoreResult, ScoreRow

DOMAINS = [
    ("referral", "Reason for referral"),
    ("presenting", "Presenting concerns"),
    ("developmental", "Developmental history"),
    ("medical", "Medical history and medications"),
    ("educational", "Educational / occupational history"),
    ("family", "Family and social history"),
    ("psychiatric", "Prior psychiatric history and treatment"),
    ("substance", "Substance use"),
    ("observations", "Behavioral observations / mental status"),
    ("other", "Other"),
]


def fields_for(variant: str) -> list[Field]:
    return [Field(k, label, "text", section="Interview") for k, label in DOMAINS]


def score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=PUBLISHED)
    for k, label in DOMAINS:
        text = (responses.get(k) or "").strip()
        if text:
            res.rows.append(ScoreRow("Interview", label, text))
    res.summary = f"{len(res.rows)} domain(s) documented."
    return res


INSTRUMENT = Instrument(
    key="interview", name="Clinical Interview Notes", short="Interview",
    flows=("A", "B"), version="interview-1", verification=PUBLISHED,
    variants=[("clinical", "Clinical interview")], fields_for=fields_for, score=score,
    description="Free-text interview notes by domain.",
)
