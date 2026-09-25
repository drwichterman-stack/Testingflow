"""On-device speech-to-text for clinician dictation (macOS only).

Uses Apple's Speech framework (SFSpeechRecognizer) with
`requiresOnDeviceRecognition = True`. With that flag the system never
sends audio to Apple's servers: if on-device recognition is unavailable
for the current language or Mac, recognition fails instead of falling
back to the cloud, and the app shows the Dictate button as unavailable.

Audio is streamed from the microphone into the recognizer in memory.
No audio is written to disk, and only the recognized text is inserted
into the note (where it is saved encrypted like any typed text).

Intended use: the clinician dictating their own notes after or between
sessions. Recording a client session raises consent requirements that
differ by state; see docs/COMPLIANCE_REVIEW.md.

Requirements: macOS 13+, pyobjc-framework-Speech and
pyobjc-framework-AVFoundation, the Info.plist usage strings
NSMicrophoneUsageDescription and NSSpeechRecognitionUsageDescription
(added by build_macos.sh), and the user's permission for microphone
and speech recognition.

STATUS: written against Apple's documented API; it could not be
executed in the Linux build environment. Test on a Mac before release
(see the offline and dictation test script in COMPLIANCE_REVIEW.md).
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Signal

AVAILABLE = False
UNAVAILABLE_REASON = "On-device dictation requires macOS."

if sys.platform == "darwin":
    try:
        import AVFoundation  # type: ignore[import-not-found]
        import Speech  # type: ignore[import-not-found]
        from Foundation import NSLocale  # type: ignore[import-not-found]
        AVAILABLE = True
        UNAVAILABLE_REASON = ""
    except ImportError:
        UNAVAILABLE_REASON = ("Dictation components are not installed "
                              "(pyobjc-framework-Speech, pyobjc-framework-AVFoundation).")


def on_device_supported() -> tuple[bool, str]:
    """True only if this Mac can transcribe the current language on-device."""
    if not AVAILABLE:
        return False, UNAVAILABLE_REASON
    rec = Speech.SFSpeechRecognizer.alloc().initWithLocale_(NSLocale.currentLocale())
    if rec is None:
        return False, "Speech recognition does not support the current language."
    if not rec.supportsOnDeviceRecognition():
        return False, ("This Mac cannot transcribe the current language on-device. "
                       "Dictation is disabled so no audio is ever sent to a server.")
    return True, ""


class OnDeviceDictation(QObject):
    """Start/stop microphone dictation. Signals are delivered on the Qt thread."""

    partial = Signal(str)   # running transcript for the current dictation
    finished = Signal(str)  # final transcript
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = None
        self._request = None
        self._task = None
        self._last = ""

    @property
    def running(self) -> bool:
        return self._engine is not None

    def start(self) -> None:
        ok, why = on_device_supported()
        if not ok:
            self.failed.emit(why)
            return
        status = Speech.SFSpeechRecognizer.authorizationStatus()
        if status == Speech.SFSpeechRecognizerAuthorizationStatusNotDetermined:
            Speech.SFSpeechRecognizer.requestAuthorization_(lambda s: None)
            self.failed.emit("Allow speech recognition in the macOS prompt, then click "
                             "Dictate again.")
            return
        if status != Speech.SFSpeechRecognizerAuthorizationStatusAuthorized:
            self.failed.emit("Speech recognition is not allowed. Enable it in System "
                             "Settings > Privacy & Security > Speech Recognition.")
            return
        recognizer = Speech.SFSpeechRecognizer.alloc().initWithLocale_(NSLocale.currentLocale())
        request = Speech.SFSpeechAudioBufferRecognitionRequest.alloc().init()
        request.setRequiresOnDeviceRecognition_(True)  # never use Apple's servers
        request.setShouldReportPartialResults_(True)
        if hasattr(request, "setAddsPunctuation_"):
            request.setAddsPunctuation_(True)
        engine = AVFoundation.AVAudioEngine.alloc().init()
        node = engine.inputNode()
        fmt = node.outputFormatForBus_(0)

        def tap(buffer, when):
            request.appendAudioPCMBuffer_(buffer)
        node.installTapOnBus_bufferSize_format_block_(0, 1024, fmt, tap)
        engine.prepare()
        started, err = engine.startAndReturnError_(None)
        if not started:
            node.removeTapOnBus_(0)
            self.failed.emit("Could not start the microphone. Check System Settings > "
                             "Privacy & Security > Microphone.")
            return

        def handler(result, error):
            if result is not None:
                self._last = str(result.bestTranscription().formattedString())
                self.partial.emit(self._last)
                if result.isFinal():
                    self._teardown()
                    self.finished.emit(self._last)
            elif error is not None and self._engine is not None:
                self._teardown()
                self.failed.emit("Dictation stopped: " + str(error.localizedDescription()))

        self._engine, self._request, self._last = engine, request, ""
        self._task = recognizer.recognitionTaskWithRequest_resultHandler_(request, handler)

    def stop(self) -> None:
        """Stop listening; the final transcript arrives via `finished`."""
        if self._engine is None:
            return
        self._engine.stop()
        self._engine.inputNode().removeTapOnBus_(0)
        self._request.endAudio()

    def _teardown(self) -> None:
        if self._engine is not None:
            try:
                self._engine.stop()
                self._engine.inputNode().removeTapOnBus_(0)
            except Exception:
                pass
        self._engine = self._request = self._task = None
