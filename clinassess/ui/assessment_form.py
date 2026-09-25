"""Data-entry form for one assessment, built from the instrument definition."""

from __future__ import annotations

from html import escape

from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import (QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                             QScrollArea, QSplitter, QTextBrowser, QVBoxLayout, QWidget)

from ..scoring import INSTRUMENTS
from ..scoring.base import Field
from .common import error


class AssessmentDialog(QDialog):
    def __init__(self, parent, service, client: dict, instrument_key: str,
                 existing: dict | None = None):
        super().__init__(parent)
        self.service = service
        self.client = client
        self.inst = INSTRUMENTS[instrument_key]
        self.existing = existing
        self.widgets: dict[str, QWidget] = {}
        self.values: dict = dict(existing["responses"]) if existing else {}
        self.setWindowTitle(f"{self.inst.name}: {client['first_name']} {client['last_name']}")
        self.resize(1100, 760)

        top = QHBoxLayout()
        self.variant = QComboBox()
        for k, label in self.inst.variants:
            self.variant.addItem(label, k)
        if existing:
            self.variant.setCurrentIndex(
                [k for k, _ in self.inst.variants].index(existing["variant"]))
        self.date = QDateEdit(calendarPopup=True)
        self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setDate(QDate.fromString(existing["administered_on"], "yyyy-MM-dd")
                          if existing else QDate.currentDate())
        top.addWidget(QLabel("Form / informant:"))
        top.addWidget(self.variant, 1)
        top.addWidget(QLabel("Date administered:"))
        top.addWidget(self.date)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.preview = QTextBrowser()
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.scroll)
        split.addWidget(self.preview)
        split.setSizes([650, 450])

        lay = QVBoxLayout(self)
        desc = QLabel(self.inst.description)
        desc.setWordWrap(True)
        lay.addWidget(desc)
        lay.addLayout(top)
        lay.addWidget(split, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        self._timer = QTimer(self, singleShot=True, interval=250)
        self._timer.timeout.connect(self._refresh_preview)
        self.variant.currentIndexChanged.connect(self._build_form)
        self.date.dateChanged.connect(self._timer.start)
        self._build_form()

    # ------------------------------------------------------------------
    def _variant(self) -> str:
        return self.variant.currentData()

    def _make_widget(self, f: Field) -> QWidget:
        v = self.values.get(f.key)
        if f.kind == "choice":
            w = QComboBox()
            w.addItem("", None)
            for code, label in f.options:
                w.addItem(f"{code}: {label}", code)
            if v is not None:
                idx = w.findData(v)
                w.setCurrentIndex(max(idx, 0))
            w.currentIndexChanged.connect(self._timer.start)
        elif f.kind == "text":
            w = QPlainTextEdit(v or "")
            w.setMinimumHeight(70)
            w.textChanged.connect(self._timer.start)
        else:
            w = QLineEdit("" if v is None else str(v))
            if f.kind == "int":
                w.setValidator(QIntValidator(int(f.minimum if f.minimum is not None else -10**6),
                                             int(f.maximum if f.maximum is not None else 10**6)))
                w.setMaximumWidth(90)
            elif f.kind == "float":
                w.setValidator(QDoubleValidator())
                w.setMaximumWidth(90)
            w.textChanged.connect(self._timer.start)
        if f.help:
            w.setToolTip(f.help)
        return w

    def _build_form(self):
        self._collect()  # keep values across variant changes
        self.widgets.clear()
        container = QWidget()
        outer = QVBoxLayout(container)
        groups: dict[str, QFormLayout] = {}
        for f in self.inst.fields_for(self._variant()):
            if f.section not in groups:
                box = QGroupBox(f.section or "Responses")
                groups[f.section] = QFormLayout(box)
                outer.addWidget(box)
            w = self._make_widget(f)
            self.widgets[f.key] = w
            groups[f.section].addRow(f.label + ":", w)
        outer.addStretch(1)
        self.scroll.setWidget(container)
        self._refresh_preview()

    def _collect(self) -> dict:
        fields = {f.key: f for f in self.inst.fields_for(self._variant())} if self.widgets else {}
        for key, w in self.widgets.items():
            f = fields.get(key)
            if isinstance(w, QComboBox):
                val = w.currentData()
            elif isinstance(w, QPlainTextEdit):
                val = w.toPlainText()
            else:
                t = w.text().strip()
                if t == "":
                    val = None
                elif f is not None and f.kind == "int":
                    val = int(t) if t.lstrip("-").isdigit() else t
                else:
                    try:
                        val = float(t)
                    except ValueError:
                        val = t
            self.values[key] = val
        # Only keys of the current variant are saved.
        current = {f.key for f in self.inst.fields_for(self._variant())}
        return {k: v for k, v in self.values.items() if k in current and v not in (None, "")}

    def _refresh_preview(self):
        responses = self._collect()
        try:
            res = self.service.score_preview(self.client["id"], self.inst.key, self._variant(),
                                             responses, self.date.date().toString("yyyy-MM-dd"))
        except ValueError as exc:
            self.preview.setHtml(f"<p style='color:#b00'><b>Entry problems:</b><br>"
                                 f"{escape(str(exc)).replace('; ', '<br>')}</p>")
            return
        html = [f"<h3>Score preview</h3><p><i>Status: {res.verification}</i></p>",
                "<table border='1' cellspacing='0' cellpadding='3'>",
                "<tr><th>Domain</th><th>Scale</th><th>Score</th><th>Classification</th></tr>"]
        for r in res.rows:
            val = escape(r.value[:300]) + (f" <small>({escape(r.note)})</small>" if r.note else "")
            html.append(f"<tr><td>{escape(r.section)}</td><td>{escape(r.label)}</td>"
                        f"<td>{val}</td><td>{escape(r.band)}</td></tr>")
        html.append("</table>")
        for w in res.warnings:
            html.append(f"<p style='color:#8a5a00'>{escape(w)}</p>")
        self.preview.setHtml("".join(html))

    def _save(self):
        responses = self._collect()
        try:
            self.saved_id = self.service.save_assessment(
                self.client["id"], self.inst.key, self._variant(),
                self.date.date().toString("yyyy-MM-dd"), responses,
                self.existing["id"] if self.existing else None)
        except (ValueError, KeyError) as exc:
            return error(self, f"Not saved: {exc}")
        self.accept()
