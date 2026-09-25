"""Encrypted archive format for exports and backups (.caarchive).

Layout:
    MAGIC (6 bytes) | salt (16) | scrypt N as uint32 big-endian (4) |
    nonce (12) | AES-256-GCM ciphertext of the serialized SQLite DB | tag (16)

The archive key comes from a separate archive password via scrypt, so
an archive can be restored on a new machine without the app's login
keystore. The header (magic, salt, N) is bound as associated data.
"""

from __future__ import annotations

import sqlite3
import struct

from . import config, crypto
from .keystore import validate_password

MAGIC = b"CAARC1"
_HDR = len(MAGIC) + config.SALT_BYTES + 4


def pack(plaintext_db: bytes, password: str, scrypt_n: int = config.SCRYPT_N) -> bytes:
    if validate_password(password):
        raise ValueError("archive password does not meet the password policy")
    salt = crypto.random_salt()
    header = MAGIC + salt + struct.pack(">I", scrypt_n)
    key = crypto.derive_key(password, salt, n=scrypt_n)
    return header + crypto.encrypt(key, plaintext_db, header)


def unpack(blob: bytes, password: str) -> bytes:
    if not blob.startswith(MAGIC) or len(blob) < _HDR:
        raise crypto.DecryptionError("not a ClinAssess archive")
    header = blob[:_HDR]
    salt = header[len(MAGIC):len(MAGIC) + config.SALT_BYTES]
    (n,) = struct.unpack(">I", header[-4:])
    if n < 2 ** 12 or n > 2 ** 22:
        raise crypto.DecryptionError("invalid archive parameters")
    key = crypto.derive_key(password, salt, n=n)
    return crypto.decrypt(key, blob[_HDR:], header)


def inspect_database(plaintext_db: bytes) -> dict:
    """Integrity-check a decrypted database image in memory only."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.deserialize(plaintext_db)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {}
        for table in ("clients", "assessments", "report_versions", "audit_log"):
            try:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.DatabaseError:
                counts[table] = None
        return {"integrity": integrity, "counts": counts}
    finally:
        conn.close()
