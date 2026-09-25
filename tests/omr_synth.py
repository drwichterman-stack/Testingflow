"""Synthetic paper forms for OMR tests.

Draws a response grid with placeholder item text (grey bars, no real
instrument wording), marks chosen answers the way people do on paper,
then optionally photographs it: perspective, rotation, uneven light,
blur, noise, and JPEG compression.
"""

from __future__ import annotations

import io
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from clinassess.omr import _homography

PAGE = (1700, 2200)


def _font(size):
    try:
        return ImageFont.load_default(size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def make_form(answers, n_cols, style="box", mark="x", top=300, pitch_y=62, pitch_x=110,
              left=900, header_after=(), pen=40, rng=None):
    """Return (PIL image, quad) where quad outlines the answer grid.

    answers: per row a column index, None (blank), or a tuple of columns.
    style: box | circle | digit | table
    mark: x | check | fill | circle | tick
    header_after: row indexes after which a section heading row is inserted.
    """
    rng = rng or random.Random(0)
    im = Image.new("L", PAGE, 255)
    d = ImageDraw.Draw(im)
    f = _font(22)
    d.text((120, 120), "RESPONSE FORM (synthetic)", fill=0, font=_font(40))
    for j in range(n_cols):
        d.text((left + j * pitch_x + 20, top - 50), f"C{j}", fill=0, font=f)
    ys = []
    y = top
    for i in range(len(answers)):
        ys.append(y)
        y += pitch_y
        if i in header_after:
            y += pitch_y  # heading row, text only on the left
            d.rectangle((120, ys[-1] + pitch_y + 20, 600, ys[-1] + pitch_y + 40), fill=60)
    x0, x1 = left, left + n_cols * pitch_x
    y0, y1 = top, y
    if style == "table":
        for yy in ys + [y]:
            d.line((120, yy, x1, yy), fill=0, width=2)
        for j in range(n_cols + 1):
            d.line((x0 + j * pitch_x, y0, x0 + j * pitch_x, y1), fill=0, width=2)
    for i, yy in enumerate(ys):
        d.text((130, yy + 18), f"{i + 1}.", fill=0, font=f)
        d.rectangle((190, yy + 24, 190 + rng.randint(300, 650), yy + 36), fill=150)
        cy = yy + pitch_y / 2
        for j in range(n_cols):
            cx = x0 + (j + 0.5) * pitch_x
            if style == "box":
                d.rectangle((cx - 15, cy - 15, cx + 15, cy + 15), outline=0, width=2)
            elif style == "circle":
                d.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), outline=0, width=2)
            elif style == "digit":
                d.text((cx - 7, cy - 13), str(j), fill=0, font=_font(26))
        a = answers[i]
        cols = () if a is None else (a if isinstance(a, tuple) else (a,))
        for j in cols:
            cx = x0 + (j + 0.5) * pitch_x + rng.uniform(-4, 4)
            cyy = cy + rng.uniform(-3, 3)
            _mark(d, cx, cyy, mark, pen, rng)
    return im, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _mark(d, cx, cy, kind, pen, rng):
    w = rng.choice([3, 4, 5])
    if kind == "x":
        s = rng.uniform(11, 17)
        d.line((cx - s, cy - s, cx + s, cy + s), fill=pen, width=w)
        d.line((cx - s, cy + s, cx + s, cy - s), fill=pen, width=w)
    elif kind == "check":
        d.line((cx - 12, cy, cx - 3, cy + 12, cx + 16, cy - 16), fill=pen, width=w, joint="curve")
    elif kind == "tick":
        d.line((cx - 6, cy + 2, cx + 8, cy - 8), fill=pen, width=w)
    elif kind == "fill":
        r = rng.uniform(11, 14)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=pen)
    elif kind == "circle":
        r = rng.uniform(20, 26)
        d.ellipse((cx - r - 3, cy - r, cx + r + 3, cy + r), outline=pen, width=w)


def photograph(im, quad, angle=0.0, perspective=0.0, blur=0.0, noise=0.0, light=0.0,
               jpeg=None, scale=1.0, seed=0):
    """Apply camera-like distortions; return (uint8 array, transformed quad)."""
    rng = np.random.default_rng(seed)
    w, h = im.size
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
    c = src.mean(0)
    t = np.deg2rad(angle)
    rot = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    dst = (src - c) @ rot.T + c
    dst += rng.uniform(-1, 1, dst.shape) * perspective * w
    dst *= scale
    dst -= dst.min(0) - 40
    out_size = tuple((dst.max(0) + 40).astype(int))
    fwd = _homography(src, dst)
    inv = np.linalg.inv(fwd)
    inv /= inv[2, 2]
    photo = im.transform(out_size, Image.Transform.PERSPECTIVE, tuple(inv.flatten()[:8]),
                         Image.Resampling.BILINEAR, fillcolor=90)
    if blur:
        photo = photo.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(photo, float)
    if light:
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        a = a * (1 - light * (xx / a.shape[1] * 0.6 + yy / a.shape[0] * 0.4))
    if noise:
        a = a + rng.normal(0, noise, a.shape)
    a = np.clip(a, 0, 255).astype(np.uint8)
    if jpeg:
        buf = io.BytesIO()
        Image.fromarray(a).save(buf, "JPEG", quality=jpeg)
        a = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("L"))
    q = np.asarray(quad, float)
    pts = np.c_[q, np.ones(len(q))] @ fwd.T
    return a, (pts[:, :2] / pts[:, 2:]).tolist()
