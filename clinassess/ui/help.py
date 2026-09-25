"""About, Getting Started, documentation viewer, license, and Preferences."""

from __future__ import annotations

import platform

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QHBoxLayout, QLabel, QTabWidget, QTextBrowser, QVBoxLayout,
                               QWidget)

from .. import config
from .. import prefs as prefs_mod
from ..scoring import INSTRUMENTS
from .branding import logo_pixmap
from .theme import set_role

GETTING_STARTED = f"""
# Getting started with {config.APP_NAME}

**1. Add a client.** Choose **Clients** in the sidebar, then **New client**. Enter the name,
date of birth, grade, and the assessment flow:

- **Flow A** for children and adolescents (6+)
- **Flow B** for adolescents and adults

For Flow A, tick **Include ASRS** only when it is developmentally appropriate.

**2. Start a session.** On the client page, **Start session** opens today's interview notes.
Type notes under each domain. Everything saves encrypted when you click **Save**.

**3. Enter assessments.** **Add assessment** lists only the measures for the client's flow.
Enter each response by item number from the paper form. The score panel on the right
updates as you type, and flags problems in red.

- For **MMPI-3, Conners 4, Brown EF/A, and TOVA**, score the test in the publisher's software
  first, then type the scores in. These tests use licensed norms that the app does not include.

**4. Write the report.** **Generate report** builds a draft from the interview and scores.
Edit any section. Score tables and headings are locked so they always match the data.
Replace every *[Clinician to complete ...]* prompt, then **Save version**.

**5. Export the PDF.** **Export PDF** creates an AES-256 encrypted PDF. Choose a password and
give it to the recipient separately (for example, by phone). Printing is disabled.

**Security habits**

- The app locks itself after a period of inactivity. **Cmd+L** locks it at once.
- There is **no password recovery**. Keep your password and your archive passwords safe.
- Test a backup every month: **Admin > Test a backup**.
"""


def _credits_html() -> str:
    rows = "".join(
        f"<tr><td><b>{i.short}</b></td><td>{i.name}</td><td>{i.verification.title()}</td></tr>"
        for i in INSTRUMENTS.values() if i.key != "interview")
    return f"""
    <h3>Assessment instruments</h3>
    <p>{config.APP_NAME} does not include, sell, or license any assessment instrument. Clinicians
    must obtain each instrument, and any required license, from its publisher. Item wording is
    shown only where the author's terms permit reproduction (Weiss scales). All names are the
    property of their owners and are used only to identify compatible data entry.</p>
    <table cellpadding="4">{rows}</table>
    <p><small>SDQ: Robert Goodman / Youth in Mind. ASRS v1.1: World Health Organization.
    CATS: Sachser, Berliner, Goldbeck et al. (CATS Consortium). WSR-II and WFIRS: Margaret D.
    Weiss. SNAP-IV: James M. Swanson. MMPI-3: University of Minnesota Press (Pearson).
    Conners 4: Multi-Health Systems. Brown EF/A Scales: Pearson. T.O.V.A.: The TOVA Company.
    </small></p>
    <h3>Open-source software</h3>
    <table cellpadding="4">
    <tr><td><b>Qt for Python (PySide6) {pyside_version}</b></td><td>LGPL v3</td></tr>
    <tr><td><b>Qt 6</b></td><td>LGPL v3</td></tr>
    <tr><td><b>cryptography</b></td><td>Apache 2.0 / BSD</td></tr>
    <tr><td><b>ReportLab</b></td><td>BSD</td></tr>
    <tr><td><b>pypdf</b></td><td>BSD</td></tr>
    <tr><td><b>Python {platform.python_version()}</b></td><td>PSF License</td></tr>
    </table>
    <p><small>Full license texts: THIRD_PARTY_NOTICES.txt in the installer. The LGPL libraries
    are dynamically linked and may be replaced by the user.</small></p>
    """


def read_text(rel: str) -> str:
    try:
        return config.resource_path(rel).read_text("utf-8")
    except OSError:
        return f"({rel} is not available in this build.)"


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {config.APP_NAME}")
        self.resize(720, 620)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(logo_pixmap(96))
        top.addWidget(logo)
        info = QVBoxLayout()
        info.addWidget(set_role(QLabel(config.APP_NAME), "h1"))
        info.addWidget(QLabel(config.APP_TAGLINE))
        info.addWidget(set_role(QLabel(
            f"Version {config.APP_VERSION}  |  License terms {config.EULA_VERSION}  |  "
            f"{config.COPYRIGHT}"), "muted"))
        top.addLayout(info, 1)
        lay.addLayout(top)
        tabs = QTabWidget()
        about = QTextBrowser()
        about.setHtml(
            f"<p>{config.APP_NAME} stores all data on this computer, encrypted with AES-256. "
            "It has no network features and sends no data anywhere.</p>"
            f"<p>{config.APP_NAME} is a scoring and documentation aid. It is not a medical "
            "device and does not make diagnoses. Results must be interpreted by a qualified "
            "clinician.</p>")
        tabs.addTab(about, "About")
        credits = QTextBrowser()
        credits.setHtml(_credits_html())
        tabs.addTab(credits, "Credits")
        lic = QTextBrowser()
        lic.setPlainText(read_text("LICENSE.txt"))
        tabs.addTab(lic, "License agreement")
        lay.addWidget(tabs, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class DocViewer(QDialog):
    def __init__(self, parent, title: str, markdown: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 700)
        lay = QVBoxLayout(self)
        view = QTextBrowser()
        view.setOpenExternalLinks(False)
        view.setMarkdown(markdown)
        lay.addWidget(view)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class GettingStartedDialog(DocViewer):
    def __init__(self, parent):
        super().__init__(parent, "Getting started", GETTING_STARTED)
        self.again = QCheckBox("Show this guide at login")
        self.again.setChecked(prefs_mod.load()["show_getting_started"])
        self.layout().insertWidget(1, self.again)

    def done(self, r):
        p = prefs_mod.load()
        p["show_getting_started"] = self.again.isChecked()
        prefs_mod.save(p)
        super().done(r)


def open_support(parent):
    if config.SUPPORT_URL:
        QDesktopServices.openUrl(QUrl(config.SUPPORT_URL))
    else:
        DocViewer(parent, "User guide", read_text("README.md")).exec()


class PreferencesDialog(QDialog):
    """Display preferences for everyone; security settings for admins."""

    def __init__(self, parent, service, on_apply):
        super().__init__(parent)
        self.service = service
        self.on_apply = on_apply
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(520)
        p = prefs_mod.load()
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.theme = QComboBox()
        for key, label in (("system", "Match macOS"), ("light", "Light"), ("dark", "Dark")):
            self.theme.addItem(label, key)
        self.theme.setCurrentIndex(self.theme.findData(p["theme"]))
        self.font = QComboBox()
        self.font.addItems(list(prefs_mod.FONT_SCALES))
        self.font.setCurrentText(p["font_scale"])
        self.guide = QCheckBox("Show Getting Started at login")
        self.guide.setChecked(p["show_getting_started"])
        self.advanced = QCheckBox("Show advanced settings")
        self.advanced.setChecked(p["advanced"])
        form.addRow("Appearance:", self.theme)
        form.addRow("Text size:", self.font)
        form.addRow("", self.guide)
        form.addRow("", self.advanced)
        lay.addLayout(form)

        self.adv_box = QWidget()
        adv = QFormLayout(self.adv_box)
        adv.addRow(set_role(QLabel("Advanced (admin)"), "h2"))
        self.idle = QComboBox()
        for m in config.IDLE_TIMEOUT_CHOICES_MIN:
            self.idle.addItem(f"{m} minutes", m)
        self.idle.setCurrentIndex(self.idle.findData(service.idle_timeout_seconds() // 60))
        self.idle.setToolTip("Automatic logoff after this much inactivity (HIPAA "
                             "164.312(a)(2)(iii)). 15 minutes or less is recommended.")
        is_admin = service.session.is_admin
        self.idle.setEnabled(is_admin)
        adv.addRow("Auto-lock after:", self.idle)
        adv.addRow(set_role(QLabel(
            f"Data folder: {config.data_dir()}\nEncryption: AES-256-GCM (database, audit log, "
            "archives), AES-256 (PDF).\nKey derivation: scrypt N=2^17, r=8, p=1."), "muted"))
        if not is_admin:
            adv.addRow(set_role(QLabel("Only an admin can change security settings."), "muted"))
        lay.addWidget(self.adv_box)
        self.adv_box.setVisible(p["advanced"])
        self.advanced.toggled.connect(self.adv_box.setVisible)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _save(self):
        p = prefs_mod.load()
        p.update(theme=self.theme.currentData(), font_scale=self.font.currentText(),
                 show_getting_started=self.guide.isChecked(), advanced=self.advanced.isChecked())
        prefs_mod.save(p)
        if self.service.session.is_admin:
            minutes = self.idle.currentData()
            if minutes * 60 != self.service.idle_timeout_seconds():
                self.service.set_idle_timeout(minutes)
        self.on_apply()
        self.accept()
