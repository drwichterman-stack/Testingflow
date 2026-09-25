# Compliance Review Guide

How to get ClinAssess reviewed before clinical use, and a step-by-step test script your compliance officer can follow. The review has four parts. Parts A and B are required before any real client data is entered.

## What the reviewer receives

| Item | Location |
|---|---|
| This guide | `docs/COMPLIANCE_REVIEW.md` |
| Technical safeguards mapped to HIPAA | `README.md`, section "HIPAA technical safeguards" |
| Known limitations | `README.md`, section "Known limitations" |
| Database schema | `clinassess/schema.sql` |
| Security constants (one file) | `clinassess/config.py` |
| Scoring rules and verification status | `docs/SCORING_REFERENCE.md` |
| Retention and deletion procedures | `docs/DATA_RETENTION.md` |
| Backup and disaster recovery policy | `docs/BACKUP_AND_DISASTER_RECOVERY_POLICY.md` |
| Log templates | `docs/templates/` |
| Automated test suite | `tests/` (run with `python -m pytest`) |

## Part A. Technical verification (reviewer, about 2 hours)

Use a test Mac or a new macOS user account and **fictitious data only**.

| # | Test | Expected result | Pass |
|---|---|---|---|
| A1 | Run `python -m pytest` | All tests pass (includes encryption, tamper detection, offline, and PDF tests) | |
| A2 | Launch the app; complete first-time setup with a weak password (for example, `password`) | Rejected with the policy message | |
| A3 | Complete setup with a strong password | License must be accepted; dashboard opens | |
| A4 | Create client "Test Patient", DOB 2015-01-01, Flow A. Add an SDQ | Dashboard and client page update | |
| A5 | In Terminal: `grep -c "Patient" ~/Library/Application\ Support/ClinAssess/*` | 0 matches in every file (no plaintext PHI) | |
| A6 | `ls -la` on the data folder | Folder `drwx------`, files `-rw-------` | |
| A7 | Quit and relaunch; enter a wrong password 5 times | "Too many failed attempts"; locked for 5 minutes, even with the right password | |
| A8 | Log in; leave the app idle for the auto-lock time | App locks and asks for the password | |
| A9 | Admin > Audit trail | "Integrity check PASSED"; shows the failed logins, views, searches, and changes with user and time; no names or field values in Details | |
| A10 | Quit the app. In a text editor, delete one line from the middle of `audit.log.enc`. Relaunch; Admin > Audit trail | "Integrity check FAILED", naming the broken line | |
| A11 | Quit. Change one byte of `clinassess.db.enc` (for example with a hex editor). Relaunch and log in | Login refused: the file fails authentication. (Restore the original file afterward) | |
| A12 | Generate report, edit a section, Save version, then Export PDF | Asks for a PDF password; opening the PDF needs it; Print is disabled in Preview; header "Patient Name: ... \| Page: N" on every page; signature block and confidentiality notice on the last page | |
| A13 | Report editor: Version history; Revert to auto-generated | All versions listed with user and time; revert creates a new version | |
| A14 | Delete the test client (reason required, type the code) | Client gone; audit trail shows `CLIENT_DELETE` with reason and counts | |
| A15 | Admin > Export encrypted archive; then Admin > Test a backup | Passes; `BACKUP_VERIFY` in the audit trail | |
| A16 | Create a second user with the clinician role; log in as that user | Admin menu functions refused | |

## Part B. Offline verification (reviewer, 20 minutes)

| # | Test | Expected result | Pass |
|---|---|---|---|
| B1 | Turn off Wi-Fi and unplug Ethernet. Launch the app | Opens normally; no network error anywhere | |
| B2 | Log in, add a client, enter an assessment, create and export a PDF | Everything works | |
| B3 | Turn Wi-Fi on during a session, then off again mid-entry | No change in behavior, no messages | |
| B4 | Optional: run Little Snitch or LuLu (outbound firewall) during a full session | ClinAssess makes **no** outbound connection attempts | |
| B5 | Optional: `sudo lsof -i -P \| grep -i clinassess` during use | No network sockets listed | |

The automated test `tests/test_offline.py` repeats B1 to B3 with every network call blocked, and fails if any module in the app imports networking code.

## Part C. On-device dictation (if the practice will use it)

| # | Test | Expected result | Pass |
|---|---|---|---|
| C1 | Start session > Dictate (first time) | macOS asks for Microphone and Speech Recognition permission | |
| C2 | Turn off Wi-Fi, then dictate a sentence | Text appears; it works fully offline | |
| C3 | On a Mac or language without on-device support | Dictate button is disabled, with an explanation (no cloud fallback) | |
| C4 | After dictation, search the data folder and `/tmp` for audio files | None: audio is never saved | |

**Policy point:** the feature is intended for the clinician dictating their own notes. Recording or transcribing a client session requires the client's informed consent and must follow your state's recording-consent law. Decide and document whether in-session dictation is allowed.

## Part E. Camera form capture (if the practice will use it)

| # | Test | Expected result | Pass |
|---|---|---|---|
| E1 | Open an SDQ, click **Capture form** (first time) | macOS asks for Camera permission; the preview shows the camera | |
| E2 | Deny permission, reopen | A message explains how to allow it in System Settings; nothing crashes | |
| E3 | Turn off Wi-Fi, capture and read a form | Works fully offline | |
| E4 | Snap a completed SDQ, outline items 1-25, apply | Responses filled in; doubtful items flagged; overlay colors match | |
| E5 | Capture a second SDQ of the same version | Saved outline is placed automatically and reads correctly | |
| E6 | Capture a WSR-II with suicide items marked | Safety items are flagged "Safety: confirm" even when read clearly | |
| E7 | Try to save with flags remaining | App asks for confirmation; the audit entry records the unchecked count | |
| E8 | After capture, search the data folder, `/tmp`, and `~/Pictures` for images | None: photos are never saved | |
| E9 | Accuracy: 10 real completed forms per instrument you will use; compare every item with a manual entry | Record wrong-but-unflagged items. **Any** such item means the feature is not approved for that form and lighting setup | |

**Policy point:** the clinician must compare every response with the paper form before saving. The paper form stays the source record under your retention policy.

## Part D. Administrative safeguards (practice, with the compliance officer)

The software covers technical safeguards only. HIPAA also requires the following, which remain the practice's responsibility:

1. **Security risk analysis** (164.308(a)(1)(ii)(A)) that includes this Mac, the backup drives, and ClinAssess. The HHS SRA Tool is a free option.
2. **Policies**: adopt `BACKUP_AND_DISASTER_RECOVERY_POLICY.md` and `DATA_RETENTION.md` with your specifics filled in.
3. **Device controls**: FileVault on; screen lock of 5 minutes or less; macOS updates on; Find My enabled; no shared macOS accounts.
4. **Workforce**: individual ClinAssess accounts for each person; training record; sanctions policy.
5. **Business Associate Agreements**: none needed for ClinAssess itself (the vendor never receives PHI). Needed for any cloud or IT service that could access PHI.
6. **Instrument licensing**: confirm you hold the needed licenses and permissions (see `SCORING_REFERENCE.md` and the README limitations).
7. **Scoring verification**: complete the sign-off table in `SCORING_REFERENCE.md`, including hand-scoring at least 2 protocols per app-scored instrument and comparing results.

## Sign-off

| Part | Reviewer | Date | Result | Notes |
|---|---|---|---|---|
| A. Technical | | | | |
| B. Offline | | | | |
| C. Dictation | | | | |
| E. Camera capture | | | | |
| D. Administrative | | | | |
| **Approved for clinical use** | | | | |

## Getting an independent review (optional, recommended for a product)

For a product sold to other clinicians, an independent security assessment strengthens the compliance story:

- A **penetration test or code review** by a firm that tests healthcare software (scope: local data at rest, key handling, audit integrity, PDF and archive encryption). Share this guide and the source.
- A **HIPAA consultant** review of the documentation set, to produce a letter customers can show their own compliance officers.
- There is no official "HIPAA certification" for software. Be careful with marketing: say "designed to support HIPAA compliance", never "HIPAA certified".
