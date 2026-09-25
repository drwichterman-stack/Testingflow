"""Capture a completed paper form with the camera and read the marked responses.

Flow: the camera preview opens; the clinician holds the page up and
clicks Snap. The page is found and straightened. Each block of response
boxes is outlined once (drag a box, then fit the corners); outlines are
saved per form and reused on the next capture. Every read is shown on the
photo (green read, amber check, red not read) before it is applied, and
the data-entry form then highlights everything that needs a person's
check.

Photos stay in memory. They are never written to disk or stored in the
database, and they are discarded when this dialog closes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QGraphicsScene, QGraphicsView, QHBoxLayout,
                               QHeaderView, QInputDialog, QLabel, QPushButton, QSplitter,
                               QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from .. import omr
from ..scoring.base import Field
from .common import confirm, error
from .theme import set_role

try:  # Qt Multimedia ships with PySide6; guard in case a build leaves it out
    from PySide6.QtMultimedia import QCamera, QImageCapture, QMediaCaptureSession, QMediaDevices
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAVE_CAMERA_API = True
except ImportError:  # pragma: no cover
    HAVE_CAMERA_API = False

COLORS = {omr.OK: "#1b7a4b", omr.CHECK: "#d08a00", omr.BLANK: "#c62828",
          omr.MULTIPLE: "#c62828", "outline": "#1f5fa8", "selected": "#e0457b"}
LAYOUT_VERSION = 1

INSTRUCTIONS = (
    "<b>1.</b> Hold the page flat, filling most of the frame, in front of a darker background. "
    "Keep it still and click <b>Snap</b>.<br>"
    "<b>2.</b> Select a block on the right, click <b>Outline</b>, and drag a box from the "
    "top-left corner of the first item's first response box to the bottom-right corner of "
    "the last item's last response box. Drag the pink corners to fit.<br>"
    "<b>3.</b> Check the dots: <span style='color:#1b7a4b'>green</span> read, "
    "<span style='color:#d08a00'>amber</span> check, <span style='color:#c62828'>red</span> "
    "no single mark. Outlines are saved for this form and reused next time.")


@dataclass
class Block:
    fields: list[Field]
    page: int | None = None
    quad: np.ndarray | None = None      # corners in page pixels (TL, TR, BR, BL)
    reverse: bool = False
    read: omr.BlockRead | None = None
    items: list[omr.ItemRead] = field(default_factory=list)
    error: str = ""

    @property
    def label(self) -> str:
        section = self.fields[0].section or "Responses"
        nums = [re.match(r"\D*?(\d+)", f.label) for f in (self.fields[0], self.fields[-1])]
        if len(self.fields) > 1 and all(nums):
            span = f"{nums[0].group(1)}-{nums[1].group(1)}"
            return section if span in section else f"{section}: items {span}"
        if len(self.fields) == 1:
            return f"{section}: {self.fields[0].label}"
        return f"{section} ({len(self.fields)} items)"

    def counts(self) -> dict:
        c = {s: 0 for s in (omr.OK, omr.CHECK, omr.BLANK, omr.MULTIPLE)}
        for it in self.items:
            c[it.status] += 1
        return c


def gray_to_pixmap(gray: np.ndarray) -> QPixmap:
    g = np.ascontiguousarray(gray, dtype=np.uint8)
    img = QImage(g.data, g.shape[1], g.shape[0], g.shape[1], QImage.Format.Format_Grayscale8)
    return QPixmap.fromImage(img.copy())


def qimage_to_gray(img: QImage) -> np.ndarray:
    g = img.convertToFormat(QImage.Format.Format_Grayscale8)
    ptr = g.constBits()
    data = bytes(ptr) if not hasattr(ptr, "tobytes") else ptr.tobytes()
    return omr.from_qimage_bytes(data[: g.bytesPerLine() * g.height()], g.width(), g.height(),
                                 g.bytesPerLine())


class PageCanvas(QGraphicsView):
    """Shows a straightened page with block outlines and read results."""

    def __init__(self, on_drawn, on_corner_moved):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.on_drawn = on_drawn
        self.on_corner_moved = on_corner_moved
        self.drawing = False
        self._start: QPointF | None = None
        self._rubber = None
        self._drag_corner: int | None = None
        self._selected_quad: np.ndarray | None = None
        self._has_page = False

    def show_page(self, gray: np.ndarray | None, blocks: list[Block], page: int,
                  selected: int | None):
        sc = self.scene()
        sc.clear()
        self._rubber = None
        self._selected_quad = None
        self._has_page = gray is not None
        if gray is None:
            return
        sc.addPixmap(gray_to_pixmap(gray))
        sc.setSceneRect(QRectF(0, 0, gray.shape[1], gray.shape[0]))
        scale = gray.shape[1] / omr.PAGE_W
        for idx, b in enumerate(blocks):
            if b.page != page or b.quad is None:
                continue
            sel = idx == selected
            poly = QPolygonF([QPointF(x, y) for x, y in b.quad])
            pen = QPen(QColor(COLORS["selected" if sel else "outline"]), 3 * scale)
            sc.addPolygon(poly, pen)
            if b.read is not None:
                pts = omr.cell_points(b.read, b.quad)
                r = 11 * scale
                for row in b.read.rows:
                    col = row.column
                    if col is None:  # no single mark: flag at the left of the row
                        x, y = pts[row.row, 0]
                        c = QColor(COLORS[row.status])
                        sc.addRect(QRectF(x - 3 * r, y - r, 2 * r * 0.8, 2 * r),
                                   QPen(c, 2 * scale), QBrush(c))
                        continue
                    x, y = pts[row.row, col]
                    c = QColor(COLORS[row.status])
                    c.setAlpha(170)
                    sc.addEllipse(QRectF(x - r, y - r, 2 * r, 2 * r), QPen(c, 2 * scale),
                                  QBrush(c))
            if sel:
                self._selected_quad = b.quad.copy()
                for x, y in b.quad:
                    h = 9 * scale
                    sc.addEllipse(QRectF(x - h, y - h, 2 * h, 2 * h),
                                  QPen(QColor("#ffffff"), 2 * scale),
                                  QBrush(QColor(COLORS["selected"])))
        self.fit()

    def fit(self):
        if self._has_page:
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit()

    def wheelEvent(self, e):
        if e.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            self.scale(f, f)
        else:
            super().wheelEvent(e)

    def _near_corner(self, view_pos) -> int | None:
        if self._selected_quad is None:
            return None
        for i, (x, y) in enumerate(self._selected_quad):
            p = self.mapFromScene(QPointF(x, y))
            if (p - view_pos).manhattanLength() < 18:
                return i
        return None

    def mousePressEvent(self, e):
        if not self._has_page or e.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(e)
        corner = self._near_corner(e.position().toPoint())
        if corner is not None:
            self._drag_corner = corner
            return
        if self.drawing:
            self._start = self.mapToScene(e.position().toPoint())
            self._rubber = self.scene().addRect(QRectF(self._start, self._start),
                                                QPen(QColor(COLORS["selected"]), 2))

    def mouseMoveEvent(self, e):
        pos = self.mapToScene(e.position().toPoint())
        if self._drag_corner is not None and self._selected_quad is not None:
            self._selected_quad[self._drag_corner] = [pos.x(), pos.y()]
            self.on_corner_moved(self._selected_quad.copy(), final=False)
            return
        if self._rubber is not None and self._start is not None:
            self._rubber.setRect(QRectF(self._start, pos).normalized())
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._drag_corner is not None:
            self._drag_corner = None
            self.on_corner_moved(self._selected_quad.copy(), final=True)
            return
        if self._rubber is not None:
            r = self._rubber.rect()
            self._rubber = None
            self._start = None
            if r.width() > 10 and r.height() > 10:
                self.on_drawn(np.array([[r.left(), r.top()], [r.right(), r.top()],
                                        [r.right(), r.bottom()], [r.left(), r.bottom()]]))
            return
        super().mouseReleaseEvent(e)


class CaptureFormDialog(QDialog):
    """Camera capture and mark reading for one paper form.

    After exec() returns Accepted, `results` maps field key -> omr.ItemRead
    and `counts` holds per-status totals.
    """

    def __init__(self, parent, service, instrument, variant: str, fields: list[Field]):
        super().__init__(parent)
        self.service = service
        self.inst = instrument
        self.variant = variant
        self.setWindowTitle(f"Capture paper form: {instrument.short}")
        self.resize(1250, 820)
        self.pages: list[np.ndarray] = []
        self.page_found: list[bool] = []
        self.blocks = [Block(fs) for _, fs in omr.choice_groups(fields)]
        self.results: dict[str, omr.ItemRead] = {}
        self.counts: dict[str, int] = {}
        self.camera = None
        self.session = None
        self.capture = None
        self._layout = self._load_layout()

        # --- left: camera or page review -----------------------------------
        self.stack = QStackedWidget()
        cam_page = QWidget()
        cl = QVBoxLayout(cam_page)
        cam_bar = QHBoxLayout()
        self.camera_box = QComboBox()
        self.camera_box.currentIndexChanged.connect(self._camera_changed)
        cam_bar.addWidget(QLabel("Camera:"))
        cam_bar.addWidget(self.camera_box, 1)
        self.mirror = QCheckBox("Mirror image")
        self.mirror.setToolTip("Tick if text in the snapped photo reads backwards.")
        cam_bar.addWidget(self.mirror)
        cl.addLayout(cam_bar)
        self.video = QVideoWidget() if HAVE_CAMERA_API else QLabel()
        self.video.setMinimumSize(560, 420)
        cl.addWidget(self.video, 1)
        self.cam_status = set_role(QLabel(""), "muted")
        self.cam_status.setWordWrap(True)
        cl.addWidget(self.cam_status)
        snap_row = QHBoxLayout()
        self.back_btn = QPushButton("Back to photos")
        self.back_btn.clicked.connect(self._show_review)
        self.snap_btn = set_role(QPushButton("\U0001F4F7  Snap"), "primary")
        self.snap_btn.setShortcut(Qt.Key.Key_Space)
        self.snap_btn.clicked.connect(self._snap)
        snap_row.addWidget(self.back_btn)
        snap_row.addStretch(1)
        snap_row.addWidget(set_role(self.snap_btn, "big"))
        cl.addLayout(snap_row)
        self.stack.addWidget(cam_page)

        review = QWidget()
        rl = QVBoxLayout(review)
        page_bar = QHBoxLayout()
        self.page_box = QComboBox()
        self.page_box.currentIndexChanged.connect(lambda _=0: self._refresh())
        page_bar.addWidget(QLabel("Photo:"))
        page_bar.addWidget(self.page_box)
        retake = QPushButton("Retake this page")
        retake.clicked.connect(lambda: self._open_camera(replace=True))
        more = QPushButton("Snap next page")
        more.clicked.connect(lambda: self._open_camera(replace=False))
        page_bar.addWidget(retake)
        page_bar.addWidget(more)
        page_bar.addStretch(1)
        rl.addLayout(page_bar)
        self.canvas = PageCanvas(self._quad_drawn, self._corner_moved)
        rl.addWidget(self.canvas, 1)
        self.page_status = set_role(QLabel(""), "muted")
        self.page_status.setWordWrap(True)
        rl.addWidget(self.page_status)
        self.stack.addWidget(review)
        self._replace_index: int | None = None

        # --- right: blocks ----------------------------------------------------
        right = QWidget()
        rr = QVBoxLayout(right)
        how = QLabel(INSTRUCTIONS)
        how.setWordWrap(True)
        rr.addWidget(how)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Block", "Photo", "Result"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._block_selected)
        rr.addWidget(self.table, 1)
        self.columns_lbl = set_role(QLabel(""), "muted")
        self.columns_lbl.setWordWrap(True)
        rr.addWidget(self.columns_lbl)
        btns = QHBoxLayout()
        self.outline_btn = QPushButton("Outline")
        self.outline_btn.setCheckable(True)
        self.outline_btn.toggled.connect(self._outline_toggled)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_block)
        self.split_btn = QPushButton("Split block...")
        self.split_btn.setToolTip("Use when a block continues in another column or on the "
                                  "next page, or has a heading between its items.")
        self.split_btn.clicked.connect(self._split_block)
        for b in (self.outline_btn, self.clear_btn, self.split_btn):
            btns.addWidget(b)
        rr.addLayout(btns)
        self.reverse = QCheckBox("Columns run from highest to lowest response")
        self.reverse.toggled.connect(self._reverse_toggled)
        rr.addWidget(self.reverse)
        self.notes = set_role(QLabel(""), "banner-warn")
        self.notes.setWordWrap(True)
        self.notes.hide()
        rr.addWidget(self.notes)
        self.save_layout = QCheckBox("Save outlines for this form")
        self.save_layout.setChecked(True)
        rr.addWidget(self.save_layout)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        rr.addWidget(self.summary)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.stack)
        split.addWidget(right)
        split.setSizes([800, 450])
        lay = QVBoxLayout(self)
        lay.addWidget(split, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.apply_btn = bb.addButton("Apply to form", QDialogButtonBox.ButtonRole.AcceptRole)
        set_role(self.apply_btn, "primary")
        bb.accepted.connect(self._apply)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        self._fill_table()
        self._open_camera(replace=False)

    # ------------------------------------------------------------------ camera
    def _open_camera(self, replace: bool):
        self._replace_index = self.page_box.currentIndex() if replace and self.pages else None
        self.back_btn.setVisible(bool(self.pages))
        self.stack.setCurrentIndex(0)
        self.snap_btn.setEnabled(False)
        if not HAVE_CAMERA_API:
            self.cam_status.setText("Camera support (Qt Multimedia) is not installed.")
            return
        if not self._camera_permitted():
            return
        devices = QMediaDevices.videoInputs()
        if not devices:
            self.cam_status.setText("No camera found. Connect a camera, or check that no "
                                    "other app is using it, then reopen this window.")
            return
        if self.camera_box.count() != len(devices):
            self.camera_box.blockSignals(True)
            self.camera_box.clear()
            for d in devices:
                self.camera_box.addItem(d.description(), d)
            default = QMediaDevices.defaultVideoInput()
            for i, d in enumerate(devices):
                if d.id() == default.id():
                    self.camera_box.setCurrentIndex(i)
            self.camera_box.blockSignals(False)
        self._start_camera(self.camera_box.currentData())

    def _camera_permitted(self) -> bool:
        try:
            from PySide6.QtCore import QCameraPermission
        except ImportError:  # Qt < 6.5: the OS prompts on first use
            return True
        app = QApplication.instance()
        perm = QCameraPermission()
        status = app.checkPermission(perm)
        if status == Qt.PermissionStatus.Granted:
            return True
        if status == Qt.PermissionStatus.Undetermined:
            self.cam_status.setText("Waiting for camera permission...")
            app.requestPermission(perm, self, lambda *_: self._open_camera(
                self._replace_index is not None))
            return False
        self.cam_status.setText(
            "Camera access is turned off for ClinAssess. On a Mac, open System Settings > "
            "Privacy & Security > Camera and turn on ClinAssess (or Terminal, when running "
            "from source), then reopen this window.")
        return False

    def _camera_changed(self, _=None):
        if self.stack.currentIndex() == 0 and self.camera_box.currentData() is not None:
            self._start_camera(self.camera_box.currentData())

    def _start_camera(self, device):
        self._stop_camera()
        self.camera = QCamera(device)
        formats = device.videoFormats()
        if formats:  # highest resolution: more pixels per response box
            best = max(formats, key=lambda f: f.resolution().width() * f.resolution().height())
            self.camera.setCameraFormat(best)
        self.session = QMediaCaptureSession()
        self.session.setCamera(self.camera)
        self.session.setVideoOutput(self.video)
        self.capture = QImageCapture()
        self.session.setImageCapture(self.capture)
        self.capture.imageCaptured.connect(self._captured)
        self.capture.errorOccurred.connect(
            lambda _id, _err, msg: self.cam_status.setText(f"Could not take the photo: {msg}"))
        self.capture.readyForCaptureChanged.connect(self.snap_btn.setEnabled)
        self.camera.errorOccurred.connect(
            lambda _err, msg: self.cam_status.setText(f"Camera error: {msg}"))
        self.camera.start()
        self.cam_status.setText("Hold the completed form up to the camera, fill most of the "
                                "picture with the page, keep it still, then click Snap "
                                "(or press Space).")

    def _stop_camera(self):
        if self.camera is not None:
            self.camera.stop()
        self.camera = self.session = self.capture = None

    def _snap(self):
        if self.capture is not None and self.capture.isReadyForCapture():
            self.snap_btn.setEnabled(False)
            self.capture.capture()

    def _captured(self, _id, image: QImage):
        gray = qimage_to_gray(image)
        if self.mirror.isChecked():
            gray = np.ascontiguousarray(gray[:, ::-1])
        self.add_photo(gray, self._replace_index)

    def _show_review(self):
        self._stop_camera()
        self.stack.setCurrentIndex(1)
        self._refresh()

    # ------------------------------------------------------------------ pages
    def add_photo(self, gray: np.ndarray, replace: int | None = None) -> int:
        """Add a snapped photo (greyscale array) as a page; returns its index."""
        quad = omr.find_page(gray)
        page = omr.straighten(gray, quad) if quad is not None else np.ascontiguousarray(gray)
        if replace is None:
            self.pages.append(page)
            self.page_found.append(quad is not None)
            idx = len(self.pages) - 1
            self.page_box.addItem(f"Page {idx + 1}")
        else:
            idx = replace
            self.pages[idx] = page
            self.page_found[idx] = quad is not None
        for b in self.blocks:
            if b.page == idx:
                b.read, b.items = None, []
        self._apply_layout(idx)
        for i, b in enumerate(self.blocks):
            if b.page == idx and b.quad is not None:
                self._read(i)
        self.page_box.setCurrentIndex(idx)
        self._replace_index = None
        self._show_review()
        return idx

    # ------------------------------------------------------------------ layout
    def _load_layout(self) -> dict:
        try:
            data = self.service.scan_layout(self.inst.key, self.variant) or {}
        except (ValueError, PermissionError):
            return {}
        if data.get("version") != LAYOUT_VERSION:
            return {}
        keys = [f.key for b in self.blocks for f in b.fields]
        for saved in data.get("blocks", []):  # recreate saved splits
            if saved.get("first") in keys and saved.get("last") in keys:
                self._split_before(saved["first"])
                nxt = keys.index(saved["last"]) + 1
                if nxt < len(keys):
                    self._split_before(keys[nxt])
        return data

    def _split_before(self, key: str) -> None:
        for i, b in enumerate(self.blocks):
            ks = [f.key for f in b.fields]
            if key in ks[1:]:
                j = ks.index(key)
                self.blocks[i:i + 1] = [Block(b.fields[:j], reverse=b.reverse),
                                        Block(b.fields[j:], reverse=b.reverse)]
                return

    def _apply_layout(self, page_idx: int) -> None:
        h, w = self.pages[page_idx].shape
        for saved in self._layout.get("blocks", []):
            if saved.get("page") != page_idx:
                continue
            for b in self.blocks:
                if b.fields[0].key == saved.get("first") and b.fields[-1].key == saved.get("last") \
                        and b.quad is None:
                    try:
                        q = np.array(saved["quad"], float).reshape(4, 2) * [w, h]
                    except (KeyError, TypeError, ValueError):
                        continue
                    b.page, b.quad, b.reverse = page_idx, q, bool(saved.get("reverse"))

    def layout(self) -> dict:
        blocks = []
        for b in self.blocks:
            if b.quad is None or b.page is None:
                continue
            h, w = self.pages[b.page].shape
            blocks.append({"first": b.fields[0].key, "last": b.fields[-1].key, "page": b.page,
                           "quad": (b.quad / [w, h]).round(5).tolist(), "reverse": b.reverse})
        return {"version": LAYOUT_VERSION, "blocks": blocks}

    # ------------------------------------------------------------------ blocks
    def _selected(self) -> int | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return rows[0].row() if rows else None

    def set_block_quad(self, idx: int, page: int, quad) -> None:
        b = self.blocks[idx]
        b.page, b.quad = page, np.asarray(quad, float)
        self._read(idx)
        self._refresh()

    def _read(self, idx: int) -> None:
        b = self.blocks[idx]
        b.read, b.items, b.error = None, [], ""
        if b.quad is None or b.page is None:
            return
        try:
            b.read = omr.read_block(self.pages[b.page], b.quad, len(b.fields),
                                    len(b.fields[0].options))
            b.items = omr.map_block(b.fields, b.read, b.reverse)
        except ValueError as exc:
            b.read, b.items, b.error = None, [], str(exc)

    def _fill_table(self):
        sel = self._selected()
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.blocks))
        for i, b in enumerate(self.blocks):
            if b.error:
                res = b.error
            elif not b.items:
                res = "Not outlined"
            else:
                c = b.counts()
                res = ", ".join(f"{n} {s}" for s, n in (("read", c[omr.OK]),
                                ("check", c[omr.CHECK]), ("blank", c[omr.BLANK]),
                                ("multiple", c[omr.MULTIPLE])) if n) or "-"
            for col, text in enumerate((b.label, "" if b.page is None else str(b.page + 1), res)):
                it = QTableWidgetItem(text)
                if col == 2 and b.items:
                    c = b.counts()
                    bad = c[omr.BLANK] + c[omr.MULTIPLE]
                    it.setForeground(QColor(COLORS[omr.BLANK] if bad else
                                            COLORS[omr.CHECK] if c[omr.CHECK] else COLORS[omr.OK]))
                self.table.setItem(i, col, it)
        self.table.resizeColumnToContents(1)
        self.table.blockSignals(False)
        if sel is not None and sel < len(self.blocks):
            self.table.selectRow(sel)
        elif self.blocks and sel is None:
            self.table.selectRow(0)

    def _block_selected(self):
        idx = self._selected()
        if idx is None:
            return
        b = self.blocks[idx]
        opts = b.fields[0].options
        order = list(reversed(opts)) if b.reverse else opts
        self.columns_lbl.setText(
            f"{len(b.fields)} items, {len(opts)} response columns, left to right: " +
            " | ".join(lbl for _, lbl in order))
        self.reverse.blockSignals(True)
        self.reverse.setChecked(b.reverse)
        self.reverse.blockSignals(False)
        if b.page is not None and b.page < len(self.pages) and \
                self.page_box.currentIndex() != b.page:
            self.page_box.setCurrentIndex(b.page)  # triggers _refresh
        else:
            self._refresh(fill=False)

    def _outline_toggled(self, on: bool):
        self.canvas.drawing = on
        self.canvas.setCursor(Qt.CursorShape.CrossCursor if on else Qt.CursorShape.ArrowCursor)

    def _quad_drawn(self, quad: np.ndarray):
        idx = self._selected()
        if idx is None or not self.pages:
            return
        self.outline_btn.setChecked(False)
        self.set_block_quad(idx, self.page_box.currentIndex(), quad)

    def _corner_moved(self, quad: np.ndarray, final: bool):
        idx = self._selected()
        if idx is None:
            return
        self.blocks[idx].quad = quad
        if final:
            self._read(idx)
            self._refresh()

    def _clear_block(self):
        idx = self._selected()
        if idx is not None:
            b = self.blocks[idx]
            b.page = b.quad = b.read = None
            b.items, b.error = [], ""
            self._refresh()

    def _reverse_toggled(self, on: bool):
        idx = self._selected()
        if idx is not None:
            self.blocks[idx].reverse = on
            self._read(idx)
            self._refresh()

    def _split_block(self):
        idx = self._selected()
        if idx is None or len(self.blocks[idx].fields) < 2:
            return
        b = self.blocks[idx]
        labels = [f.label for f in b.fields[1:]]
        choice, ok = QInputDialog.getItem(self, "Split block",
                                          "Start the second part at item:", labels, 0, False)
        if ok:
            key = b.fields[1 + labels.index(choice)].key
            self._split_before(key)
            self._refresh()

    def _refresh(self, fill: bool = True):
        if fill:
            self._fill_table()
        page = self.page_box.currentIndex()
        gray = self.pages[page] if 0 <= page < len(self.pages) else None
        self.canvas.show_page(gray, self.blocks, page, self._selected())
        if gray is not None:
            self.page_status.setText(
                "Page edges found; the photo was straightened." if self.page_found[page] else
                "Page edges were not found, so the whole photo is used and saved outlines may "
                "not line up. For best results hold the page against a darker background, or "
                "fit the outlines by hand.")
        idx = self._selected()
        notes = []
        if idx is not None:
            b = self.blocks[idx]
            if b.error:
                notes.append(b.error)
            if b.read is not None:
                notes += b.read.notes
        self.notes.setText("\n".join(notes))
        self.notes.setVisible(bool(notes))
        tot = {s: 0 for s in (omr.OK, omr.CHECK, omr.BLANK, omr.MULTIPLE)}
        for b in self.blocks:
            for s, n in b.counts().items():
                tot[s] += n
        n_items = sum(len(b.fields) for b in self.blocks)
        done = sum(tot.values())
        self.summary.setText(
            f"<b>{done} of {n_items} items outlined.</b> {tot[omr.OK]} read, "
            f"{tot[omr.CHECK]} to check, {tot[omr.BLANK]} blank, "
            f"{tot[omr.MULTIPLE]} with more than one mark.")
        self.apply_btn.setEnabled(done > 0)

    # ------------------------------------------------------------------ finish
    def _apply(self):
        results = {it.key: it for b in self.blocks for it in b.items}
        if not results:
            return error(self, "Outline at least one block first.")
        missing = sum(len(b.fields) for b in self.blocks if not b.items)
        if missing and not confirm(self, f"{missing} items are not outlined and will be left "
                                         "as they are on the form. Apply the rest?"):
            return
        self.results = results
        self.counts = {s: sum(1 for it in results.values() if it.status == s)
                       for s in (omr.OK, omr.CHECK, omr.BLANK, omr.MULTIPLE)}
        self.counts["pages"] = len(self.pages)
        if self.save_layout.isChecked():
            try:
                self.service.save_scan_layout(self.inst.key, self.variant, self.layout())
            except (ValueError, PermissionError) as exc:
                error(self, f"Outlines were not saved: {exc}")
        self.accept()

    def done(self, r):
        self._stop_camera()
        self.pages.clear()  # drop the photos from memory
        self.canvas.scene().clear()
        super().done(r)
