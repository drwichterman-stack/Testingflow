# Secure Deletion Log

Record every deletion of client records, backups, archives, exported reports, and drives. Keep for 6 years. Do not write client names here; use the ClinAssess reference code.

| Date | Performed by | What was deleted (client ref code / backup / archive / PDF / drive) | Reason (retention ended, request, rotation, error) | Method | Audit trail entry (action, seq) | Copies remaining and expiry date | Verified by |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |

**Methods:**
- **In-app deletion:** record removed, database re-encrypted and replaced; `CLIENT_DELETE` or `ASSESSMENT_DELETE` in the audit trail.
- **Time Machine pruning:** `tmutil delete` of specified backups.
- **Drive erase:** Disk Utility erase with a new encrypted volume (cryptographic erase), or physical destruction (shredding service certificate number).
- **File deletion:** delete and empty Trash. On FileVault Macs the freed blocks hold only encrypted data.
