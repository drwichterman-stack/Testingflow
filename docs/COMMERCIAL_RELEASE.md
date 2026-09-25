# Commercial Release Checklist

What must happen before ClinAssess is sold (for example, on Gumroad for $79 to $129). Items are ordered by risk. The first section contains **blockers**: selling before they are resolved exposes the publisher to infringement or liability claims.

## 1. Blockers

### 1.1 Permission from instrument owners

Selling software that scores an instrument is different from a clinician using that instrument. Get **written** permission for each app-scored instrument, or remove it from the commercial build.

| Instrument | What the form or owner states | Action |
|---|---|---|
| **SDQ** | Youth in Mind does not allow electronic versions for any purpose without prior written authorization, and paper use is free only when no charge is made to families | **Contact Youth in Mind (sdqinfo.org) for a commercial license** covering scoring software. Highest risk item. |
| **ASRS v1.1** | "Requests for permission to reproduce or translate, whether for sale or for noncommercial distribution" go to Prof. Ronald Kessler, Harvard Medical School | Request written permission for scoring software sold commercially |
| **WSR-II, WFIRS-P, WFIRS-S** | Free for clinicians and researchers; may be replicated; contact Dr. Weiss to post online, for research, or for translation | The app shows item text. Get written permission from Dr. Margaret Weiss for inclusion in a sold product |
| **CATS** | Freely accessible; no copyright or licensing fees | Low risk. Email the CATS Consortium (Dr. Cedric Sachser) to confirm commercial software use and to get the caregiver-form cutoffs |
| **SNAP-IV** | Widely distributed without charge; the terms are not printed on the form | Confirm terms with Dr. James Swanson or his institution |
| **MMPI-3, Conners 4, Brown EF/A, TOVA** | The app does not score them or include norms; it uses the names only to label the entry fields | Keep the trademark notice (About > Credits). Do not use publisher logos. Never add norm tables. Have the attorney confirm nominative use |

If a permission is refused, the instrument can move to the transcription model (enter totals from a scored paper form) or be removed. The flows are defined in one place (`clinassess/scoring/__init__.py`).

### 1.2 Legal review

- [ ] Attorney review of `LICENSE.txt` (EULA draft), including limitation of liability and the governing-law clause.
- [ ] Form a business entity (for example, an LLC) and set `PUBLISHER` in `clinassess/config.py`.
- [ ] Professional or product liability (errors and omissions) insurance that covers software sold to clinicians.
- [ ] **Regulatory question:** ask a regulatory attorney whether the scoring and classification functions are device software functions under FDA rules or fall under the Clinical Decision Support exemption (FD&C Act section 520(o); FDA CDS guidance, September 2022). Displaying the rule and basis for each score (which the app does) is relevant to that analysis. Do not assume either answer.
- [ ] Marketing text reviewed: say "designed to support HIPAA compliance" and "works offline", never "HIPAA certified" or "HIPAA compliant software" as a guarantee.

### 1.3 Open-source license compliance

- [x] GUI moved from PyQt6 (GPL v3, which would require publishing the full source or buying a commercial license) to PySide6 (LGPL v3).
- [ ] Keep Qt as separate replaceable libraries (PyInstaller's default layout does this). Do not static-link Qt.
- [ ] Ship `THIRD_PARTY_NOTICES.txt` with full license texts (the build script appends them).
- [ ] The attorney confirms the LGPL relinking offer in `THIRD_PARTY_NOTICES.txt`.

## 2. Build and distribution

- [ ] Apple Developer Program membership ($99 per year) for a **Developer ID Application** certificate.
- [ ] Build on a Mac: `SIGN_IDENTITY=... NOTARY_PROFILE=... ./build_macos.sh`. This produces a signed, notarized, stapled `.dmg`. Without notarization, customers see "cannot be opened because the developer cannot be verified".
- [ ] Architecture: PyInstaller builds for the build Mac's CPU. Build on Apple Silicon for Apple Silicon customers, and either build a second Intel `.dmg` or use a universal2 Python for a universal build. State the requirements on the sales page (macOS 13 or later).
- [ ] Test the `.dmg` on a clean Mac with no Python installed, with Wi-Fi off (COMPLIANCE_REVIEW.md, Part B).
- [ ] Test dictation on real hardware (Part C). It could not be run in the Linux development environment.
- [ ] Test camera capture on real hardware with real completed forms (COMPLIANCE_REVIEW.md, Part E). Only the reading engine has been tested, on synthetic forms.
- [ ] Publish the SHA-256 checksum of each `.dmg` on the sales page.

## 3. Product decisions to confirm

| Topic | Current design | Decide |
|---|---|---|
| **License enforcement** | None. Your offline requirement rules out activation servers | Accept that copies can be shared, or add an offline license key check (a key signed by you, verified locally, no network) in a later version |
| **Group practices** | Several user accounts on **one Mac**. There is no shared network database, by design (offline, local-only) | Sell as "per Mac" licensing; state that there is no multi-computer sync |
| **Updates** | No automatic updates (no network). Customers download new versions | The database has a `schema_version` for future migrations; every release must include a tested migration |
| **Windows** | Not supported. The app is built and tested for macOS only | A Windows build is possible (PySide6 is cross-platform) but needs its own dictation engine, installer, and testing. Camera capture uses Qt Multimedia, which supports Windows webcams, so it should carry over with testing |
| **Support** | No telemetry or crash reports (offline, and they could contain PHI) | Support policy: customers must never send PHI or screenshots with PHI. Publish this on the support page |
| **Password recovery** | None (the publisher cannot decrypt customer data) | Say this clearly at purchase and in the setup screen (the app already warns) |

## 4. Before each release

- [ ] `python -m pytest` passes (includes offline and security tests).
- [ ] Version number updated in `clinassess/config.py`.
- [ ] Release notes, including any scoring-rule changes. A scoring change must change that instrument's `version` string, which is stored with every scored record.
- [ ] Scoring reference updated.
- [ ] Signed, notarized `.dmg` built and tested on a clean Mac.
