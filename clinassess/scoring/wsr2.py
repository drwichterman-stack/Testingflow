"""Weiss Symptom Record II (WSR-II) and Weiss Functional Impairment Rating
Scales (WFIRS-P parent report, WFIRS-S self report), M. D. Weiss.

Source: the official WSR-II, WFIRS-P, and WFIRS-S forms. The copyright
notice on each form states: "The scale can be used by clinicians and
researchers free of charge and can be posted on the Internet or
replicated as needed." Item labels are therefore reproduced exactly as
printed.

WSR-II (form-verified structure):
  * 19 sections; each item rated None (0), Mild (1), Moderate (2),
    Severe (3), or N/A ("not a problem or not relevant").
  * The form prints no scoring rule. The app reports, per section, the
    number of items rated Moderate or Severe (2-3) and the mean rating
    (N/A excluded, following the WFIRS convention by the same author).
  * DSM-5 symptom-count thresholds are shown only where the section maps
    one-to-one onto DSM-5 criteria: Attention (9 items) and
    Hyperactivity/Impulsivity (9) = ADHD criteria A1 and A2, 6+ if
    age < 17 and 5+ if 17 or older; Oppositional (8) = ODD criterion A, 4+.
    Counting "Moderate or Severe" as present is a convention (VERIFY).
  * Any Suicide item rated Mild or higher, or "Self-injurious behaviour"
    rated Mild or higher, raises a safety alert.

WFIRS-P / WFIRS-S (form-verified scoring): each domain reports
"Number of items scored 2 or 3", "Total score", and "Mean score (N/A
items not included in calculation)", plus a Total row, exactly as the
form's scoring box specifies. Items rated 0-3 or n/a.
"""

from __future__ import annotations

from .base import PUBLISHED, VERIFY, Field, Instrument, ScoreResult, ScoreRow

NA = -1

# ---------------------------------------------------------------------------
# WSR-II
# ---------------------------------------------------------------------------
WSR_RESPONSES = [(0, "None"), (1, "Mild"), (2, "Moderate"), (3, "Severe"), (NA, "N/A")]

WSR_SECTIONS: list[tuple[str, str, list[str]]] = [
    ("att", "Attention", [
        "Attention to details or makes careless mistakes",
        "Holding attention or remaining focused",
        "Listening or mind seems elsewhere",
        "Instructions or finishing work",
        "Organizing (e.g. time, messy, deadlines)",
        "Avoids or dislikes activities requiring effort",
        "Loses or misplaces things",
        "Easily distracted",
        "Forgetful (e.g. chores, bills, appointments)"]),
    ("hyp", "Hyperactivity and Impulsivity", [
        "Fidgets or squirms",
        "Trouble staying seated",
        "Runs about or feels restless inside",
        "Loud or difficulty being quiet",
        "Often on the go",
        "Talks too much",
        "Blurts out comments",
        "Dislikes waiting (e.g. taking turns or in line)",
        "Interrupts or intrudes on others (e.g. butting in)"]),
    ("opp", "Oppositional", [
        "Loses temper", "Easily annoyed", "Angry and resentful", "Argues", "Defiant",
        "Deliberately annoys other people", "Blames other people rather than themselves",
        "Spiteful"]),
    ("dev", "Development and Learning", [
        "Wetting, (after age 5)", "Soiling (after age 4)", "Reading", "Spelling", "Math",
        "Writing"]),
    ("asd", "Autism Spectrum", [
        "Difficulty with talking back and forth",
        "Unusual eye contact or body language",
        "Speech is odd (monotone, unusual words)",
        "Restricted, fixed, intense interests",
        "Odd, repetitive movements (e.g. flapping)",
        'Does not easily "chit chat"']),
    ("mot", "Motor Disorders", [
        "Repetitive noises (e.g. sniffing, throat clearing)",
        "Repetitive movements (blinking, shrugging)", "Clumsy"]),
    ("psy", "Psychosis", [
        "Hearing voices that are not there", "Seeing things that are not there",
        "Scrambled thinking", "Paranoia (feeling people are against you)"]),
    ("dep", "Depression", [
        "Sad or depressed most of the day",
        "Lack of interest or pleasure most of the day",
        "Weight loss, weight gain or change in appetite",
        "Difficulty sleeping or sleeping too much", "Agitated", "Slowed down",
        "Feels worthless", "Tired, no energy", "Hopeless, pessimistic",
        "Withdrawal from usual interests/people", "Decrease in concentration"]),
    ("moo", "Mood Regulation", [
        "Distinct period(s) of intense excitement",
        "Distinct period(s) of inflated self-esteem, grandiose",
        "Distinct period(s) of increased energy",
        "Distinct period(s) of decreased need for sleep",
        "Distinct period(s) of racing thoughts or speech",
        "Irritable behaviour that is out of character",
        "Rage attacks, anger outbursts, hostility"]),
    ("sui", "Suicide", ["Suicidal thoughts", "Suicide attempt(s) or a plan"]),
    ("anx", "Anxiety", [
        "Intense fears (e.g. heights, crowds, spiders)",
        "Fear of social situations or performing", "Panic attacks",
        "Fear of leaving e.g. the house, public transportation.",
        "Worrying and/or anxious most days", "Nervous, can't relax",
        "Obsessive thoughts (e.g. germs, perfectionism)",
        "Compulsive rituals (e.g. checking, hand washing)",
        "Hair pulling, nail biting or skin picking",
        "Preoccupation with physical complaints", "Chronic pain"]),
    ("str", "Stress Related Disorders", [
        "Physical abuse", "Sexual abuse", "Neglect", "Other severe trauma"]),
    ("ptsd", "PTSD", [
        "Flashbacks or nightmares", "Avoidance", "Intrusive thoughts of traumatic events"]),
    ("slp", "Sleep", [
        "Trouble falling asleep or staying asleep", "Excessive daytime sleepiness",
        "Snoring or stops breathing during sleep"]),
    ("eat", "Eating", [
        "Distorted body image", "Underweight", "Binge eating", "Overweight",
        "Eating too little or refusing to eat"]),
    ("con", "Conduct", [
        "Verbal aggression", "Physical aggression",
        "Used a weapon against people (stones, sticks etc.)", "Cruel to animals",
        "Physically cruel to people", "Stealing or shoplifting", "Deliberately sets fires",
        "Deliberately destroys property", "Frequent lying", "Lack of remorse or guilt",
        "Lack of empathy or concern for others"]),
    ("sub", "Substance Use", [
        "Misuse of prescription drugs", "Alcohol > 14 drinks/week or 4 drinks at once",
        "Smoking or tobacco use", "Marijuana", "Other street drugs",
        "Excessive over the counter medications",
        "Excessive caffeine (colas, coffee, tea, pills)"]),
    ("add", "Addictions", [
        "Gambling", "Excessive internet, gaming or screen time", "Other addiction"]),
    ("per", "Personality", [
        "Self-destructive", "Stormy, conflicted relationships",
        "Self-injurious behaviour (e.g. cutting)", "Low self-esteem", "Manipulative",
        "Self-centered", "Arrogant", "Suspicious", "Deceitful with no remorse",
        "Breaking the law or antisocial behaviour", "Tends to be a loner"]),
]
SAFETY_ITEMS = {("sui", 1), ("sui", 2), ("per", 3)}

WSR_VARIANTS = [("self", "Self-report"), ("parent", "Parent report"),
                ("teacher", "Teacher report"), ("clinician", "Clinician-rated")]


def dsm_threshold(section: str, age: int | None) -> int | None:
    if section == "opp":
        return 4
    if section in ("att", "hyp"):
        return 5 if age is not None and age >= 17 else 6
    return None


def wsr_fields(variant: str) -> list[Field]:
    fs = []
    for key, title, items in WSR_SECTIONS:
        for i, label in enumerate(items, start=1):
            fs.append(Field(f"{key}_{i}", f"{i}. {label}", "choice", WSR_RESPONSES,
                            section=title, critical=(key, i) in SAFETY_ITEMS))
    fs.append(Field("addiction_other", "Other addiction (describe)", "line",
                    section="Addictions"))
    fs.append(Field("other", "Other difficulties (as written on form)", "text",
                    section="Other"))
    return fs


def _stats(values: list):
    rated = [v for v in values if v not in (None, "", NA)]
    na = sum(1 for v in values if v == NA)
    blank = sum(1 for v in values if v in (None, ""))
    count = sum(1 for v in rated if v >= 2)
    total = sum(rated)
    mean = total / len(rated) if rated else None
    return count, total, mean, len(rated), na, blank


def wsr_score(variant: str, responses: dict, context: dict) -> ScoreResult:
    res = ScoreResult(verification=VERIFY)
    age = context.get("age")
    parts = []
    for key, title, items in WSR_SECTIONS:
        vals = [responses.get(f"{key}_{i}") for i in range(1, len(items) + 1)]
        count, total, mean, n_rated, na, blank = _stats(vals)
        if n_rated == 0 and na == 0:
            continue
        th = dsm_threshold(key, age)
        band = ""
        if th is not None:
            if count >= th:
                band = f"Meets DSM-5 symptom count ({th}+)"
            elif count + blank >= th:
                band = "Indeterminate (blank items)"
            else:
                band = f"Below DSM-5 symptom count ({th}+)"
            parts.append(f"{title} {count}/{len(items)}")
        note = ", ".join(x for x in (f"{na} N/A" if na else "",
                                     f"{blank} blank" if blank else "") if x)
        res.rows.append(ScoreRow(title, "Moderate or Severe (2-3)", f"{count}/{len(items)}",
                                 band, note))
        if mean is not None:
            res.rows.append(ScoreRow(title, "Mean rating (N/A excluded)", f"{mean:.2f}"))
    alerts = []
    for key, idx in sorted(SAFETY_ITEMS):
        v = responses.get(f"{key}_{idx}")
        if v not in (None, "", NA) and v >= 1:
            label = dict((k, items) for k, _, items in WSR_SECTIONS)[key][idx - 1]
            alerts.append(f"{label}: {dict(WSR_RESPONSES)[v]}")
    if alerts:
        res.warnings.insert(0, "SAFETY ALERT: " + "; ".join(alerts) +
                            ". Complete a risk assessment.")
        res.rows.insert(0, ScoreRow("Safety", "Critical items endorsed", "; ".join(alerts),
                                    "Requires risk assessment"))
    if age is None and any(r.band for r in res.rows):
        res.warnings.append("Age unknown; ADHD threshold of 6 applied.")
    for key, label in (("addiction_other", "Other addiction"), ("other", "Other difficulties")):
        t = (responses.get(key) or "").strip()
        if t:
            res.rows.append(ScoreRow("Other", label, t))
    res.summary = (("; ".join(parts) + "." if parts else "") +
                   (" SAFETY ALERT." if alerts else "")).strip()
    return res


WSR2 = Instrument(
    key="wsr2", name="Weiss Symptom Record II", short="WSR-II",
    flows=("A", "B"), version="wsr2-form-2", verification=VERIFY,
    variants=WSR_VARIANTS, fields_for=wsr_fields, score=wsr_score,
    description="19 sections rated None/Mild/Moderate/Severe/N-A. ADHD and ODD sections are "
                "compared with DSM-5 symptom counts. Suicide items raise a safety alert.",
    paper_form=True,
)

# ---------------------------------------------------------------------------
# WFIRS
# ---------------------------------------------------------------------------
WFIRS_RESPONSES = [(0, "Never or not at all"), (1, "Sometimes or somewhat"),
                   (2, "Often or much"), (3, "Very often or very much"), (NA, "n/a")]

WFIRS_P_DOMAINS: list[tuple[str, str, list[str]]] = [
    ("A", "A Family", [
        "Having problems with brothers & sisters", "Causing problems between parents",
        "Takes time away from family members' work or activities",
        "Causing fighting in the family",
        "Isolating the family from friends and social activities",
        "Makes it hard for the family to have fun together", "Makes parenting difficult",
        "Makes it hard to give fair attention to all family members",
        "Provokes others to hit or scream at him/her", "Costs the family more money"]),
    ("BL", "B School: Learning", [
        "Makes it difficult to keep up with schoolwork", "Needs extra help at school",
        "Needs tutoring", "Receives grades that are not as good as his/her ability"]),
    ("BB", "B School: Behaviour", [
        "Causes problems for the teacher in the classroom",
        'Receives "time-out" or removal from the classroom',
        "Having problems in the school yard",
        "Receives detentions (during or after school)", "Suspended or expelled from school",
        "Misses classes or is late for school"]),
    ("C", "C Life Skills", [
        "Excessive use of TV, computer, or video games",
        "Keeping clean, brushing teeth, brushing hair, bathing, etc.",
        "Problems getting ready for school", "Problems getting ready for bed",
        "Problems with eating (picky eater, junk food)", "Problems with sleeping",
        "Gets hurt or injured", "Avoids exercise", "Needs more medical care",
        "Has trouble taking medication, getting needles or visiting the doctor/dentist"]),
    ("D", "D Child's Self-Concept", [
        "My child feels bad about himself/herself", "My child does not have enough fun",
        "My child is not happy with his/her life"]),
    ("E", "E Social Activities", [
        "Being teased or bullied by other children", "Teases or bullies other children",
        "Problems getting along with other children",
        "Problems participating in after-school activities (sports, music, clubs)",
        "Problems making new friends", "Problems keeping friends",
        "Difficulty with parties (not invited, avoids them, misbehaves)"]),
    ("F", "F Risky Activities", [
        "Easily led by other children (peer pressure)", "Breaking or damaging things",
        "Doing things that are illegal", "Being involved with the police",
        "Smoking cigarettes", "Taking illegal drugs", "Doing dangerous things",
        "Causes injury to others", "Says mean or inappropriate things",
        "Sexually inappropriate behaviour"]),
]

WFIRS_S_DOMAINS: list[tuple[str, str, list[str]]] = [
    ("A", "A Family", [
        "Having problems with family", "Having problems with spouse/partner",
        "Relying on others to do things for you", "Causing fighting in the family",
        "Makes it hard for the family to have fun together",
        "Problems taking care of your family",
        "Problems balancing your needs against those of your family",
        "Problems losing control with family"]),
    ("B", "B Work", [
        "Problems performing required duties",
        "Problems with getting your work done efficiently",
        "Problems with your supervisor", "Problems keeping a job", "Getting fired from work",
        "Problems working in a team", "Problems with your attendance",
        "Problems with being late", "Problems taking on new tasks",
        "Problems working to your potential", "Poor performance evaluations"]),
    ("C", "C School", [
        "Problems taking notes", "Problems completing assignments",
        "Problems getting your work done efficiently", "Problems with teachers",
        "Problems with school administrators",
        "Problems meeting minimum requirements to stay in school",
        "Problems with attendance", "Problems with being late",
        "Problems with working to your potential", "Problems with inconsistent grades"]),
    ("D", "D Life Skills", [
        "Excessive or inappropriate use of internet, video games or TV",
        "Problems keeping an acceptable appearance",
        "Problems getting ready to leave the house", "Problems getting to bed",
        "Problems with nutrition", "Problems with sex", "Problems with sleeping",
        "Getting hurt or injured", "Avoiding exercise",
        "Problems keeping regular appointments with doctor/dentist",
        "Problems keeping up with household chores", "Problems managing money"]),
    ("E", "E Self-Concept", [
        "Feeling bad about yourself", "Feeling frustrated with yourself",
        "Feeling discouraged", "Not feeling happy with your life", "Feeling incompetent"]),
    ("F", "F Social", [
        "Getting into arguments", "Trouble cooperating", "Trouble getting along with people",
        "Problems having fun with other people", "Problems participating in hobbies",
        "Problems making friends", "Problems keeping friends",
        "Saying inappropriate things", "Complaints from neighbours"]),
    ("G", "G Risk", [
        "Aggressive driving", "Doing other things while driving", "Road rage",
        "Breaking or damaging things", "Doing things that are illegal",
        "Being involved with the police", "Smoking cigarettes", "Smoking marijuana",
        "Drinking alcohol", 'Taking "street" drugs',
        "Sex without protection (birth control, condom)", "Sexually inappropriate behaviour",
        "Being physically aggressive", "Being verbally aggressive"]),
]


def _wfirs_fields(domains):
    def fields_for(variant: str) -> list[Field]:
        return [Field(f"{key}_{i}", f"{i}. {label}", "choice", WFIRS_RESPONSES, section=title)
                for key, title, items in domains for i, label in enumerate(items, start=1)]
    return fields_for


def _wfirs_score(domains):
    def score(variant: str, responses: dict, context: dict) -> ScoreResult:
        res = ScoreResult(verification=PUBLISHED)
        all_vals = []
        for key, title, items in domains:
            vals = [responses.get(f"{key}_{i}") for i in range(1, len(items) + 1)]
            all_vals += vals
            count, total, mean, n_rated, na, blank = _stats(vals)
            if n_rated == 0 and na == 0:
                continue
            note = f"mean of {n_rated} answered" + (f"; {na} n/a" if na else "") + \
                (f"; {blank} blank" if blank else "")
            res.rows.append(ScoreRow(title, "Items scored 2 or 3", str(count)))
            res.rows.append(ScoreRow(title, "Total score", str(total)))
            res.rows.append(ScoreRow(title, "Mean score", f"{mean:.2f}" if mean is not None
                                     else "n/a", "", note))
        count, total, mean, n_rated, na, blank = _stats(all_vals)
        if n_rated:
            res.rows.append(ScoreRow("Total", "Items scored 2 or 3", str(count)))
            res.rows.append(ScoreRow("Total", "Total score", str(total)))
            res.rows.append(ScoreRow("Total", "Mean score", f"{mean:.2f}", "",
                                     f"calculated from {n_rated} answered questions"))
            res.summary = f"Total mean {mean:.2f}; {count} item(s) scored 2 or 3."
        return res
    return score


WFIRS_P = Instrument(
    key="wfirs_p", name="Weiss Functional Impairment Rating Scale, Parent Report",
    short="WFIRS-P", flows=("A",), version="wfirs-p-form-1", verification=PUBLISHED,
    variants=[("parent", "Parent report")], fields_for=_wfirs_fields(WFIRS_P_DOMAINS),
    score=_wfirs_score(WFIRS_P_DOMAINS),
    description="Functional impairment in the last month. Scored per the form's scoring box.",
    paper_form=True,
)

WFIRS_S = Instrument(
    key="wfirs_s", name="Weiss Functional Impairment Rating Scale, Self Report",
    short="WFIRS-S", flows=("B",), version="wfirs-s-form-1", verification=PUBLISHED,
    variants=[("self", "Self report")], fields_for=_wfirs_fields(WFIRS_S_DOMAINS),
    score=_wfirs_score(WFIRS_S_DOMAINS),
    description="Functional impairment in the last month. Scored per the form's scoring box. "
                "Leave Work or School blank (or n/a) if not applicable.",
    paper_form=True,
)

INSTRUMENT = WSR2  # backwards-compatible name
