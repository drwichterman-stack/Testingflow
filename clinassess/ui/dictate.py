"""Dictate button that inserts on-device speech-to-text into a text box."""

from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QPushButton

from .. import dictation
from .common import error


class DictateButton(QPushButton):
    IDLE = "\U0001F3A4  Dictate"
    LIVE = "■  Stop dictation"

    def __init__(self, target: QPlainTextEdit):
        super().__init__(self.IDLE)
        self.target = target
        self.engine = dictation.OnDeviceDictation(self)
        self.engine.partial.connect(self._partial)
        self.engine.finished.connect(self._done)
        self.engine.failed.connect(self._failed)
        self._start = self._len = 0
        ok, why = (dictation.on_device_supported() if dictation.AVAILABLE
                   else (False, dictation.UNAVAILABLE_REASON))
        self.setEnabled(ok)
        self.setToolTip("Speech-to-text processed entirely on this Mac. Audio is never "
                        "saved or sent anywhere." if ok else why)
        self.clicked.connect(self._toggle)

    def _toggle(self):
        if self.engine.running:
            self.engine.stop()
            return
        cur = self.target.textCursor()
        self._start, self._len = cur.position(), 0
        self.setText(self.LIVE)
        self.engine.start()

    def _partial(self, text: str):
        cur = self.target.textCursor()
        cur.setPosition(self._start)
        cur.setPosition(self._start + self._len, QTextCursor.MoveMode.KeepAnchor)
        cur.insertText(text)
        self._len = len(text)
        self.target.setTextCursor(cur)

    def _done(self, text: str):
        self._partial(text)
        self.setText(self.IDLE)

    def _failed(self, message: str):
        self.setText(self.IDLE)
        error(self, message, "Dictation")
