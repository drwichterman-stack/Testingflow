"""Shared dialogs and helpers for the GUI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                             QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget)

from ..keystore import validate_password


def error(parent: QWidget | None, text: str, title: str = "Error") -> None:
    QMessageBox.critical(parent, title, text)


def info(parent: QWidget | None, text: str, title: str = "ClinAssess") -> None:
    QMessageBox.information(parent, title, text)


def confirm(parent: QWidget | None, text: str, title: str = "Confirm") -> bool:
    return QMessageBox.question(parent, title, text) == QMessageBox.StandardButton.Yes


class PasswordDialog(QDialog):
    """Ask for a new password twice (for PDF or archive encryption)."""

    def __init__(self, parent, title: str, explanation: str, confirm_twice: bool = True,
                 enforce_policy: bool = True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.enforce_policy = enforce_policy
        lay = QVBoxLayout(self)
        lbl = QLabel(explanation)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        form = QFormLayout()
        self.pw1 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        form.addRow("Password:", self.pw1)
        self.pw2 = None
        if confirm_twice:
            self.pw2 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
            form.addRow("Confirm:", self.pw2)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _ok(self):
        pw = self.pw1.text()
        if self.pw2 is not None and pw != self.pw2.text():
            return error(self, "Passwords do not match.")
        if self.enforce_policy:
            problems = validate_password(pw)
            if problems:
                return error(self, "Password needs " + " and ".join(problems) + ".")
        if not pw:
            return
        self.accept()

    def password(self) -> str:
        return self.pw1.text()


class ReasonDialog(QDialog):
    """Deletion confirmation: requires a reason and typing the reference code."""

    def __init__(self, parent, what: str, ref_code: str):
        super().__init__(parent)
        self.ref_code = ref_code
        self.setWindowTitle("Confirm permanent deletion")
        lay = QVBoxLayout(self)
        lbl = QLabel(
            f"Permanently delete {what}?\n\nThis cannot be undone in the app. The deletion, "
            "your reason, and the record counts are written to the audit trail. Copies in "
            "earlier backups remain until those backups expire (see DATA_RETENTION.md).")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        form = QFormLayout()
        self.reason = QPlainTextEdit()
        self.reason.setFixedHeight(60)
        form.addRow("Reason (required):", self.reason)
        self.typed = QLineEdit()
        form.addRow(f"Type {ref_code} to confirm:", self.typed)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _ok(self):
        if not self.reason.toPlainText().strip():
            return error(self, "A reason is required.")
        if self.typed.text().strip() != self.ref_code:
            return error(self, "The reference code does not match.")
        self.accept()

    def reason_text(self) -> str:
        return self.reason.toPlainText().strip()


def wrap_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lbl
