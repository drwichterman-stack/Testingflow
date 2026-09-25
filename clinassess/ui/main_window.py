"""Main window: sidebar navigation, dashboard, client workspace, menus."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMainWindow, QMenu, QPushButton,
                               QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
                               QToolButton, QVBoxLayout, QWidget)

from .. import config
from ..scoring import FLOW_LABELS, INSTRUMENTS
from . import admin, help as help_ui
from .assessment_form import AssessmentDialog
from .branding import logo_pixmap
from .client_dialog import ClientDialog
from .common import PasswordDialog, ReasonDialog, confirm, error
from .report_editor import ReportEditor, export_pdf_flow
from .theme import set_role, tokens

LOCK = "\U0001F512"
CHECK = "✓"


def table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    t.setAlternatingRowColors(True)
    t.setShowGrid(False)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(34)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    return t


def fill(t: QTableWidget, rows: list[list], ids: list | None = None):
    t.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            item = QTableWidgetItem("" if v is None else str(v))
            if ids is not None:
                item.setData(Qt.ItemDataRole.UserRole, ids[i])
            t.setItem(i, j, item)


def card(*widgets, layout=None) -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    lay = layout or QVBoxLayout()
    lay.setContentsMargins(18, 16, 18, 16)
    for w in widgets:
        lay.addWidget(w)
    f.setLayout(lay)
    return f


def button(text: str, slot, role: str = "", tip: str = "") -> QPushButton:
    b = QPushButton(text)
    b.clicked.connect(slot)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if role:
        set_role(b, role)
    if tip:
        b.setToolTip(tip)
    return b


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardPage(QWidget):
    def __init__(self, main: "MainWindow"):
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)
        head = QHBoxLayout()
        title = QVBoxLayout()
        title.addWidget(set_role(QLabel("Dashboard"), "h1"))
        self.subtitle = set_role(QLabel(), "muted")
        title.addWidget(self.subtitle)
        head.addLayout(title, 1)
        head.addWidget(button("+  New client", main.new_client, "primary",
                              "Start a new client intake (Cmd+N)"))
        head.addWidget(button("Find client", main.go_clients, "",
                              "Search by name, reference code, or date of birth"))
        lay.addLayout(head)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.stats = {}
        for col, (key, label, tip) in enumerate((
                ("active", "Active clients", "Clients with any activity in the last 90 days"),
                ("pending", "Pending assessments", "Active clients with measures not yet entered"),
                ("awaiting", "Awaiting report", "Clients with scores but no report yet"),
                ("drafts", "Draft reports", "Reports that still contain clinician prompts"))):
            num = set_role(QLabel("0"), "stat")
            lbl = set_role(QLabel(label), "muted")
            c = card(num, lbl)
            c.setToolTip(tip)
            grid.addWidget(c, 0, col)
            self.stats[key] = num
        lay.addLayout(grid)

        lists = QHBoxLayout()
        lists.setSpacing(14)
        self.pending = table(["Client", "Ref", "Measures not entered"])
        self.pending.doubleClicked.connect(lambda: self._open(self.pending))
        self.reports = table(["Client", "Ref", "Version", "Status", "Saved"])
        self.reports.doubleClicked.connect(lambda: self._open(self.reports))
        lists.addWidget(card(set_role(QLabel("Pending assessments"), "h2"),
                             set_role(QLabel("Double-click a row to open the client."), "muted"),
                             self.pending), 1)
        lists.addWidget(card(set_role(QLabel("Recent reports"), "h2"),
                             set_role(QLabel("Latest version of each report."), "muted"),
                             self.reports), 1)
        lay.addLayout(lists, 1)

    def refresh(self):
        d = self.main.service.dashboard()
        self.subtitle.setText(f"{date.today():%A, %B %d, %Y}  |  {d['total_clients']} client "
                              f"record(s)  |  {LOCK} all data encrypted on this Mac")
        self.stats["active"].setText(str(len(d["active"])))
        self.stats["pending"].setText(str(len(d["pending"])))
        self.stats["awaiting"].setText(str(len(d["awaiting_report"])))
        self.stats["drafts"].setText(str(len(d["drafts"])))
        fill(self.pending, [[f"{p['last_name']}, {p['first_name']}", p["ref_code"],
                             ", ".join(p["missing"])] for p in d["pending"]],
             [p["id"] for p in d["pending"]])
        fill(self.reports, [[f"{r['last_name']}, {r['first_name']}", r["ref_code"],
                             f"v{r['version_no']}", "Draft" if r["draft"] else f"{CHECK} Complete",
                             r["created_at"][:16].replace("T", " ")] for r in d["reports"]],
             [r["client_id"] for r in d["reports"]])

    def _open(self, t: QTableWidget):
        items = t.selectedItems()
        if items:
            self.main.open_client(items[0].data(Qt.ItemDataRole.UserRole))


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
class ClientsPage(QWidget):
    def __init__(self, main: "MainWindow"):
        super().__init__()
        self.main = main
        self.service = main.service
        self.client_id: int | None = None
        self.client: dict | None = None

        # Search panel
        self.q_name = QLineEdit(placeholderText="Name or reference code")
        self.q_dob = QLineEdit(placeholderText="Date of birth (YYYY or YYYY-MM-DD)")
        for w in (self.q_name, self.q_dob):
            w.returnPressed.connect(self.search)
        self.results = table(["Name", "DOB", "Flow"])
        self.results.itemSelectionChanged.connect(self._select)
        left = QVBoxLayout()
        left.addWidget(set_role(QLabel("Clients"), "h2"))
        left.addWidget(self.q_name)
        left.addWidget(self.q_dob)
        row = QHBoxLayout()
        row.addWidget(button("Search", self.search, "", "Each search is recorded in the "
                                                        "audit trail (terms are not recorded)"))
        row.addWidget(button("+  New client", main.new_client, "primary"))
        left.addLayout(row)
        left.addWidget(self.results, 1)
        left_w = card(layout=left)

        # Detail panel
        self.name = set_role(QLabel("No client selected"), "h1")
        self.meta = set_role(QLabel("Search for a client, or start a new intake."), "muted")
        self.meta.setWordWrap(True)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.hide()

        self.start_btn = button("Start session", self.start_session, "primary",
                                "Open today's interview notes for this client")
        self.add_btn = QToolButton(text="Add assessment  ▾")
        self.add_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.add_btn.setToolTip("Only the measures for this client's flow are listed")
        self.add_menu = QMenu(self)
        self.add_btn.setMenu(self.add_menu)
        set_role(self.add_btn, "big")
        self.report_btn = button("Generate report", self.open_report, "big",
                                 "Review and edit the report before export")
        self.pdf_btn = button(f"{LOCK}  Export PDF", self.export_pdf, "big",
                              "Encrypted PDF (AES-256) of the latest saved report version")
        for b in (self.start_btn, self.report_btn, self.pdf_btn):
            if b.property("role") != "primary":
                set_role(b, "big")
        self.start_btn.setMinimumHeight(44)
        actions = QHBoxLayout()
        for b in (self.start_btn, self.add_btn, self.report_btn, self.pdf_btn):
            actions.addWidget(b)
        actions.addStretch(1)

        self.assess = table(["Measure", "Form / informant", "Date", "Result", "Entered by"])
        self.assess.doubleClicked.connect(self.open_assessment)
        self.assess.setToolTip("Double-click to open or edit an entry")
        minor = QHBoxLayout()
        minor.addWidget(button("Open entry", self.open_assessment))
        minor.addWidget(button("Delete entry", self.delete_assessment, "danger"))
        minor.addStretch(1)
        minor.addWidget(button("Edit client", self.edit_client))
        minor.addWidget(button("Delete client", self.delete_client, "danger",
                               "Permanently delete this client (reason required, audited)"))
        self.detail_widgets = [self.start_btn, self.add_btn, self.report_btn, self.pdf_btn]

        right = QVBoxLayout()
        right.addWidget(self.name)
        right.addWidget(self.meta)
        right.addWidget(self.banner)
        right.addSpacing(6)
        right.addLayout(actions)
        right.addSpacing(8)
        right.addWidget(set_role(QLabel("Assessments"), "h2"))
        right.addWidget(self.assess, 1)
        right.addLayout(minor)
        self.minor_buttons = [minor.itemAt(i).widget() for i in range(minor.count())
                              if minor.itemAt(i).widget()]
        right_w = card(layout=right)

        split = QSplitter()
        split.addWidget(left_w)
        split.addWidget(right_w)
        split.setSizes([360, 900])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.addWidget(split)
        self._enable(False)

    def _enable(self, on: bool):
        for w in self.detail_widgets + self.minor_buttons:
            w.setEnabled(on)

    def search(self):
        rows = self.service.search_clients(self.q_name.text(), self.q_dob.text())
        fill(self.results, [[f"{r['last_name']}, {r['first_name']}", r["dob"], r["flow"]]
                            for r in rows], [r["id"] for r in rows])
        self.main.toast(f"{len(rows)} client(s) found", "info")

    def _select(self):
        items = self.results.selectedItems()
        if items:
            cid = items[0].data(Qt.ItemDataRole.UserRole)
            if cid != self.client_id:
                self.show_client(cid)

    def show_client(self, cid: int | None, log: bool = True):
        self.client_id = cid
        self.assess.setRowCount(0)
        if cid is None:
            self.client = None
            self.name.setText("No client selected")
            self.meta.setText("Search for a client, or start a new intake.")
            self.banner.hide()
            self._enable(False)
            return
        c = self.service.get_client(cid, log=log)
        self.client = c
        self.name.setText(f"{c['first_name']} {c['last_name']}")
        asrs = "  |  ASRS enabled" if c["flow"] == "A" and c["asrs_enabled"] else ""
        self.meta.setText(f"Ref {c['ref_code']}  |  DOB {c['dob']}  |  Age {c['age']}  |  "
                          f"Grade {c['grade'] or 'n/a'}\n{FLOW_LABELS[c['flow']]}{asrs}")
        self.add_menu.clear()
        entered = self.service.list_assessments(cid)
        done = {a["instrument"] for a in entered}
        for inst in self.service.available_instruments(cid):
            mark = f"{CHECK}  " if inst.key in done else "     "
            act = self.add_menu.addAction(f"{mark}{inst.short}: {inst.name}")
            act.triggered.connect(lambda _=False, k=inst.key: self.add_assessment(k))
        fill(self.assess, [[INSTRUMENTS[a["instrument"]].short,
                            dict(INSTRUMENTS[a["instrument"]].variants).get(a["variant"],
                                                                            a["variant"]),
                            a["administered_on"], a["scores"].summary, a["updated_by"]]
                           for a in entered], [a["id"] for a in entered])
        alerts = [a for a in entered if any(w.startswith("SAFETY ALERT")
                                            for w in a["scores"].warnings)]
        if alerts:
            self.banner.setText("SAFETY ALERT: critical items endorsed on "
                                + ", ".join(INSTRUMENTS[a["instrument"]].short for a in alerts)
                                + ". Complete and document a risk assessment.")
            set_role(self.banner, "banner-danger")
            self.banner.show()
        elif self.service.report_is_stale(cid):
            self.banner.setText("Scores changed after the last report version. Review the "
                                "report before exporting.")
            set_role(self.banner, "banner-warn")
            self.banner.show()
        else:
            self.banner.hide()
        self._enable(True)

    def _selected_assessment(self) -> int | None:
        items = self.assess.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None

    # Actions ----------------------------------------------------------------
    def start_session(self):
        existing = self.service.todays_interview(self.client_id)
        if existing:
            existing = self.service.get_assessment(self.client_id, existing["id"])
        dlg = AssessmentDialog(self, self.service, self.client, "interview", existing)
        if dlg.exec():
            self.main.toast("Session notes saved (encrypted)")
            self.show_client(self.client_id, log=False)

    def add_assessment(self, key: str):
        dlg = AssessmentDialog(self, self.service, self.client, key)
        if dlg.exec():
            self.main.toast(f"{INSTRUMENTS[key].short} saved and scored")
            self.show_client(self.client_id, log=False)

    def open_assessment(self):
        aid = self._selected_assessment()
        if aid is None:
            return
        a = self.service.get_assessment(self.client_id, aid)
        allowed = {i.key for i in self.service.available_instruments(self.client_id)}
        if a["instrument"] not in allowed:
            return error(self, "This measure is no longer part of the client's flow. It still "
                               "appears in the report and can be deleted.")
        dlg = AssessmentDialog(self, self.service, self.client, a["instrument"], a)
        if dlg.exec():
            self.main.toast(f"{INSTRUMENTS[a['instrument']].short} updated and re-scored")
            self.show_client(self.client_id, log=False)

    def delete_assessment(self):
        aid = self._selected_assessment()
        if aid is None:
            return error(self, "Select an entry first.")
        dlg = ReasonDialog(self, f"assessment entry #{aid}", self.client["ref_code"])
        if dlg.exec():
            self.service.delete_assessment(self.client_id, aid, dlg.reason_text())
            self.main.toast("Entry deleted and recorded in the audit trail")
            self.show_client(self.client_id, log=False)

    def edit_client(self):
        dlg = ClientDialog(self, self.service, self.service.get_client(self.client_id, log=False))
        if dlg.exec():
            self.main.toast("Client details saved")
            self.show_client(self.client_id, log=False)

    def delete_client(self):
        c = self.client
        dlg = ReasonDialog(self, f"client {c['ref_code']} and ALL entries and reports",
                           c["ref_code"])
        if not dlg.exec():
            return
        counts = self.service.delete_client(self.client_id, dlg.reason_text())
        self.main.toast(f"Client deleted ({counts['assessments']} entries, "
                        f"{counts['report_versions']} report versions); audited")
        self.results.setRowCount(0)
        self.show_client(None)

    def open_report(self):
        ReportEditor(self, self.service, self.client_id, self.main.toast).exec()
        self.show_client(self.client_id, log=False)

    def export_pdf(self):
        if self.service.latest_report(self.client_id) is None:
            if not confirm(self, "No report has been saved yet. Create the report draft now "
                                 "and review it before export?"):
                return
            return self.open_report()
        if export_pdf_flow(self, self.service, self.client_id):
            self.main.toast("Encrypted PDF exported")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self, service, on_lock, on_prefs_changed=None):
        super().__init__()
        self.service = service
        self.on_lock = on_lock
        self.on_prefs_changed = on_prefs_changed or (lambda: None)
        self.resize(1320, 840)
        self.setMinimumSize(1024, 680)

        self.dashboard = DashboardPage(self)
        self.clients = ClientsPage(self)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.clients)

        side = QWidget(objectName="sidebar")
        side.setFixedWidth(220)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(14, 18, 14, 14)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(logo_pixmap(36))
        brand.addWidget(logo)
        name = QLabel(f"<b style='font-size:15pt;color:#ffffff'>{config.APP_NAME}</b>")
        brand.addWidget(name, 1)
        sv.addLayout(brand)
        sv.addSpacing(18)
        self.nav = QButtonGroup(self)
        self.nav_dash = self._nav_button(sv, "▦   Dashboard", self.go_dashboard)
        self.nav_clients = self._nav_button(sv, "☺   Clients", self.go_clients)
        sv.addStretch(1)
        for text, slot in (("⚙   Preferences", self.preferences),
                           ("?   Help", self.getting_started),
                           (f"{LOCK}   Lock", lambda: self.on_lock("LOGOUT"))):
            b = QPushButton(text)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(slot)
            sv.addWidget(b)

        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(side)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.lock_label = QLabel()
        self.toast_label = QLabel()
        self.statusBar().addPermanentWidget(self.lock_label)
        self.statusBar().addWidget(self.toast_label, 1)
        self._toast_timer = QTimer(self, singleShot=True, interval=5000)
        self._toast_timer.timeout.connect(lambda: self.toast_label.setText(""))
        self._build_menus()

    def _nav_button(self, layout, text, slot) -> QPushButton:
        b = QPushButton(text)
        b.setCheckable(True)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        self.nav.addButton(b)
        layout.addWidget(b)
        return b

    def _build_menus(self):
        mb = self.menuBar()
        f = mb.addMenu("File")
        self._act(f, "New client", self.new_client, QKeySequence.StandardKey.New)
        self._act(f, "Find client", self.go_clients, QKeySequence.StandardKey.Find)
        f.addSeparator()
        self._act(f, "Preferences...", self.preferences, QKeySequence.StandardKey.Preferences)
        self._act(f, "Change my password", lambda: admin.ChangePasswordDialog(
            self, self.service).exec())
        self._act(f, "Lock now", lambda: self.on_lock("LOGOUT"), "Ctrl+L")
        f.addSeparator()
        self._act(f, "Quit", self.close, QKeySequence.StandardKey.Quit)
        a = mb.addMenu("Admin")
        self._act(a, "Audit trail", lambda: self._admin(admin.AuditDialog))
        self._act(a, "User accounts", lambda: self._admin(admin.UsersDialog))
        self._act(a, "Retention review", lambda: self._admin(admin.RetentionDialog))
        a.addSeparator()
        self._act(a, "Export encrypted archive", self.export_archive)
        self._act(a, "Test a backup (restore test)",
                  lambda: self._admin(lambda p, s: admin.verify_backup_flow(p, s)))
        self._act(a, "Restore from archive", self.restore_archive)
        hm = mb.addMenu("Help")
        self._act(hm, "Getting started", self.getting_started)
        self._act(hm, "User guide" if not config.SUPPORT_URL else "Support and documentation",
                  lambda: help_ui.open_support(self))
        self._act(hm, "Scoring reference", lambda: help_ui.DocViewer(
            self, "Scoring reference", help_ui.read_text("docs/SCORING_REFERENCE.md")).exec())
        self._act(hm, "Data retention and deletion", lambda: help_ui.DocViewer(
            self, "Data retention", help_ui.read_text("docs/DATA_RETENTION.md")).exec())
        hm.addSeparator()
        self._act(hm, f"About {config.APP_NAME}", lambda: help_ui.AboutDialog(self).exec())

    def _act(self, menu, text, slot, shortcut=None):
        act = QAction(text, self)
        if shortcut is not None:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)

    # Navigation ---------------------------------------------------------------
    def start(self):
        s = self.service.session
        self.setWindowTitle(f"{config.APP_NAME}  |  {s.username}")
        self.lock_label.setText(f"{LOCK} Encrypted (AES-256)  |  Signed in as {s.username} "
                                f"({s.role})  ")
        self.lock_label.setToolTip("All client data is encrypted at rest on this Mac. Nothing "
                                   "is sent over the network.")
        self.go_dashboard()

    def go_dashboard(self):
        self.nav_dash.setChecked(True)
        self.stack.setCurrentWidget(self.dashboard)
        self.dashboard.refresh()

    def go_clients(self):
        self.nav_clients.setChecked(True)
        self.stack.setCurrentWidget(self.clients)
        self.clients.q_name.setFocus()

    def open_client(self, cid: int):
        self.go_clients()
        ref = self.service.get_client(cid, log=False)["ref_code"]
        self.clients.q_name.setText(ref)
        self.clients.q_dob.clear()
        self.clients.search()
        self.clients.results.selectRow(0)
        self.clients.show_client(cid)

    def toast(self, message: str, kind: str = "ok"):
        t = tokens()
        color = {"ok": t["ok"], "info": t["muted"], "warn": t["warn"]}.get(kind, t["ok"])
        prefix = f"{CHECK}  " if kind == "ok" else ""
        self.toast_label.setStyleSheet(f"color: {color}; font-weight: 600; padding-left: 6px;")
        self.toast_label.setText(prefix + message)
        self._toast_timer.start()

    # Actions ----------------------------------------------------------------
    def new_client(self):
        dlg = ClientDialog(self, self.service)
        if dlg.exec():
            self.toast("Client created (encrypted)")
            self.open_client(dlg.client_id)

    def preferences(self):
        help_ui.PreferencesDialog(self, self.service, self._prefs_applied).exec()

    def _prefs_applied(self):
        self.on_prefs_changed()
        self.toast("Preferences saved")

    def getting_started(self):
        help_ui.GettingStartedDialog(self).exec()

    def _admin(self, factory):
        if not self.service.session.is_admin:
            return error(self, "This function requires the admin role.")
        dlg = factory(self, self.service)
        if dlg is not None:
            dlg.exec()

    def export_archive(self):
        if not self.service.session.is_admin:
            return error(self, "This function requires the admin role.")
        dlg = PasswordDialog(
            self, "Archive password",
            "The archive holds ALL client data, encrypted with AES-256-GCM under this password. "
            "It is separate from your login password. A lost archive password cannot be "
            "recovered. Store archives only on encrypted media.")
        if not dlg.exec():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save archive", f"clinassess_{date.today().isoformat()}.caarchive",
            "ClinAssess archive (*.caarchive)")
        if path:
            self.service.export_archive(path, dlg.password())
            self.toast("Encrypted archive saved; record it in your backup log")

    def restore_archive(self):
        if not self.service.session.is_admin:
            return error(self, "This function requires the admin role.")
        path, _ = QFileDialog.getOpenFileName(self, "Choose archive", "",
                                              "ClinAssess archive (*.caarchive)")
        if not path or not confirm(self, "Restoring REPLACES all current client data with the "
                                         "archive contents. Continue?"):
            return
        dlg = PasswordDialog(self, "Archive password", "Enter the archive password.",
                             confirm_twice=False, enforce_policy=False)
        if not dlg.exec():
            return
        try:
            self.service.restore_archive(path, dlg.password())
        except Exception as exc:
            return error(self, f"Restore failed ({type(exc).__name__}): wrong password or "
                               "damaged archive. Current data was not changed.")
        self.clients.show_client(None)
        self.go_dashboard()
        self.toast("Archive restored")

    def closeEvent(self, event):
        self.on_lock("LOGOUT", quit_app=True)
        event.accept()
