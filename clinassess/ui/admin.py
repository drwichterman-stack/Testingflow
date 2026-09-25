"""Administrative dialogs: users, audit trail, retention review, backup testing."""

from __future__ import annotations

import json

from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                             QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

from .. import config
from ..keystore import ROLES
from .common import PasswordDialog, confirm, error, info, wrap_label


def _table(headers: list[str], rows: list[list]) -> QTableWidget:
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            t.setItem(i, j, QTableWidgetItem("" if v is None else str(v)))
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    return t


class UsersDialog(QDialog):
    def __init__(self, parent, service):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("User accounts")
        lay = QVBoxLayout(self)
        self.list = QListWidget()
        lay.addWidget(self.list)
        form = QFormLayout()
        self.user = QLineEdit()
        self.role = QComboBox()
        self.role.addItems(ROLES)
        form.addRow("New username:", self.user)
        form.addRow("Role:", self.role)
        lay.addLayout(form)
        row = QHBoxLayout()
        add = QPushButton("Add user")
        add.clicked.connect(self._add)
        rm = QPushButton("Remove selected")
        rm.clicked.connect(self._remove)
        row.addWidget(add)
        row.addWidget(rm)
        lay.addLayout(row)
        lay.addWidget(wrap_label(
            "Each user has an individual login so the audit trail identifies who did what. "
            "Do not share accounts."))
        self._refresh()

    def _refresh(self):
        self.list.clear()
        for u, r in self.service.keystore.list_users():
            self.list.addItem(f"{u}  ({r})")

    def _add(self):
        u = self.user.text().strip()
        dlg = PasswordDialog(self, "Initial password", f"Set the initial password for {u}.")
        if not dlg.exec():
            return
        try:
            self.service.add_user(u, dlg.password(), self.role.currentText())
        except (ValueError, PermissionError) as exc:
            return error(self, str(exc))
        self.user.clear()
        self._refresh()

    def _remove(self):
        item = self.list.currentItem()
        if not item:
            return
        u = item.text().split()[0]
        if not confirm(self, f"Remove user {u}? Their audit history is kept."):
            return
        try:
            self.service.remove_user(u)
        except (ValueError, PermissionError) as exc:
            return error(self, str(exc))
        self._refresh()


class ChangePasswordDialog(QDialog):
    def __init__(self, parent, service):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Change password")
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.old = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.new1 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.new2 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        form.addRow("Current password:", self.old)
        form.addRow("New password:", self.new1)
        form.addRow("Confirm new:", self.new2)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _ok(self):
        if self.new1.text() != self.new2.text():
            return error(self, "New passwords do not match.")
        try:
            self.service.change_password(self.old.text(), self.new1.text())
        except Exception as exc:  # AuthError, ValueError
            return error(self, str(exc))
        info(self, "Password changed.")
        self.accept()


class AuditDialog(QDialog):
    def __init__(self, parent, service):
        super().__init__(parent)
        self.setWindowTitle("Audit trail")
        self.resize(1100, 650)
        events, result = service.read_audit()
        lay = QVBoxLayout(self)
        status = (f"Integrity check PASSED: {result.count} entries, hash chain intact."
                  if result.ok else "Integrity check FAILED:\n" + "\n".join(result.problems))
        lbl = wrap_label(status)
        lbl.setStyleSheet("color:#0a6b2d;" if result.ok else "color:#b00; font-weight:bold;")
        lay.addWidget(lbl)
        rows = [[e["seq"], e["ts"], e["user"], e["action"], e.get("client_ref") or "",
                 e.get("entity") or "", e.get("entity_id") or "",
                 json.dumps(e.get("details") or {})] for e in reversed(events)]
        lay.addWidget(_table(["Seq", "Time (UTC)", "User", "Action", "Client ref", "Entity",
                              "ID", "Details"], rows))


class RetentionDialog(QDialog):
    def __init__(self, parent, service):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Retention review")
        self.resize(800, 500)
        lay = QVBoxLayout(self)
        lay.addWidget(wrap_label(
            "Lists clients with no activity for at least the chosen number of years. Confirm "
            "the retention period required by your state law and licensing board (for minors, "
            "often measured from the age of majority) before deleting anything."))
        row = QHBoxLayout()
        self.years = QSpinBox(minimum=1, maximum=50, value=config.DEFAULT_RETENTION_YEARS)
        go = QPushButton("Run review")
        go.clicked.connect(self._run)
        row.addWidget(QLabel("Inactive for at least (years):"))
        row.addWidget(self.years)
        row.addWidget(go)
        row.addStretch(1)
        lay.addLayout(row)
        self.table = _table(["Ref", "Last", "First", "DOB", "Last activity (UTC)"], [])
        lay.addWidget(self.table)

    def _run(self):
        rows = self.service.retention_review(self.years.value())
        t = _table(["Ref", "Last", "First", "DOB", "Last activity (UTC)"],
                   [[r["ref_code"], r["last_name"], r["first_name"], r["dob"],
                     r["last_activity"]] for r in rows])
        self.layout().replaceWidget(self.table, t)
        self.table.deleteLater()
        self.table = t


def verify_backup_flow(parent, service):
    path, _ = QFileDialog.getOpenFileName(
        parent, "Choose a backup to test",
        "", "ClinAssess backups (*.caarchive *.enc);;All files (*)")
    if not path:
        return
    password = None
    with open(path, "rb") as fh:
        is_archive = fh.read(6) == b"CAARC1"
    if is_archive:
        dlg = PasswordDialog(parent, "Archive password", "Enter the archive password.",
                             confirm_twice=False, enforce_policy=False)
        if not dlg.exec():
            return
        password = dlg.password()
    r = service.verify_backup(path, password)
    if r["ok"]:
        c = r["counts"]
        info(parent, f"Backup test PASSED.\n\nType: {r['file_type']}\nSQLite integrity: "
                     f"{r['integrity']}\nClients: {c['clients']}\nAssessments: "
                     f"{c['assessments']}\nReport versions: {c['report_versions']}\n\n"
                     "The result is recorded in the audit trail (BACKUP_VERIFY). Record it "
                     "in your backup testing log too.")
    else:
        error(parent, f"Backup test FAILED.\n\n{r.get('error') or r.get('integrity')}\n\n"
                      "The failure is recorded in the audit trail. Follow the incident "
                      "steps in BACKUP_AND_DISASTER_RECOVERY_POLICY.md.")
