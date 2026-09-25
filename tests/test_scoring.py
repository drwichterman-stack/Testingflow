import pytest

from clinassess.scoring import INSTRUMENTS, instruments_for, run_scoring
from clinassess.scoring import asrs, cats, sdq, wsr2


def rows(result):
    return {r.label: r for r in result.rows}


# --------------------------------------------------------------------- SDQ
def test_sdq_reverse_scoring_and_totals():
    # All items "Not True" (0): reversed items (7, 11, 14, 21, 25) score 2.
    resp = {f"item{i}": 0 for i in range(1, 26)}
    r = rows(sdq.score("parent", resp, {}))
    assert r["Emotional Symptoms"].value == "0"
    assert r["Conduct Problems"].value == "2"          # item 7 reversed
    assert r["Hyperactivity/Inattention"].value == "4"  # items 21, 25 reversed
    assert r["Peer Relationship Problems"].value == "4"  # items 11, 14 reversed
    assert r["Prosocial Behaviour"].value == "0"
    assert r["Total Difficulties"].value == "10"
    assert r["Total Difficulties"].band == "Normal"
    assert r["Prosocial Behaviour"].band == "Abnormal"
    assert r["Peer Relationship Problems"].band == "Abnormal"  # parent 4-10


def test_sdq_max_difficulties():
    resp = {f"item{i}": 2 for i in range(1, 26)}
    r = rows(sdq.score("self", resp, {}))
    # Each difficulty scale: 3 regular items (6) + reversed items (0).
    assert r["Conduct Problems"].value == "8"
    assert r["Emotional Symptoms"].value == "10"
    assert r["Total Difficulties"].value == str(10 + 8 + 6 + 6)


def test_sdq_prorating_and_minimum_items():
    resp = {"item3": 2, "item8": 1, "item13": 1}  # 3 of 5 emotional items
    r = rows(sdq.score("parent", resp, {}))
    assert r["Emotional Symptoms"].value == "7"  # round(4/3*5 = 6.67)
    assert r["Conduct Problems"].value == "not scored"
    assert r["Total Difficulties"].value == "not scored"


def test_sdq_band_boundaries_teacher():
    cut = sdq.CUTOFFS["teacher"]["total"]
    from clinassess.scoring.base import band
    assert band(11, cut) == "Normal" and band(12, cut) == "Borderline"
    assert band(15, cut) == "Borderline" and band(16, cut) == "Abnormal"


def test_sdq_impact():
    resp = {"difficulties": 2, "imp_distress": 3, "imp_home": 2, "imp_friends": 1,
            "imp_class": 0, "imp_leisure": 3}
    r = rows(sdq.score("parent", resp, {}))
    assert r["Impact score"].value == "5"  # 2 + 1 + 0 + 0 + 2
    assert r["Impact score"].band == "Abnormal"


# -------------------------------------------------------------------- ASRS
def test_asrs_part_a_thresholds():
    # Items 1-3 at Sometimes (shaded), items 4-6 at Sometimes (not shaded).
    resp = {f"item{i}": 2 for i in range(1, 7)}
    r = rows(asrs.score("self", resp, {"age": 30}))
    assert r["Part A shaded items (of 6)"].value == "3"
    assert r["Part A shaded items (of 6)"].band == "Negative screen"
    resp["item4"] = 3
    r = rows(asrs.score("self", resp, {"age": 30}))
    assert r["Part A shaded items (of 6)"].value == "4"
    assert r["Part A shaded items (of 6)"].band.startswith("Positive")


def test_asrs_totals_and_minor_warning():
    resp = {f"item{i}": 4 for i in range(1, 19)}
    res = asrs.score("self", resp, {"age": 15})
    r = rows(res)
    assert r["Total raw (0-72)"].value == "72"
    assert r["Part B shaded items (of 12)"].value == "12"
    assert any("18+" in w for w in res.warnings)


def test_asrs_indeterminate_when_missing():
    resp = {"item1": 4, "item2": 4, "item3": 4}
    r = rows(asrs.score("self", resp, {"age": 30}))
    assert r["Part A shaded items (of 6)"].band.startswith("Indeterminate")


# -------------------------------------------------------------------- CATS
def test_cats_bands():
    resp = {f"item{i}": 1 for i in range(1, 21)}  # total 20
    r = rows(cats.score("self_7_17", resp, {}))
    assert r["Symptom total (0-60)"].value == "20"
    assert r["Symptom total (0-60)"].band == "Moderate trauma-related distress"
    resp["item1"] = 2
    assert rows(cats.score("self_7_17", resp, {}))["Symptom total (0-60)"].band == "Probable PTSD"


def test_cats_young_version_has_no_band():
    resp = {f"item{i}": 3 for i in range(1, 17)}
    r = rows(cats.score("caregiver_3_6", resp, {}))
    assert r["Symptom total (0-48)"].value == "48"
    assert r["Symptom total (0-48)"].band == ""


# ------------------------------------------------------------------ WSR-II
def test_wsr2_symptom_counts_age_threshold():
    resp = {f"adhd_in_{i}": 2 for i in range(1, 6)}  # 5 present
    resp.update({f"adhd_in_{i}": 1 for i in range(6, 10)})
    young = rows(wsr2.score("parent", resp, {"age": 12}))
    adult = rows(wsr2.score("self", resp, {"age": 25}))
    assert young["Symptoms present (rated 2-3)"].band.startswith("Below")
    assert adult["Symptoms present (rated 2-3)"].band.startswith("Meets")


# ---------------------------------------------------------------- licensed
def test_mmpi3_range_validation_and_flag():
    with pytest.raises(ValueError):
        run_scoring("mmpi3", "standard", {"RCd_t": 130}, {})
    r = run_scoring("mmpi3", "standard", {"RCd_t": 72, "RC1_t": 50}, {})
    assert "RCd" in r.summary and "RC1" not in r.summary


def test_conners4_bands():
    r = rows(run_scoring("conners4", "parent", {"HYP_t": 67, "IED_t": 71, "ANX_t": 50}, {}))
    assert r["Hyperactivity"].band == "Elevated"
    assert r["Inattention/Executive Dysfunction"].band == "Very Elevated"
    assert r["Anxious Thoughts"].band == "Average"


def test_choice_validation_rejects_bad_codes():
    with pytest.raises(ValueError):
        run_scoring("sdq", "parent", {"item1": 5}, {})


# ------------------------------------------------------------------- flows
def test_flow_membership_and_asrs_gate():
    a = [i.key for i in instruments_for("A", False)]
    assert a == ["interview", "sdq", "cats", "conners4", "tova", "wsr2"]
    assert "asrs" in [i.key for i in instruments_for("A", True)]
    b = [i.key for i in instruments_for("B", False)]
    assert b == ["interview", "mmpi3", "brown", "wsr2", "asrs", "tova"]


def test_every_instrument_scores_empty_form():
    for inst in INSTRUMENTS.values():
        for v, _ in inst.variants:
            inst.score(v, {}, {"age": 10})
