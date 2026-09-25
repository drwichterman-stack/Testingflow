"""Instrument registry and flow definitions."""

from __future__ import annotations

from . import asrs, cats, interview, licensed, sdq, wsr2
from .base import Instrument, ScoreResult, validate  # noqa: F401

# Display order within each flow follows the specification.
FLOW_ORDER = {
    "A": ["interview", "sdq", "cats", "conners4", "tova", "wsr2", "asrs"],
    "B": ["interview", "mmpi3", "brown", "wsr2", "asrs", "tova"],
}
FLOW_LABELS = {"A": "Flow A: Children/Adolescents (6+)",
               "B": "Flow B: Adolescents/Adults"}

INSTRUMENTS: dict[str, Instrument] = {
    i.key: i for i in [interview.INSTRUMENT, sdq.INSTRUMENT, cats.INSTRUMENT,
                       licensed.CONNERS4, licensed.TOVA, wsr2.INSTRUMENT,
                       asrs.INSTRUMENT, licensed.MMPI3, licensed.BROWN]
}


def instruments_for(flow: str, asrs_enabled: bool) -> list[Instrument]:
    """Instruments shown for a client. ASRS in Flow A appears only if enabled."""
    out = []
    for key in FLOW_ORDER[flow]:
        inst = INSTRUMENTS[key]
        if key == "asrs" and flow == "A" and not asrs_enabled:
            continue
        out.append(inst)
    return out


def run_scoring(instrument_key: str, variant: str, responses: dict, context: dict) -> ScoreResult:
    inst = INSTRUMENTS[instrument_key]
    errors = validate(inst.fields_for(variant), responses)
    if errors:
        raise ValueError("; ".join(errors))
    return inst.score(variant, responses, context)
