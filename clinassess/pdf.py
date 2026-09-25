"""PDF rendering of the edited report, encrypted with AES-256.

The PDF is built in memory, encrypted with pypdf (AES-256, PDF 2.0
security handler, revision 6), and only then written to disk. No
unencrypted PDF is ever written.

Page furniture (fixed; the report editor cannot change it):
  * Header on every page, top right: "Patient Name: <name> | Page: <n>"
  * Footer on every page: generation date, clinician line (left blank by
    design for manual signature), "CONFIDENTIAL" marking
  * Final page: signature block and confidentiality statement, kept
    together so they never split across pages
"""

from __future__ import annotations

import io
import secrets
from datetime import date
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions as Perm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from . import report
from .keystore import validate_password

MARGIN = 0.9 * inch
BLANK_LINE = "_" * 34

_ss = getSampleStyleSheet()
STYLES = {
    "title": ParagraphStyle("t", parent=_ss["Title"], fontSize=15, spaceAfter=10),
    "h1": ParagraphStyle("h1", parent=_ss["Heading2"], fontSize=12.5, spaceBefore=12,
                         spaceAfter=5, textColor=colors.HexColor("#1f3a5f")),
    "h2": ParagraphStyle("h2", parent=_ss["Heading4"], fontSize=10, spaceBefore=6,
                         spaceAfter=3),
    "body": ParagraphStyle("b", parent=_ss["BodyText"], fontSize=10, leading=13.5,
                           spaceAfter=6),
    "bullet": ParagraphStyle("bl", parent=_ss["BodyText"], fontSize=10, leading=13.5,
                             leftIndent=14, bulletIndent=4, spaceAfter=2),
    "label": ParagraphStyle("lb", parent=_ss["BodyText"], fontSize=10, leading=13.5,
                            spaceAfter=4, keepWithNext=1),
    "cell": ParagraphStyle("c", parent=_ss["BodyText"], fontSize=8.5, leading=10.5),
    "note": ParagraphStyle("n", parent=_ss["BodyText"], fontSize=8, leading=10,
                           textColor=colors.HexColor("#555555"), spaceAfter=4),
    "disclaimer": ParagraphStyle("d", parent=_ss["BodyText"], fontSize=8, leading=10.5,
                                 alignment=TA_CENTER, textColor=colors.HexColor("#333333")),
}


def _para_text(text: str) -> str:
    return escape(text).replace("\n", "<br/>")


def narrative(text: str) -> list:
    """Convert editor text to flowables: blank line = new paragraph,
    "- " = bullet, short line ending in ":" = subheading."""
    flow = []
    for block in (text or "").split("\n\n"):
        lines = [ln.rstrip() for ln in block.strip("\n").split("\n")]
        buf: list[str] = []

        def flush():
            if buf:
                flow.append(Paragraph(_para_text("\n".join(buf)), STYLES["body"]))
                buf.clear()
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            if s.startswith(("- ", "* ")):
                flush()
                flow.append(Paragraph(_para_text(s[2:]), STYLES["bullet"], bulletText="•"))
            elif s.endswith(":") and len(s) <= 70 and not buf:
                flow.append(Paragraph(f"<b>{escape(s)}</b>", STYLES["label"]))
            else:
                buf.append(s)
        flush()
    return flow


def score_table(assessment: dict) -> list:
    """Locked score table for one assessment entry, built from stored scores."""
    ikey = assessment["instrument"]
    s = assessment["scores"]
    out = [Paragraph(escape(f"{report.variant_label(ikey, assessment['variant'])}, "
                            f"administered {report._fmt_date(assessment['administered_on'])}"),
                     ParagraphStyle("h2k", parent=STYLES["h2"], keepWithNext=1))]
    rows = [[Paragraph(f"<b>{h}</b>", STYLES["cell"])
             for h in ("Domain", "Scale / measure", "Score", "Classification")]]
    for r in s.rows:
        score = r.value + (f" ({r.note})" if r.note else "")
        rows.append([Paragraph(_para_text(c), STYLES["cell"])
                     for c in (r.section, r.label, score, r.band)])
    if len(rows) > 1:
        t = Table(rows, colWidths=[1.35 * inch, 2.35 * inch, 1.45 * inch, 1.55 * inch],
                  repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf3")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b8c4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        out.append(t)
    note = report.VERIFICATION_NOTES.get(s.verification, "")
    for w in s.warnings:
        note += " " + w
    out.append(Paragraph(escape(note.strip()), STYLES["note"]))
    return out


def signature_block(sections: dict) -> list:
    def val(key):
        v = (sections.get(key) or "").strip()
        return escape(v) if v else BLANK_LINE
    rows = [
        ["Clinician signature:", BLANK_LINE],
        ["Clinician name:", val("sig_name")],
        ["Credentials:", val("sig_credentials")],
        ["License number:", val("sig_license")],
        ["Date:", val("sig_date")],
    ]
    t = Table([[Paragraph(f"<b>{a}</b>", STYLES["body"]), Paragraph(b, STYLES["body"])]
               for a, b in rows], colWidths=[1.7 * inch, 4.3 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                           ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    return [Paragraph("Signature", STYLES["h1"]), t]


def build_story(client: dict, rep: dict, assessments: list[dict]) -> list:
    sections = rep["sections"]
    template = rep["template"]
    assessed = {a["instrument"] for a in assessments if a["instrument"] != "interview"}
    story = [Paragraph(escape(report.TEMPLATE_TITLES[template]), STYLES["title"])]
    for key, title in report.layout(template, sections, assessed):
        story.append(Paragraph(escape(title), ParagraphStyle("h1k", parent=STYLES["h1"],
                                                             keepWithNext=1)))
        if key.startswith("results:"):
            ikey = key.split(":", 1)[1]
            for a in assessments:
                if a["instrument"] == ikey:
                    story += score_table(a)
            text = sections.get(key, "")
            if text.strip():
                story.append(Paragraph("<b>Interpretation</b>", STYLES["label"]))
        story += narrative(sections.get(key, ""))
    final = signature_block(sections) + [
        Spacer(1, 16),
        Paragraph("<b>Confidentiality Notice</b>", STYLES["disclaimer"]),
        Spacer(1, 3),
        Paragraph(escape(report.CONFIDENTIALITY_STATEMENT), STYLES["disclaimer"]),
    ]
    story.append(Spacer(1, 14))
    story.append(KeepTogether(final))
    return story


def render(client: dict, rep: dict, assessments: list[dict],
           generated_on: date | None = None) -> bytes:
    """Render the report to unencrypted PDF bytes (in memory only)."""
    name = f"{client['first_name']} {client['last_name']}"
    gen = (generated_on or date.today()).strftime("%m/%d/%Y")
    buf = io.BytesIO()

    def furniture(canvas, doc):
        canvas.saveState()
        w, h = letter
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(w - MARGIN, h - 0.55 * inch,
                               f"Patient Name: {name} | Page: {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#b0b8c4"))
        canvas.line(MARGIN, h - 0.62 * inch, w - MARGIN, h - 0.62 * inch)
        canvas.line(MARGIN, 0.62 * inch, w - MARGIN, 0.62 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(MARGIN, 0.45 * inch, f"Generated: {gen}")
        canvas.drawCentredString(w / 2, 0.45 * inch, "CONFIDENTIAL PHI")
        canvas.drawRightString(w - MARGIN, 0.45 * inch, "Clinician: " + "_" * 22)
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=0.9 * inch, bottomMargin=0.85 * inch,
                            title="Assessment Report", author="", subject="",
                            creator="ClinAssess", producer="ClinAssess")
    doc.build(build_story(client, rep, assessments),
              onFirstPage=furniture, onLaterPages=furniture)
    return buf.getvalue()


# Printing, copying, and editing are disallowed for the user password. PDF
# permission flags are advisory: compliant viewers (Preview, Acrobat)
# enforce them, but they are not cryptographic controls. The AES-256
# encryption is the actual protection.
PERMISSIONS = Perm.all() & ~(Perm.PRINT | Perm.PRINT_TO_REPRESENTATION | Perm.MODIFY |
                             Perm.EXTRACT | Perm.ADD_OR_MODIFY | Perm.ASSEMBLE_DOC |
                             Perm.EXTRACT_TEXT_AND_GRAPHICS)


def encrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf_bytes)))
    writer.encrypt(user_password=password, owner_password=secrets.token_urlsafe(32),
                   algorithm="AES-256", permissions_flag=PERMISSIONS)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def render_encrypted(client: dict, rep: dict, assessments: list[dict], password: str) -> bytes:
    problems = validate_password(password)
    if problems:
        raise ValueError("PDF password needs " + " and ".join(problems))
    return encrypt_pdf(render(client, rep, assessments), password)
