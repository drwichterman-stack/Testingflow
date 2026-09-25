# Data Retention and Deletion Procedures

This document describes how ClinAssess stores, keeps, and deletes client data, and what the practice must do alongside it. Fill in the bracketed items for your practice.

## 1. What is stored, and where

| Data | Location | Protection |
|---|---|---|
| Demographics, interview notes, responses, scores, report versions | `clinassess.db.enc` | AES-256-GCM, key wrapped by each user's password |
| Audit trail | `audit.log.enc` and the `audit_log` table | Sealed per entry (X25519 + AES-256-GCM); SHA-256 hash chain |
| Exported reports | Location chosen at export (default `reports/`) | AES-256 PDF password |
| Archives | Location chosen at export | AES-256-GCM, archive password |
| Time Machine copies of the above | Backup drive | Same file encryption, plus Time Machine disk encryption |

The data folder is `~/Library/Application Support/ClinAssess/`. No data is stored anywhere else, and none is transmitted.

## 2. Retention period

- **Practice retention period:** [e.g., 7 years after the last date of service for adults; for minors, until [N] years after the age of majority, whichever is later].
- **Legal basis:** [state statute or regulation], [licensing board rule], [APA Record Keeping Guidelines as professional guidance].
- HIPAA itself sets no retention period for clinical records. It requires keeping HIPAA documentation (policies, risk analyses, audit-related records) for 6 years (45 CFR 164.316(b)(2)). Keep **audit trail exports and the logs in `docs/templates/`** for at least 6 years.

## 3. Retention review (quarterly)

1. Admin > **Retention review**, set the number of years, and run it. The review is itself audited (`RETENTION_REVIEW`).
2. For each client listed, confirm against the paper chart and the retention rules (for minors, check the age-of-majority rule, which the app does not compute).
3. Delete eligible records as in section 4, or record why a record is kept (litigation hold, ongoing care).

## 4. Deleting a client record

1. Open the client, click **Delete client**.
2. Enter the reason (for example, "Retention period ended 2026-09-30") and type the reference code to confirm.
3. The app then:
   - deletes the client, all assessment entries, and all report versions in one transaction;
   - runs SQLite `VACUUM` so freed pages are cleared from the in-memory database image;
   - re-encrypts and replaces `clinassess.db.enc` (atomic write), so the new file does not contain the deleted records;
   - writes `CLIENT_DELETE` to the audit trail with the reference code, reason, record counts, user, and time.
4. Record the deletion in `docs/templates/SECURE_DELETION_LOG.md`.

**What the audit trail keeps after deletion:** the reference code (for example, `C-7F3A2B`), counts, reason, user, and time. It never holds names, dates of birth, field values, or search terms, so the trail can be kept for 6 years without holding the deleted PHI.

## 5. Where deleted data can still exist, and how long

Be precise with your compliance officer on this point:

| Copy | Contains deleted data until | Action |
|---|---|---|
| Previous versions of `clinassess.db.enc` in Time Machine | That backup ages out (see the backup policy, 90 days) | None needed; it stays encrypted. To purge early, delete the specific backups (section 6). |
| Earlier `.caarchive` exports | The archive is destroyed | Destroy archives according to the backup policy |
| Exported PDFs | The file is deleted | Track exported PDFs; delete local copies when no longer needed |
| Freed blocks on the Mac's SSD | Overwritten by the SSD over time | None needed: those blocks held only AES-256 ciphertext, and FileVault encrypts the disk too |

**Note on "secure overwrite":** on modern SSDs with APFS, overwriting a file in place does not reliably erase the old physical blocks (wear leveling and copy-on-write). ClinAssess therefore relies on **cryptographic protection**: the plaintext never reaches the disk, so any old blocks contain only ciphertext. This is the approach NIST SP 800-88 Rev. 1 recognizes for encrypted media (cryptographic erase). A policy that promises physical overwriting of deleted records on an SSD would be inaccurate; describe it as above.

## 6. Purging a record from backups early (when required)

Some requests (for example, a court order) require removing a record from backups before they expire:

1. Delete the client in the app (section 4).
2. Identify the Time Machine backups made since the record was created: `tmutil listbackups`.
3. Delete them with `sudo tmutil delete -d /Volumes/<BackupDisk> -t <timestamp>` (syntax differs between macOS versions; check `man tmutil`), or erase the backup drive and start a new backup set.
4. Destroy any `.caarchive` files made in that period.
5. Record every step in the secure deletion log.

## 7. End of use (practice closure or leaving the app)

1. Export a final archive and keep it for the retention period on encrypted media, with the archive password stored separately. Test it with **Admin > Test a backup**.
2. Export the audit trail view (screenshots or printed to an encrypted PDF) for HIPAA documentation.
3. Delete the data folder, then erase the Mac (System Settings > General > Transfer or Reset > Erase All Content and Settings). On FileVault Macs this is a cryptographic erase.
4. Erase the backup drives when their retention ends (Disk Utility, erase with a new encrypted APFS volume, or physical destruction).
