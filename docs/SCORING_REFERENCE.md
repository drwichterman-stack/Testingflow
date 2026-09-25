# Scoring Reference

This document states exactly what the app computes for each instrument, the source of each rule, and how far each rule has been verified. The code for each rule is in `clinassess/scoring/`, and `tests/test_scoring.py` checks it.

## Verification status

| Status | Meaning | Action before clinical use |
|---|---|---|
| **PUBLISHED** | Implemented from the publisher's public scoring document | Spot-check 2 or 3 hand-scored protocols against the app |
| **VERIFY** | Implemented, but one or more cutoffs, item keys, or structures must be confirmed against the official manual or form | Check each item listed under "To verify" and record the result in the sign-off table at the end |
| **TRANSCRIBED** | Licensed norms; the app does **not** compute scores. The clinician enters scores from the publisher's software | Confirm the scale list matches your publisher report |

Status is printed next to every score table in the app and in the PDF.

**Item wording.** Item text is shown only where the author's printed terms allow reproduction (WSR-II, WFIRS-P, WFIRS-S). For every other instrument the clinician enters responses by item number from the official form, so no copyrighted item content is reproduced.

## Summary

"Form-verified" means the rule was checked against the official form supplied by the practice (September 2026): ASRS v1.1 checklist, CATS Youth Report, SDQ US English P4-10 and P/T 11-17, WSR-II, WFIRS-P, WFIRS-S, SNAP-IV-26.

| Instrument | Flow | App computes | Status |
|---|---|---|---|
| SDQ | A | Five scales, Total Difficulties, Externalising/Internalising, Impact, three-band classification | PUBLISHED (item key form-verified) |
| CATS (Child and Adolescent Trauma Screen) | A | Events, symptom total and band, DSM-5 cluster sums, interference | PUBLISHED for youth 7-17 (form-verified); VERIFY for caregiver forms |
| SNAP-IV 26 | A | Subscale averages vs 5% cutoffs, symptom counts | VERIFY (cutoffs not printed on the form) |
| WSR-II | A, B | 19 sections: count rated Moderate/Severe, mean; DSM-5 counts for ADHD and ODD; safety alert | VERIFY (structure form-verified; the form prints no scoring rule) |
| WFIRS-P | A | Per-domain count of items scored 2-3, total, mean (N/A excluded) | PUBLISHED (form-verified) |
| WFIRS-S | B | Same as WFIRS-P | PUBLISHED (form-verified) |
| ASRS v1.1 | A (gated), B | Part A screener, Part B shaded count, raw totals | PUBLISHED (shading form-verified) |
| Conners 4 | A | T-score entry, descriptive band | TRANSCRIBED (bands VERIFY) |
| TOVA | A, B | Standard-score entry only | TRANSCRIBED |
| MMPI-3 | B | T-score entry, T >= 65 flag | TRANSCRIBED |
| Brown EF/A | B | T-score and percentile entry only | TRANSCRIBED |

---|---|---|---|
| SDQ | A | Five scales, Total Difficulties, Externalising/Internalising, Impact, three-band classification | PUBLISHED |
| CATS (Child and Adolescent Trauma Screen) | A | Symptom total, severity band (7-17), impairment count | VERIFY |
| ASRS v1.1 | A (gated), B | Part A screener, Part B shaded count, raw totals | VERIFY |
| WSR-II | A, B | ADHD and ODD symptom counts vs DSM-5 thresholds, mean ratings | VERIFY |
| Conners 4 | A | T-score entry, descriptive band | TRANSCRIBED (bands VERIFY) |
| TOVA | A, B | Standard-score entry only | TRANSCRIBED |
| MMPI-3 | B | T-score entry, T >= 65 flag | TRANSCRIBED |
| Brown EF/A | B | T-score and percentile entry only | TRANSCRIBED |

---

## SDQ: Strengths and Difficulties Questionnaire

**Source:** Goodman, R. (1997). *Journal of Child Psychology and Psychiatry, 38*, 581-586. Scoring document "Scoring the SDQ" and SPSS syntax, Youth in Mind, sdqinfo.org.
**Code:** `clinassess/scoring/sdq.py` | **Status:** PUBLISHED

**Forms:** Parent (P4-10, or P/T 11-17 completed by a parent), Teacher (T4-10, or P/T 11-17 completed by a teacher), Self-report (S11-17).

**Form verification:** the item order and the five reverse-keyed items were checked against the US English P4-10 and P/T 11-17 forms supplied by the practice. The self-report form was not supplied; it uses the same item order and key per the SDQ scoring document.

**Item coding:** 0 = Not True, 1 = Somewhat True, 2 = Certainly True.
**Reverse-scored items:** 7, 11, 14, 21, 25 (scored 2, 1, 0).

| Scale | Items | Range |
|---|---|---|
| Emotional Symptoms | 3, 8, 13, 16, 24 | 0-10 |
| Conduct Problems | 5, **7**, 12, 18, 22 | 0-10 |
| Hyperactivity/Inattention | 2, 10, 15, **21**, **25** | 0-10 |
| Peer Relationship Problems | 6, **11**, **14**, 19, 23 | 0-10 |
| Prosocial Behaviour | 1, 4, 9, 17, 20 | 0-10 |
| Total Difficulties | Sum of the first four scales | 0-40 |
| Externalising | Conduct + Hyperactivity | 0-20 |
| Internalising | Emotional + Peer | 0-20 |

**Missing data:** a scale is scored only if at least 3 of its 5 items are answered. It is prorated as round(mean x 5), with halves rounded up (SPSS `RND`). Total Difficulties is scored only when all four difficulty scales are scored.

**Impact supplement:** scored only if the "any difficulties" answer is Yes. Not at all = 0, Only a little = 0, A medium amount (US forms; "Quite a lot" on UK forms) = 1, A great deal = 2. The chronicity question ("How long?") and the burden question are recorded but not scored, as in the official scoring. Parent and self forms: distress plus 4 areas (home life, friendships, classroom learning, leisure), range 0-10. Teacher form: distress plus 2 areas (peer relationships, classroom learning), range 0-6. If the answer is No, impact = 0.

**Bands (original three-band categorisation):**

| Scale | Parent N / B / A | Teacher N / B / A | Self N / B / A |
|---|---|---|---|
| Total Difficulties | 0-13 / 14-16 / 17-40 | 0-11 / 12-15 / 16-40 | 0-15 / 16-19 / 20-40 |
| Emotional | 0-3 / 4 / 5-10 | 0-4 / 5 / 6-10 | 0-5 / 6 / 7-10 |
| Conduct | 0-2 / 3 / 4-10 | 0-2 / 3 / 4-10 | 0-3 / 4 / 5-10 |
| Hyperactivity | 0-5 / 6 / 7-10 | 0-5 / 6 / 7-10 | 0-5 / 6 / 7-10 |
| Peer | 0-2 / 3 / 4-10 | 0-3 / 4 / 5-10 | 0-3 / 4-5 / 6-10 |
| Prosocial | 6-10 / 5 / 0-4 | 6-10 / 5 / 0-4 | 6-10 / 5 / 0-4 |
| Impact | 0 / 1 / 2+ | 0 / 1 / 2+ | 0 / 1 / 2+ |

N = Normal, B = Borderline, A = Abnormal. Youth in Mind has also published a newer four-band scheme (close to average, slightly raised, high, very high). The app uses the three-band scheme. Tell me if you prefer the four-band scheme.

**Licensing note:** see README, Known limitations, item 2.

---

## CATS: Child and Adolescent Trauma Screen

**Source:** Sachser, C., Berliner, L., Holt, T., Jensen, T. K., Jungbluth, N., Risch, E., Rosner, R., & Goldbeck, L. (2017). International development and psychometric properties of the Child and Adolescent Trauma Screen (CATS). *Journal of Affective Disorders, 210*, 189-195. The form states: freely accessible, no copyright or licensing fees.
**Code:** `clinassess/scoring/cats.py` | **Status:** PUBLISHED (youth 7-17, form-verified); VERIFY (caregiver 7-17 and 3-6)

**Form structure (verified, Youth Report):**
- **Events:** 15 Yes/No items; item 15 is "other" with a description.
- **Symptoms (last two weeks):** 20 items, 0 = Never, 1 = Once in a while, 2 = Half the time, 3 = Almost always. Total 0-60.
- **Interference:** 5 Yes/No items: getting along with others, hobbies/fun, school or work, family relationships, general happiness.

**Severity bands (printed on the form, ages 7-17):**

| Total | Band |
|---|---|
| < 15 | Normal. Not clinically elevated. |
| 15-20 | Moderate trauma-related distress. |
| 21+ | Probable PTSD. |

If blank items could change the band, the app reports "Indeterminate (missing items)".

**DSM-5 cluster sums (supplementary):** the 20 items follow DSM-5 order: items 1-5 = B intrusion, 6-7 = C avoidance, 8-14 = D negative cognitions and mood, 15-20 = E arousal and reactivity. The app reports each cluster sum and whether the symptom pattern B >= 1, C >= 1, D >= 2, E >= 2 is met, counting an item as present when rated 2 or 3. **VERIFY** this "2 or 3 = present" convention against Sachser et al. (2017); it is labeled "screening only; not a diagnosis".

**To verify:** the caregiver 7-17 form's cutoffs (the app uses the youth cutoffs and warns); cutoffs for the caregiver 3-6 form (16 items; no band applied).

---|---|
| 0-14 | Normal range |
| 15-20 | Moderate trauma-related distress |
| 21+ | Probable PTSD |

If items are missing and the missing items could change the band, the app reports "Indeterminate (missing items)". The 3-6 version has no automatic band.

**To verify:**
1. The 15 and 21 cutoffs on the CATS version you use. The CATS has had revisions, including a DSM-5 and ICD-11 version.
2. The number of symptom items (20 or 16) and impairment items (5) on your form.
3. Whether to add the 3-6 cutoffs (the app can add them once confirmed).

---

## ASRS v1.1: Adult ADHD Self-Report Scale

**Source:** Kessler, R. C., Adler, L., Ames, M., et al. (2005). The World Health Organization Adult ADHD Self-Report Scale (ASRS). *Psychological Medicine, 35*, 245-256. ASRS-v1.1 Symptom Checklist and scoring instructions (WHO / Harvard NCS).
**Code:** `clinassess/scoring/asrs.py` | **Status:** PUBLISHED

**Coding:** 0 = Never, 1 = Rarely, 2 = Sometimes, 3 = Often, 4 = Very Often.

**Shaded thresholds (item counts when at or above its threshold):**

| Threshold | Items |
|---|---|
| Sometimes or higher | 1, 2, 3, 9, 12, 16, 18 |
| Often or higher | 4, 5, 6, 7, 8, 10, 11, 13, 14, 15, 17 |

**Part A screener (items 1-6):** 4 or more shaded = "symptoms highly consistent with ADHD in adults; further investigation is warranted." If fewer than 4 are shaded but missing items could reach 4, the app reports "Indeterminate".

**Part B (items 7-18):** number shaded is reported. There is no official Part B cutoff.

**Raw totals (supplementary, no official cutoff):** Inattentive = items 1-4 and 7-11 (0-36). Hyperactive-Impulsive = items 5, 6, 12-18 (0-36). Total = 0-72.

**Age:** the ASRS is designed for adults. For clients under 18 the app shows a warning. In Flow A the ASRS appears only when enabled at intake.

**Form verification:** the shaded cells of all 18 rows were measured on the official WHO checklist supplied by the practice. The Sometimes threshold applies exactly to items 1, 2, 3, 9, 12, 16, 18, matching the app. The Part A "4 or more" rule comes from the WHO scoring instructions (not printed on the checklist).

**Licensing:** the checklist states "Requests for permission to reproduce or translate, whether for sale or for noncommercial distribution" go to Prof. Ronald Kessler, Harvard Medical School. The app reproduces no item wording. For a commercial product, ask for written confirmation that scoring software is acceptable.

---

## WSR-II: Weiss Symptom Record II

**Source:** Weiss, M. D. Weiss Symptom Record II. The form states it "can be used by clinicians and researchers free of charge and can be posted on the Internet or replicated as needed"; contact Dr. Weiss for Internet posting, research use, or translation.
**Code:** `clinassess/scoring/wsr2.py` | **Status:** VERIFY

**Form structure (verified):** each item is rated None (0), Mild (1), Moderate (2), Severe (3), or N/A ("not a problem or not relevant"). 19 sections, with item labels shown in the app exactly as printed:

| Section | Items | Section | Items |
|---|---|---|---|
| Attention | 9 | Anxiety | 11 |
| Hyperactivity and Impulsivity | 9 | Stress Related Disorders | 4 |
| Oppositional | 8 | PTSD | 3 |
| Development and Learning | 6 | Sleep | 3 |
| Autism Spectrum | 6 | Eating | 5 |
| Motor Disorders | 3 | Conduct | 11 |
| Psychosis | 4 | Substance Use | 7 |
| Depression | 11 | Addictions | 3 (plus "other" text) |
| Mood Regulation | 7 | Personality | 11 |
| Suicide | 2 | Other | free text |

**Scoring applied:** the form prints no scoring rule. For each section the app reports the number of items rated Moderate or Severe (2-3) and the mean rating with N/A excluded (the same conventions as the WFIRS scoring box by the same author).

**DSM-5 symptom counts** only where a section maps one-to-one onto DSM-5 criteria:

| Section | DSM-5 criterion | Threshold |
|---|---|---|
| Attention (9) | ADHD A1 | 6+ if age < 17; 5+ if 17 or older |
| Hyperactivity and Impulsivity (9) | ADHD A2 | 6+ if age < 17; 5+ if 17 or older |
| Oppositional (8) | ODD A | 4+ |

Meeting a count is not a diagnosis. N/A counts as not present; a blank item can make the result "Indeterminate".

**Safety alert:** Suicidal thoughts, Suicide attempt(s) or a plan, or Self-injurious behaviour rated Mild or higher shows a red alert in the score panel, the client page, and the report tables.

**To verify:** whether Dr. Weiss's guidance counts "Moderate" (2) as a present symptom for the DSM counts.

---

## WFIRS-P and WFIRS-S: Weiss Functional Impairment Rating Scale

**Source:** Weiss, M. D. WFIRS Parent Report and Self Report. Same free-use terms as the WSR-II.
**Code:** `clinassess/scoring/wsr2.py` | **Status:** PUBLISHED (form-verified)

**Rating:** 0 Never or not at all, 1 Sometimes or somewhat, 2 Often or much, 3 Very often or very much, n/a.

**Domains (verified):**

| WFIRS-P (parent) | Items | WFIRS-S (self) | Items |
|---|---|---|---|
| A Family | 10 | A Family | 8 |
| B School: Learning | 4 | B Work | 11 |
| B School: Behaviour | 6 | C School | 10 |
| C Life Skills | 10 | D Life Skills | 12 |
| D Child's Self-Concept | 3 | E Self-Concept | 5 |
| E Social Activities | 7 | F Social | 9 |
| F Risky Activities | 10 | G Risk | 14 |

**Scoring (exactly as the form's scoring box):** for each domain and for the Total: number of items scored 2 or 3; total score; mean score with n/a items not included; and the number of answered questions.

**Not applied:** interpretive cutoffs. Some published work treats a domain as impaired when at least 2 items are rated 2 or at least 1 item is rated 3, or when the mean exceeds 1.5. The form does not print these, so the app does not apply them. Tell me if you want them added as flagged guidance.

---

## SNAP-IV 26: Teacher and Parent Rating Scale

**Source:** Swanson, J. M., University of California, Irvine. SNAP-IV-26 form (July 2022) and the SNAP-IV scoring instructions.
**Code:** `clinassess/scoring/snap4.py` | **Status:** VERIFY

**Form (verified):** 26 items, 0 Not at all, 1 Just a little, 2 Quite a bit, 3 Very much. Items 1-9 inattention, 10-18 hyperactivity/impulsivity, 19-26 oppositional defiant. Item wording follows DSM criteria and is not reproduced in the app.

**Scoring:** subscale score = average item rating (sum divided by items answered). Symptom count = items rated 2 or 3.

**5% cutoffs (average item score at or above = clinically significant):**

| Subscale | Teacher | Parent |
|---|---|---|
| Inattention (1-9) | 2.56 | 1.78 |
| Hyperactivity/Impulsivity (10-18) | 1.78 | 1.44 |
| Combined (1-18) | 2.00 | 1.67 |
| ODD (19-26) | 1.38 | 1.88 |

**To verify:** these cutoffs against the SNAP-IV scoring instructions you use. The uploaded form does not print them.

---|---|---|
| ADHD Inattention | 9 | 6+ if age < 17; 5+ if age 17 or older |
| ADHD Hyperactivity-Impulsivity | 9 | 6+ if age < 17; 5+ if age 17 or older |
| Oppositional Defiant | 8 | 4+ |

A symptom counts as present when rated 2 or 3. The app reports the count, the mean item rating, and whether the count meets the DSM-5 threshold. Meeting a symptom count is **not** a diagnosis: onset, duration, settings, and impairment criteria remain clinical judgments.

**Other WSR-II sections** (anxiety, mood, and others) are entered as a clinician summary.

**To verify:**
1. Item order and count in each section of your WSR-II form.
2. That "rated 2 or 3 = present" matches the WSR-II instructions.
3. Which other sections you want scored; each can be added as another section.

---

## Conners 4

**Source:** Conners, C. K. (2022). *Conners 4th Edition (Conners 4) Manual.* Multi-Health Systems.
**Code:** `clinassess/scoring/licensed.py` | **Status:** TRANSCRIBED (T-score bands VERIFY)

**Entered from the MHS report, per informant (self, parent, teacher):**
- Content Scales: Inattention/Executive Dysfunction, Hyperactivity, Impulsivity, Emotional Dysregulation, Depressed Mood, Anxious Thoughts
- Impairment and Functional Outcome Scales: Schoolwork, Peer Interactions, Family Life (not on the teacher form)
- DSM Symptom Scales: ADHD Inattentive, ADHD Hyperactive/Impulsive, Total ADHD, ODD, CD
- Conners 4-ADHD Index probability (%)
- Critical items, validity/response style notes, publisher interpretation (text)

**Valid ranges enforced:** T 20-120, percentile 1-99, probability 0-100.

**Descriptive bands applied:**

| T-score | Band |
|---|---|
| 70+ | Very Elevated |
| 65-69 | Elevated |
| 60-64 | High Average |
| 40-59 | Average |
| < 40 | Low |

**To verify:** these bands against the Conners 4 Manual's T-score interpretation table. If they differ, the app will use the manual's values.

---

## TOVA: Test of Variables of Attention

**Source:** The TOVA Company. *T.O.V.A. Professional Manual.*
**Code:** `clinassess/scoring/licensed.py` | **Status:** TRANSCRIBED

**Entered from the TOVA report (visual or auditory):** standard scores (mean 100, SD 15) for Response Time Variability, Response Time, Commission Errors, Omission Errors, and d' for Half 1, Half 2, and Total. Attention Comparison Score (ACS). Validity notes and the report's interpretation.

**The app applies no classification.** Use the interpretation in the TOVA report.

---

## MMPI-3

**Source:** Ben-Porath, Y. S., & Tellegen, A. (2020). *MMPI-3 Manual for Administration, Scoring, and Interpretation.* University of Minnesota Press. Scored in Pearson Q-global.
**Code:** `clinassess/scoring/licensed.py` | **Status:** TRANSCRIBED

**Entered from Q-global (52 scales plus CNS):**
- Validity (10): CRIN, VRIN, TRIN (with T/F direction), F, Fp, Fs, FBS, RBS, L, K; CNS raw count
- Higher-Order (3): EID, THD, BXD
- Restructured Clinical (9): RCd, RC1, RC2, RC3, RC4, RC6, RC7, RC8, RC9
- Specific Problems (26): MLS, NUC, EAT, COG; SUI, HLP, SFD, NFC, STR, WRY, CMP, ARX, ANP, BRF; FML, JCP, SUB, IMP, ACT, AGG, CYN; SFI, DOM, DSF, SAV, SHY
- PSY-5 (5): AGGR-r, PSYC-r, DISC-r, NEGE-r, INTR-r

Total: 10 + 3 + 9 + 26 + 5 = 53 T-score fields (RC5 does not exist). Confirm this list against your Q-global report.

**Flag applied:** substantive scales with T >= 65 are marked "T >= 65", the general MMPI-3 threshold for clinically significant elevation. **The app does not judge protocol validity.** Validity scale T-scores are shown as entered with "interpret per MMPI-3 Manual". Some scales have other interpretive ranges (including low scores); use the Q-global report for those.

---

## Brown EF/A Scales

**Source:** Brown, T. E. (2019). *Brown Executive Function/Attention Scales Manual.* Pearson. Scored in Q-global.
**Code:** `clinassess/scoring/licensed.py` | **Status:** TRANSCRIBED

**Forms:** Self, Parent, Teacher, and the legacy Brown ADD Scales.

**Entered:** T-score and percentile for Activation, Focus, Effort, Emotion, Memory, Action, and Total Composite. Validity notes and interpretation text.

**The app applies no classification.** Use the descriptors printed in the Q-global report. (The legacy Brown ADD Scales have different clusters for some age forms; leave unused clusters blank.)

---

## Verification sign-off

Complete this table before clinical use. Keep a copy with the compliance review record.

| Instrument | Item checked | Manual / form edition | Matches app? | Checked by | Date |
|---|---|---|---|---|---|
| SDQ | Item key, reverse items (done: US forms, Sept 2026); bands for 3 informants | | | | |
| SDQ | 3 hand-scored protocols match app | | | | |
| CATS | Youth form (done, Sept 2026); caregiver form cutoffs; "2-3 = present" rule | | | | |
| SNAP-IV | 5% cutoffs, teacher and parent | | | | |
| WSR-II | Structure (done, Sept 2026); "Moderate = present" for DSM counts | | | | |
| WFIRS-P / S | Structure and scoring box (done, Sept 2026); 2 hand-scored protocols | | | | |
| ASRS | Shaded cells (done, Sept 2026); Part A "4 or more" rule | | | | |
| Conners 4 | Scale list, T-score bands | | | | |
| TOVA | Variable list | | | | |
| MMPI-3 | 53 scale list, T >= 65 convention | | | | |
| Brown EF/A | Cluster list | | | | |
