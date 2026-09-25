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

    from clinassess.ui import theme
    from clinassess.ui.help import AboutDialog, PreferencesDialog, GettingStartedDialog
    theme.apply(qapp)
    locks = []
    w = MainWindow(svc, lambda *a, **k: locks.append(a))
    w.start()
    assert w.dashboard.stats["active"].text() == "1"
    cp = w.clients
    cp.search()
    assert cp.results.rowCount() == 1
    w.open_client(client_a)
    labels = [a.text().strip() for a in cp.add_menu.actions()]
    assert any(t.startswith("SDQ") for t in labels)
    assert any(t.startswith("SNAP-IV") for t in labels)
    assert not any(t.startswith("ASRS") for t in labels)  # gated off for this client

    dlg = AssessmentDialog(w, svc, cp.client, "sdq")
    for i in range(1, 26):
        dlg.widgets[f"item{i}"].buttons[1].click()
    dlg._refresh_preview()
    assert "Total Difficulties" in dlg.preview.toPlainText()
    dlg.variant.setCurrentIndex(1)  # teacher: rebuild keeps item values
    assert dlg.widgets["item3"].value() == 1
    dlg.widgets["item3"].buttons[1].click()  # clicking again clears
    assert dlg.widgets["item3"].value() is None
    dlg.widgets["item3"].buttons[2].click()
    dlg._save()
    assert svc.list_assessments(client_a)[0]["variant"] == "teacher"

    ed = ReportEditor(w, svc, client_a)
    ed.editors["diagnostic"].setPlainText("Clinician text.")
    assert ed.is_dirty()
    ed.save()
    assert svc.latest_report(client_a)["sections"]["diagnostic"] == "Clinician text."
    assert "results:sdq" in ed.editors

    AuditDialog(w, svc)
    AboutDialog(w)
    GettingStartedDialog(w)
    PreferencesDialog(w, svc, lambda: None)
    w.toast("ok")
    w.go_dashboard()
    assert w.dashboard.stats["drafts"].text() == "1"
