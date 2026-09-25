"""Optical mark reading (OMR) for paper forms photographed with a camera.

The clinician holds the completed form up to the camera and snaps a
photo. The page is found and straightened (find_page, straighten). Each
block of response boxes (for example SDQ items 1-25, three columns) is
outlined once per form layout; outlines are stored relative to the page,
so later snaps of the same form reuse them. For each block this module:

  1. Straightens the outlined quadrilateral into a rectangle, which
     corrects rotation and camera perspective.
  2. Converts it to black and white with a local (adaptive) threshold,
     so uneven room lighting does not read as ink.
  3. Removes long printed rules (table lines) and finds the row and
     column centres from the table lines or the printed boxes. If they
     cannot be found reliably, it assumes evenly spaced rows and columns,
     says so, and marks every read in the block for checking.
  4. Measures the ink in every cell, subtracts the ink of an unmarked
     cell in the same column (the printed box or digit), and decides for
     each item: one clear mark, a faint mark to check, no mark, or more
     than one mark.

Nothing is guessed silently: faint, blank, and multiple marks are
returned with a status so the form can highlight them for review. Item
text is never read, so no instrument content is needed or stored.

Photos are held in memory only and never written to disk. Only numpy and
Pillow are used (no OpenCV, no cloud OCR service); the module makes no
network connections.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image

# Size of one cell after straightening. Large enough to keep pen strokes,
# small enough to be fast.
CELL_W, CELL_H = 48, 40

# Cell score = ink coverage / COVER_SCALE + peak local density / PEAK_SCALE.
# Decisions use "excess": the score minus that of an unmarked cell in the
# same column. Tuned on synthetic forms (tests/test_omr.py); see
# docs/CAMERA_FORM_CAPTURE.md.
LOCAL_R = 6            # radius of the peak-density window, straightened pixels
COVER_SCALE = 0.05     # typical ink coverage of a pen X in a cell
PEAK_SCALE = 0.30      # typical peak density of a pen stroke
MIN_MARK = 0.6         # below this excess (in the units above), a cell is unmarked
NOISE_FACTOR = 3.0     # threshold is at least this many noise deviations
CLEAR_FACTOR = 2.0     # a mark this many thresholds strong is "clear"
SECOND_RATIO = 0.5     # second mark at least this share of the first = multiple
MAX_SHIFT = 0.35       # detected row/column may sit this share of a pitch off even spacing

OK, CHECK, BLANK, MULTIPLE = "ok", "check", "blank", "multiple"
FLAG_TEXT = {CHECK: "Check", BLANK: "No mark", MULTIPLE: "2+ marks"}
STATUS_TEXT = {
    OK: "Read",
    CHECK: "Faint or unclear mark: check",
    BLANK: "No mark found",
    MULTIPLE: "More than one mark",
}


# ---------------------------------------------------------------------------
# Geometry

def _homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """3x3 matrix mapping the 4 src points onto the 4 dst points."""
    a, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b += [u, v]
    try:
        h = np.linalg.solve(np.array(a, float), np.array(b, float))
    except np.linalg.LinAlgError as exc:
        raise ValueError("The outlined area is not a valid four-sided shape.") from exc
    return np.append(h, 1.0).reshape(3, 3)


def _quad_ok(quad: np.ndarray) -> bool:
    """Convex, non-degenerate, corners in order."""
    cross = []
    for i in range(4):
        p, q, r = quad[i], quad[(i + 1) % 4], quad[(i + 2) % 4]
        cross.append((q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0]))
    return all(c > 0 for c in cross) or all(c < 0 for c in cross)


def warp_quad(gray: np.ndarray, quad, out_w: int, out_h: int) -> np.ndarray:
    """Straighten the quadrilateral (TL, TR, BR, BL) into an out_w x out_h image."""
    quad = np.asarray(quad, float)
    if quad.shape != (4, 2) or not _quad_ok(quad):
        raise ValueError("The outlined area is not a valid four-sided shape.")
    # Downscale first when the source is much finer than the target, so thin
    # pen strokes are averaged rather than skipped by point sampling.
    x0, y0 = np.floor(quad.min(0)).astype(int)
    x1, y1 = np.ceil(quad.max(0)).astype(int)
    x0, y0 = max(x0 - 2, 0), max(y0 - 2, 0)
    x1, y1 = min(x1 + 2, gray.shape[1]), min(y1 + 2, gray.shape[0])
    if x1 - x0 < 4 or y1 - y0 < 4:
        raise ValueError("The outlined area is outside the image or too small.")
    crop = gray[y0:y1, x0:x1]
    local = quad - [x0, y0]
    scale = min((x1 - x0) / out_w, (y1 - y0) / out_h)
    if scale > 1.5:
        f = scale / 1.2
        size = (max(int(crop.shape[1] / f), 1), max(int(crop.shape[0] / f), 1))
        crop = np.asarray(Image.fromarray(crop).resize(size, Image.Resampling.BOX))
        local = local * [crop.shape[1] / (x1 - x0), crop.shape[0] / (y1 - y0)]
    dst = np.array([[0, 0], [out_w, 0], [out_w, out_h], [0, out_h]], float)
    h = _homography(dst, local)
    u, v = np.meshgrid(np.arange(out_w) + 0.5, np.arange(out_h) + 0.5)
    den = h[2, 0] * u + h[2, 1] * v + h[2, 2]
    sx = (h[0, 0] * u + h[0, 1] * v + h[0, 2]) / den - 0.5
    sy = (h[1, 0] * u + h[1, 1] * v + h[1, 2]) / den - 0.5
    return _bilinear(crop.astype(np.float32), sx, sy)


def _bilinear(img: np.ndarray, sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
    hgt, wid = img.shape
    outside = (sx < -0.5) | (sy < -0.5) | (sx > wid - 0.5) | (sy > hgt - 0.5)
    sx = np.clip(sx, 0, wid - 1)
    sy = np.clip(sy, 0, hgt - 1)
    x0 = np.floor(sx).astype(int)
    y0 = np.floor(sy).astype(int)
    x1 = np.minimum(x0 + 1, wid - 1)
    y1 = np.minimum(y0 + 1, hgt - 1)
    fx, fy = sx - x0, sy - y0
    top = img[y0, x0] * (1 - fx) + img[y0, x1] * fx
    bot = img[y1, x0] * (1 - fx) + img[y1, x1] * fx
    out = top * (1 - fy) + bot * fy
    out[outside] = 255.0
    return out


def from_qimage_bytes(data: bytes, width: int, height: int, stride: int) -> np.ndarray:
    """Greyscale array from raw 8-bit greyscale scanlines (Qt Format_Grayscale8)."""
    a = np.frombuffer(data, np.uint8, count=stride * height).reshape(height, stride)
    return np.ascontiguousarray(a[:, :width])


def _otsu(values: np.ndarray) -> float:
    hist = np.bincount(values.ravel(), minlength=256).astype(float)
    p = hist / hist.sum()
    omega = p.cumsum()
    mu = (p * np.arange(256)).cumsum()
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (mu[-1] * omega - mu) ** 2 / (omega * (1 - omega))
    return float(np.nanargmax(between))


def _largest_component(mask: np.ndarray) -> np.ndarray:
    """Largest 4-connected region of True pixels (small masks only)."""
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    best, best_n, cur = 0, 0, 0
    flat = mask.ravel()
    lab = labels.ravel()
    for start in np.flatnonzero(flat):
        if lab[start]:
            continue
        cur += 1
        lab[start] = cur
        stack, n = [start], 0
        while stack:
            i = stack.pop()
            n += 1
            y, x = divmod(i, w)
            for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1), (i - w, y > 0), (i + w, y < h - 1)):
                if ok and flat[j] and not lab[j]:
                    lab[j] = cur
                    stack.append(j)
        if n > best_n:
            best, best_n = cur, n
    return labels == best if best else np.zeros_like(mask)


def find_page(gray: np.ndarray) -> np.ndarray | None:
    """Corners (TL, TR, BR, BL) of the paper page in a photo, or None.

    The page is taken to be the largest bright region. Its corners are the
    region's extreme points along the two diagonals, which tolerates a
    tilt of about 30 degrees and fingers holding the edges.
    """
    h, w = gray.shape
    f = max(h, w) / 320
    small = np.asarray(Image.fromarray(gray).resize(
        (max(int(w / f), 1), max(int(h / f), 1)), Image.Resampling.BOX))
    bright = small > _otsu(small)
    # Close small gaps (printed text) so the page is one region.
    grown = bright.copy()
    for _ in range(2):
        g = grown.copy()
        g[1:] |= grown[:-1]
        g[:-1] |= grown[1:]
        g[:, 1:] |= grown[:, :-1]
        g[:, :-1] |= grown[:, 1:]
        grown = g
    region = _largest_component(grown) & bright  # undo the growth at the edges
    area = region.sum()
    if area < 0.15 * region.size:
        return None
    ys, xs = np.nonzero(region)
    s, d = xs + ys, xs - ys
    quad = np.array([[xs[s.argmin()], ys[s.argmin()]], [xs[d.argmax()], ys[d.argmax()]],
                     [xs[s.argmax()], ys[s.argmax()]], [xs[d.argmin()], ys[d.argmin()]]],
                    float) + 0.5
    if not _quad_ok(quad):
        return None
    x, y = quad[:, 0], quad[:, 1]
    quad_area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    # A page fills its outline; a blob of background light does not.
    if quad_area <= 0 or not 0.8 <= area / quad_area <= 1.25:
        return None
    if quad_area > 0.97 * region.size:  # page fills the frame: nothing to crop
        return None
    return quad * f


PAGE_W = 1275  # straightened page width in pixels (US Letter at 150 dpi)


def straighten(gray: np.ndarray, quad) -> np.ndarray:
    """Warp the page to an upright rectangle PAGE_W wide."""
    q = np.asarray(quad, float)
    width = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
    height = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
    out_h = int(round(PAGE_W * height / max(width, 1)))
    return np.clip(warp_quad(gray, q, PAGE_W, max(out_h, 1)), 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Image processing (numpy only)

def _box_mean(img: np.ndarray, r: int) -> np.ndarray:
    """Mean over a (2r+1) square window, edges replicated."""
    p = np.pad(img.astype(np.float64), r + 1, mode="edge")
    s = p.cumsum(0).cumsum(1)
    n = 2 * r + 1
    tot = s[n:, n:] - s[:-n, n:] - s[n:, :-n] + s[:-n, :-n]
    return (tot / (n * n))[: img.shape[0], : img.shape[1]]


def binarize(gray: np.ndarray, radius: int, offset: float = 10.0) -> np.ndarray:
    """Adaptive threshold: ink where a pixel is darker than its neighbourhood."""
    return gray < (_box_mean(gray, radius) - offset)


def _runs(mask: np.ndarray, length: int, axis: int) -> np.ndarray:
    """Pixels belonging to a straight run of at least `length` ink pixels."""
    if length < 2:
        return mask.copy()
    m = np.moveaxis(mask, axis, -1).astype(np.int32)
    c = np.concatenate([np.zeros(m.shape[:-1] + (1,), np.int32), m.cumsum(-1)], -1)
    full = (c[..., length:] - c[..., :-length]) == length  # window start positions
    starts = np.concatenate([full, np.zeros(m.shape[:-1] + (length - 1,), bool)], -1)
    # Dilate the start positions forward by length-1 to cover the run.
    s = np.concatenate([np.zeros(starts.shape[:-1] + (1,), np.int32),
                        starts.astype(np.int32).cumsum(-1)], -1)
    idx = np.arange(m.shape[-1])
    lo = np.maximum(idx - length + 1, 0)
    covered = (s[..., idx + 1] - s[..., lo]) > 0
    return np.moveaxis(covered, -1, axis)


def rule_masks(ink: np.ndarray, min_h: int, min_v: int) -> tuple[np.ndarray, np.ndarray]:
    """Printed horizontal and vertical lines longer than a cell edge."""
    thick_v = ink.copy()
    thick_v[1:] |= ink[:-1]
    thick_v[:-1] |= ink[1:]
    horiz = _runs(thick_v, min_h, axis=1) & ink
    thick_h = ink.copy()
    thick_h[:, 1:] |= ink[:, :-1]
    thick_h[:, :-1] |= ink[:, 1:]
    vert = _runs(thick_h, min_v, axis=0) & ink
    return horiz, vert


def centres_from_rules(rule_profile: np.ndarray, n: int, pitch: float) -> np.ndarray | None:
    """Cell centres from table rules: n cells need n+1 lines, the outer two
    at the ends of the outlined area (the outline edges count as lines)."""
    on = rule_profile > 0.5
    edges = np.flatnonzero(np.diff(np.concatenate([[0], on.view(np.int8), [0]])))
    lines = [(a + b - 1) / 2 for a, b in zip(edges[::2], edges[1::2])]
    size = len(rule_profile)
    merged: list[float] = []
    for y in lines:
        if merged and y - merged[-1] < 0.3 * pitch:
            merged[-1] = (merged[-1] + y) / 2
        else:
            merged.append(y)
    if not merged or merged[0] > 0.3 * pitch:
        merged.insert(0, 0.0)
    if merged[-1] < size - 1 - 0.3 * pitch:
        merged.append(float(size - 1))
    if len(merged) != n + 1:
        return None
    b = np.array(merged)
    if np.diff(b).min() < 0.45 * pitch:
        return None
    return (b[:-1] + b[1:]) / 2


def _smooth(p: np.ndarray, k: int) -> np.ndarray:
    k = max(int(k) | 1, 1)
    return np.convolve(p, np.ones(k) / k, mode="same")


def find_centers(profile: np.ndarray, n: int, pitch: float) -> tuple[np.ndarray, bool]:
    """Find n band centres in a projection profile.

    Returns (centres, detected). detected is False when n clear bands could
    not be found; the centres are then evenly spaced.
    """
    uniform = (np.arange(n) + 0.5) * (len(profile) / n)
    p = _smooth(profile, pitch / 5)
    top = float(p.max())
    if top <= 0:
        return uniform, False
    for frac in (0.35, 0.25, 0.45, 0.15, 0.55, 0.65):
        on = p > frac * top
        edges = np.flatnonzero(np.diff(np.concatenate([[0], on.view(np.int8), [0]])))
        segs = [[a, b] for a, b in zip(edges[::2], edges[1::2])]
        merged: list[list[int]] = []
        for a, b in segs:
            if merged and a - merged[-1][1] < 0.25 * pitch:
                merged[-1][1] = b
            else:
                merged.append([a, b])
        merged = [s for s in merged if s[1] - s[0] >= 0.12 * pitch]
        if len(merged) != n:
            continue
        centres = np.array([np.average(np.arange(a, b), weights=p[a:b] + 1e-9)
                            for a, b in merged])
        if n > 1 and np.diff(centres).min() < 0.45 * pitch:
            continue
        # The outline covers one run of evenly printed rows, so each band
        # must sit close to its evenly spaced position. Bands that do not
        # (stray marks, leftover line fragments) are not trusted.
        if np.abs(centres - uniform).max() > MAX_SHIFT * (len(profile) / n):
            continue
        return centres, True
    return uniform, False


# ---------------------------------------------------------------------------
# Reading

@dataclass
class RowRead:
    row: int
    column: int | None      # physical column index (left to right), None if unread
    status: str             # OK, CHECK, BLANK, MULTIPLE
    strength: float         # excess ink of the strongest cell
    runner_up: float        # excess ink of the second strongest cell


@dataclass
class BlockRead:
    rows: list[RowRead]
    ink: np.ndarray                 # rows x cols ink fraction per cell
    row_centres: np.ndarray         # in straightened pixels
    col_centres: np.ndarray
    rows_detected: bool
    cols_detected: bool
    width: int
    height: int
    notes: list[str] = field(default_factory=list)

    def cell_centre_fraction(self, r: int, c: int) -> tuple[float, float]:
        """Cell centre as a fraction (0..1) of the outlined area."""
        return self.col_centres[c] / self.width, self.row_centres[r] / self.height


def read_block(gray: np.ndarray, quad, n_rows: int, n_cols: int) -> BlockRead:
    """Read one outlined block of n_rows items x n_cols response columns."""
    if n_rows < 1 or n_cols < 2:
        raise ValueError("A block needs at least one row and two columns.")
    w, h = n_cols * CELL_W, n_rows * CELL_H
    img = warp_quad(gray, quad, w, h)
    ink = binarize(img, radius=CELL_H, offset=10.0)
    horiz, vert = rule_masks(ink, min_h=int(CELL_W * 0.9), min_v=int(CELL_H * 0.9))
    clean = ink & ~(horiz | vert)

    # A ruled table gives exact cell edges; otherwise use the printed boxes.
    rows_c = centres_from_rules(horiz.mean(1), n_rows, CELL_H)
    rows_ok = rows_c is not None
    if not rows_ok:
        rows_c, rows_ok = find_centers(clean.mean(1), n_rows, CELL_H)
    cols_c = centres_from_rules(vert.mean(0), n_cols, CELL_W)
    cols_ok = cols_c is not None
    if not cols_ok:
        cols_c, cols_ok = find_centers(clean.mean(0), n_cols, CELL_W)
    notes = []
    if not rows_ok:
        notes.append("Row positions were estimated (evenly spaced). Check that the outline "
                     "covers exactly the first to the last item.")
    if not cols_ok:
        notes.append("Column positions were estimated (evenly spaced). Check that the "
                     "outline covers exactly the first to the last response column.")

    def half_gaps(c: np.ndarray, pitch: float) -> np.ndarray:
        if len(c) == 1:
            return np.array([pitch / 2])
        d = np.diff(c)
        left = np.concatenate([[d[0]], d])
        right = np.concatenate([d, [d[-1]]])
        return np.minimum(left, right) / 2

    hy = half_gaps(rows_c, CELL_H) * 0.85
    hx = half_gaps(cols_c, CELL_W) * 0.85
    local = _box_mean(clean, LOCAL_R)
    vals = np.zeros((n_rows, n_cols))
    for i, (cy, ry) in enumerate(zip(rows_c, hy)):
        y0, y1 = int(max(cy - ry, 0)), int(min(cy + ry + 1, h))
        for j, (cx, rx) in enumerate(zip(cols_c, hx)):
            x0, x1 = int(max(cx - rx, 0)), int(min(cx + rx + 1, w))
            if y1 > y0 and x1 > x0:
                # Coverage catches large marks (circles, fills); peak local
                # density catches small dense marks (ticks, checks).
                vals[i, j] = (clean[y0:y1, x0:x1].mean() / COVER_SCALE +
                              local[y0:y1, x0:x1].max() / PEAK_SCALE)

    rows = decide(vals)
    if not (rows_ok and cols_ok):
        # Positions are a guess, so no read in this block counts as clear.
        for r in rows:
            if r.status == OK:
                r.status = CHECK
    return BlockRead(rows, vals, rows_c, cols_c, rows_ok, cols_ok, w, h, notes)


def decide(vals: np.ndarray) -> list[RowRead]:
    """Turn a rows x cols ink matrix into one decision per row."""
    n_rows, n_cols = vals.shape
    arg = vals.argmax(1)
    not_top = np.ones_like(vals, bool)
    not_top[np.arange(n_rows), arg] = False
    empty_all = vals[not_top]
    global_base = float(np.median(empty_all)) if empty_all.size else 0.0
    base = np.empty(n_cols)
    for j in range(n_cols):
        e = vals[not_top[:, j], j]
        base[j] = float(np.median(e)) if e.size >= 3 else global_base
    excess = vals - base
    e_empty = excess[not_top]
    if e_empty.size >= 4:
        mad = float(np.median(np.abs(e_empty - np.median(e_empty)))) * 1.4826
    else:
        mad = 0.0
    thr = max(MIN_MARK, NOISE_FACTOR * mad)

    out = []
    for i in range(n_rows):
        order = np.argsort(excess[i])[::-1]
        e1 = float(excess[i, order[0]])
        e2 = float(excess[i, order[1]])
        if e1 < thr:
            status, col = BLANK, None
        elif e2 >= thr and e2 >= SECOND_RATIO * e1:
            status, col = MULTIPLE, None
        elif e2 >= thr or e1 < CLEAR_FACTOR * thr:
            status, col = CHECK, int(order[0])
        else:
            status, col = OK, int(order[0])
        out.append(RowRead(i, col, status, e1, e2))
    return out


def cell_points(read: BlockRead, quad) -> np.ndarray:
    """Image coordinates of every cell centre: array (rows, cols, 2)."""
    rect = np.array([[0, 0], [read.width, 0], [read.width, read.height], [0, read.height]],
                    float)
    h = _homography(rect, np.asarray(quad, float))
    u, v = np.meshgrid(read.col_centres, read.row_centres)
    den = h[2, 0] * u + h[2, 1] * v + h[2, 2]
    x = (h[0, 0] * u + h[0, 1] * v + h[0, 2]) / den
    y = (h[1, 0] * u + h[1, 1] * v + h[1, 2]) / den
    return np.stack([x, y], -1)


# ---------------------------------------------------------------------------
# Mapping to instrument fields

@dataclass
class ItemRead:
    key: str
    code: int | None
    status: str


def choice_groups(fields) -> list[tuple[str, list]]:
    """Consecutive choice fields sharing a section and response options.

    These are the default blocks to outline on the paper form.
    """
    groups: list[tuple[str, list]] = []
    prev = None
    for f in fields:
        if f.kind != "choice":
            prev = None
            continue
        sig = (f.section, tuple(f.options))
        if prev == sig:
            groups[-1][1].append(f)
        else:
            groups.append((f.section or "Responses", [f]))
        prev = sig
    return groups


def map_block(block_fields, read: BlockRead, reverse: bool = False) -> list[ItemRead]:
    """Convert physical columns to response codes for the block's fields."""
    opts = block_fields[0].options
    if any(f.options != opts for f in block_fields):
        raise ValueError("All items in a block must share the same response options.")
    if len(read.rows) != len(block_fields):
        raise ValueError("Row count does not match the number of items.")
    n = len(opts)
    out = []
    for f, r in zip(block_fields, read.rows):
        code = None
        if r.column is not None:
            idx = n - 1 - r.column if reverse else r.column
            code = opts[idx][0]
        out.append(ItemRead(f.key, code, r.status))
    return out
