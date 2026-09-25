"""First-run setup (with license acceptance) and login dialogs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QTextBrowser, QVBoxLayout)

from .. import config
from ..keystore import AuthError, LockedOutError, validate_password, validate_username
from .branding import logo_pixmap
from .common import error
from .help import read_text
from .theme import set_role


def _brand_header(layout, subtitle: str):
    row = QHBoxLayout()
    logo = QLabel()
    logo.setPixmap(logo_pixmap(64))
    row.addWidget(logo)
    col = QVBoxLayout()
    col.addWidget(set_role(QLabel(config.APP_NAME), "h1"))
    col.addWidget(set_role(QLabel(subtitle), "muted"))
    row.addLayout(col, 1)
    layout.addLayout(row)
    layout.addSpacing(8)


class SetupDialog(QDialog):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.setWindowTitle(f"Welcome to {config.APP_NAME}")
        self.setMinimumWidth(620)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        _brand_header(lay, "First-time setup")

        lay.addWidget(set_role(QLabel("1. License agreement"), "h2"))
        eula = QTextBrowser()
        eula.setPlainText(read_text("LICENSE.txt"))
        eula.setMinimumHeight(170)
        lay.addWidget(eula)
        self.accept_box = QCheckBox("I have read and accept the license agreement")
        lay.addWidget(self.accept_box)
        lay.addSpacing(10)

        lay.addWidget(set_role(QLabel("2. Create the administrator account"), "h2"))
        warn = set_role(QLabel(
            "This password protects the encryption key for all client data. There is NO "
            "password recovery: if every administrator password is lost, the data cannot be "
            "decrypted by anyone, including the publisher. Store it somewhere safe."),
            "banner-warn")
        warn.setWordWrap(True)
        lay.addWidget(warn)
        form = QFormLayout()
        self.user = QLineEdit()
        self.pw1 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.pw2 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.pw1.setToolTip(f"At least {config.MIN_PASSWORD_LENGTH} characters and 3 of: "
                            "lowercase, uppercase, digit, symbol")
        self.hint = set_role(QLabel(), "muted")
        self.pw1.textChanged.connect(self._hint)
        form.addRow("Username:", self.user)
        form.addRow("Password:", self.pw1)
        form.addRow("", self.hint)
        form.addRow("Confirm password:", self.pw2)
        lay.addLayout(form)
        self._hint()
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = set_role(QPushButton("Create account and continue"), "primary")
        ok.clicked.connect(self._ok)
        ok.setDefault(True)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

    def _hint(self):
        problems = validate_password(self.pw1.text())
        self.hint.setText("✓ Password meets the policy" if not problems
                          else "Needs " + " and ".join(problems))

    def _ok(self):
        if not self.accept_box.isChecked():
            return error(self, "Please accept the license agreement to continue.")
        u, p = self.user.text().strip(), self.pw1.text()
        if not validate_username(u):
            return error(self, "Username: 2-32 characters, letters, digits, . _ - only.")
        if p != self.pw2.text():
            return error(self, "Passwords do not match.")
        problems = validate_password(p)
        if problems:
            return error(self, "Password needs " + " and ".join(problems) + ".")
        self.service.setup(u, p, config.EULA_VERSION)
        self.accept()


class LoginDialog(QDialog):
    def __init__(self, service, message: str = ""):
        super().__init__()
        self.service = service
        self.setWindowTitle(f"{config.APP_NAME}: sign in")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        _brand_header(lay, f"Version {config.APP_VERSION}")
        if message:
            m = set_role(QLabel(message), "banner-warn")
            m.setWordWrap(True)
            lay.addWidget(m)
        form = QFormLayout()
        self.user = QLineEdit()
        self.pw = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.user)
        form.addRow("Password:", self.pw)
        lay.addLayout(form)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.hide()
        lay.addWidget(self.status)
        lay.addWidget(set_role(QLabel("\U0001F512 Authorized users only. All access is logged."),
                               "muted"))
        row = QHBoxLayout()
        row.addStretch(1)
        quit_btn = QPushButton("Quit")
        quit_btn.clicked.connect(self.reject)
        self.ok = set_role(QPushButton("Sign in"), "primary")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self._ok)
        row.addWidget(quit_btn)
        row.addWidget(self.ok)
        lay.addLayout(row)
        self.user.setFocus(Qt.FocusReason.OtherFocusReason)

    def _ok(self):
        self.status.setText("Unlocking...")
        set_role(self.status, "muted")
        self.status.show()
        self.repaint()
        try:
            self.service.login(self.user.text().strip(), self.pw.text())
        except LockedOutError:
            self.pw.clear()
            self.status.setText(f"Too many failed attempts. Try again in "
                                f"{config.LOCKOUT_SECONDS // 60} minutes.")
            set_role(self.status, "banner-danger")
            return
        except AuthError:
            self.pw.clear()
            self.status.setText("Incorrect username or password.")
            set_role(self.status, "banner-danger")
            return
        self.pw.clear()
        self.accept()
