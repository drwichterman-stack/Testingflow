"""Application paths and security constants.

Every security-relevant constant lives in this file so a reviewer can
confirm the settings in one place.
"""

import os
import sys
from pathlib import Path

APP_NAME = "ClinAssess"
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Storage location
# ---------------------------------------------------------------------------
# macOS default: ~/Library/Application Support/ClinAssess
# CLINASSESS_HOME overrides the location (used by the automated tests).


def data_dir() -> Path:
    override = os.environ.get("CLINASSESS_HOME")
    if override:
        base = Path(override)
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path.home() / f".{APP_NAME.lower()}"
    base.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(base, 0o700)  # owner-only access to the data directory
    except OSError:
        pass
    return base


def keystore_path() -> Path:
    return data_dir() / "keystore.json"


def database_path() -> Path:
    return data_dir() / "clinassess.db.enc"


def audit_log_path() -> Path:
    return data_dir() / "audit.log.enc"


def reports_dir() -> Path:
    p = data_dir() / "reports"
    p.mkdir(exist_ok=True)
    try:
        os.chmod(p, 0o700)
    except OSError:
        pass
    return p


# ---------------------------------------------------------------------------
# Cryptography
# ---------------------------------------------------------------------------
# Key derivation: scrypt (RFC 7914). N=2^17, r=8, p=1 uses 128 MiB of memory
# and takes roughly 0.3 to 0.6 seconds on Apple Silicon, which slows
# offline password guessing.
SCRYPT_N = 2 ** 17
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 256 * 1024 * 1024
KEY_BYTES = 32  # 256-bit keys for AES-256-GCM
NONCE_BYTES = 12  # 96-bit GCM nonce (NIST SP 800-38D recommendation)
SALT_BYTES = 16

# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
MIN_PASSWORD_LENGTH = 12
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300
IDLE_TIMEOUT_SECONDS = 15 * 60  # automatic logoff, 45 CFR 164.312(a)(2)(iii)

# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------
# Default retention review threshold in years. Adjust to your state's
# record-retention law and your professional board's rules.
DEFAULT_RETENTION_YEARS = 7
