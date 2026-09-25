"""Application entry point: splash, setup, login, idle auto-lock, errors."""

from __future__ import annotations

import sys
import time

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from .. import config
from .. import prefs as prefs_mod
from ..service import AppService, NotLoggedIn
from . import theme
from .branding import app_icon, splash
from .help import GettingStartedDialog
from .login import LoginDialog, SetupDialog
from .main_window import MainWindow

SPLASH_SECONDS = 1.2


class IdleWatcher(QObject):
    """Restarts the idle timer on any keyboard or mouse input."""

    EVENTS = {QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove,
              QEvent.Type.Wheel}

    def __init__(self, timer: QTimer):
        super().__init__()
        self.timer = timer

    def eventFilter(self, obj, event):
        if event.type() in self.EVENTS and self.timer.isActive():
            self.timer.start()
        return False


class Controller:
    def __init__(self, app: QApplication):
        self.app = app
        self.service = AppService()
        self.window: MainWindow | None = None
        self.idle = QTimer(singleShot=True)
        self.idle.timeout.connect(lambda: self.lock("AUTO_LOCK"))
        self.watcher = IdleWatcher(self.idle)
        app.installEventFilter(self.watcher)
        self._locking = False

    def start(self) -> bool:
        if self.service.needs_setup:
            if not SetupDialog(self.service).exec():
                return False
        elif not LoginDialog(self.service).exec():
            return False
        self._show_main(first=True)
        return True

    def _show_main(self, first: bool = False):
        if self.window is None:
            self.window = MainWindow(self.service, self.lock, self.reapply_theme)
        self.window.start()
        self.window.show()
        self.idle.setInterval(self.service.idle_timeout_seconds() * 1000)
        self.idle.start()
        if first and prefs_mod.load()["show_getting_started"]:
            QTimer.singleShot(300, lambda: self.window and
                              GettingStartedDialog(self.window).exec())

    def reapply_theme(self):
        theme.apply(self.app)
        if self.service.session is not None:
            self.idle.setInterval(self.service.idle_timeout_seconds() * 1000)
            self.idle.start()
        if self.window is not None:
            self.window.go_dashboard()

    def lock(self, reason: str = "LOGOUT", quit_app: bool = False):
        """Log out: close open dialogs, clear the screen, drop keys, re-prompt."""
        if self._locking or self.service.session is None:
            if quit_app:
                self.app.quit()
            return
        self._locking = True
        self.idle.stop()
        for w in self.app.topLevelWidgets():
            if isinstance(w, (QDialog, QMessageBox)) and w.isVisible():
                w.reject()
        self.service.logout(reason)
        if self.window is not None:
            self.window.hide()
            self.window.deleteLater()
            self.window = None
        self._locking = False
        if quit_app:
            self.app.quit()
            return
        QTimer.singleShot(0, lambda: self._relogin(reason))

    def _relogin(self, reason: str):
        msg = ("Locked after inactivity. Unsaved entries in open forms were discarded."
               if reason == "AUTO_LOCK" else "")
        if LoginDialog(self.service, msg).exec():
            self._show_main()
        else:
            self.app.quit()


def _install_excepthook(controller: Controller):
    def hook(exc_type, exc, tb):
        if issubclass(exc_type, NotLoggedIn):
            return  # a dialog closed by auto-lock tried to continue; nothing to do
        # Exception messages can contain PHI, so only the exception type is
        # logged. Nothing is written to stderr or to crash files.
        try:
            if controller.service.session is not None:
                controller.service.audit("APP_ERROR", details={"type": exc_type.__name__})
        except Exception:
            pass
        QMessageBox.critical(None, "Unexpected error",
                             f"An unexpected error occurred ({exc_type.__name__}). Your last "
                             "saved data is safe. If this repeats, contact support. Never "
                             "send client data to support.")
    sys.excepthook = hook


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)
    theme.apply(app)

    sp = splash()
    sp.show()
    deadline = time.monotonic() + SPLASH_SECONDS
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    controller = Controller(app)
    _install_excepthook(controller)
    sp.close()

    if not controller.start():
        return 0
    code = app.exec()
    if controller.service.session is not None:
        controller.service.logout("LOGOUT")
    return code
