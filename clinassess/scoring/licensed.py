"""Licensed instruments: MMPI-3, Conners 4, Brown EF/A Scales, TOVA.

These tests are scored with proprietary normative tables that the
publishers license and do not release. This app does NOT compute their
standard scores. The clinician scores each test in the publisher's
software (Q-global, MHS Online Assessment Center+, TOVA software) and
types the resulting scores here. The app:
  * checks each entry against the valid range for its metric,
  * records who entered it and when (audit trail),
  * applies only interpretive ranges printed in the publisher's manual
    (flagged VERIFY), and
  * carries the scores into the report.
"""

from __future__ import annotations

from .base import TRANSCRIBED, Field, Instrument, ScoreResult, ScoreRow, band


def _num(v):
    if v in (None, ""):
        return None
    f = float(v)
    return int(f) if f == int(f) else f


def _t_fields(scales, section, with_pct=False):
    fs = []
    for code, label in scales:
        fs.append(Field(f"{code}_t", f"{label} T", "int", minimum=20, maximum=120,
                        section=section))
        if with_pct:
            fs.append(Field(f"{code}_pct", f"{label} %ile", "int", minimum=1, maximum=99,
                            section=section))
    return fs


def _common_tail(section="Publisher report"):
    return [Field("validity_notes", "Validity / response style (from publisher report)",
                  "text", section=section),
            Field("interpretation", "Publisher interpretation summary", "text",
                  section=section)]


def _add_text_rows(res, responses):
    for key, label in (("validity_notes", "Validity / response style"),
                       ("interpretation", "Publisher interpretation")):
        t = (responses.get(key) or "").strip()
        if t:
            res.rows.append(ScoreRow("Publisher report", label, t))


# ---------------------------------------------------------------------------
# MMPI-3 (Ben-Porath & Tellegen, 2020; University of Minnesota Press)
# ---------------------------------------------------------------------------

MMPI3_VALIDITY = [("CRIN", "CRIN"), ("VRIN", "VRIN"), ("TRIN", "TRIN"), ("F", "F"),
                  ("Fp", "Fp"), ("Fs", "Fs"), ("FBS", "FBS"), ("RBS", "RBS"),
                  ("L", "L"), ("K", "K")]
MMPI3_GROUPS = [
    ("Higher-Order", [("EID", "EID Emotional/Internalizing Dysfunction"),
                      ("THD", "THD Thought Dysfunction"),
                      ("BXD", "BXD Behavioral/Externalizing Dysfunction")]),
    ("Restructured Clinical", [("RCd", "RCd Demoralization"),
                               ("RC1", "RC1 Somatic Complaints"),
                               ("RC2", "RC2 Low Positive Emotions"),
                               ("RC3", "RC3 Cynicism"),
                               ("RC4", "RC4 Antisocial Behavior"),
                               ("RC6", "RC6 Ideas of Persecution"),
                               ("RC7", "RC7 Dysfunctional Negative Emotions"),
                               ("RC8", "RC8 Aberrant Experiences"),
                               ("RC9", "RC9 Hypomanic Activation")]),
    ("SP: Somatic/Cognitive", [("MLS", "MLS Malaise"), ("NUC", "NUC Neurological Complaints"),
                               ("EAT", "EAT Eating Concerns"),
                               ("COG", "COG Cognitive Complaints")]),
    ("SP: Internalizing", [("SUI", "SUI Suicidal/Death Ideation"),
                           ("HLP", "HLP Helplessness/Hopelessness"),
                           ("SFD", "SFD Self-Doubt"), ("NFC", "NFC Inefficacy"),
                           ("STR", "STR Stress"), ("WRY", "WRY Worry"),
                           ("CMP", "CMP Compulsivity"),
                           ("ARX", "ARX Anxiety-Related Experiences"),
                           ("ANP", "ANP Anger Proneness"),
                           ("BRF", "BRF Behavior-Restricting Fears")]),
    ("SP: Externalizing", [("FML", "FML Family Problems"),
                           ("JCP", "JCP Juvenile Conduct Problems"),
                           ("SUB", "SUB Substance Abuse"), ("IMP", "IMP Impulsivity"),
                           ("ACT", "ACT Activation"), ("AGG", "AGG Aggression"),
                           ("CYN", "CYN Cynicism")]),
    ("SP: Interpersonal", [("SFI", "SFI Self-Importance"), ("DOM", "DOM Dominance"),
                           ("DSF", "DSF Disaffiliativeness"),
                           ("SAV", "SAV Social Avoidance"), ("SHY", "SHY Shyness")]),
    ("PSY-5", [("AGGR", "AGGR-r Aggressiveness"), ("PSYC", "PSYC-r Psychoticism"),
               ("DISC", "DISC-r Disconstraint"),
               ("NEGE", "NEGE-r Negative Emotionality/Neuroticism"),
               ("INTR", "INTR-r Introversion/Low Positive Emotionality")]),
]
MMPI3_TRIN_DIR = [(0, "T (true direction)"), (1, "F (false direction)"), (2, "n/a")]


def mmpi3_fields(variant: str) -> list[Field]:
    fs = [Field("CNS", "CNS (Cannot Say) raw count", "int", minimum=0, maximum=335,
                section="Validity")]
    fs += _t_fields(MMPI3_VALIDITY, "Validity")
    fs.append(Field("TRIN_dir", "TRIN direction", "choice", MMPI3_TRIN_DIR, section="Validity"))
    for section, scales in MMPI3_GROUPS:
        fs += _t_fields(scales, section)
    return fs + _common_tail()


def mmpi3_score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=TRANSCRIBED)
    cns = _num(responses.get("CNS"))
    if cns is not None:
        res.rows.append(ScoreRow("Validity", "CNS (Cannot Say)", str(cns)))
    for code, label in MMPI3_VALIDITY:
        t = _num(responses.get(f"{code}_t"))
        if t is not None:
            val = f"{t}"
            if code == "TRIN" and responses.get("TRIN_dir") in (0, 1):
                val += "T" if responses["TRIN_dir"] == 0 else "F"
            res.rows.append(ScoreRow("Validity", label, val, "",
                                     "interpret per MMPI-3 Manual"))
    elevated = []
    for section, scales in MMPI3_GROUPS:
        for code, label in scales:
            t = _num(responses.get(f"{code}_t"))
            if t is None:
                continue
            b = "T >= 65" if t >= 65 else ""
            if b:
                elevated.append(code)
            res.rows.append(ScoreRow(section, label, str(t), b))
    _add_text_rows(res, responses)
    res.summary = ("Substantive scales at T >= 65: " + ", ".join(elevated) + "."
                   if elevated else "No substantive scale at T >= 65.")
    res.warnings.append("T >= 65 is the general MMPI-3 threshold for clinically significant "
                        "elevation. Some scales have other interpretive ranges; see the "
                        "MMPI-3 Manual and the Q-global report.")
    return res


MMPI3 = Instrument(
    key="mmpi3", name="Minnesota Multiphasic Personality Inventory-3", short="MMPI-3",
    flows=("B",), version="mmpi3-entry-1", verification=TRANSCRIBED,
    variants=[("standard", "Standard (Q-global)")], fields_for=mmpi3_fields,
    score=mmpi3_score,
    description="Enter T-scores from the Q-global Score or Interpretive Report.",
)

# ---------------------------------------------------------------------------
# Conners 4 (Conners, 2022; MHS)
# ---------------------------------------------------------------------------

CONNERS4_GROUPS = [
    ("Content Scales", [("IED", "Inattention/Executive Dysfunction"),
                        ("HYP", "Hyperactivity"), ("IMP", "Impulsivity"),
                        ("EMD", "Emotional Dysregulation"), ("DEP", "Depressed Mood"),
                        ("ANX", "Anxious Thoughts")]),
    ("Impairment & Functional Outcome", [("SCH", "Schoolwork"),
                                         ("PEER", "Peer Interactions"),
                                         ("FAM", "Family Life")]),
    ("DSM Symptom Scales", [("DSMIN", "ADHD Inattentive Symptoms"),
                            ("DSMHI", "ADHD Hyperactive/Impulsive Symptoms"),
                            ("DSMTOT", "Total ADHD Symptoms"),
                            ("ODD", "Oppositional Defiant Disorder Symptoms"),
                            ("CD", "Conduct Disorder Symptoms")]),
]
# Conners 4 Manual T-score guidelines. VERIFY against the manual.
CONNERS4_BANDS = [(70, 120, "Very Elevated"), (65, 69, "Elevated"), (60, 64, "High Average"),
                  (40, 59, "Average"), (20, 39, "Low")]


def conners4_fields(variant: str) -> list[Field]:
    fs = []
    for section, scales in CONNERS4_GROUPS:
        fs += _t_fields(scales, section, with_pct=True)
    fs.append(Field("ADHDI_prob", "Conners 4-ADHD Index probability (%)", "int",
                    minimum=0, maximum=100, section="ADHD Index"))
    fs.append(Field("critical", "Critical / screener items endorsed", "text",
                    section="Publisher report"))
    return fs + _common_tail()


def conners4_score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=TRANSCRIBED)
    elevated = []
    for section, scales in CONNERS4_GROUPS:
        for code, label in scales:
            t = _num(responses.get(f"{code}_t"))
            if t is None:
                continue
            pct = _num(responses.get(f"{code}_pct"))
            b = band(t, CONNERS4_BANDS)
            if t >= 65:
                elevated.append(label)
            res.rows.append(ScoreRow(section, label, f"T {t}" + (f", {pct}th %ile" if pct else ""), b))
    p = _num(responses.get("ADHDI_prob"))
    if p is not None:
        res.rows.append(ScoreRow("ADHD Index", "ADHD Index probability", f"{p}%"))
    crit = (responses.get("critical") or "").strip()
    if crit:
        res.rows.append(ScoreRow("Publisher report", "Critical items", crit))
    _add_text_rows(res, responses)
    res.summary = ("Elevated (T >= 65): " + ", ".join(elevated) + "."
                   if elevated else "No scale at T >= 65.")
    if variant == "teacher" and responses.get("FAM_t") not in (None, ""):
        res.warnings.append("Family Life is not part of the teacher form; check entry.")
    return res


CONNERS4 = Instrument(
    key="conners4", name="Conners 4th Edition", short="Conners 4",
    flows=("A",), version="conners4-entry-1", verification=TRANSCRIBED,
    variants=[("self", "Self-report (ages 8-18)"), ("parent", "Parent report"),
              ("teacher", "Teacher report")],
    fields_for=conners4_fields, score=conners4_score,
    description="Enter T-scores and percentiles from the MHS report. "
                "Add one entry per informant.",
)

# ---------------------------------------------------------------------------
# Brown Executive Function/Attention Scales (Brown, 2019; Pearson)
# ---------------------------------------------------------------------------

BROWN_CLUSTERS = [("ACT", "Activation"), ("FOC", "Focus"), ("EFF", "Effort"),
                  ("EMO", "Emotion"), ("MEM", "Memory"), ("ACN", "Action"),
                  ("TOT", "Total Composite")]


def brown_fields(variant: str) -> list[Field]:
    return _t_fields(BROWN_CLUSTERS, "Clusters", with_pct=True) + _common_tail()


def brown_score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=TRANSCRIBED)
    for code, label in BROWN_CLUSTERS:
        t = _num(responses.get(f"{code}_t"))
        if t is None:
            continue
        pct = _num(responses.get(f"{code}_pct"))
        res.rows.append(ScoreRow("Clusters", label,
                                 f"T {t}" + (f", {pct}th %ile" if pct else "")))
    _add_text_rows(res, responses)
    tot = _num(responses.get("TOT_t"))
    res.summary = f"Total Composite T {tot}." if tot is not None else ""
    res.warnings.append("Descriptive ranges are not applied automatically. Use the "
                        "classification printed in the Q-global report.")
    return res


BROWN = Instrument(
    key="brown", name="Brown Executive Function/Attention Scales", short="Brown EF/A",
    flows=("B",), version="brown-entry-1", verification=TRANSCRIBED,
    variants=[("self", "Self-report"), ("parent", "Parent report"),
              ("teacher", "Teacher report"), ("add_legacy", "Brown ADD Scales (legacy)")],
    fields_for=brown_fields, score=brown_score,
    description="Enter cluster T-scores and percentiles from Q-global.",
)

# ---------------------------------------------------------------------------
# TOVA (The TOVA Company)
# ---------------------------------------------------------------------------

TOVA_VARS = [("RTV", "Response Time Variability"), ("RT", "Response Time"),
             ("COM", "Commission Errors"), ("OMI", "Omission Errors"), ("DPR", "d' (D Prime)")]
TOVA_PERIODS = [("h1", "Half 1"), ("h2", "Half 2"), ("tot", "Total")]


def tova_fields(variant: str) -> list[Field]:
    fs = []
    for code, label in TOVA_VARS:
        for p, plabel in TOVA_PERIODS:
            fs.append(Field(f"{code}_{p}", f"{label}: {plabel} SS", "int",
                            minimum=0, maximum=200, section=label))
    fs.append(Field("ACS", "Attention Comparison Score (ACS)", "float",
                    minimum=-20, maximum=20, section="Summary"))
    return fs + _common_tail()


def tova_score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=TRANSCRIBED)
    for code, label in TOVA_VARS:
        parts = []
        for p, plabel in TOVA_PERIODS:
            v = _num(responses.get(f"{code}_{p}"))
            if v is not None:
                parts.append(f"{plabel} {v}")
        if parts:
            res.rows.append(ScoreRow("Standard scores (M=100, SD=15)", label, "; ".join(parts)))
    acs = _num(responses.get("ACS"))
    if acs is not None:
        res.rows.append(ScoreRow("Summary", "Attention Comparison Score", str(acs)))
    _add_text_rows(res, responses)
    res.summary = f"ACS {acs}." if acs is not None else ""
    res.warnings.append("Interpretive classification comes from the TOVA report; "
                        "the app does not classify TOVA scores.")
    return res


TOVA = Instrument(
    key="tova", name="Test of Variables of Attention", short="TOVA",
    flows=("A", "B"), version="tova-entry-1", verification=TRANSCRIBED,
    variants=[("visual", "Visual"), ("auditory", "Auditory")],
    fields_for=tova_fields, score=tova_score,
    description="Enter standard scores from the TOVA report.",
)
