"""Camera capture dialog, driven headlessly with synthetic snapped photos.

No camera exists on the test machine, so photos are handed to the dialog
the way a snap would (add_photo). The real camera path needs a person;
see docs/CAMERA_FORM_CAPTURE.md.
"""

import os
import random

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from .omr_synth import PAGE, make_form, photograph  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def yes(monkeypatch):
    from clinassess.ui import assessment_form, capture_form
    monkeypatch.setattr(capture_form, "confirm", lambda *a, **k: True)
    monkeypatch.setattr(assessment_form, "confirm", lambda *a, **k: True)


def _sdq_photo(answers, seed):
    rng = random.Random(seed)
    im, grid = make_form(answers, 3, mark="x", rng=rng)
    page = [(0, 0), (PAGE[0], 0), PAGE, (0, PAGE[1])]
    arr, _ = photograph(im, page + grid, angle=rng.uniform(-6, 6), perspective=0.02, blur=1.0,
                        noise=4, light=0.3, jpeg=80, scale=0.45, seed=seed)
    return arr, np.array(grid) / PAGE


def test_capture_fill_review_and_save(qapp, svc, client_a, yes):
    from clinassess import omr
    from clinassess.ui.assessment_form import AssessmentDialog
    from clinassess.ui.capture_form import CaptureFormDialog

    rng = random.Random(2)
    answers = [rng.randrange(3) for _ in range(25)]
    answers[6] = None
    photo, frac = _sdq_photo(answers, 2)

    form = AssessmentDialog(None, svc, svc.get_client(client_a), "sdq")
    assert form.capture_btn is not None
    fields = form.inst.fields_for("parent")
    dlg = CaptureFormDialog(form, svc, form.inst, "parent", fields)
    assert "No camera found" in dlg.cam_status.text() or dlg.cam_status.text()
    idx = dlg.add_photo(photo)
    assert dlg.page_found[idx]
    page = dlg.pages[idx]
    dlg.set_block_quad(0, idx, frac * [page.shape[1], page.shape[0]])
    assert len(dlg.blocks[0].items) == 25
    dlg._apply()
    assert dlg.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert not dlg.pages  # photo discarded

    assert form.apply_capture(dlg.results, dlg.counts)
    for i, want in enumerate(answers, start=1):
        got = form.widgets[f"item{i}"].value()
        read = dlg.results[f"item{i}"]
        if read.status == omr.OK:
            assert got == want
        else:
            assert form.widgets[f"item{i}"].flagged
    assert form.widgets["item7"].flagged and form.widgets["item7"].value() is None
    assert not form.review_banner.isHidden()

    # Checking a flagged item clears its flag.
    form.widgets["item7"].buttons[0].click()
    assert not form.widgets["item7"].flagged and "item7" not in form.review_flags
    for k in list(form.review_flags):
        form.widgets[k].clear_flag()
    for i, want in enumerate(answers, start=1):  # the reviewer corrects anything left
        if want is not None and form.widgets[f"item{i}"].value() != want:
            form.widgets[f"item{i}"].buttons[want].click()
    form._save()
    saved = svc.list_assessments(client_a)[0]
    assert saved["instrument"] == "sdq"
    entries, _ = svc.read_audit()
    actions = [e["action"] for e in entries]
    assert "FORM_CAPTURE" in actions and "SCAN_LAYOUT_SAVE" in actions
    create = [e for e in entries if e["action"] == "ASSESSMENT_CREATE"][-1]
    assert create["details"]["camera_capture"] is True
    assert create["details"]["flags_unchecked"] == 0
    # The audit trail holds counts, never responses.
    cap = [e for e in entries if e["action"] == "FORM_CAPTURE"][-1]
    assert set(cap["details"]) <= {"instrument", "variant", "ok", "check", "blank",
                                   "multiple", "pages", "items"}


def test_saved_outline_reused_on_next_capture(qapp, svc, client_a, yes):
    from clinassess.ui.assessment_form import AssessmentDialog
    from clinassess.ui.capture_form import CaptureFormDialog

    form = AssessmentDialog(None, svc, svc.get_client(client_a), "sdq")
    fields = form.inst.fields_for("parent")
    first, frac = _sdq_photo([0, 1, 2, 1, 0] * 5, 4)
    dlg = CaptureFormDialog(form, svc, form.inst, "parent", fields)
    idx = dlg.add_photo(first)
    p = dlg.pages[idx]
    dlg.set_block_quad(0, idx, frac * [p.shape[1], p.shape[0]])
    dlg._apply()

    answers = [2, 2, 1, 0, 0] * 5
    second, _ = _sdq_photo(answers, 9)  # a different, tilted snap
    dlg2 = CaptureFormDialog(form, svc, form.inst, "parent", fields)
    dlg2.add_photo(second)
    items = dlg2.blocks[0].items
    assert len(items) == 25  # read with no outlining
    ok = [(it, want) for it, want in zip(items, answers) if it.status == "ok"]
    assert len(ok) >= 20 and all(it.code == want for it, want in ok)
    dlg2.reject()


def test_split_blocks_and_safety_flags(qapp, svc, client_a, yes):
    from clinassess import omr
    from clinassess.ui.assessment_form import AssessmentDialog
    from clinassess.ui.capture_form import CaptureFormDialog

    form = AssessmentDialog(None, svc, svc.get_client(client_a), "wsr2")
    fields = form.inst.fields_for(form._variant())
    dlg = CaptureFormDialog(form, svc, form.inst, form._variant(), fields)
    n = len(dlg.blocks)
    dlg.table.selectRow(0)
    dlg._split_before("att_5")
    assert len(dlg.blocks) == n + 1
    assert [f.key for f in dlg.blocks[1].fields][0] == "att_5"
    dlg.reject()
    # A clear read of a suicide item is still flagged for a person to confirm.
    form.apply_capture({"sui_1": omr.ItemRead("sui_1", 0, omr.OK),
                        "att_1": omr.ItemRead("att_1", 2, omr.OK)})
    assert form.widgets["sui_1"].flagged and form.widgets["sui_1"].value() == 0
    assert not form.widgets["att_1"].flagged


def test_no_capture_button_for_licensed_forms(qapp, svc, client_a):
    from clinassess.ui.assessment_form import AssessmentDialog
    form = AssessmentDialog(None, svc, svc.get_client(client_a), "conners4")
    assert form.capture_btn is None
