"""Encrypted, tamper-evident audit log (audit.log.enc).

Each line is one event:
    {"seq": N, "prev": "<sha256 of previous line>", "epk": "...", "ct": "..."}

* `ct` is the event JSON sealed to the audit public key
  (X25519 + HKDF-SHA256 + AES-256-GCM). Anyone can append (so failed logins
  are recorded before unlock), but only a logged-in user can read.
* `prev` chains each line to the SHA-256 of the line before it. Editing,
  reordering, or deleting a line in the middle breaks the chain, and
  `verify()` reports it.
* `seq` and `prev` are bound into the AES-GCM associated data, so a line's
  ciphertext cannot be moved to another position.
* The last sequence number seen while unlocked is also stored inside the
  encrypted database (settings key `audit_head_seq`), so removing lines
  from the end of the file is detected too.

Events contain usernames, action names, client reference codes, and the
names of fields that changed. They do not contain clinical content.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import config, crypto
from .database import now_iso

GENESIS = "0" * 64


@dataclass
class VerifyResult:
    ok: bool
    count: int
    problems: list[str] = field(default_factory=list)


def _aad(seq: int, prev: str) -> bytes:
    return f"clinassess-audit-v1|{seq}|{prev}".encode()


class AuditLog:
    def __init__(self, public_key: bytes, path=None):
        self.path = Path(path or config.audit_log_path())
        self.public_key = public_key

    def _tail(self) -> tuple[int, str]:
        """Return (last_seq, sha256 of last line)."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return 0, GENESIS
        with open(self.path, "rb") as fh:
            size = fh.seek(0, os.SEEK_END)
            chunk = min(size, 65536)
            fh.seek(size - chunk)
            lines = fh.read().rstrip(b"\n").split(b"\n")
        last = lines[-1]
        return int(json.loads(last)["seq"]), crypto.sha256_hex(last)

    def append(self, username: str, action: str, client_ref: str | None = None,
               entity: str | None = None, entity_id: int | None = None,
               details: dict | None = None) -> int:
        seq, prev = self._tail()
        seq += 1
        event = {
            "ts": now_iso(), "user": username, "action": action,
            "client_ref": client_ref, "entity": entity, "entity_id": entity_id,
            "details": details or {},
        }
        epk, ct = crypto.seal(self.public_key, json.dumps(event).encode("utf-8"),
                              _aad(seq, prev))
        line = json.dumps({"seq": seq, "prev": prev, "epk": crypto.b64e(epk),
                           "ct": crypto.b64e(ct)}, separators=(",", ":"))
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "ab") as fh:
            fh.write(line.encode("ascii") + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        return seq

    def read(self, private_key: bytes, expected_head: int | None = None
             ) -> tuple[list[dict], VerifyResult]:
        """Decrypt all events and verify the hash chain."""
        events: list[dict] = []
        problems: list[str] = []
        if not self.path.exists():
            return events, VerifyResult(expected_head in (None, 0), 0,
                                        [] if expected_head in (None, 0)
                                        else ["audit log file is missing"])
        prev = GENESIS
        expected_seq = 1
        for lineno, raw in enumerate(self.path.read_bytes().splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
                seq = int(rec["seq"])
                if rec["prev"] != prev:
                    problems.append(f"line {lineno}: hash chain broken")
                if seq != expected_seq:
                    problems.append(f"line {lineno}: sequence {seq}, expected {expected_seq}")
                pt = crypto.unseal(private_key, crypto.b64d(rec["epk"]),
                                   crypto.b64d(rec["ct"]), _aad(seq, rec["prev"]))
                ev = json.loads(pt)
                ev["seq"] = seq
                events.append(ev)
                expected_seq = seq + 1
            except (ValueError, KeyError, crypto.DecryptionError) as exc:
                problems.append(f"line {lineno}: unreadable or altered ({type(exc).__name__})")
                expected_seq += 1
            prev = crypto.sha256_hex(raw)
        last = expected_seq - 1
        if expected_head is not None and last < expected_head:
            problems.append(
                f"log ends at sequence {last} but the database recorded {expected_head}; "
                "entries may have been removed from the end of the file")
        return events, VerifyResult(not problems, len(events), problems)
