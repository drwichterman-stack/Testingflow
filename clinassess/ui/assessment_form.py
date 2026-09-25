"""Data-entry form for one assessment, built from the instrument definition."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QScrollArea, QSplitter, QTextBrowser, QVBoxLayout,
                               QWidget)

from ..scoring import INSTRUMENTS
from ..scoring.base import Field
from .common import error
from .dictate import DictateButton
from .theme import html_table_css, set_role


class SegmentedChoice(QWidget):
    """One-click response buttons. Clicking the selected button clears it."""

    def __init__(self, options: list[tuple[int, str]], value, on_change, compact: bool):
        super().__init__()
        self._value = None
        self._on_change = on_change
        self.buttons: dict[int, QPushButton] = {}
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        for code, label in options:
            text = ("N/A" if code < 0 else str(code)) if compact else \
                (label if code < 0 else f"{code}  {label}")
            b = QPushButton(text)
            b.setCheckable(True)
            b.setToolTip(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumWidth(52 if compact else 0)
            b.clicked.connect(lambda _=False, c=code: self._clicked(c))
            set_role(b, "seg")
            self.buttons[code] = b
            lay.addWidget(b)
        lay.addStretch(1)
        self.setValue(value)

    def _clicked(self, code):
        self.setValue(None if self._value == code else code)
        self._on_change()

    def setValue(self, value):
        self._value = value if value in self.buttons else None
        for c, b in self.buttons.items():
            b.setChecked(c == self._value)

    def value(self):
        return self._value


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
        save = bb.button(QDialogButtonBox.StandardButton.Save)
        save.setText("\U0001F512  Save (encrypted)")
        set_role(save, "primary")
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
            compact = sum(len(lbl) for _, lbl in f.options) > 48
            w = SegmentedChoice(f.options, v, self._timer.start, compact)
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
                groups[f.section].setVerticalSpacing(8)
                if f.kind == "choice" and sum(len(lbl) for _, lbl in f.options) > 48:
                    legend = QLabel("   ".join(("N/A" if c < 0 else str(c)) + " = " + lbl
                                               for c, lbl in f.options))
                    legend.setWordWrap(True)
                    groups[f.section].addRow(set_role(legend, "muted"))
                outer.addWidget(box)
            w = self._make_widget(f)
            self.widgets[f.key] = w
            row_w = w
            if f.kind == "text":
                row_w = QWidget()
                v = QVBoxLayout(row_w)
                v.setContentsMargins(0, 0, 0, 0)
                v.addWidget(w)
                h = QHBoxLayout()
                h.addStretch(1)
                h.addWidget(DictateButton(w))
                v.addLayout(h)
            groups[f.section].addRow(f.label + ":", row_w)
        outer.addStretch(1)
        self.scroll.setWidget(container)
        self._refresh_preview()

    def _collect(self) -> dict:
        fields = {f.key: f for f in self.inst.fields_for(self._variant())} if self.widgets else {}
        for key, w in self.widgets.items():
            f = fields.get(key)
            if isinstance(w, SegmentedChoice):
                val = w.value()
            elif isinstance(w, QComboBox):
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
            self.preview.setHtml(f"{html_table_css()}<p class='danger'>Entry problems:<br>"
                                 f"{escape(str(exc)).replace('; ', '<br>')}</p>")
            return
        html = [html_table_css(), "<h3>Live score</h3>",
                f"<p class='muted'>Scoring status: {res.verification}</p>",
                "<table cellspacing='0' cellpadding='3'>",
                "<tr><th>Domain</th><th>Scale</th><th>Score</th><th>Classification</th></tr>"]
        for r in res.rows:
            val = escape(r.value[:300]) + (f" <small>({escape(r.note)})</small>" if r.note else "")
            html.append(f"<tr><td>{escape(r.section)}</td><td>{escape(r.label)}</td>"
                        f"<td>{val}</td><td>{escape(r.band)}</td></tr>")
        html.append("</table>")
        for w in res.warnings:
            cls = "danger" if w.startswith("SAFETY") else "warn"
            html.append(f"<p class='{cls}'>{escape(w)}</p>")
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
