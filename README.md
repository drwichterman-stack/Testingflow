# ClinAssess

A local desktop application for scoring clinical assessments and writing reports. It runs entirely on one Mac. Client data never leaves the machine unless the clinician exports it, and every export is encrypted.

> **Status: pre-clinical.** Do not enter real client data until the compliance review in [docs/COMPLIANCE_REVIEW.md](docs/COMPLIANCE_REVIEW.md) is complete and the items marked **VERIFY** in [docs/SCORING_REFERENCE.md](docs/SCORING_REFERENCE.md) are checked against the official manuals.

## Contents

- [Features](#features)
- [Setup on macOS](#setup-on-macos)
- [Daily use](#daily-use)
- [Architecture](#architecture)
- [HIPAA technical safeguards](#hipaa-technical-safeguards)
- [Known limitations](#known-limitations)
- [Documentation index](#documentation-index)

## Features

| Area | What it does |
|---|---|
| **Login** | Per-user accounts, scrypt-protected keys, lockout after 5 failed attempts, auto-lock after 15 minutes idle |
| **Client intake** | Name, date of birth (age is computed), grade, Flow A or B, ASRS gate for Flow A |
| **Dynamic forms** | Shows only the instruments for the client's flow. Forms are built from each instrument's definition |
| **Scoring** | SDQ, CATS (trauma screen), ASRS v1.1, and WSR-II are scored by the app. MMPI-3, Conners 4, Brown EF/A, and TOVA scores are entered from the publisher's software (see [licensing](#known-limitations)) |
| **Report editor** | Auto-drafted report; every narrative section can be edited; score tables and headers are locked; each save is a version; revert to auto-generated at any time |
| **PDF** | "Patient Name: X \| Page: N" header on every page (top right); footer with generation date and a blank clinician line; signature block and confidentiality notice on the final page; AES-256 encrypted; printing disabled |
| **Search** | By name, reference code, or date of birth |
| **Audit trail** | Encrypted, hash-chained log file plus a database table; records logins, failed logins, views, searches, changes (field names only), deletions, exports, backup tests |
| **Deletion** | Requires a reason and typed confirmation; audited with record counts |
| **Backup** | Encrypted archive export and restore; built-in restore test for archives and Time Machine copies |
| **Retention** | Lists clients inactive for N years |

Flow contents:

| Flow A: Children/Adolescents (6+) | Flow B: Adolescents/Adults |
|---|---|
| Interview notes | Interview notes |
| SDQ (parent, teacher, self) | MMPI-3 |
| CATS: Child and Adolescent Trauma Screen | Brown EF/A Scales |
| Conners 4 (self, parent, teacher) | WSR-II |
| TOVA | ASRS v1.1 |
| WSR-II | TOVA |
| ASRS v1.1 (only if enabled at intake) | |

## Setup on macOS

**Requirements:** macOS 13 or later, Python 3.11 or later (from python.org or Homebrew), FileVault turned on.

```bash
# 1. Get the code
git clone https://github.com/drwichterman-stack/Testingflow.git
cd Testingflow

# 2. Create an isolated Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 3. Run the test suite (should report all tests passed)
python -m pytest

# 4. Start the app
python -m clinassess
```

On first launch the app asks you to create the **administrator account**. That password protects the encryption key. **There is no recovery.** If every administrator password is lost, the data cannot be decrypted. Keep the password in a secure place (for example, a sealed envelope in the locked cabinet, or a password manager).

### Building a double-clickable .app

```bash
./build_macos.sh
# Result: dist/ClinAssess.app  (copy it to /Applications)
```

The build is unsigned. For clinical use, have it code-signed and notarized with an Apple Developer ID, or approve it once via System Settings > Privacy & Security.

### Where data is stored

`~/Library/Application Support/ClinAssess/` (folder permissions 0700, files 0600):

| File | Contents | Encrypted |
|---|---|---|
| `clinassess.db.enc` | All client data (SQLite image) | AES-256-GCM |
| `audit.log.enc` | Audit trail, one sealed entry per line | X25519 + AES-256-GCM |
| `keystore.json` | Usernames, roles, wrapped keys. **No PHI** | Keys wrapped with AES-256-GCM |
| `reports/` | Default folder for exported PDFs | AES-256 (PDF) |

Time Machine backs up this folder automatically. See [docs/BACKUP_AND_DISASTER_RECOVERY_POLICY.md](docs/BACKUP_AND_DISASTER_RECOVERY_POLICY.md).

## Daily use

1. **Log in.** The app locks itself after 15 minutes without input (File > Lock now, or Cmd+L, locks it at once).
2. **New client intake:** enter name, DOB, grade, and flow. For Flow A, tick *Include ASRS* only when developmentally appropriate.
3. **Add assessment:** choose the instrument, form/informant, and date. Enter responses by item number from the paper form. The score preview updates as you type.
4. **Report (edit and PDF):** review each section, replace every `[Clinician to complete ...]` prompt, then **Save version**. **Generate PDF** asks for a PDF password. Send that password to the recipient separately from the file.
5. **Admin menu:** audit trail (with integrity check), users, retention review, encrypted archive, backup test, restore.

## Architecture

```
clinassess/
  config.py          all security constants in one place
  crypto.py          AES-256-GCM, scrypt, X25519 sealed boxes, atomic 0600 writes
  keystore.py        user accounts, key wrapping, lockout
  database.py        in-memory SQLite, encrypted persistence
  schema.sql         database schema (clients, assessments, report_versions, audit_log)
  audit.py           encrypted hash-chained audit log
  service.py         every data operation, each one audited
  archive.py         encrypted export format and restore test
  report.py          report sections, locked titles, auto-draft text
  pdf.py             PDF layout and AES-256 encryption
  scoring/           one module per instrument, pure functions, unit tested
  ui/                PyQt6 windows (no data logic)
tests/               pytest suite: scoring, security, report/PDF, GUI smoke test
docs/                compliance, scoring, retention, backup documents and log templates
```

**Key hierarchy**

```
login password --scrypt(N=2^17, r=8, p=1)--> key-encryption key (per user)
key-encryption key --AES-256-GCM--> data key (DEK, random 256-bit, one per installation)
DEK --AES-256-GCM--> clinassess.db.enc
DEK --AES-256-GCM--> audit-log private key
audit public key --X25519 + HKDF-SHA256 + AES-256-GCM--> each audit line
archive password --scrypt--> archive key --AES-256-GCM--> .caarchive
PDF password --> PDF 2.0 AES-256 (V5/R6)
```

**Why an in-memory database instead of SQLCipher.** SQLCipher needs a native build that is hard to package and verify on Apple Silicon. Here, SQLite runs in memory, and after each committed change the whole database is serialized, encrypted with AES-256-GCM, and written atomically. Plaintext never reaches the disk, including SQLite journal or temp files. GCM authentication also detects any change to the file. For a solo practice (1 to 5 clients a week), the database stays in the low megabytes, so rewriting it on each save takes milliseconds.

## HIPAA technical safeguards

Mapping to the Security Rule, 45 CFR 164.312. Administrative and physical safeguards (164.308, 164.310) are the practice's responsibility; see [docs/COMPLIANCE_REVIEW.md](docs/COMPLIANCE_REVIEW.md).

| Standard | Requirement | Implementation | Where |
|---|---|---|---|
| 164.312(a)(1) Access control | Unique user identification (R) | Individual accounts; username recorded on every audit entry and record | `keystore.py`, `service.py` |
| | Emergency access procedure (R) | Encrypted archive plus a second admin account; documented in the DR policy | `archive.py`, DR policy |
| | Automatic logoff (A) | 15-minute idle lock; keys dropped from the session | `ui/app.py`, `config.IDLE_TIMEOUT_SECONDS` |
| | Encryption and decryption (A) | AES-256-GCM for database, audit log, archives; AES-256 for PDFs | `crypto.py`, `database.py`, `pdf.py` |
| 164.312(b) Audit controls | Record and examine activity | Encrypted hash-chained log file plus `audit_log` table; in-app viewer with integrity check | `audit.py`, `ui/admin.py` |
| 164.312(c)(1) Integrity | Protect PHI from improper alteration | GCM authentication on every file; hash chain on audit log; report versions never overwritten; score tables cannot be edited in reports | `crypto.py`, `audit.py`, `service.py` |
| 164.312(d) Authentication | Verify identity | Password (12+ characters, 3 character classes), scrypt, lockout after 5 failures for 5 minutes | `keystore.py` |
| 164.312(e)(1) Transmission security | Guard PHI in transmission | The app has no network code. Exports are encrypted before they are written | whole codebase (no network imports) |

**What is logged:** logins, failed logins, logout, auto-lock, client create, view, update (changed field names), search (result count only, not search terms), delete (reason and counts), assessment create, view, update, delete, report view, save, export, archive export and restore, backup tests, retention reviews, user changes, password changes, application errors (exception type only).

**What is not logged:** field values, search terms, clinical text. The trail therefore holds no PHI beyond client reference codes, so it can be kept after a client record is deleted.

## Known limitations

State these to your compliance officer:

1. **Licensed instruments are not scored by the app.** MMPI-3, Conners 4, Brown EF/A, and TOVA norms are proprietary. You score them in Q-global, MHS, or TOVA software and enter the results. This keeps you within those licenses.
2. **SDQ electronic use.** Youth in Mind restricts electronic versions of the SDQ. The app shows no item wording, only item numbers. Still, confirm with Youth in Mind (sdqinfo.org) that local electronic scoring is allowed in your setting, especially in a fee-charging practice.
3. **Scoring cutoffs marked VERIFY** were written from published sources but must be checked against the manuals before clinical use (ASRS Part B shading, CATS cutoffs, WSR-II structure, Conners 4 T-score bands).
4. **Memory.** Python cannot guarantee that key material is wiped from memory. Decrypted data exists in RAM while the app is unlocked. macOS encrypts swap. Lock the app when you step away.
5. **Keys are not rotated when a user is removed.** A removed user who kept an old copy of `keystore.json` and knows their old password could decrypt an old copy of the database. For a single-clinician practice this is low risk. For a staff departure, export an archive, reinstall, and restore.
6. **PDF permissions are advisory.** "No printing" is honored by Preview and Acrobat, but any viewer can ignore it once the PDF is opened. The AES-256 password is the real control.
7. **Screen capture** is not blocked.
8. **Unsaved form entries are discarded** on auto-lock.
9. **Lockout counters** are stored in `keystore.json`. Someone with file access could reset them, but offline guessing is still slowed by scrypt.

## Documentation index

| Document | Purpose |
|---|---|
| [docs/COMPLIANCE_REVIEW.md](docs/COMPLIANCE_REVIEW.md) | How to get the app reviewed before clinical use; reviewer test script |
| [docs/SCORING_REFERENCE.md](docs/SCORING_REFERENCE.md) | Scoring rules, sources, and verification status for every instrument |
| [docs/DATA_RETENTION.md](docs/DATA_RETENTION.md) | Retention and deletion procedures |
| [docs/BACKUP_AND_DISASTER_RECOVERY_POLICY.md](docs/BACKUP_AND_DISASTER_RECOVERY_POLICY.md) | Backup and DR policy (draft for the compliance officer) |
| [docs/templates/](docs/templates/) | Backup testing log, secure deletion log, breach notification log |
| [clinassess/schema.sql](clinassess/schema.sql) | Database schema |
