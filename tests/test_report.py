import io

import pytest
from pypdf import PdfReader

from clinassess import report


@pytest.fixture
def scored(svc, client_a):
    svc.save_assessment(client_a, "interview", "clinical", "2026-09-01",
                        {"referral": "Attention concerns at school."})
    svc.save_assessment(client_a, "sdq", "parent", "2026-09-02",
                        {f"item{i}": 1 for i in range(1, 26)})
    return client_a


def test_auto_report_contents(svc, scored):
    rep = svc.open_report(scored)
    s = rep["sections"]
    assert rep["version_no"] == 1 and rep["source"] == "auto" and rep["template"] == "child"
    assert "Jane Doe" in s["identifying"]
    assert "Attention concerns at school." in s["interview"]
    assert "Total Difficulties" in s["results:sdq"]
    assert report.PLACEHOLDER in s["recommendations"]
    assert s["sig_name"] == ""  # left blank by design


def test_edit_versioning_and_revert(svc, scored):
    rep = svc.open_report(scored)
    s = dict(rep["sections"])
    s["diagnostic"] = "Edited impressions."
    s["bogus_key"] = "ignored"
    assert svc.save_report(scored, s) == 2
    assert svc.save_report(scored, s) == 2  # no change, no new version
    latest = svc.latest_report(scored)
    assert latest["source"] == "edited" and latest["sections"]["diagnostic"] == "Edited impressions."
    assert "bogus_key" not in latest["sections"]
    assert svc.revert_report_to_auto(scored) == 3
    assert report.PLACEHOLDER in svc.latest_report(scored)["sections"]["diagnostic"]
    hist = svc.report_history(scored)
    assert [h["source"] for h in hist] == ["reverted", "edited", "auto"]
    assert all(h["created_by"] == "drsmith" for h in hist)


def test_stale_detection(svc, scored):
    svc.open_report(scored)
    assert not svc.report_is_stale(scored)
    import time
    time.sleep(1.1)
    svc.save_assessment(scored, "cats", "self_7_17", "2026-09-03", {"item1": 2})
    assert svc.report_is_stale(scored)


def test_pdf_encrypted_with_header_and_final_page(svc, scored, home):
    rep = svc.open_report(scored)
    s = dict(rep["sections"])
    s["recommendations"] = "School / educational:\n- Preferential seating.\n" + "Long text. " * 900
    svc.save_report(scored, s)
    out = home / "reports" / "r.pdf"
    out.parent.mkdir(exist_ok=True)
    with pytest.raises(ValueError):
        svc.export_report_pdf(scored, out, "short")
    svc.export_report_pdf(scored, out, "Pdf-Password-2026")
    raw = out.read_bytes()
    assert b"Doe" not in raw and b"Preferential" not in raw
    r = PdfReader(io.BytesIO(raw))
    assert r.is_encrypted
    assert r.decrypt("Pdf-Password-2026")
    enc = r.trailer["/Encrypt"].get_object()
    assert enc["/V"] == 5 and enc["/R"] == 6  # AES-256 (PDF 2.0)
    assert enc["/CF"]["/StdCF"]["/CFM"] == "/AESV3"
    n = len(r.pages)
    assert n >= 3
    for i, page in enumerate(r.pages, start=1):
        assert f"Patient Name: Jane Doe | Page: {i}" in page.extract_text()
        assert "Generated:" in page.extract_text()
    last = r.pages[-1].extract_text()
    assert "Confidentiality Notice" in last and "Clinician signature" in last
    assert "Confidentiality Notice" not in r.pages[0].extract_text()
    events, _ = svc.read_audit()
    assert any(e["action"] == "REPORT_EXPORT_PDF" for e in events)
