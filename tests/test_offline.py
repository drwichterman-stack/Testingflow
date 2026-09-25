"""Offline guarantee: the app must work with no network at all.

Every socket operation is replaced with one that raises, then the whole
workflow runs: setup, login, intake, scoring, report editing, encrypted
PDF, archive, backup test, audit verification, and the GUI. A second
test cuts the network in the middle of a session. A static test checks
that no module in the package imports networking code.
"""

import ast
import os
import socket
from pathlib import Path

import pytest

from clinassess.keystore import KeyStore
from clinassess.service import AppService

PKG = Path(__file__).resolve().parent.parent / "clinassess"
NETWORK_MODULES = {"socket", "ssl", "urllib", "http", "requests", "httpx", "aiohttp",
                   "ftplib", "smtplib", "xmlrpc", "websocket", "PySide6.QtNetwork",
                   "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"}


class NetworkUsed(AssertionError):
    pass


def _deny(*a, **k):
    raise NetworkUsed("network access attempted")


@pytest.fixture
def no_network(monkeypatch):
    for name in ("connect", "connect_ex", "sendto", "bind"):
        monkeypatch.setattr(socket.socket, name, _deny)
    monkeypatch.setattr(socket, "create_connection", _deny)
    monkeypatch.setattr(socket, "getaddrinfo", _deny)
    monkeypatch.setattr(socket, "gethostbyname", _deny)


def _workflow(svc, home):
    cid = svc.create_client({"last_name": "Offline", "first_name": "Test", "dob": "2012-01-01",
                             "grade": "8", "flow": "A", "asrs_enabled": True})
    svc.save_assessment(cid, "interview", "clinical", "2026-09-01", {"referral": "x"})
    svc.save_assessment(cid, "sdq", "parent", "2026-09-01", {f"item{i}": 1 for i in range(1, 26)})
    svc.save_assessment(cid, "asrs", "self", "2026-09-01", {"item1": 3})
    rep = svc.open_report(cid)
    svc.save_report(cid, {**rep["sections"], "diagnostic": "Offline edit."})
    svc.export_report_pdf(cid, home / "r.pdf", "Pdf-Password-2026")
    svc.export_archive(home / "a.caarchive", "Archive-Pass-2026")
    assert svc.verify_backup(home / "a.caarchive", "Archive-Pass-2026")["ok"]
    svc.dashboard()
    _, result = svc.read_audit()
    assert result.ok
    return cid


def test_full_workflow_with_network_blocked(no_network, home):
    svc = AppService(KeyStore(home / "keystore.json", scrypt_n=2 ** 12),
                     home / "db.enc", home / "audit.log.enc")
    svc.setup("drsmith", "Correct-Horse-42")
    _workflow(svc, home)
    svc.logout()
    svc.login("drsmith", "Correct-Horse-42")


def test_network_lost_mid_session(svc, home, monkeypatch):
    cid = svc.create_client({"last_name": "Mid", "first_name": "Session", "dob": "2010-01-01",
                             "grade": "", "flow": "B"})
    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, _deny)
    monkeypatch.setattr(socket, "getaddrinfo", _deny)
    svc.save_assessment(cid, "asrs", "self", "2026-09-01", {"item1": 4})
    svc.open_report(cid)
    svc.export_report_pdf(cid, home / "mid.pdf", "Pdf-Password-2026")


def test_gui_with_network_blocked(no_network, svc):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QtWidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from clinassess.ui import theme
    from clinassess.ui.main_window import MainWindow
    theme.apply(app)
    w = MainWindow(svc, lambda *a, **k: None)
    w.start()
    w.go_clients()
    w.clients.search()


def test_no_networking_imports():
    offenders = []
    for path in PKG.rglob("*.py"):
        tree = ast.parse(path.read_text("utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                if any(n == m or n.startswith(m + ".") for m in NETWORK_MODULES):
                    offenders.append(f"{path.name}: {n}")
    assert offenders == []
