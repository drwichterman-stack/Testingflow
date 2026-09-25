"""Report editor: review and edit every narrative section before PDF export.

Locked (read-only): section titles, score tables, page header, page
numbering, confidentiality statement. Editable: all narrative text and
the signature fields.
"""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

from PySide6.QtWidgets import (QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                             QPushButton, QStackedWidget, QTextBrowser, QVBoxLayout, QWidget)

from .. import config, report
from .common import PasswordDialog, confirm, error, info, wrap_label


class ReportEditor(QDialog):
    def __init__(self, parent, service, client_id: int):
        super().__init__(parent)
        self.service = service
        self.client_id = client_id
        self.client = service.get_client(client_id, log=False)
        self.resize(1150, 800)
        self.setWindowTitle(f"Report: {self.client['first_name']} {self.client['last_name']}")

        self.status = QLabel()
        self.banner = wrap_label("")
        self.banner.setStyleSheet("background:#fff4d6; color:#5a4300; padding:6px;")
        self.sections_list = QListWidget()
        self.sections_list.setMaximumWidth(300)
        self.stack = QStackedWidget()
        self.sections_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        body = QHBoxLayout()
        body.addWidget(self.sections_list)
        body.addWidget(self.stack, 1)

        buttons = QHBoxLayout()
        for text, slot in (("Save version", self.save), ("Revert to auto-generated", self.revert),
                           ("Version history", self.history),
                           ("Generate PDF", self.export_pdf), ("Close", self.close_editor)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            buttons.addWidget(b)

        lay = QVBoxLayout(self)
        lay.addWidget(self.status)
        lay.addWidget(self.banner)
        lay.addLayout(body, 1)
        lay.addLayout(buttons)
        self.load(service.open_report(client_id))

    # ------------------------------------------------------------------
    def load(self, rep: dict):
        self.rep = rep
        self.editors: dict[str, QPlainTextEdit | QLineEdit] = {}
        self.sections_list.clear()
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        assessments = self.service.list_assessments(self.client_id)
        assessed = {a["instrument"] for a in assessments if a["instrument"] != "interview"}
        header = QTextBrowser()
        header.setHtml(
            f"<h3>{escape(report.TEMPLATE_TITLES[rep['template']])}</h3>"
            f"<p><b>Page header (locked):</b> Patient Name: {escape(self.client['first_name'])} "
            f"{escape(self.client['last_name'])} | Page: N (top right, every page)</p>"
            "<p><b>Page footer (locked):</b> Generated: date | CONFIDENTIAL | Clinician: "
            "blank line</p><p><b>Final page (locked):</b> signature block and confidentiality "
            f"notice.</p><p><b>Confidentiality notice:</b><br>"
            f"{escape(report.CONFIDENTIALITY_STATEMENT)}</p>")
        self._add_page("Page layout (locked)", header)

        for key, title in report.layout(rep["template"], rep["sections"], assessed):
            page = QWidget()
            v = QVBoxLayout(page)
            t = QLabel(f"<h3>{escape(title)}</h3>")
            v.addWidget(t)
            if key.startswith("results:"):
                ikey = key.split(":", 1)[1]
                tbl = QTextBrowser()
                tbl.setHtml(self._score_html([a for a in assessments if a["instrument"] == ikey]))
                tbl.setMaximumHeight(260)
                v.addWidget(QLabel("Score tables (locked; edit the assessment entry to change "
                                   "a score):"))
                v.addWidget(tbl)
                v.addWidget(QLabel("Interpretation (editable):"))
            ed = QPlainTextEdit(rep["sections"].get(key, ""))
            v.addWidget(ed, 1)
            v.addWidget(QLabel("Formatting: blank line = new paragraph; '- ' = bullet; a short "
                               "line ending in ':' = subheading."))
            self.editors[key] = ed
            short = (f"Results: {report.INSTRUMENTS[key.split(':', 1)[1]].short}"
                     if key.startswith("results:") else title)
            self._add_page(short, page)

        sig = QWidget()
        form = QFormLayout(sig)
        form.addRow(QLabel("<h3>Signature block</h3>"))
        form.addRow(wrap_label("Left blank by default for a manual signature. Any value "
                               "entered here is printed in the signature block."))
        for key, label in report.SIGNATURE_FIELDS:
            ed = QLineEdit(rep["sections"].get(key, ""))
            self.editors[key] = ed
            form.addRow(label + ":", ed)
        self._add_page("Signature", sig)
        self.sections_list.setCurrentRow(1)
        self._update_status()

    def _add_page(self, title: str, widget: QWidget):
        self.sections_list.addItem(QListWidgetItem(title))
        self.stack.addWidget(widget)

    @staticmethod
    def _score_html(entries: list[dict]) -> str:
        out = []
        for a in entries:
            s = a["scores"]
            out.append(f"<p><b>{escape(report.variant_label(a['instrument'], a['variant']))}, "
                       f"{escape(a['administered_on'])}</b> <i>({s.verification})</i></p>"
                       "<table border='1' cellspacing='0' cellpadding='2'>")
            for r in s.rows:
                out.append(f"<tr><td>{escape(r.section)}</td><td>{escape(r.label)}</td>"
                           f"<td>{escape(r.value[:200])}</td><td>{escape(r.band)}</td></tr>")
            out.append("</table>")
        return "".join(out) or "<p>No entries.</p>"

    def _update_status(self):
        r = self.rep
        self.status.setText(f"Version {r['version_no']} ({r['source']}) saved "
                            f"{r['created_at']} by {r['created_by']}")
        notes = []
        if self.service.report_is_stale(self.client_id):
            notes.append("Scores or demographics changed after this version was saved. "
                         "Score tables in the PDF always show current scores; review the "
                         "narrative, or use 'Revert to auto-generated' to rebuild it.")
        left = report.placeholders_remaining(self.current_sections())
        if left:
            notes.append(f"{len(left)} section(s) still contain '[Clinician to complete' "
                         "prompts.")
        self.banner.setText("\n".join(notes))
        self.banner.setVisible(bool(notes))

    def current_sections(self) -> dict:
        return {k: (e.toPlainText() if isinstance(e, QPlainTextEdit) else e.text())
                for k, e in self.editors.items()}

    def is_dirty(self) -> bool:
        cur = self.current_sections()
        return any(cur.get(k, "") != self.rep["sections"].get(k, "") for k in cur)

    # ------------------------------------------------------------------
    def save(self) -> bool:
        if not self.is_dirty():
            info(self, "No changes to save.")
            return True
        self.service.save_report(self.client_id, self.current_sections(), source="edited")
        self.load(self.service.latest_report(self.client_id))
        return True

    def revert(self):
        if not confirm(self, "Replace the text with a fresh auto-generated draft from the current "
                             "scores? Your edited versions stay in the version history."):
            return
        self.service.revert_report_to_auto(self.client_id)
        self.load(self.service.latest_report(self.client_id))

    def history(self):
        rows = self.service.report_history(self.client_id)
        lines = [f"v{r['version_no']}  {r['source']:<9} {r['created_at']}  {r['created_by']}"
                 for r in rows]
        info(self, "Report versions (newest first):\n\n" + "\n".join(lines),
             "Version history")

    def export_pdf(self):
        if self.is_dirty():
            if not confirm(self, "Save your edits as a new version before generating the PDF?"):
                return
            self.save()
        left = report.placeholders_remaining(self.rep["sections"])
        if left and not confirm(self, f"{len(left)} section(s) still contain '[Clinician to "
                                      "complete' prompts. Generate the PDF anyway?"):
            return
        dlg = PasswordDialog(
            self, "Encrypt PDF",
            "The PDF is encrypted with AES-256 and printing is disabled. Choose a password to "
            "open it. Give the password to the recipient by a separate channel (for example, "
            "by phone), never in the same email as the file.")
        if not dlg.exec():
            return
        default = config.reports_dir() / (
            f"{self.client['ref_code']}_report_{date.today().isoformat()}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Save encrypted PDF", str(default),
                                              "PDF (*.pdf)")
        if not path:
            return
        try:
            self.service.export_report_pdf(self.client_id, Path(path), dlg.password())
        except (ValueError, OSError) as exc:
            return error(self, f"PDF not created: {exc}")
        info(self, f"Encrypted PDF saved:\n{path}\n\nThe file name uses the client reference "
                   "code, not the name, so PHI is not exposed in file listings.")

    def close_editor(self):
        if self.is_dirty() and confirm(self, "Save your edits as a new version before closing?"):
            self.save()
        self.accept()
