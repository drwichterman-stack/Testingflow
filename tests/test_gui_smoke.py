"""Headless GUI smoke test (Qt offscreen platform)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_windows_build_and_score(qapp, svc, client_a):
    from clinassess.ui.assessment_form import AssessmentDialog
    from clinassess.ui.main_window import MainWindow
    from clinassess.ui.report_editor import ReportEditor
    from clinassess.ui.admin import AuditDialog

    locks = []
    w = MainWindow(svc, lambda *a, **k: locks.append(a))
    w.refresh_title()
    w.search()
    assert w.results.rowCount() == 1
    w._show_client(client_a)
    labels = [a.text() for a in w.add_menu.actions()]
    assert any(t.startswith("SDQ") for t in labels)
    assert not any(t.startswith("ASRS") for t in labels)  # gated off for this client

    dlg = AssessmentDialog(w, svc, w.client, "sdq")
    for i in range(1, 26):
        combo = dlg.widgets[f"item{i}"]
        combo.setCurrentIndex(combo.findData(1))
    dlg._refresh_preview()
    assert "Total Difficulties" in dlg.preview.toPlainText()
    dlg.variant.setCurrentIndex(1)  # teacher: rebuild keeps item values
    assert dlg.widgets["item3"].currentData() == 1
    dlg._save()
    assert svc.list_assessments(client_a)[0]["variant"] == "teacher"

    ed = ReportEditor(w, svc, client_a)
    ed.editors["diagnostic"].setPlainText("Clinician text.")
    assert ed.is_dirty()
    ed.save()
    assert svc.latest_report(client_a)["sections"]["diagnostic"] == "Clinician text."
    assert "results:sdq" in ed.editors

    AuditDialog(w, svc)
