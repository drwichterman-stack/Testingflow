"""Optical mark reading: synthetic forms under camera-like conditions.

The forms are drawn by tests/omr_synth.py (placeholder text, no real
instrument wording). The key safety property is that a wrong response is
never reported as a clear read: every doubtful item must be flagged.
"""

import random
import zlib

import numpy as np
import pytest

from clinassess import omr
from clinassess.scoring import INSTRUMENTS
from .omr_synth import PAGE, make_form, photograph

PAPER = ["sdq", "cats", "snap4", "wsr2", "wfirs_p", "wfirs_s", "asrs"]


def _read(style, mark, n_cols, answers, distort, seed):
    rng = random.Random(seed)
    im, quad = make_form(answers, n_cols, style=style, mark=mark, rng=rng)
    if distort:
        arr, quad = photograph(im, quad, angle=rng.uniform(-6, 6), perspective=0.03, blur=1.2,
                               noise=6, light=0.4, jpeg=70, scale=0.6, seed=seed)
    else:
        arr = np.asarray(im)
    # A person's outline is a few pixels off.
    quad = np.asarray(quad) + np.random.default_rng(seed).uniform(-4, 4, (4, 2))
    return omr.read_block(arr, quad, len(answers), n_cols)


@pytest.mark.parametrize("style", ["box", "circle", "digit", "table"])
@pytest.mark.parametrize("mark", ["x", "check", "fill", "circle"])
@pytest.mark.parametrize("distort", [False, True])
def test_reads_marks_and_never_reports_a_wrong_clear_read(style, mark, distort):
    seed = zlib.crc32(f"{style}{mark}{distort}".encode()) % 10_000
    rng = random.Random(seed)
    answers = [rng.randrange(4) for _ in range(20)]
    answers[3] = None           # skipped item
    answers[11] = (0, 3)        # two marks
    read = _read(style, mark, 4, answers, distort, seed)
    clear = 0
    for want, got in zip(answers, read.rows):
        if got.status == omr.OK:
            assert got.column == want, (want, got)
            clear += 1
        if want is None:
            assert got.status != omr.OK
        if isinstance(want, tuple):
            assert got.status != omr.OK
    assert clear >= 6  # flags are safe but costly; the overall rate is tested below


def test_overall_clear_read_rate():
    clear = total = 0
    for i, (style, mark) in enumerate([(s, m) for s in ("box", "circle", "digit", "table")
                                       for m in ("x", "check", "fill", "circle")]):
        rng = random.Random(100 + i)
        answers = [rng.randrange(3) for _ in range(20)]
        read = _read(style, mark, 3, answers, i % 2 == 1, 100 + i)
        for want, got in zip(answers, read.rows):
            assert got.status != omr.OK or got.column == want
            clear += got.status == omr.OK
            total += 1
    assert clear / total >= 0.8, clear / total


def test_blank_and_multiple_are_named():
    answers = [0, 1, 2, None, 1, (0, 2), 2, 0, 1, 2]
    read = _read("box", "x", 3, answers, False, 1)
    assert read.rows[3].status == omr.BLANK and read.rows[3].column is None
    assert read.rows[5].status == omr.MULTIPLE and read.rows[5].column is None


def test_mostly_one_column_still_reads():
    # A child with no difficulties: nearly every answer in the first column.
    answers = [0] * 22 + [2, 1, 0]
    read = _read("box", "x", 3, answers, True, 7)
    for want, got in zip(answers, read.rows):
        assert got.status != omr.OK or got.column == want
    assert sum(r.status == omr.OK for r in read.rows) >= 22


def test_two_columns_yes_no():
    answers = [1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0]
    read = _read("box", "fill", 2, answers, True, 3)
    for want, got in zip(answers, read.rows):
        assert got.status != omr.OK or got.column == want
    assert sum(r.status == omr.OK for r in read.rows) >= 13


def test_misplaced_outline_is_not_trusted():
    # An outline that includes a heading row cannot line up with evenly spaced
    # items; the reads must all be flagged rather than shifted silently.
    answers = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0]
    rng = random.Random(5)
    im, quad = make_form(answers, 3, header_after=(4,), rng=rng)
    read = omr.read_block(np.asarray(im), quad, len(answers), 3)
    for want, got in zip(answers, read.rows):
        assert got.status != omr.OK or got.column == want


def test_find_page_and_saved_outline_on_webcam_snap():
    rng = random.Random(11)
    answers = [rng.randrange(3) for _ in range(25)]
    im, grid = make_form(answers, 3, mark="x", rng=rng)
    page = [(0, 0), (PAGE[0], 0), PAGE, (0, PAGE[1])]
    # About 1080 pixels tall, tilted, as from a laptop camera.
    arr, pts = photograph(im, page + grid, angle=8, perspective=0.03, blur=1.2, noise=5,
                          light=0.3, jpeg=80, scale=0.42, seed=11)
    found = omr.find_page(arr)
    assert found is not None
    assert np.abs(found - np.array(pts[:4])).max() < 15
    straight = omr.straighten(arr, found)
    assert straight.shape[1] == omr.PAGE_W
    frac = np.array(grid) / PAGE  # an outline saved from an earlier capture
    read = omr.read_block(straight, frac * [straight.shape[1], straight.shape[0]], 25, 3)
    for want, got in zip(answers, read.rows):
        assert got.status != omr.OK or got.column == want
    assert sum(r.status == omr.OK for r in read.rows) >= 22


def test_find_page_returns_none_without_a_page():
    noise = np.random.default_rng(0).integers(0, 255, (600, 800), dtype=np.uint8)
    assert omr.find_page(noise) is None


def test_cell_points_follow_the_outline():
    answers = [0, 1, 2, 1]
    im, quad = make_form(answers, 3)
    read = omr.read_block(np.asarray(im), quad, 4, 3)
    pts = omr.cell_points(read, quad)
    assert pts.shape == (4, 3, 2)
    x0, y0 = quad[0]
    x1, y1 = quad[2]
    assert x0 < pts[..., 0].min() < pts[..., 0].max() < x1
    assert y0 < pts[..., 1].min() < pts[..., 1].max() < y1


def test_bad_outline_rejected():
    arr = np.full((500, 500), 255, np.uint8)
    with pytest.raises(ValueError):
        omr.read_block(arr, [[0, 0], [100, 100], [100, 0], [0, 100]], 5, 3)  # crossed
    with pytest.raises(ValueError):
        omr.read_block(arr, [[0, 0], [100, 0], [100, 100], [0, 100]], 5, 1)


def test_from_qimage_bytes_drops_row_padding():
    raw = bytes(range(12)) * 2  # 2 rows, stride 12, width 10
    a = omr.from_qimage_bytes(raw, 10, 2, 12)
    assert a.shape == (2, 10) and a[1, 0] == 0 and a[0, 9] == 9


@pytest.mark.parametrize("key", PAPER)
def test_every_paper_form_splits_into_blocks(key):
    inst = INSTRUMENTS[key]
    assert inst.paper_form
    for variant, _ in inst.variants:
        fields = inst.fields_for(variant)
        groups = omr.choice_groups(fields)
        keys = [f.key for _, fs in groups for f in fs]
        assert keys == [f.key for f in fields if f.kind == "choice"]
        for _, fs in groups:
            assert len({tuple(f.options) for f in fs}) == 1


def test_licensed_forms_have_no_camera_capture():
    for key in ("conners4", "tova", "mmpi3", "brown", "interview"):
        assert not INSTRUMENTS[key].paper_form


def test_map_block_codes_and_reverse_order():
    fields = INSTRUMENTS["wsr2"].fields_for("self")[:3]  # None, Mild, Moderate, Severe, N/A
    rows = [omr.RowRead(0, 0, omr.OK, 5, 0), omr.RowRead(1, 4, omr.CHECK, 2, 0),
            omr.RowRead(2, None, omr.BLANK, 0, 0)]
    read = omr.BlockRead(rows, np.zeros((3, 5)), np.zeros(3), np.zeros(5), True, True, 1, 1)
    out = omr.map_block(fields, read)
    assert [(i.code, i.status) for i in out] == [(0, "ok"), (-1, "check"), (None, "blank")]
    rev = omr.map_block(fields, read, reverse=True)
    assert [i.code for i in rev] == [-1, 0, None]


def test_safety_items_marked_critical():
    crit = {f.key for f in INSTRUMENTS["wsr2"].fields_for("parent") if f.critical}
    assert crit == {"sui_1", "sui_2", "per_3"}
