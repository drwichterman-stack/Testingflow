"""Report model: section layout, auto-generated draft text, and sanitizing.

A saved report is a dict {section_key: text}, stored as a versioned row in
report_versions. Section TITLES, the score tables, the page header, and
the confidentiality statement are fixed by the code and cannot be
edited. Only the narrative text of each section can be edited.

Score tables are always rebuilt from the scored assessment records when
the PDF is made. The report editor cannot change a score. To correct a
score, edit the assessment entry; that change is re-scored and audited.

The app does not write clinical opinion. Case conceptualization,
diagnostic impressions, and recommendations start as outlines with
"[Clinician to complete ...]" prompts. Export warns while any prompt is
left in the text.
"""

from __future__ import annotations

import re
from datetime import date

from .scoring import FLOW_LABELS, FLOW_ORDER, INSTRUMENTS
from .scoring.base import PUBLISHED, TRANSCRIBED, VERIFY

PLACEHOLDER = "[Clinician to complete"
MAX_SECTION_CHARS = 50_000

TEMPLATE_TITLES = {
    "child": "Psychological Assessment Report: Child/Adolescent",
    "adult": "Psychological Assessment Report: Adolescent/Adult",
}

# (key, locked title, multiline?)
HEAD_SECTIONS = [
    ("identifying", "Identifying Information", True),
    ("interview", "Interview Summary", True),
]
TAIL_SECTIONS = [
    ("conceptualization", "Case Conceptualization", True),
    ("diagnostic", "Diagnostic Impressions", True),
    ("recommendations", "Recommendations", True),
]
SIGNATURE_FIELDS = [
    ("sig_name", "Clinician name"),
    ("sig_credentials", "Credentials"),
    ("sig_license", "License number"),
    ("sig_date", "Date signed"),
]

REC_CATEGORIES = {
    "child": ["School / educational", "Home / parenting", "Therapeutic intervention",
              "Medical / psychiatric consultation", "Follow-up and re-evaluation"],
    "adult": ["Therapeutic intervention", "Workplace / academic accommodations",
              "Medical / psychiatric consultation", "Self-management strategies",
              "Follow-up and re-evaluation"],
}

VERIFICATION_NOTES = {
    PUBLISHED: "Scored by the app from the publisher's public scoring rules.",
    VERIFY: "Scored by the app. Cutoffs are pending verification against the official manual.",
    TRANSCRIBED: "Scores computed in the publisher's licensed software and entered by the "
                 "clinician. Not computed by this app.",
}

CONFIDENTIALITY_STATEMENT = (
    "CONFIDENTIAL. This report contains protected health information (PHI) covered by "
    "HIPAA (45 CFR Parts 160 and 164) and applicable state law. It is intended only for "
    "the person(s) or entity to which it is released under a valid authorization or as "
    "otherwise permitted by law. Redisclosure without authorization may be prohibited. "
    "Test scores should be interpreted only by a qualified professional in the context "
    "of the full evaluation. The electronic record of this evaluation is stored encrypted "
    "(AES-256) on the evaluating clinician's device and in encrypted backups, under the "
    "clinician's records retention policy. If you received this report in error, notify "
    "the sender and destroy all copies."
)


def results_key(instrument_key: str) -> str:
    return f"results:{instrument_key}"


def results_title(instrument_key: str) -> str:
    inst = INSTRUMENTS[instrument_key]
    return f"Assessment Results: {inst.name} ({inst.short})"


def layout(template: str, sections: dict, assessed=()) -> list[tuple[str, str]]:
    """Ordered (key, title) list of narrative sections for a template.

    A results section appears if the saved report has text for it or the
    client has at least one scored entry for that instrument (`assessed`)."""
    flow = "A" if template == "child" else "B"
    out = [(k, t) for k, t, _ in HEAD_SECTIONS]
    for ikey in FLOW_ORDER[flow]:
        if ikey == "interview":
            continue
        if results_key(ikey) in sections or ikey in assessed:
            out.append((results_key(ikey), results_title(ikey)))
    out += [(k, t) for k, t, _ in TAIL_SECTIONS]
    return out


def allowed_keys(template: str) -> set[str]:
    flow = "A" if template == "child" else "B"
    keys = {k for k, _, _ in HEAD_SECTIONS + TAIL_SECTIONS}
    keys |= {k for k, _ in SIGNATURE_FIELDS}
    keys |= {results_key(i) for i in FLOW_ORDER[flow] if i != "interview"}
    return keys


_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_sections(sections: dict, template: str) -> dict:
    """Keep only known section keys; strip control characters; cap length."""
    keys = allowed_keys(template)
    out = {}
    for k, v in sections.items():
        if k not in keys:
            continue
        text = _CTRL.sub("", str(v or "")).replace("\r\n", "\n").replace("\r", "\n")
        out[k] = text[:MAX_SECTION_CHARS]
    return out


def placeholders_remaining(sections: dict) -> list[str]:
    return [k for k, v in sections.items() if PLACEHOLDER in (v or "")]


def variant_label(instrument_key: str, variant: str) -> str:
    return dict(INSTRUMENTS[instrument_key].variants).get(variant, variant)


def _fmt_date(iso: str) -> str:
    try:
        return date.fromisoformat(iso).strftime("%m/%d/%Y")
    except (TypeError, ValueError):
        return iso or ""


def auto_sections(client: dict, assessments: list[dict]) -> dict:
    """Build the auto-generated draft text from demographics and scores."""
    template = "child" if client["flow"] == "A" else "adult"
    sections: dict[str, str] = {}

    scored = [a for a in assessments if a["instrument"] != "interview"]
    dates = sorted(a["administered_on"] for a in assessments)
    measures = []
    for ikey in FLOW_ORDER[client["flow"]]:
        if ikey != "interview" and any(a["instrument"] == ikey for a in scored):
            measures.append(f"{INSTRUMENTS[ikey].name} ({INSTRUMENTS[ikey].short})")
    ident = [
        f"Name: {client['first_name']} {client['last_name']}",
        f"Date of birth: {_fmt_date(client['dob'])}",
        f"Age at time of report: {client.get('age', '')}",
    ]
    if client.get("grade"):
        ident.append(f"Grade: {client['grade']}")
    ident.append(f"Assessment pathway: {FLOW_LABELS[client['flow']]}")
    if dates:
        span = _fmt_date(dates[0]) if dates[0] == dates[-1] else \
            f"{_fmt_date(dates[0])} to {_fmt_date(dates[-1])}"
        ident.append(f"Date(s) of assessment: {span}")
    ident.append("Measures administered: " + ("; ".join(measures) if measures else "none recorded"))
    sections["identifying"] = "\n".join(ident)

    interviews = [a for a in assessments if a["instrument"] == "interview"]
    if interviews:
        parts = []
        for a in interviews:
            if len(interviews) > 1:
                parts.append(f"Interview of {_fmt_date(a['administered_on'])}:")
            for row in a["scores"].rows:
                parts.append(f"{row.label}: {row.value}")
            parts.append("")
        sections["interview"] = "\n\n".join(p for p in parts if p).strip()
    else:
        sections["interview"] = (f"{PLACEHOLDER}: no interview notes recorded. Summarize the "
                                 "interview by domain.]")

    for ikey in FLOW_ORDER[client["flow"]]:
        if ikey == "interview":
            continue
        entries = [a for a in scored if a["instrument"] == ikey]
        if not entries:
            continue
        lines = []
        for a in entries:
            s = a["scores"]
            line = f"{variant_label(ikey, a['variant'])}, administered {_fmt_date(a['administered_on'])}"
            line += f": {s.summary}" if s.summary else "."
            lines.append(line)
        lines.append("")
        lines.append(f"{PLACEHOLDER}: interpretation of {INSTRUMENTS[ikey].short} results "
                     "in the context of the full evaluation.]")
        sections[results_key(ikey)] = "\n".join(lines)

    sections["conceptualization"] = (
        "Synthesis:\n"
        f"{PLACEHOLDER}: integrate history, interview, observations, and test results.]\n\n"
        "Strengths and protective factors:\n"
        f"{PLACEHOLDER}.]")
    sections["diagnostic"] = (
        f"{PLACEHOLDER}: diagnostic impressions with codes and supporting criteria, or "
        "state that no diagnosis is given.]")
    sections["recommendations"] = "\n\n".join(
        f"{cat}:\n- {PLACEHOLDER}.]" for cat in REC_CATEGORIES[template])
    for k, _ in SIGNATURE_FIELDS:
        sections[k] = ""  # left blank by design for manual signature
    return sanitize_sections(sections, template)
