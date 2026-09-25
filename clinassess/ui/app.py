"""Application entry point: setup, login, idle auto-lock, and error handling."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from .. import config
from ..service import AppService, NotLoggedIn
from .login import LoginDialog, SetupDialog
from .main_window import MainWindow


class IdleWatcher(QObject):
    """Resets the idle timer on any keyboard or mouse input."""

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
        self.idle = QTimer(interval=config.IDLE_TIMEOUT_SECONDS * 1000, singleShot=True)
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
        self._show_main()
        return True

    def _show_main(self):
        if self.window is None:
            self.window = MainWindow(self.service, self.lock)
        self.window.refresh_title()
        self.window.show()
        self.window.search()
        self.idle.start()

    def lock(self, reason: str = "LOGOUT", quit_app: bool = False):
        """Log out: close open dialogs, clear the screen, drop keys, re-prompt."""
        if self._locking or self.service.session is None:
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
                             "saved data is safe. If this repeats, contact support.")
    sys.excepthook = hook


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    controller = Controller(app)
    _install_excepthook(controller)
    if not controller.start():
        return 0
    code = app.exec()
    if controller.service.session is not None:
        controller.service.logout("LOGOUT")
    return code
