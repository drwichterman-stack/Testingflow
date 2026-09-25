"""Main window: client search, client detail, assessments, and menus."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMainWindow, QMenu, QPushButton, QSplitter, QTableWidget,
                             QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from .. import config
from ..scoring import FLOW_LABELS, INSTRUMENTS
from . import admin
from .assessment_form import AssessmentDialog
from .client_dialog import ClientDialog
from .common import PasswordDialog, ReasonDialog, confirm, error, info
from .report_editor import ReportEditor


def _ro_table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    return t


class MainWindow(QMainWindow):
    def __init__(self, service, on_lock):
        super().__init__()
        self.service = service
        self.on_lock = on_lock
        self.client_id: int | None = None
        self.resize(1250, 780)
        self._build_menus()

        # Left: search
        self.q_name = QLineEdit(placeholderText="Name or reference code")
        self.q_dob = QLineEdit(placeholderText="DOB (YYYY, YYYY-MM or YYYY-MM-DD)")
        for w in (self.q_name, self.q_dob):
            w.returnPressed.connect(self.search)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search)
        new_btn = QPushButton("New client intake")
        new_btn.clicked.connect(self.new_client)
        self.results = _ro_table(["Ref", "Last", "First", "DOB", "Flow"])
        self.results.itemSelectionChanged.connect(self._select_client)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel("<b>Clients</b>"))
        lv.addWidget(self.q_name)
        lv.addWidget(self.q_dob)
        row = QHBoxLayout()
        row.addWidget(search_btn)
        row.addWidget(new_btn)
        lv.addLayout(row)
        lv.addWidget(self.results, 1)

        # Right: client detail
        self.header = QLabel("Select a client.")
        self.header.setTextFormat(Qt.TextFormat.RichText)
        self.header.setWordWrap(True)
        self.assess = _ro_table(["ID", "Instrument", "Form / informant", "Date", "Summary",
                                 "Entered by"])
        self.assess.doubleClicked.connect(self.open_assessment)
        self.add_btn = QToolButton(text="Add assessment")
        self.add_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.add_menu = QMenu(self)
        self.add_btn.setMenu(self.add_menu)
        btns = [self.add_btn]
        for text, slot in (("Open / edit", self.open_assessment),
                           ("Delete assessment", self.delete_assessment),
                           ("Edit client", self.edit_client),
                           ("Report (edit and PDF)", self.open_report),
                           ("Delete client", self.delete_client)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.append(b)
        self.detail_buttons = btns
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.addWidget(self.header)
        brow = QHBoxLayout()
        for b in btns:
            brow.addWidget(b)
        brow.addStretch(1)
        rv.addLayout(brow)
        rv.addWidget(self.assess, 1)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([420, 830])
        self.setCentralWidget(split)
        self._set_detail_enabled(False)

    def _build_menus(self):
        mb = self.menuBar()
        f = mb.addMenu("File")
        self._act(f, "Lock now", lambda: self.on_lock("LOGOUT"), "Ctrl+L")
        self._act(f, "Change my password", self.change_password)
        f.addSeparator()
        self._act(f, "Quit", self.close, "Ctrl+Q")
        a = mb.addMenu("Admin")
        self._act(a, "Audit trail", lambda: self._admin(admin.AuditDialog))
        self._act(a, "User accounts", lambda: self._admin(admin.UsersDialog))
        self._act(a, "Retention review", lambda: self._admin(admin.RetentionDialog))
        a.addSeparator()
        self._act(a, "Export encrypted archive", self.export_archive)
        self._act(a, "Test a backup (restore test)", lambda: self._admin(
            lambda p, s: admin.verify_backup_flow(p, s)))
        self._act(a, "Restore from archive", self.restore_archive)

    def _act(self, menu, text, slot, shortcut=None):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)

    def _admin(self, factory):
        if not self.service.session.is_admin:
            return error(self, "This function requires the admin role.")
        try:
            dlg = factory(self, self.service)
        except PermissionError as exc:
            return error(self, str(exc))
        if dlg is not None:
            dlg.exec()

    def refresh_title(self):
        s = self.service.session
        self.setWindowTitle(f"{config.APP_NAME} {config.APP_VERSION}: {s.username} ({s.role})")

    # ------------------------------------------------------------------ search
    def search(self):
        rows = self.service.search_clients(self.q_name.text(), self.q_dob.text())
        self.results.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, key in enumerate(("ref_code", "last_name", "first_name", "dob", "flow")):
                item = QTableWidgetItem(r[key])
                item.setData(Qt.ItemDataRole.UserRole, r["id"])
                self.results.setItem(i, j, item)
        if not rows:
            self._show_client(None)

    def _select_client(self):
        items = self.results.selectedItems()
        if items:
            cid = items[0].data(Qt.ItemDataRole.UserRole)
            if cid != self.client_id:
                self._show_client(cid)

    def _set_detail_enabled(self, on: bool):
        for b in self.detail_buttons:
            b.setEnabled(on)

    def _show_client(self, cid: int | None, log: bool = True):
        self.client_id = cid
        self.assess.setRowCount(0)
        if cid is None:
            self.header.setText("Select a client.")
            self._set_detail_enabled(False)
            return
        c = self.service.get_client(cid, log=log)
        self.client = c
        self.header.setText(
            f"<h2>{c['first_name']} {c['last_name']}</h2>"
            f"Ref {c['ref_code']} | DOB {c['dob']} | Age {c['age']} | Grade {c['grade'] or '-'}"
            f"<br>{FLOW_LABELS[c['flow']]}"
            + (" | ASRS enabled" if c["flow"] == "A" and c["asrs_enabled"] else ""))
        self.add_menu.clear()
        for inst in self.service.available_instruments(cid):
            act = self.add_menu.addAction(f"{inst.short}: {inst.name}")
            act.triggered.connect(lambda _=False, k=inst.key: self.add_assessment(k))
        rows = self.service.list_assessments(cid)
        self.assess.setRowCount(len(rows))
        for i, a in enumerate(rows):
            inst = INSTRUMENTS[a["instrument"]]
            vals = [a["id"], inst.short, dict(inst.variants).get(a["variant"], a["variant"]),
                    a["administered_on"], a["scores"].summary, a["updated_by"]]
            for j, v in enumerate(vals):
                self.assess.setItem(i, j, QTableWidgetItem(str(v)))
        self._set_detail_enabled(True)

    # ----------------------------------------------------------------- clients
    def new_client(self):
        dlg = ClientDialog(self, self.service)
        if dlg.exec():
            self.q_name.setText(self.service.get_client(dlg.client_id, log=False)["ref_code"])
            self.q_dob.clear()
            self.search()
            self._show_client(dlg.client_id, log=False)

    def edit_client(self):
        if self.client_id is None:
            return
        dlg = ClientDialog(self, self.service, self.service.get_client(self.client_id, log=False))
        if dlg.exec():
            self._show_client(self.client_id, log=False)

    def delete_client(self):
        if self.client_id is None:
            return
        c = self.client
        dlg = ReasonDialog(self, f"client {c['ref_code']} and ALL assessments and reports",
                           c["ref_code"])
        if not dlg.exec():
            return
        counts = self.service.delete_client(self.client_id, dlg.reason_text())
        info(self, f"Deleted {c['ref_code']}: {counts['assessments']} assessment(s), "
                   f"{counts['report_versions']} report version(s). Recorded in the audit trail.")
        self.search()
        self._show_client(None)

    # ------------------------------------------------------------- assessments
    def _selected_assessment_id(self) -> int | None:
        items = self.assess.selectedItems()
        return int(self.assess.item(items[0].row(), 0).text()) if items else None

    def add_assessment(self, key: str):
        dlg = AssessmentDialog(self, self.service, self.client, key)
        if dlg.exec():
            self._show_client(self.client_id, log=False)

    def open_assessment(self):
        aid = self._selected_assessment_id()
        if aid is None:
            return
        a = self.service.get_assessment(self.client_id, aid)
        allowed = {i.key for i in self.service.available_instruments(self.client_id)}
        if a["instrument"] not in allowed:
            return error(self, "This instrument is no longer part of the client's flow. "
                               "It can be viewed in the report or deleted.")
        dlg = AssessmentDialog(self, self.service, self.client, a["instrument"], a)
        if dlg.exec():
            self._show_client(self.client_id, log=False)

    def delete_assessment(self):
        aid = self._selected_assessment_id()
        if aid is None:
            return
        dlg = ReasonDialog(self, f"assessment #{aid}", self.client["ref_code"])
        if dlg.exec():
            self.service.delete_assessment(self.client_id, aid, dlg.reason_text())
            self._show_client(self.client_id, log=False)

    def open_report(self):
        if self.client_id is not None:
            ReportEditor(self, self.service, self.client_id).exec()

    # ------------------------------------------------------------------- admin
    def change_password(self):
        admin.ChangePasswordDialog(self, self.service).exec()

    def export_archive(self):
        if not self.service.session.is_admin:
            return error(self, "This function requires the admin role.")
        dlg = PasswordDialog(
            self, "Archive password",
            "The archive holds ALL client data, encrypted with AES-256-GCM under this "
            "password. It is separate from your login password, and a lost archive password "
            "cannot be recovered. Store archives only on encrypted media (FileVault or an "
            "encrypted APFS volume).")
        if not dlg.exec():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save archive", f"clinassess_{date.today().isoformat()}.caarchive",
            "ClinAssess archive (*.caarchive)")
        if path:
            self.service.export_archive(path, dlg.password())
            info(self, "Encrypted archive saved. Record it in your backup log.")

    def restore_archive(self):
        if not self.service.session.is_admin:
            return error(self, "This function requires the admin role.")
        path, _ = QFileDialog.getOpenFileName(self, "Choose archive", "",
                                              "ClinAssess archive (*.caarchive)")
        if not path:
            return
        if not confirm(self, "Restoring REPLACES all current client data with the archive "
                             "contents. Export a current archive first if unsure. Continue?"):
            return
        dlg = PasswordDialog(self, "Archive password", "Enter the archive password.",
                             confirm_twice=False, enforce_policy=False)
        if not dlg.exec():
            return
        try:
            self.service.restore_archive(path, dlg.password())
        except Exception as exc:
            return error(self, f"Restore failed: {type(exc).__name__}. Wrong password or "
                               "damaged archive. Current data was not changed.")
        info(self, "Archive restored.")
        self.search()
        self._show_client(None)

    def closeEvent(self, event):
        self.on_lock("LOGOUT", quit_app=True)
        event.accept()
