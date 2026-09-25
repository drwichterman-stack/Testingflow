"""Data-entry form for one assessment, built from the instrument definition."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QDoubleValidator, QFont, QFontMetrics, QIntValidator
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QScrollArea, QSplitter, QTextBrowser, QVBoxLayout,
                               QWidget)

from ..scoring import INSTRUMENTS
from ..scoring.base import Field
from .. import omr
from .common import confirm, error
from .dictate import DictateButton
from .theme import html_table_css, set_role


class SegmentedChoice(QWidget):
    """One-click response buttons. Clicking the selected button clears it.

    After a camera read, a review flag can be shown under the buttons.
    Clicking any response, or the flag itself, marks the item as checked.
    """

    def __init__(self, options: list[tuple[int, str]], value, on_change, compact: bool,
                 on_reviewed=None):
        super().__init__()
        self._value = None
        self._on_change = on_change
        self._on_reviewed = on_reviewed
        self.buttons: dict[int, QPushButton] = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(3)
        lay = QHBoxLayout()
        lay.setSpacing(4)
        outer.addLayout(lay)
        for code, label in options:
            text = ("N/A" if code < 0 else str(code)) if compact else \
                (label if code < 0 else f"{code}  {label}")
            b = QPushButton(text)
            b.setCheckable(True)
            b.setToolTip(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            set_role(b, "seg")
            bold = QFont(b.font())
            bold.setBold(True)  # the selected state is bold; keep its text unclipped
            b.setMinimumWidth(max(52 if compact else 0,
                                  QFontMetrics(bold).horizontalAdvance(text) + 24))
            b.clicked.connect(lambda _=False, c=code: self._clicked(c))
            self.buttons[code] = b
            lay.addWidget(b)
        lay.addStretch(1)
        # Review flag after a camera read, on its own line so it never
        # squeezes the response buttons.
        flag_row = QHBoxLayout()
        self.flag = QPushButton()
        self.flag.setCursor(Qt.CursorShape.PointingHandCursor)
        self.flag.clicked.connect(self.clear_flag)
        self.flag.hide()
        flag_row.addWidget(self.flag)
        flag_row.addStretch(1)
        outer.addLayout(flag_row)
        self.setValue(value)

    @property
    def flagged(self) -> bool:
        return not self.flag.isHidden()

    def set_flag(self, text: str, danger: bool = False, detail: str = ""):
        self.flag.setText("\u26A0 " + text)
        self.flag.setToolTip((detail + "\n\n" if detail else "") +
                             "Compare with the paper form, then click here (or choose the "
                             "correct response) to mark this item checked.")
        set_role(self.flag, "flag-danger" if danger else "flag")
        self.flag.show()
        self.updateGeometry()

    def clear_flag(self):
        if self.flagged:
            self.flag.hide()
            self.updateGeometry()
            if self._on_reviewed:
                self._on_reviewed()

    def _clicked(self, code):
        self.setValue(None if self._value == code else code)
        self.clear_flag()
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
        self.review_flags: dict[str, tuple[str, bool, str]] = {}  # key -> (text, danger, detail)
        self.captured = False
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
        self.capture_btn = None
        if self.inst.paper_form:
            self.capture_btn = QPushButton("\U0001F4F7  Capture form")
            self.capture_btn.setToolTip("Hold the completed paper form up to the camera and "
                                        "fill in the responses from the photo.")
            self.capture_btn.clicked.connect(self._capture)
            top.addWidget(self.capture_btn)
        self.review_banner = QLabel()
        self.review_banner.setWordWrap(True)
        set_role(self.review_banner, "banner-warn")
        self.review_banner.hide()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.preview = QTextBrowser()
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.scroll)
        split.addWidget(self.preview)
        split.setSizes([700, 400])

        lay = QVBoxLayout(self)
        desc = QLabel(self.inst.description)
        desc.setWordWrap(True)
        lay.addWidget(desc)
        lay.addLayout(top)
        lay.addWidget(self.review_banner)
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
            w = SegmentedChoice(f.options, v, self._timer.start, compact,
                                on_reviewed=lambda k=f.key: self._reviewed(k))
            if f.key in self.review_flags:
                w.set_flag(*self.review_flags[f.key])
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

    # ------------------------------------------------------------------
    # Camera capture of the paper form

    def _capture(self):
        from .capture_form import CaptureFormDialog
        fields = self.inst.fields_for(self._variant())
        dlg = CaptureFormDialog(self, self.service, self.inst, self._variant(), fields)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.apply_capture(dlg.results, dlg.counts)

    def apply_capture(self, results: dict, counts: dict | None = None) -> bool:
        """Put camera-read responses on the form and flag what needs checking."""
        self._collect()
        fields = {f.key: f for f in self.inst.fields_for(self._variant())}
        results = {k: r for k, r in results.items() if k in fields}
        replaced = [k for k, r in results.items()
                    if self.values.get(k) not in (None, "") and self.values.get(k) != r.code]
        if replaced and not confirm(self, f"The photo gives different responses for "
                                          f"{len(replaced)} items that are already filled in. "
                                          "Replace them with the photo's responses?"):
            return False
        for key, r in results.items():
            self.values[key] = r.code
            text = None if r.status == omr.OK else omr.FLAG_TEXT[r.status]
            detail = "" if r.status == omr.OK else omr.STATUS_TEXT[r.status]
            danger = r.status in (omr.BLANK, omr.MULTIPLE)
            if fields[key].critical:
                text, danger = "Safety: confirm", True
                detail = "Safety item. Always confirm it against the paper form."
            if text:
                self.review_flags[key] = (text, danger, detail)
            else:
                self.review_flags.pop(key, None)
            w = self.widgets.get(key)
            if isinstance(w, SegmentedChoice):
                w.setValue(r.code)
                if text:
                    w.set_flag(text, danger, detail)
                else:
                    w.clear_flag()
        self.captured = True
        self.service.record_form_capture(self.client["id"], self.inst.key, self._variant(),
                                         counts or {"items": len(results)})
        self._update_banner()
        self._refresh_preview()
        return True

    def _reviewed(self, key: str):
        self.review_flags.pop(key, None)
        self._update_banner()

    def _update_banner(self):
        if not self.captured:
            return
        n = len(self.review_flags)
        if n:
            self.review_banner.setText(
                f"Responses were filled in from the camera photo. {n} items are flagged "
                "\u26A0 for checking. Compare every response with the paper form before "
                "saving; click a flag once its item is correct.")
            set_role(self.review_banner, "banner-warn")
        else:
            self.review_banner.setText(
                "Responses were filled in from the camera photo and all flagged items have "
                "been checked. Compare the remaining responses with the paper form before "
                "saving.")
            set_role(self.review_banner, "banner-ok")
        self.review_banner.show()

    def _save(self):
        responses = self._collect()
        current = {f.key for f in self.inst.fields_for(self._variant())}
        open_flags = sorted(k for k in self.review_flags if k in current)
        if open_flags and not confirm(
                self, f"{len(open_flags)} items read from the camera photo are still flagged "
                      "for checking. Save anyway?"):
            return
        extra = ({"camera_capture": True, "flags_unchecked": len(open_flags)}
                 if self.captured else None)
        try:
            self.saved_id = self.service.save_assessment(
                self.client["id"], self.inst.key, self._variant(),
                self.date.date().toString("yyyy-MM-dd"), responses,
                self.existing["id"] if self.existing else None, audit_details=extra)
        except (ValueError, KeyError) as exc:
            return error(self, f"Not saved: {exc}")
        self.accept()
