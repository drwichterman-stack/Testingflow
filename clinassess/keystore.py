"""User accounts and key wrapping.

keystore.json holds no PHI. It contains:
  * usernames and roles (workforce identities, not patient data)
  * per-user scrypt salt and parameters
  * the database key (DEK), wrapped separately for each user with
    AES-256-GCM under that user's password-derived key
  * the audit-log public key, and the private key encrypted under the DEK
  * failed-login counters for lockout

The username and role are bound into the AES-GCM associated data of each
wrapped key. Editing a role in the file (for example, "user" to "admin")
makes that user's key fail to unwrap, so the change cannot be used to
raise privileges.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from . import config, crypto

ROLES = ("admin", "clinician")


class AuthError(Exception):
    pass


class LockedOutError(AuthError):
    pass


@dataclass
class Session:
    username: str
    role: str
    dek: bytes
    log_private_key: bytes

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dek_aad(username: str, role: str) -> bytes:
    return f"clinassess-dek-v1|{username}|{role}".encode()


def validate_password(password: str) -> list[str]:
    """Return a list of policy violations (empty list means acceptable)."""
    problems = []
    if len(password) < config.MIN_PASSWORD_LENGTH:
        problems.append(f"at least {config.MIN_PASSWORD_LENGTH} characters")
    classes = sum([
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ])
    if classes < 3:
        problems.append("at least 3 of: lowercase, uppercase, digit, symbol")
    return problems


def validate_username(username: str) -> bool:
    return (2 <= len(username) <= 32
            and all(c.isalnum() or c in "._-" for c in username))


class KeyStore:
    def __init__(self, path=None, scrypt_n: int | None = None):
        self.path = path or config.keystore_path()
        self.scrypt_n = scrypt_n or config.SCRYPT_N
        self.data: dict = {}
        if self.exists():
            self.data = json.loads(self.path.read_text("utf-8"))

    def exists(self) -> bool:
        return self.path.exists()

    def save(self) -> None:
        crypto.atomic_write(self.path, json.dumps(self.data, indent=2).encode("utf-8"))

    @property
    def log_public_key(self) -> bytes:
        return crypto.b64d(self.data["log_public_key"])

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def initialize(self, admin_username: str, admin_password: str) -> Session:
        if self.exists():
            raise RuntimeError("keystore already initialized")
        if not validate_username(admin_username):
            raise ValueError("invalid username")
        if validate_password(admin_password):
            raise ValueError("password does not meet policy")
        dek = crypto.random_key()
        log_priv, log_pub = crypto.generate_log_keypair()
        self.data = {
            "format": "clinassess-keystore",
            "version": 1,
            "created": _now_iso(),
            "log_public_key": crypto.b64e(log_pub),
            "log_private_key_enc": crypto.b64e(
                crypto.encrypt(dek, log_priv, b"clinassess-logkey-v1")),
            "users": {},
        }
        self._put_user(admin_username, admin_password, "admin", dek)
        self.save()
        return Session(admin_username, "admin", dek, log_priv)

    def _put_user(self, username: str, password: str, role: str, dek: bytes) -> None:
        salt = crypto.random_salt()
        kek = crypto.derive_key(password, salt, n=self.scrypt_n)
        existing = self.data["users"].get(username, {})
        self.data["users"][username] = {
            "role": role,
            "kdf": {"alg": "scrypt", "n": self.scrypt_n, "r": config.SCRYPT_R,
                    "p": config.SCRYPT_P, "salt": crypto.b64e(salt)},
            "wrapped_dek": crypto.b64e(crypto.encrypt(kek, dek, _dek_aad(username, role))),
            "created": existing.get("created", _now_iso()),
            "password_changed": _now_iso(),
            "failed_attempts": 0,
            "locked_until": 0,
        }

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def authenticate(self, username: str, password: str) -> Session:
        user = self.data.get("users", {}).get(username)
        if user is None:
            # Run the KDF anyway so response time does not reveal
            # whether the username exists.
            crypto.derive_key(password, b"\0" * config.SALT_BYTES, n=self.scrypt_n)
            raise AuthError("invalid username or password")
        if user.get("locked_until", 0) > time.time():
            raise LockedOutError("account temporarily locked")
        kdf = user["kdf"]
        kek = crypto.derive_key(password, crypto.b64d(kdf["salt"]),
                                n=kdf["n"], r=kdf["r"], p=kdf["p"])
        try:
            dek = crypto.decrypt(kek, crypto.b64d(user["wrapped_dek"]),
                                 _dek_aad(username, user["role"]))
        except crypto.DecryptionError:
            user["failed_attempts"] = user.get("failed_attempts", 0) + 1
            if user["failed_attempts"] >= config.MAX_FAILED_LOGINS:
                user["locked_until"] = time.time() + config.LOCKOUT_SECONDS
                user["failed_attempts"] = 0
                self.save()
                raise LockedOutError("too many failed attempts; account locked")
            self.save()
            raise AuthError("invalid username or password")
        if user.get("failed_attempts") or user.get("locked_until"):
            user["failed_attempts"] = 0
            user["locked_until"] = 0
            self.save()
        log_priv = crypto.decrypt(dek, crypto.b64d(self.data["log_private_key_enc"]),
                                  b"clinassess-logkey-v1")
        return Session(username, user["role"], dek, log_priv)

    # ------------------------------------------------------------------
    # User management (requires an authenticated session)
    # ------------------------------------------------------------------
    def list_users(self) -> list[tuple[str, str]]:
        return sorted((u, d["role"]) for u, d in self.data["users"].items())

    def add_user(self, session: Session, username: str, password: str, role: str) -> None:
        if not session.is_admin:
            raise PermissionError("admin role required")
        if role not in ROLES:
            raise ValueError("invalid role")
        if not validate_username(username):
            raise ValueError("invalid username")
        if username in self.data["users"]:
            raise ValueError("user already exists")
        if validate_password(password):
            raise ValueError("password does not meet policy")
        self._put_user(username, password, role, session.dek)
        self.save()

    def remove_user(self, session: Session, username: str) -> None:
        if not session.is_admin:
            raise PermissionError("admin role required")
        if username == session.username:
            raise ValueError("cannot remove the account you are logged in with")
        if username not in self.data["users"]:
            raise ValueError("no such user")
        admins = [u for u, d in self.data["users"].items() if d["role"] == "admin"]
        if self.data["users"][username]["role"] == "admin" and len(admins) <= 1:
            raise ValueError("cannot remove the last admin")
        del self.data["users"][username]
        self.save()

    def change_password(self, session: Session, old_password: str, new_password: str) -> None:
        self.authenticate(session.username, old_password)
        if validate_password(new_password):
            raise ValueError("password does not meet policy")
        self._put_user(session.username, new_password, session.role, session.dek)
        self.save()
