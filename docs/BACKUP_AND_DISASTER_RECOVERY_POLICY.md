# Backup and Disaster Recovery Policy

**Practice:** [Practice name]
**Policy owner (Security Official):** [Name, credentials]
**Applies to:** ClinAssess [version] on [Mac model / serial number]
**Effective date:** [date]  |  **Review:** annually and after any incident
**Regulatory basis:** HIPAA Security Rule, 45 CFR 164.308(a)(7) (contingency plan: data backup plan, disaster recovery plan, emergency mode operation plan, testing and revision procedures, applications and data criticality analysis), 164.310(d)(2)(iii)-(iv) (accountability; data backup and storage), 164.312(a)(2)(ii) (emergency access procedure).

> **Draft status.** This draft was prepared with the software. It combines the practice's stated framework with corrections needed so the policy matches what macOS and the app actually do. Corrections are marked **[Correction]**. The practice's compliance officer should review and adopt it.

## 1. Purpose

To make sure client assessment data in ClinAssess can be recovered after hardware failure, loss, theft, corruption, or disaster, and to do so without creating unencrypted copies of PHI.

## 2. Data covered and criticality

| Data | Criticality | Recovery time objective | Recovery point objective |
|---|---|---|---|
| ClinAssess database (`clinassess.db.enc`), keystore (`keystore.json`), audit log (`audit.log.enc`) | High: active clinical records | 2 business days | 24 hours |
| Exported encrypted PDFs | Medium: can be regenerated from the database | 5 business days | 24 hours |

All covered files are in `~/Library/Application Support/ClinAssess/`.

## 3. Primary storage safeguards

- ClinAssess encrypts all PHI at rest with AES-256-GCM. Plaintext is never written to disk.
- The Mac's internal disk is encrypted with **FileVault** (verify: System Settings > Privacy & Security > FileVault is On).
- App access requires an individual password. The app locks after [15] minutes of inactivity; the Mac screen locks after [5] minutes.
- ClinAssess has no network features and makes no cloud connections.

## 4. Backup method 1: Time Machine (daily, automatic)

| Item | Standard |
|---|---|
| Destination | Dedicated external drive, used only for this Mac's backups |
| Encryption | **Time Machine "Encrypt backups" must be turned on** when the disk is added. **[Correction]** FileVault protects the Mac's internal disk, not the external backup drive. The backup drive is protected by Time Machine's own encryption (encrypted APFS). Verify: System Settings > General > Time Machine shows the disk as "Encrypted". |
| Frequency | Time Machine backs up hourly while the drive is connected. Standard: connect the drive at least once per business day so at least one daily backup exists. |
| Storage | Drive kept in a locked cabinet in [room] when not connected. Key held by [the clinician only]. |
| Exclusions | None for `~/Library/Application Support/ClinAssess`. Do not exclude this folder. |
| Double protection | Files inside the backup remain ClinAssess-encrypted. A person with the drive and its Time Machine password still cannot read client data without a ClinAssess password. |

**Retention of Time Machine backups (90 days). [Correction]** Time Machine has no setting to keep backups for exactly 90 days. It keeps hourly backups for 24 hours, daily backups for a month, and weekly backups until the drive is full, then deletes the oldest. To meet a 90-day standard, use **one** of these:

- **Option A (recommended): drive rotation.** Use [two or three] drives. Each quarter (every 90 days), erase the oldest drive (Disk Utility > Erase, new encrypted APFS volume) and start a fresh Time Machine backup on it. Record each erase in the secure deletion log.
- **Option B: manual pruning.** On the first business day of each month, list backups (`tmutil listbackups`) and delete those older than 90 days (`sudo tmutil delete`, see `man tmutil`). Record it in the log.

Also, a 90-day backup window means a client record deleted in the app can remain, encrypted, in backups for up to 90 days. That must be consistent with `DATA_RETENTION.md`.

## 5. Backup method 2: ClinAssess encrypted archive (monthly, offline copy)

Time Machine alone does not protect against ransomware that reaches the connected drive, or against a fire that destroys the Mac and the cabinet together. Monthly:

1. ClinAssess: Admin > **Export encrypted archive**. Use an archive password different from the login password.
2. Save the `.caarchive` file to a separate encrypted USB drive (encrypted APFS).
3. Store that drive off-site: [safe deposit box / home safe / second office].
4. Keep the archive password in [sealed envelope in a separate location / password manager].
5. Keep [3] monthly archives; destroy older ones and log it.

**No cloud storage.** Archives and backups are never copied to iCloud Drive, Dropbox, Google Drive, OneDrive, or any cloud service unless a Business Associate Agreement is signed with that provider and this policy is updated. Confirm iCloud Drive "Desktop & Documents" sync is **off** if archives are ever saved to those folders.

## 6. Monthly restore test (backup testing)

On the [first business day] of each month:

1. ClinAssess: Admin > **Test a backup (restore test)**.
2. Select the newest `.caarchive` and enter its password. The app decrypts it in memory only, runs a SQLite integrity check, and shows the record counts.
3. Also test a Time Machine copy: in Time Machine, restore `clinassess.db.enc` from yesterday's backup to a temporary folder (not over the live file), then run the same test on that file. Delete the temporary copy afterward.
4. Compare the counts with the live database (Dashboard shows the total client count).
5. Each test is recorded automatically in the audit trail as `BACKUP_VERIFY` with the result. Also record it in `templates/BACKUP_TEST_LOG.md`.
6. A failed test is a security incident: follow section 9.

## 7. Disaster recovery procedures

**A. Mac lost or stolen**
1. Treat it as a possible breach and start the breach log (section 9). With FileVault, the ClinAssess encryption, and a locked Mac, the data is very likely "secured PHI" under HHS guidance, which affects notification duties. Document the analysis.
2. Use Find My to lock or erase the Mac.
3. On a replacement Mac: enable FileVault, install ClinAssess, restore using B or C below.

**B. Restore from Time Machine (preferred; newest data)**
1. Restore the folder `~/Library/Application Support/ClinAssess/` (all files together, from the same backup time) using Migration Assistant or Time Machine.
2. Open ClinAssess and log in with the usual password.
3. Admin > Audit trail: confirm the integrity check passes.

**C. Restore from an encrypted archive**
1. Install ClinAssess and complete first-time setup (a new admin account).
2. Admin > **Restore from archive**, select the `.caarchive`, and enter the archive password.
3. Data after the archive date must be re-entered from paper records.

**D. Forgotten passwords.** There is no recovery by design. Keep a second admin account (for example, a sealed emergency account) or the archive password in a separate secure place. That is the emergency access procedure under 164.312(a)(2)(ii).

## 8. Emergency mode operation

If ClinAssess is unavailable, clinicians continue with paper protocols and score manually from the official manuals. Paper records are kept in the locked cabinet and entered into ClinAssess after recovery.

## 9. Incidents and breach assessment

Any loss of a device or drive, failed restore test, integrity-check failure in the audit trail, or suspected unauthorized access:
1. Record it in `templates/BREACH_NOTIFICATION_LOG.md` the same day.
2. Perform the four-factor risk assessment (45 CFR 164.402).
3. If notification is required: individuals without unreasonable delay and within 60 days of discovery; HHS (within 60 days if 500 or more individuals, otherwise in the annual report within 60 days after the end of the calendar year); media if more than 500 residents of a state. Check state law, which may be stricter.

## 10. Roles

| Role | Person | Duties |
|---|---|---|
| Security Official | [Name] | Owns this policy; reviews logs monthly |
| Backup operator | [Name] | Monthly archive, monthly restore test, drive rotation |
| Emergency access holder | [Name] | Holds the sealed emergency credentials |

## 11. Review and approval

| Version | Date | Change | Approved by |
|---|---|---|---|
| 1.0 draft | [date] | Initial draft | |
