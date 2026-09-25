"""First-run setup and login dialogs."""

from __future__ import annotations

from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                             QVBoxLayout)

from .. import config
from ..keystore import AuthError, validate_password, validate_username
from .common import error


class SetupDialog(QDialog):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.setWindowTitle(f"{config.APP_NAME}: first-time setup")
        lay = QVBoxLayout(self)
        lbl = QLabel(
            "Create the administrator account. This password protects the encryption key "
            "for all client data.\n\nThere is no password recovery. If every administrator "
            "password is lost, the data cannot be decrypted. Record the password in a secure "
            f"place.\n\nPassword: at least {config.MIN_PASSWORD_LENGTH} characters and 3 of: "
            "lowercase, uppercase, digit, symbol.")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        form = QFormLayout()
        self.user = QLineEdit()
        self.pw1 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.pw2 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.user)
        form.addRow("Password:", self.pw1)
        form.addRow("Confirm password:", self.pw2)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _ok(self):
        u, p = self.user.text().strip(), self.pw1.text()
        if not validate_username(u):
            return error(self, "Username: 2-32 characters, letters, digits, . _ - only.")
        if p != self.pw2.text():
            return error(self, "Passwords do not match.")
        problems = validate_password(p)
        if problems:
            return error(self, "Password needs " + " and ".join(problems) + ".")
        self.service.setup(u, p)
        self.accept()


class LoginDialog(QDialog):
    def __init__(self, service, message: str = ""):
        super().__init__()
        self.service = service
        self.setWindowTitle(f"{config.APP_NAME}: log in")
        lay = QVBoxLayout(self)
        if message:
            m = QLabel(message)
            m.setWordWrap(True)
            lay.addWidget(m)
        form = QFormLayout()
        self.user = QLineEdit()
        self.pw = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.user)
        form.addRow("Password:", self.pw)
        lay.addLayout(form)
        notice = QLabel("Authorized users only. All access is logged.")
        lay.addWidget(notice)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _ok(self):
        try:
            self.service.login(self.user.text().strip(), self.pw.text())
        except AuthError as exc:
            self.pw.clear()
            return error(self, str(exc).capitalize() + ".")
        self.pw.clear()
        self.accept()
