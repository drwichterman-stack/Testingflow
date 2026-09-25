"""Encrypted SQLite storage.

Design: the SQLite database lives in memory while the app is unlocked.
After each committed transaction the whole database is serialized
(sqlite3 `serialize()`), encrypted with AES-256-GCM under the DEK, and
written atomically to clinassess.db.enc with 0600 permissions.

Result: plaintext PHI is never written to disk, not even as SQLite
journal or WAL files. The file is authenticated, so any modification of
the ciphertext is detected at load time.

This approach suits a single-user practice database (a few MB). It does
not need a native SQLCipher build, which is hard to package and verify on
macOS.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import config, crypto

MAGIC = b"CADB\x01"
SCHEMA_VERSION = "1"
_SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def decrypt_file(dek: bytes, blob: bytes) -> bytes:
    """Decrypt a clinassess.db.enc image (also used to verify backup copies)."""
    if not blob.startswith(MAGIC):
        raise crypto.DecryptionError("not a ClinAssess database file")
    return crypto.decrypt(dek, blob[len(MAGIC):], MAGIC)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EncryptedDatabase:
    def __init__(self, dek: bytes, path=None):
        self.path = Path(path or config.database_path())
        self._dek = dek
        self.conn = sqlite3.connect(":memory:", isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        if self.path.exists():
            self._load(self.path.read_bytes())
        self._configure()
        self.conn.executescript(_SCHEMA_FILE.read_text("utf-8"))
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,))
        if not self.path.exists():
            self.flush()

    def _configure(self) -> None:
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Keep temporary tables and sort spill in memory, never on disk.
        self.conn.execute("PRAGMA temp_store = MEMORY")

    def _load(self, blob: bytes) -> None:
        self.conn.deserialize(decrypt_file(self._dek, blob))

    def serialize(self) -> bytes:
        return self.conn.serialize()

    def flush(self) -> None:
        """Encrypt the in-memory database and write it to disk."""
        blob = MAGIC + crypto.encrypt(self._dek, self.conn.serialize(), MAGIC)
        crypto.atomic_write(self.path, blob)

    @contextmanager
    def transaction(self):
        """Run statements in one transaction, then persist encrypted."""
        self.conn.execute("BEGIN")
        try:
            yield self.conn
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        self.conn.execute("COMMIT")
        self.flush()

    def replace_contents(self, plaintext_db: bytes) -> None:
        """Replace the whole database (used by archive restore)."""
        self.conn.deserialize(plaintext_db)
        self._configure()
        self.conn.executescript(_SCHEMA_FILE.read_text("utf-8"))
        self.flush()

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.transaction() as c:
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                      "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))

    def close(self) -> None:
        try:
            self.flush()
        finally:
            self.conn.close()
            self._dek = b""
