import json

import pytest

from clinassess import archive, crypto
from clinassess.keystore import AuthError, KeyStore, LockedOutError
from clinassess.service import AppService

from .conftest import PASSWORD


def test_database_file_has_no_plaintext_phi(svc, client_a, home):
    svc.save_assessment(client_a, "interview", "clinical", "2026-09-01",
                        {"presenting": "Distinctive-Phrase-XYZ"})
    blob = (home / "db.enc").read_bytes()
    for needle in (b"Doe", b"Jane", b"2015-03-10", b"Distinctive-Phrase-XYZ", b"SQLite"):
        assert needle not in blob
    assert b"Doe" not in (home / "audit.log.enc").read_bytes()
    assert b"Doe" not in (home / "keystore.json").read_bytes()
    # No stray plaintext files in the data directory.
    names = {p.name for p in home.iterdir()}
    assert names <= {"keystore.json", "db.enc", "audit.log.enc", "reports"}


def test_reopen_and_wrong_password(svc, client_a, home):
    svc.logout()
    ks = KeyStore(home / "keystore.json", scrypt_n=2 ** 12)
    s2 = AppService(ks, home / "db.enc", home / "audit.log.enc")
    with pytest.raises(AuthError):
        s2.login("drsmith", "wrong-password-1A!")
    s2.login("drsmith", PASSWORD)
    assert s2.get_client(client_a)["last_name"] == "Doe"


def test_lockout(svc, home):
    svc.logout()
    for _ in range(4):
        with pytest.raises(AuthError):
            svc.login("drsmith", "Wrong-password-99")
    with pytest.raises(LockedOutError):
        svc.login("drsmith", "Wrong-password-99")
    with pytest.raises(LockedOutError):
        svc.login("drsmith", PASSWORD)  # locked even with the right password


def test_role_tampering_breaks_unwrap(svc, home):
    svc.add_user("assistant", "Another-Pass-77", "clinician")
    svc.logout()
    path = home / "keystore.json"
    data = json.loads(path.read_text())
    data["users"]["assistant"]["role"] = "admin"
    path.write_text(json.dumps(data))
    ks = KeyStore(path, scrypt_n=2 ** 12)
    s = AppService(ks, home / "db.enc", home / "audit.log.enc")
    with pytest.raises(AuthError):
        s.login("assistant", "Another-Pass-77")


def test_tampered_database_rejected(svc, home):
    svc.logout()
    p = home / "db.enc"
    b = bytearray(p.read_bytes())
    b[-5] ^= 0xFF
    p.write_bytes(bytes(b))
    s = AppService(KeyStore(home / "keystore.json", scrypt_n=2 ** 12), p, home / "audit.log.enc")
    with pytest.raises(crypto.DecryptionError):
        s.login("drsmith", PASSWORD)
    assert s.session is None and s.db is None


def test_audit_log_chain_and_failed_login(svc, client_a, home):
    svc.get_client(client_a)
    svc.logout()
    with pytest.raises(AuthError):
        svc.login("drsmith", "Wrong-password-99")
    svc.login("drsmith", PASSWORD)
    events, result = svc.read_audit()
    assert result.ok, result.problems
    actions = [e["action"] for e in events]
    for a in ("SETUP", "LOGIN_SUCCESS", "CLIENT_CREATE", "CLIENT_VIEW", "LOGOUT",
              "LOGIN_FAILURE"):
        assert a in actions
    assert all(e["user"] == "drsmith" for e in events)


def test_audit_log_detects_edits_and_truncation(svc, client_a, home):
    p = home / "audit.log.enc"
    lines = p.read_bytes().splitlines()
    # Remove a middle line.
    p.write_bytes(b"\n".join(lines[:2] + lines[3:]) + b"\n")
    _, result = svc.read_audit()
    assert not result.ok
    # Truncate the end.
    p.write_bytes(b"\n".join(lines[:2]) + b"\n")
    _, result = svc.read_audit()
    assert not result.ok and any("removed from the end" in x for x in result.problems)


def test_audit_never_contains_field_values(svc, client_a):
    svc.update_client(client_a, {"last_name": "Smithers", "first_name": "Jane",
                                 "dob": "2015-03-10", "grade": "6", "flow": "A"})
    events, _ = svc.read_audit()
    upd = [e for e in events if e["action"] == "CLIENT_UPDATE"][0]
    assert sorted(upd["details"]["fields_changed"]) == ["grade", "last_name"]
    assert "Smithers" not in json.dumps(events)


def test_delete_client_removes_data_and_audits(svc, client_a, home):
    svc.save_assessment(client_a, "interview", "clinical", "2026-09-01",
                        {"presenting": "Unique-Deleted-Text"})
    svc.open_report(client_a)
    counts = svc.delete_client(client_a, "Retention period expired")
    assert counts == {"assessments": 1, "report_versions": 1}
    assert svc.search_clients("Doe") == []
    assert b"Unique-Deleted-Text" not in svc.db.serialize()
    events, _ = svc.read_audit()
    d = [e for e in events if e["action"] == "CLIENT_DELETE"][0]
    assert d["details"]["reason"] == "Retention period expired"
    assert d["client_ref"].startswith("C-")


def test_archive_roundtrip_and_verify(svc, client_a, home):
    path = home / "backup.caarchive"
    svc.export_archive(path, "Archive-Pass-2026")
    assert b"Doe" not in path.read_bytes()
    with pytest.raises(crypto.DecryptionError):
        archive.unpack(path.read_bytes(), "Wrong-Archive-Pass-1")
    ok = svc.verify_backup(path, "Archive-Pass-2026")
    assert ok["ok"] and ok["counts"]["clients"] == 1
    # A copied db.enc (as Time Machine would hold) verifies with the current key.
    copy = home / "tm-copy.db.enc"
    copy.write_bytes((home / "db.enc").read_bytes())
    assert svc.verify_backup(copy)["ok"]
    svc.delete_client(client_a, "test")
    svc.restore_archive(path, "Archive-Pass-2026")
    assert len(svc.search_clients("Doe")) == 1
    _, result = svc.read_audit()
    assert result.ok, result.problems


def test_non_admin_restrictions(svc, home):
    svc.add_user("assistant", "Another-Pass-77", "clinician")
    svc.logout()
    svc.login("assistant", "Another-Pass-77")
    with pytest.raises(PermissionError):
        svc.read_audit()
    with pytest.raises(PermissionError):
        svc.export_archive(home / "x.caarchive", "Archive-Pass-2026")


def test_dashboard_and_settings(svc, client_a):
    d = svc.dashboard()
    assert d["total_clients"] == 1 and len(d["active"]) == 1
    assert d["pending"][0]["missing"][0] == "Interview"
    svc.save_assessment(client_a, "sdq", "parent", "2026-09-02", {"item1": 1})
    assert len(svc.dashboard()["awaiting_report"]) == 1
    svc.open_report(client_a)
    d = svc.dashboard()
    assert d["drafts"] and not d["awaiting_report"]
    assert svc.idle_timeout_seconds() == 15 * 60
    svc.set_idle_timeout(5)
    assert svc.idle_timeout_seconds() == 300
    with pytest.raises(ValueError):
        svc.set_idle_timeout(240)
