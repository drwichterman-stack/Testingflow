# ClinAssess

Offline desktop software for scoring clinical assessments and writing reports on macOS. All data stays on one Mac, encrypted with AES-256. The app needs no internet connection and makes no network connections: no license checks, analytics, updates, or cloud features.

> **Status: pre-release.** Before entering real client data, complete [docs/COMPLIANCE_REVIEW.md](docs/COMPLIANCE_REVIEW.md) and the sign-off table in [docs/SCORING_REFERENCE.md](docs/SCORING_REFERENCE.md). Before selling, resolve the blockers in [docs/COMMERCIAL_RELEASE.md](docs/COMMERCIAL_RELEASE.md).

## Contents

- [Features](#features)
- [Instruments and flows](#instruments-and-flows)
- [Setup on macOS](#setup-on-macos)
- [Daily use](#daily-use)
- [Architecture](#architecture)
- [HIPAA technical safeguards](#hipaa-technical-safeguards)
- [Offline guarantee](#offline-guarantee)
- [Known limitations](#known-limitations)
- [Documentation index](#documentation-index)

## Features

| Area | What it does |
|---|---|
| **Dashboard** | Active clients, pending assessments, clients awaiting a report, draft reports, recent reports |
| **Client workspace** | One-click **Start session**, **Add assessment**, **Generate report**, **Export PDF** |
| **Login** | Individual accounts, scrypt-protected keys, lockout after 5 failed attempts, auto-lock after 5 to 30 minutes idle (admin setting, default 15) |
| **Intake** | Name, date of birth (age computed), grade, Flow A or B, ASRS gate for Flow A |
| **Data entry** | Forms built from each instrument's definition; one-click response buttons; live scoring panel with range checks |
| **Safety alerts** | Suicide and self-injury items on the WSR-II raise a red alert on the form, the client page, and in the report tables |
| **Report editor** | Auto-drafted report; every narrative section editable; score tables, headings, header, and disclaimer locked; each save is a new version; revert to auto-generated at any time |
| **PDF** | "Patient Name: X \| Page: N" at the top right of every page; footer with generation date and a blank clinician line; signature block and confidentiality notice on the final page; AES-256 encrypted; printing disabled |
| **Dictation** | On-device macOS speech-to-text into notes and report sections. Audio never leaves the Mac and is never saved |
| **Audit trail** | Encrypted, hash-chained log of logins, failed logins, views, searches, changes (field names only), deletions, exports, backup tests |
| **Deletion** | Reason and typed confirmation required; audited with record counts |
| **Backup** | Encrypted archive export and restore; built-in restore test for archives and Time Machine copies |
| **Look and feel** | Light and dark themes (or follow macOS), four text sizes, tooltips, Getting Started guide, About dialog with credits and license |

## Instruments and flows

| Flow A: Children/Adolescents (6+) | Flow B: Adolescents/Adults |
|---|---|
| Interview notes | Interview notes |
| SDQ (parent, teacher, self) | MMPI-3 |
| CATS: Child and Adolescent Trauma Screen | Brown EF/A Scales |
| Conners 4 (self, parent, teacher) | WSR-II |
| SNAP-IV 26 (parent, teacher) | WFIRS-S (self report) |
| TOVA | ASRS v1.1 |
| WSR-II | TOVA |
| WFIRS-P (parent report) | |
| ASRS v1.1 (only if enabled at intake) | |

**Scored by the app:** SDQ, CATS, SNAP-IV, WSR-II, WFIRS-P, WFIRS-S, ASRS. Scoring rules were checked against the official forms supplied by the practice; see [docs/SCORING_REFERENCE.md](docs/SCORING_REFERENCE.md) for each rule, its source, and its status.

**Entered from the publisher's software:** MMPI-3, Conners 4, Brown EF/A, TOVA. Their norms are proprietary; the app never computes them.

## Setup on macOS

**For customers:** open `ClinAssess-<version>.dmg`, drag ClinAssess to Applications, and open it. See the Quick Start Guide on the disk image.

**For development:** macOS 13 or later, Python 3.11 or later, FileVault on.

```bash
git clone https://github.com/drwichterman-stack/Testingflow.git
cd Testingflow
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest          # all tests should pass
python -m clinassess      # start the app
./build_macos.sh          # build dist/ClinAssess.app and dist/ClinAssess-<version>.dmg
```

`build_macos.sh` runs the tests, draws the app icon, bundles the app without Qt's networking modules, adds the macOS privacy strings for dictation, and builds the `.dmg` (app, Applications shortcut, license agreement, README, quick start guide, third-party notices). With `SIGN_IDENTITY` and `NOTARY_PROFILE` set, it also signs and notarizes. See [docs/COMMERCIAL_RELEASE.md](docs/COMMERCIAL_RELEASE.md).

On first launch the app shows the license agreement and asks you to create the **administrator account**. That password protects the encryption key. **There is no recovery.**

### Where data is stored

`~/Library/Application Support/ClinAssess/` (folder 0700, files 0600):

| File | Contents | Encrypted |
|---|---|---|
| `clinassess.db.enc` | All client data (SQLite image) | AES-256-GCM |
| `audit.log.enc` | Audit trail, one sealed entry per line | X25519 + AES-256-GCM |
| `keystore.json` | Usernames, roles, wrapped keys. **No PHI** | Keys wrapped with AES-256-GCM |
| `preferences.json` | Theme, text size. **No PHI** | Not needed |
| `reports/` | Default folder for exported PDFs | AES-256 (PDF) |

## Daily use

1. **Sign in.** Cmd+L locks the app at once.
2. **New client:** name, DOB, grade, flow. For Flow A, tick *Include ASRS* only when appropriate.
3. **Start session:** opens today's interview notes (type or dictate).
4. **Add assessment:** enter responses by item number from the paper form; the score panel updates as you click.
5. **Generate report:** edit sections, replace every `[Clinician to complete ...]` prompt, **Save version**.
6. **Export PDF:** choose a PDF password and send it to the recipient separately from the file.
7. **Monthly:** Admin > Export encrypted archive, then Admin > Test a backup.

## Architecture

```
clinassess/
  config.py          security constants and publisher details in one place
  crypto.py          AES-256-GCM, scrypt, X25519 sealed boxes, atomic 0600 writes
  keystore.py        user accounts, key wrapping, lockout
  database.py        in-memory SQLite with encrypted persistence
  schema.sql         schema: clients, assessments, report_versions, audit_log, settings
  audit.py           encrypted hash-chained audit log
  service.py         every data operation; each one audited
  archive.py         encrypted export format and restore test
  report.py          report sections, locked titles, auto-draft text
  pdf.py             PDF layout and AES-256 encryption
  dictation.py       on-device speech recognition (macOS Speech framework)
  prefs.py           display preferences (no PHI)
  scoring/           one module per instrument; pure functions; unit tested
  ui/                PySide6 windows (no data logic)
tests/               scoring, security, report/PDF, offline, GUI smoke tests
docs/                compliance, scoring, retention, backup, release documents and log templates
```

**Key hierarchy**

```
login password -> [scrypt(N=2^17, r=8, p=1)] -> key-encryption key (per user)
key-encryption key -> [AES-256-GCM] -> data key (DEK, random 256-bit)
DEK -> [AES-256-GCM] -> clinassess.db.enc
DEK -> [AES-256-GCM] -> audit-log private key
audit public key -> [X25519 + HKDF-SHA256 + AES-256-GCM] -> each audit line
archive password -> [scrypt] -> archive key -> [AES-256-GCM] -> .caarchive
PDF password -> PDF 2.0 AES-256 (V5/R6)
```

**Why an in-memory database instead of SQLCipher.** SQLite runs in memory while the app is unlocked. After each committed change the whole database is serialized, encrypted with AES-256-GCM, and written atomically. Plaintext never reaches the disk, not even as SQLite journal or temp files, and GCM authentication detects any change to the file. It avoids a native SQLCipher build that is hard to package and verify on macOS. At 1 to 5 clients a week the database stays in the low megabytes, so each save takes milliseconds.

## HIPAA technical safeguards

Mapping to the Security Rule, 45 CFR 164.312. Administrative and physical safeguards (164.308, 164.310) remain the practice's responsibility; see [docs/COMPLIANCE_REVIEW.md](docs/COMPLIANCE_REVIEW.md), Part D.

| Standard | Requirement | Implementation | Where |
|---|---|---|---|
| 164.312(a)(1) Access control | Unique user identification (R) | Individual accounts; username on every audit entry and record | `keystore.py`, `service.py` |
| | Emergency access procedure (R) | Encrypted archive plus a second admin account; documented in the DR policy | `archive.py`, DR policy |
| | Automatic logoff (A) | Idle lock (admin-set, 5 to 30 minutes); keys dropped from the session | `ui/app.py`, `service.py` |
| | Encryption and decryption (A) | AES-256-GCM for database, audit log, archives; AES-256 for PDFs | `crypto.py`, `database.py`, `pdf.py` |
| 164.312(b) Audit controls | Record and examine activity | Encrypted hash-chained log file plus `audit_log` table; viewer with integrity check | `audit.py`, `ui/admin.py` |
| 164.312(c)(1) Integrity | Protect PHI from improper alteration | GCM authentication on every file; hash chain on the audit log; report versions never overwritten; score tables not editable in reports | `crypto.py`, `audit.py`, `service.py` |
| 164.312(d) Authentication | Verify identity | Password policy (12+ characters, 3 character classes), scrypt, lockout after 5 failures | `keystore.py` |
| 164.312(e)(1) Transmission security | Guard PHI in transmission | No network code at all; exports are encrypted before they are written | `tests/test_offline.py` |

**Logged:** logins, failed logins, logout, auto-lock, client create, view, update (changed field names), search (result count only), delete (reason and counts), assessment create, view, update, delete, report view, save, export, dashboard views, archive export and restore, backup tests, retention reviews, setting changes, user changes, password changes, database integrity failures, application errors (exception type only).

**Never logged:** field values, search terms, clinical text. The trail can be kept after a client is deleted without holding that client's PHI.

## Offline guarantee

- The package imports no networking code. `tests/test_offline.py` checks this on every test run by parsing every module.
- The same test file runs the full workflow and the GUI with every socket call replaced by one that fails, and cuts the network in the middle of a session.
- The `.app` is built without Qt's networking and web modules.
- Dictation requires on-device recognition (`requiresOnDeviceRecognition`). If a Mac cannot transcribe on-device, the Dictate button is disabled; it never falls back to Apple's servers.
- The only way anything leaves the app is an explicit user export (PDF or archive), and both are encrypted.

## Known limitations

1. **Instrument permissions for sale.** See [docs/COMMERCIAL_RELEASE.md](docs/COMMERCIAL_RELEASE.md), section 1.1. The SDQ in particular requires a license from Youth in Mind for electronic use.
2. **Licensed instruments are not scored.** MMPI-3, Conners 4, Brown EF/A, and TOVA scores are typed in from the publisher's software.
3. **Items marked VERIFY** in the scoring reference need checking against the manuals (SNAP-IV cutoffs, WSR-II symptom convention, CATS caregiver cutoffs, Conners 4 bands).
4. **Dictation is untested on hardware.** It was written against Apple's documented API but could not run in the Linux build environment. Test it on a Mac (COMPLIANCE_REVIEW.md, Part C).
5. **Memory.** Decrypted data exists in RAM while the app is unlocked; Python cannot guarantee that keys are wiped. macOS encrypts swap. Lock the app when away.
6. **Keys are not rotated when a user is removed.** For a staff departure: export an archive, reinstall, restore.
7. **PDF print restriction is advisory.** Preview and Acrobat honor it; other viewers may not. The AES-256 password is the real control.
8. **Screen capture is not blocked.** Unsaved form entries are discarded on auto-lock.
9. **One Mac per installation.** There is no multi-computer sync, by design.

## Documentation index

| Document | Purpose |
|---|---|
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Quick start guide (also in the app under Help) |
| [docs/COMPLIANCE_REVIEW.md](docs/COMPLIANCE_REVIEW.md) | How to get the app reviewed; reviewer test script, including offline and dictation tests |
| [docs/SCORING_REFERENCE.md](docs/SCORING_REFERENCE.md) | Scoring rules, sources, form verification, and sign-off |
| [docs/DATA_RETENTION.md](docs/DATA_RETENTION.md) | Retention and deletion procedures |
| [docs/BACKUP_AND_DISASTER_RECOVERY_POLICY.md](docs/BACKUP_AND_DISASTER_RECOVERY_POLICY.md) | Backup and DR policy for the compliance officer |
| [docs/templates/](docs/templates/) | Backup testing log, secure deletion log, breach notification log |
| [docs/COMMERCIAL_RELEASE.md](docs/COMMERCIAL_RELEASE.md) | Blockers and checklist before selling |
| [LICENSE.txt](LICENSE.txt) | End user license agreement (draft for attorney review) |
| [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt) | Open-source licenses and instrument ownership |
| [clinassess/schema.sql](clinassess/schema.sql) | Database schema |
