"""Client intake / edit dialog."""

from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
                             QFormLayout, QLabel, QLineEdit, QVBoxLayout)

from ..scoring import FLOW_LABELS
from ..service import age_on
from .common import error


class ClientDialog(QDialog):
    def __init__(self, parent, service, client: dict | None = None):
        super().__init__(parent)
        self.service = service
        self.client = client
        self.client_id = client["id"] if client else None
        self.setWindowTitle("Edit client" if client else "New client intake")
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.last = QLineEdit(client["last_name"] if client else "")
        self.first = QLineEdit(client["first_name"] if client else "")
        self.dob = QDateEdit(calendarPopup=True)
        self.dob.setDisplayFormat("yyyy-MM-dd")
        self.dob.setMaximumDate(QDate.currentDate())
        self.dob.setDate(QDate.fromString(client["dob"], "yyyy-MM-dd") if client
                         else QDate.currentDate().addYears(-10))
        self.age = QLabel()
        self.grade = QLineEdit(client["grade"] if client else "")
        self.flow = QComboBox()
        for k, label in FLOW_LABELS.items():
            self.flow.addItem(label, k)
        if client:
            self.flow.setCurrentIndex(0 if client["flow"] == "A" else 1)
        self.asrs = QCheckBox("Include ASRS v1.1 (Flow A: clinician decision; "
                              "always included in Flow B)")
        self.asrs.setChecked(bool(client["asrs_enabled"]) if client else False)
        form.addRow("Last name:", self.last)
        form.addRow("First name:", self.first)
        form.addRow("Date of birth:", self.dob)
        form.addRow("Age:", self.age)
        form.addRow("Grade:", self.grade)
        form.addRow("Assessment flow:", self.flow)
        form.addRow("", self.asrs)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.dob.dateChanged.connect(self._update)
        self.flow.currentIndexChanged.connect(self._update)
        self._update()

    def _update(self):
        a = age_on(self.dob.date().toString("yyyy-MM-dd"))
        self.age.setText(f"{a} years" if a is not None else "")
        is_b = self.flow.currentData() == "B"
        self.asrs.setEnabled(not is_b)
        if is_b:
            self.asrs.setChecked(True)
        if self.flow.currentData() == "A" and a is not None and a < 6:
            self.age.setText(f"{a} years (Flow A is designed for ages 6+)")

    def data(self) -> dict:
        return {"last_name": self.last.text(), "first_name": self.first.text(),
                "dob": self.dob.date().toString("yyyy-MM-dd"), "grade": self.grade.text(),
                "flow": self.flow.currentData(), "asrs_enabled": self.asrs.isChecked()}

    def _save(self):
        try:
            if self.client_id is None:
                self.client_id = self.service.create_client(self.data())
            else:
                self.service.update_client(self.client_id, self.data())
        except ValueError as exc:
            return error(self, str(exc).capitalize() + ".")
        self.accept()
