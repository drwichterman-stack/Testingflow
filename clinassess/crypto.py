"""Cryptographic primitives.

All encryption uses AES-256-GCM (authenticated encryption) from the
`cryptography` package, which wraps OpenSSL. No custom ciphers are used.

Key hierarchy
-------------
    password --scrypt--> KEK (per user)  --AES-256-GCM wraps--> DEK
    DEK (random 256-bit) --AES-256-GCM--> database file
    DEK                  --AES-256-GCM--> audit-log private key (X25519)
    audit public key     --X25519 + HKDF + AES-256-GCM--> each audit log line
    export password --scrypt--> archive key --AES-256-GCM--> backup archive

The audit log is sealed to a public key so that events that happen before
login (for example, failed login attempts) can still be written encrypted.
Only a logged-in user, who holds the DEK, can decrypt the private key and
read the log.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from . import config


class DecryptionError(Exception):
    """Raised when authenticated decryption fails (wrong key or tampering)."""


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def random_key() -> bytes:
    return secrets.token_bytes(config.KEY_BYTES)


def random_salt() -> bytes:
    return secrets.token_bytes(config.SALT_BYTES)


def derive_key(password: str, salt: bytes, n: int = config.SCRYPT_N,
               r: int = config.SCRYPT_R, p: int = config.SCRYPT_P) -> bytes:
    """Derive a 256-bit key from a password with scrypt."""
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p,
        maxmem=config.SCRYPT_MAXMEM, dklen=config.KEY_BYTES,
    )


def encrypt(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """AES-256-GCM encrypt. Returns nonce || ciphertext || tag."""
    if len(key) != 32:
        raise ValueError("AES-256 requires a 32-byte key")
    nonce = os.urandom(config.NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def decrypt(key: bytes, blob: bytes, aad: bytes = b"") -> bytes:
    if len(key) != 32:
        raise ValueError("AES-256 requires a 32-byte key")
    nonce, ct = blob[:config.NONCE_BYTES], blob[config.NONCE_BYTES:]
    try:
        return AESGCM(key).decrypt(nonce, ct, aad)
    except InvalidTag as exc:
        raise DecryptionError("authentication failed") from exc


# ---------------------------------------------------------------------------
# Sealed boxes for the audit log (X25519 + HKDF-SHA256 + AES-256-GCM)
# ---------------------------------------------------------------------------

_SEAL_INFO = b"clinassess-audit-seal-v1"


def generate_log_keypair() -> tuple[bytes, bytes]:
    """Return (private_raw, public_raw), 32 bytes each."""
    priv = X25519PrivateKey.generate()
    priv_raw = priv.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
        serialization.NoEncryption())
    pub_raw = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return priv_raw, pub_raw


def _seal_key(shared: bytes, epk: bytes, rpk: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=epk + rpk,
                info=_SEAL_INFO).derive(shared)


def seal(recipient_pub: bytes, plaintext: bytes, aad: bytes = b"") -> tuple[bytes, bytes]:
    """Encrypt to a public key. Returns (ephemeral_public_key, nonce||ct)."""
    eph = X25519PrivateKey.generate()
    epk = eph.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    shared = eph.exchange(X25519PublicKey.from_public_bytes(recipient_pub))
    key = _seal_key(shared, epk, recipient_pub)
    return epk, encrypt(key, plaintext, aad)


def unseal(recipient_priv: bytes, epk: bytes, blob: bytes, aad: bytes = b"") -> bytes:
    priv = X25519PrivateKey.from_private_bytes(recipient_priv)
    rpk = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    shared = priv.exchange(X25519PublicKey.from_public_bytes(epk))
    return decrypt(_seal_key(shared, epk, rpk), blob, aad)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data: bytes) -> None:
    """Write a file atomically with owner-only permissions (0600)."""
    path = os.fspath(path)
    tmp = f"{path}.tmp-{secrets.token_hex(4)}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
