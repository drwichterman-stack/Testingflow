"""Common types for instrument definitions and scoring results.

An Instrument describes (1) the fields the data-entry form shows and
(2) a pure function that turns those responses into a ScoreResult. The
GUI builds each form from these definitions, so all scoring logic lives
in this package and is covered by unit tests.

Verification status (shown in the UI, the PDF, and SCORING_REFERENCE.md):
  PUBLISHED     rule implemented from the publisher's public scoring document
  VERIFY        rule implemented, but a cutoff or item key must be checked
                against the official manual before clinical use
  TRANSCRIBED   licensed instrument; scores are computed in the publisher's
                software and typed in here. The app does not compute norms.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable

PUBLISHED = "PUBLISHED"
VERIFY = "VERIFY"
TRANSCRIBED = "TRANSCRIBED"


@dataclass
class Field:
    key: str
    label: str
    kind: str  # "choice" | "int" | "float" | "text" | "line"
    options: list[tuple[int, str]] = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    section: str = ""
    help: str = ""
    critical: bool = False  # safety item: always re-checked by a person after a camera read


@dataclass
class ScoreRow:
    section: str
    label: str
    value: str
    band: str = ""
    note: str = ""


@dataclass
class ScoreResult:
    rows: list[ScoreRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""
    verification: str = PUBLISHED

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "ScoreResult":
        return ScoreResult(
            rows=[ScoreRow(**r) for r in d.get("rows", [])],
            warnings=list(d.get("warnings", [])),
            summary=d.get("summary", ""),
            verification=d.get("verification", PUBLISHED),
        )


@dataclass
class Instrument:
    key: str
    name: str
    short: str
    flows: tuple[str, ...]
    version: str
    verification: str
    variants: list[tuple[str, str]]  # (key, label)
    fields_for: Callable[[str], list[Field]]
    score: Callable[[str, dict, dict], ScoreResult]  # (variant, responses, context)
    description: str = ""
    gated: bool = False  # Flow A ASRS: shown only if enabled at intake
    paper_form: bool = False  # free paper form: responses can be read with the camera


class ValidationError(ValueError):
    pass


def validate(fields: list[Field], responses: dict) -> list[str]:
    """Check entered values against field types and ranges."""
    errors = []
    for f in fields:
        v = responses.get(f.key)
        if v in (None, ""):
            continue
        if f.kind == "choice":
            if v not in {o[0] for o in f.options}:
                errors.append(f"{f.label}: invalid response {v!r}")
        elif f.kind in ("int", "float"):
            try:
                num = float(v)
            except (TypeError, ValueError):
                errors.append(f"{f.label}: not a number")
                continue
            if f.kind == "int" and num != int(num):
                errors.append(f"{f.label}: must be a whole number")
            if f.minimum is not None and num < f.minimum:
                errors.append(f"{f.label}: below minimum {f.minimum:g}")
            if f.maximum is not None and num > f.maximum:
                errors.append(f"{f.label}: above maximum {f.maximum:g}")
    return errors


def round_half_up(x: float) -> int:
    """SPSS-style RND(): halves round away from zero (scores are non-negative)."""
    return int(x + 0.5)


def band(value: float, cutoffs: list[tuple[float, float, str]]) -> str:
    for lo, hi, label in cutoffs:
        if lo <= value <= hi:
            return label
    return ""
