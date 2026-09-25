"""Application service layer.

Every read or write of client data goes through this class, so every
access is audited in one place. The GUI never touches the database
directly.
"""

from __future__ import annotations

import json
import secrets
from datetime import date, datetime, timedelta, timezone

from . import archive, config, crypto, report
from .audit import AuditLog
from .database import EncryptedDatabase, decrypt_file, now_iso
from .keystore import AuthError, KeyStore, Session
from .scoring import INSTRUMENTS, ScoreResult, instruments_for, run_scoring

CLIENT_FIELDS = ("last_name", "first_name", "dob", "grade", "flow", "asrs_enabled")


def age_on(dob: str, on: date | None = None) -> int | None:
    try:
        b = date.fromisoformat(dob)
    except (TypeError, ValueError):
        return None
    on = on or date.today()
    return on.year - b.year - ((on.month, on.day) < (b.month, b.day))


class NotLoggedIn(RuntimeError):
    pass


class AppService:
    def __init__(self, keystore: KeyStore | None = None, db_path=None, audit_path=None):
        self.keystore = keystore or KeyStore()
        self._db_path = db_path
        self._audit_path = audit_path
        self.session: Session | None = None
        self.db: EncryptedDatabase | None = None
        self.audit_log: AuditLog | None = (
            AuditLog(self.keystore.log_public_key, audit_path) if self.keystore.exists() else None)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    @property
    def needs_setup(self) -> bool:
        return not self.keystore.exists()

    def setup(self, username: str, password: str, eula_version: str | None = None) -> None:
        session = self.keystore.initialize(username, password)
        self.audit_log = AuditLog(self.keystore.log_public_key, self._audit_path)
        self._open(session)
        self.audit("SETUP", details={"admin": username, "eula_accepted": eula_version})
        self.audit("LOGIN_SUCCESS")

    def login(self, username: str, password: str) -> None:
        try:
            session = self.keystore.authenticate(username, password)
        except AuthError as exc:
            self.audit_log.append(username, "LOGIN_FAILURE", details={"reason": str(exc)})
            raise
        self._open(session)
        self.audit("LOGIN_SUCCESS")

    def _open(self, session: Session) -> None:
        try:
            db = EncryptedDatabase(session.dek, self._db_path)
        except crypto.DecryptionError:
            self.audit_log.append(session.username, "DB_INTEGRITY_FAILURE",
                                  details={"file": "clinassess.db.enc"})
            raise
        self.session = session
        self.db = db

    def logout(self, reason: str = "LOGOUT") -> None:
        if self.session is None:
            return
        self.audit(reason)
        self.db.close()
        self.db = None
        self.session = None

    def _require(self) -> tuple[Session, EncryptedDatabase]:
        if self.session is None or self.db is None:
            raise NotLoggedIn()
        return self.session, self.db

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    def audit(self, action: str, client_ref: str | None = None, entity: str | None = None,
              entity_id: int | None = None, details: dict | None = None) -> None:
        session, db = self._require()
        seq = self.audit_log.append(session.username, action, client_ref, entity,
                                    entity_id, details)
        with db.transaction() as c:
            c.execute("INSERT INTO audit_log (ts, username, action, client_ref, entity, "
                      "entity_id, details_json, file_seq) VALUES (?,?,?,?,?,?,?,?)",
                      (now_iso(), session.username, action, client_ref, entity, entity_id,
                       json.dumps(details or {}), seq))
            c.execute("INSERT INTO settings (key, value) VALUES ('audit_head_seq', ?) "
                      "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (str(seq),))

    def read_audit(self):
        session, db = self._require()
        if not session.is_admin:
            raise PermissionError("admin role required")
        head = int(db.get_setting("audit_head_seq", "0"))
        events, result = self.audit_log.read(session.log_private_key, head)
        self.audit("AUDIT_VIEW", details={"verified": result.ok})
        return events, result

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------
    @staticmethod
    def _check_client(data: dict) -> dict:
        d = {k: data.get(k) for k in CLIENT_FIELDS}
        d["last_name"] = (d["last_name"] or "").strip()
        d["first_name"] = (d["first_name"] or "").strip()
        d["grade"] = (d["grade"] or "").strip()
        d["asrs_enabled"] = 1 if d["asrs_enabled"] else 0
        if not d["last_name"] or not d["first_name"]:
            raise ValueError("first and last name are required")
        try:
            dob = date.fromisoformat(d["dob"] or "")
        except ValueError:
            raise ValueError("date of birth must be YYYY-MM-DD") from None
        if dob > date.today():
            raise ValueError("date of birth is in the future")
        if d["flow"] not in ("A", "B"):
            raise ValueError("flow must be A or B")
        if d["flow"] == "B":
            d["asrs_enabled"] = 1  # ASRS is always part of Flow B
        return d

    def create_client(self, data: dict) -> int:
        session, db = self._require()
        d = self._check_client(data)
        ref = "C-" + secrets.token_hex(3).upper()
        ts = now_iso()
        with db.transaction() as c:
            cur = c.execute(
                "INSERT INTO clients (ref_code, last_name, first_name, dob, grade, flow, "
                "asrs_enabled, created_at, created_by, updated_at, updated_by) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (ref, d["last_name"], d["first_name"], d["dob"], d["grade"], d["flow"],
                 d["asrs_enabled"], ts, session.username, ts, session.username))
            cid = cur.lastrowid
        self.audit("CLIENT_CREATE", ref, "client", cid, {"flow": d["flow"]})
        return cid

    def update_client(self, client_id: int, data: dict) -> list[str]:
        session, db = self._require()
        old = self._client_row(client_id)
        d = self._check_client(data)
        changed = [k for k in CLIENT_FIELDS if str(old[k] or "") != str(d[k] or "")]
        if not changed:
            return []
        with db.transaction() as c:
            c.execute("UPDATE clients SET last_name=?, first_name=?, dob=?, grade=?, flow=?, "
                      "asrs_enabled=?, updated_at=?, updated_by=? WHERE id=?",
                      (d["last_name"], d["first_name"], d["dob"], d["grade"], d["flow"],
                       d["asrs_enabled"], now_iso(), session.username, client_id))
        # Field names only; values are not written to the audit trail.
        self.audit("CLIENT_UPDATE", old["ref_code"], "client", client_id,
                   {"fields_changed": changed})
        return changed

    def _client_row(self, client_id: int):
        _, db = self._require()
        row = db.conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if row is None:
            raise KeyError("client not found")
        return row

    def get_client(self, client_id: int, log: bool = True) -> dict:
        row = dict(self._client_row(client_id))
        row["age"] = age_on(row["dob"])
        if log:
            self.audit("CLIENT_VIEW", row["ref_code"], "client", client_id)
        return row

    def search_clients(self, text: str = "", dob: str = "") -> list[dict]:
        _, db = self._require()
        sql = "SELECT id, ref_code, last_name, first_name, dob, grade, flow FROM clients WHERE 1=1"
        params: list = []
        for term in text.split():
            sql += " AND (last_name LIKE ? OR first_name LIKE ? OR ref_code LIKE ?)"
            like = f"%{term}%"
            params += [like, like, like]
        if dob.strip():
            sql += " AND dob LIKE ?"
            params.append(f"{dob.strip()}%")
        sql += " ORDER BY last_name COLLATE NOCASE, first_name COLLATE NOCASE"
        rows = [dict(r) for r in db.conn.execute(sql, params).fetchall()]
        # Search terms are PHI, so only the fact of a search and the result
        # count are logged.
        self.audit("CLIENT_SEARCH", details={"results": len(rows),
                                             "by_name": bool(text.strip()),
                                             "by_dob": bool(dob.strip())})
        return rows

    def delete_client(self, client_id: int, reason: str) -> dict:
        session, db = self._require()
        if not reason.strip():
            raise ValueError("a reason is required for deletion")
        row = self._client_row(client_id)
        counts = {
            "assessments": db.conn.execute("SELECT COUNT(*) FROM assessments WHERE client_id=?",
                                           (client_id,)).fetchone()[0],
            "report_versions": db.conn.execute(
                "SELECT COUNT(*) FROM report_versions WHERE client_id=?",
                (client_id,)).fetchone()[0],
        }
        with db.transaction() as c:
            c.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        # The database is re-serialized from memory after the delete, so the
        # deleted rows are not present in the new encrypted file. VACUUM
        # also clears freed pages in the in-memory image.
        db.conn.execute("VACUUM")
        db.flush()
        self.audit("CLIENT_DELETE", row["ref_code"], "client", client_id,
                   {"reason": reason.strip(), "deleted_records": counts})
        return counts

    # ------------------------------------------------------------------
    # Assessments
    # ------------------------------------------------------------------
    def available_instruments(self, client_id: int):
        c = self._client_row(client_id)
        return instruments_for(c["flow"], bool(c["asrs_enabled"]))

    def score_preview(self, client_id: int, instrument: str, variant: str,
                      responses: dict, administered_on: str | None = None) -> ScoreResult:
        c = self._client_row(client_id)
        on = date.fromisoformat(administered_on) if administered_on else None
        return run_scoring(instrument, variant, responses, {"age": age_on(c["dob"], on)})

    def save_assessment(self, client_id: int, instrument: str, variant: str,
                        administered_on: str, responses: dict,
                        assessment_id: int | None = None) -> int:
        session, db = self._require()
        client = self._client_row(client_id)
        allowed = {i.key for i in instruments_for(client["flow"], bool(client["asrs_enabled"]))}
        if instrument not in allowed:
            raise ValueError(f"{instrument} is not part of this client's flow")
        inst = INSTRUMENTS[instrument]
        if variant not in {v for v, _ in inst.variants}:
            raise ValueError("invalid variant")
        date.fromisoformat(administered_on)
        result = self.score_preview(client_id, instrument, variant, responses, administered_on)
        ts = now_iso()
        with db.transaction() as c:
            if assessment_id is None:
                cur = c.execute(
                    "INSERT INTO assessments (client_id, instrument, variant, administered_on, "
                    "responses_json, scores_json, scoring_version, created_at, created_by, "
                    "updated_at, updated_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (client_id, instrument, variant, administered_on, json.dumps(responses),
                     json.dumps(result.to_dict()), inst.version, ts, session.username, ts,
                     session.username))
                aid, action, details = cur.lastrowid, "ASSESSMENT_CREATE", {}
            else:
                old = c.execute("SELECT * FROM assessments WHERE id=? AND client_id=?",
                                (assessment_id, client_id)).fetchone()
                if old is None:
                    raise KeyError("assessment not found")
                old_resp = json.loads(old["responses_json"])
                changed = sorted(k for k in set(old_resp) | set(responses)
                                 if old_resp.get(k) != responses.get(k))
                if old["variant"] != variant:
                    changed.append("variant")
                if old["administered_on"] != administered_on:
                    changed.append("administered_on")
                c.execute("UPDATE assessments SET variant=?, administered_on=?, "
                          "responses_json=?, scores_json=?, scoring_version=?, updated_at=?, "
                          "updated_by=? WHERE id=?",
                          (variant, administered_on, json.dumps(responses),
                           json.dumps(result.to_dict()), inst.version, ts, session.username,
                           assessment_id))
                aid, action, details = assessment_id, "ASSESSMENT_UPDATE", {
                    "fields_changed": changed}
        self.audit(action, client["ref_code"], "assessment", aid,
                   {"instrument": instrument, "variant": variant, **details})
        return aid

    def list_assessments(self, client_id: int) -> list[dict]:
        _, db = self._require()
        rows = db.conn.execute(
            "SELECT * FROM assessments WHERE client_id=? ORDER BY administered_on, id",
            (client_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["responses"] = json.loads(d.pop("responses_json"))
            d["scores"] = ScoreResult.from_dict(json.loads(d.pop("scores_json")))
            out.append(d)
        return out

    def get_assessment(self, client_id: int, assessment_id: int) -> dict:
        for a in self.list_assessments(client_id):
            if a["id"] == assessment_id:
                self.audit("ASSESSMENT_VIEW", self._client_row(client_id)["ref_code"],
                           "assessment", assessment_id, {"instrument": a["instrument"]})
                return a
        raise KeyError("assessment not found")

    def delete_assessment(self, client_id: int, assessment_id: int, reason: str) -> None:
        _, db = self._require()
        if not reason.strip():
            raise ValueError("a reason is required for deletion")
        client = self._client_row(client_id)
        row = db.conn.execute("SELECT instrument FROM assessments WHERE id=? AND client_id=?",
                              (assessment_id, client_id)).fetchone()
        if row is None:
            raise KeyError("assessment not found")
        with db.transaction() as c:
            c.execute("DELETE FROM assessments WHERE id=?", (assessment_id,))
        db.conn.execute("VACUUM")
        db.flush()
        self.audit("ASSESSMENT_DELETE", client["ref_code"], "assessment", assessment_id,
                   {"instrument": row["instrument"], "reason": reason.strip()})

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def report_template(self, client_id: int) -> str:
        return "child" if self._client_row(client_id)["flow"] == "A" else "adult"

    def build_auto_report(self, client_id: int) -> dict:
        client = self.get_client(client_id, log=False)
        return report.auto_sections(client, self.list_assessments(client_id))

    def latest_report(self, client_id: int) -> dict | None:
        _, db = self._require()
        row = db.conn.execute("SELECT * FROM report_versions WHERE client_id=? "
                              "ORDER BY version_no DESC LIMIT 1", (client_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["sections"] = json.loads(d.pop("sections_json"))
        return d

    def report_history(self, client_id: int) -> list[dict]:
        _, db = self._require()
        return [dict(r) for r in db.conn.execute(
            "SELECT id, version_no, source, created_at, created_by FROM report_versions "
            "WHERE client_id=? ORDER BY version_no DESC", (client_id,)).fetchall()]

    def open_report(self, client_id: int) -> dict:
        """Return the latest saved report, creating the auto version if none exists."""
        rep = self.latest_report(client_id)
        client = self._client_row(client_id)
        if rep is None:
            self.save_report(client_id, self.build_auto_report(client_id), source="auto")
            rep = self.latest_report(client_id)
        self.audit("REPORT_VIEW", client["ref_code"], "report", rep["id"],
                   {"version": rep["version_no"]})
        return rep

    def save_report(self, client_id: int, sections: dict, source: str = "edited") -> int:
        session, db = self._require()
        client = self._client_row(client_id)
        template = self.report_template(client_id)
        clean = report.sanitize_sections(sections, template)
        prev = self.latest_report(client_id)
        changed = sorted(k for k in clean if not prev or prev["sections"].get(k) != clean[k])
        if prev and not changed and source == "edited":
            return prev["version_no"]
        version = (prev["version_no"] + 1) if prev else 1
        with db.transaction() as c:
            cur = c.execute("INSERT INTO report_versions (client_id, version_no, template, source, "
                            "sections_json, created_at, created_by) VALUES (?,?,?,?,?,?,?)",
                            (client_id, version, template, source, json.dumps(clean), now_iso(),
                             session.username))
        self.audit("REPORT_SAVE", client["ref_code"], "report", cur.lastrowid,
                   {"version": version, "source": source, "sections_changed": changed})
        return version

    def revert_report_to_auto(self, client_id: int) -> int:
        """Regenerate the auto text from current scores and save it as a new version.

        Earlier edited versions stay in the history."""
        return self.save_report(client_id, self.build_auto_report(client_id), source="reverted")

    def report_is_stale(self, client_id: int) -> bool:
        """True if assessments or demographics changed after the latest report version."""
        rep = self.latest_report(client_id)
        if rep is None:
            return False
        _, db = self._require()
        newest = db.conn.execute(
            "SELECT MAX(t) FROM (SELECT MAX(updated_at) t FROM assessments WHERE client_id=? "
            "UNION ALL SELECT updated_at FROM clients WHERE id=?)",
            (client_id, client_id)).fetchone()[0]
        return bool(newest and newest > rep["created_at"])

    def export_report_pdf(self, client_id: int, path, password: str) -> None:
        session, _ = self._require()
        rep = self.latest_report(client_id)
        if rep is None:
            raise ValueError("no report saved yet")
        client = self.get_client(client_id, log=False)
        from . import pdf  # imported lazily; ReportLab is heavy
        data = pdf.render_encrypted(client, rep, self.list_assessments(client_id), password)
        crypto.atomic_write(path, data)
        self.audit("REPORT_EXPORT_PDF", client["ref_code"], "report", rep["id"],
                   {"version": rep["version_no"], "encrypted": "AES-256"})

    # ------------------------------------------------------------------
    # Archive / retention / users
    # ------------------------------------------------------------------
    def export_archive(self, path, password: str) -> None:
        session, db = self._require()
        if not session.is_admin:
            raise PermissionError("admin role required")
        crypto.atomic_write(path, archive.pack(db.serialize(), password))
        self.audit("ARCHIVE_EXPORT", details={"encrypted": "AES-256-GCM"})

    def restore_archive(self, path, password: str) -> None:
        session, db = self._require()
        if not session.is_admin:
            raise PermissionError("admin role required")
        with open(path, "rb") as fh:
            plaintext = archive.unpack(fh.read(), password)
        head = db.get_setting("audit_head_seq", "0")
        db.replace_contents(plaintext)
        db.set_setting("audit_head_seq", head)
        self.audit("ARCHIVE_RESTORE", details={})

    def verify_backup(self, path, password: str | None = None) -> dict:
        """Test that a backup can be restored, without restoring it.

        Accepts either a .caarchive export (needs its archive password) or a
        copy of clinassess.db.enc taken from a Time Machine backup (decrypted
        with the current data key). The file is decrypted in memory only and
        checked with SQLite PRAGMA integrity_check. Each test is written to the
        audit trail as BACKUP_VERIFY, which serves as the backup testing log.
        """
        session, _ = self._require()
        with open(path, "rb") as fh:
            blob = fh.read()
        kind = "archive" if blob.startswith(archive.MAGIC) else "database"
        result = {"file_type": kind, "file_bytes": len(blob)}
        try:
            if kind == "archive":
                if not password:
                    raise ValueError("archive password required")
                plaintext = archive.unpack(blob, password)
            else:
                plaintext = decrypt_file(session.dek, blob)
            result.update(archive.inspect_database(plaintext))
            result["ok"] = result["integrity"] == "ok"
        except (crypto.DecryptionError, ValueError) as exc:
            result.update(ok=False, error=str(exc))
        self.audit("BACKUP_VERIFY", details=result)
        return result

    def retention_review(self, years: int) -> list[dict]:
        _, db = self._require()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=365.25 * years)).isoformat()
        rows = db.conn.execute(
            "SELECT c.id, c.ref_code, c.last_name, c.first_name, c.dob, "
            "MAX(c.updated_at, COALESCE(MAX(a.updated_at), '')) AS last_activity "
            "FROM clients c LEFT JOIN assessments a ON a.client_id = c.id "
            "GROUP BY c.id HAVING last_activity < ? ORDER BY last_activity", (cutoff,)).fetchall()
        self.audit("RETENTION_REVIEW", details={"years": years, "results": len(rows)})
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Dashboard and security settings
    # ------------------------------------------------------------------
    def dashboard(self, active_days: int = 90) -> dict:
        """Counts and short lists for the home screen (one audited view)."""
        _, db = self._require()
        since = (datetime.now(timezone.utc) - timedelta(days=active_days)).isoformat()
        clients = [dict(r) for r in db.conn.execute(
            "SELECT c.id, c.ref_code, c.last_name, c.first_name, c.flow, c.asrs_enabled, "
            "MAX(c.updated_at, COALESCE(MAX(a.updated_at), ''), "
            "    COALESCE(MAX(rv.created_at), '')) AS last_activity "
            "FROM clients c LEFT JOIN assessments a ON a.client_id = c.id "
            "LEFT JOIN report_versions rv ON rv.client_id = c.id "
            "GROUP BY c.id ORDER BY last_activity DESC").fetchall()]
        active = [c for c in clients if c["last_activity"] >= since]
        entered = {}
        for r in db.conn.execute("SELECT client_id, instrument FROM assessments"):
            entered.setdefault(r["client_id"], set()).add(r["instrument"])
        pending = []
        for c in active:
            expected = [i for i in instruments_for(c["flow"], bool(c["asrs_enabled"]))]
            missing = [i.short for i in expected if i.key not in entered.get(c["id"], set())]
            if missing:
                pending.append({**c, "missing": missing, "expected": len(expected)})
        reports = []
        for r in db.conn.execute(
                "SELECT rv.client_id, rv.version_no, rv.source, rv.created_at, rv.created_by, "
                "rv.sections_json, c.ref_code, c.last_name, c.first_name "
                "FROM report_versions rv JOIN clients c ON c.id = rv.client_id "
                "WHERE rv.version_no = (SELECT MAX(version_no) FROM report_versions x "
                "                       WHERE x.client_id = rv.client_id) "
                "ORDER BY rv.created_at DESC LIMIT 10"):
            d = dict(r)
            d["draft"] = bool(report.placeholders_remaining(json.loads(d.pop("sections_json"))))
            reports.append(d)
        no_report = [c for c in active if c["id"] in entered and
                     not any(r["client_id"] == c["id"] for r in reports)]
        self.audit("DASHBOARD_VIEW", details={"active": len(active)})
        return {"total_clients": len(clients), "active": active, "pending": pending,
                "reports": reports, "drafts": [r for r in reports if r["draft"]],
                "awaiting_report": no_report}

    def idle_timeout_seconds(self) -> int:
        _, db = self._require()
        try:
            minutes = int(db.get_setting("idle_timeout_min", "0"))
        except ValueError:
            minutes = 0
        if minutes in config.IDLE_TIMEOUT_CHOICES_MIN:
            return minutes * 60
        return config.IDLE_TIMEOUT_SECONDS

    def set_idle_timeout(self, minutes: int) -> None:
        session, db = self._require()
        if not session.is_admin:
            raise PermissionError("admin role required")
        if minutes not in config.IDLE_TIMEOUT_CHOICES_MIN:
            raise ValueError("unsupported timeout")
        db.set_setting("idle_timeout_min", str(minutes))
        self.audit("SETTING_CHANGE", details={"idle_timeout_min": minutes})

    def todays_interview(self, client_id: int) -> dict | None:
        """The interview entry dated today, if any ("Start session" reopens it)."""
        today = date.today().isoformat()
        for a in self.list_assessments(client_id):
            if a["instrument"] == "interview" and a["administered_on"] == today:
                return a
        return None

    def add_user(self, username: str, password: str, role: str) -> None:
        session, _ = self._require()
        self.keystore.add_user(session, username, password, role)
        self.audit("USER_CREATE", details={"username": username, "role": role})

    def remove_user(self, username: str) -> None:
        session, _ = self._require()
        self.keystore.remove_user(session, username)
        self.audit("USER_DELETE", details={"username": username})

    def change_password(self, old: str, new: str) -> None:
        session, _ = self._require()
        self.keystore.change_password(session, old, new)
        self.audit("PASSWORD_CHANGE")
