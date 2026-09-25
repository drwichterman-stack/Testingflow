/**
 * Sample NCE course content, bundled with the app so it works offline.
 *
 * This is original sample material on core counselor-education topics,
 * written to exercise the app. Replace it with the course content from
 * thelicensureprofessor.com before release (see README, "Replacing the
 * sample content"). IDs are derived from the stable keys below, so
 * progress survives content updates as long as the keys stay the same.
 */

import type { Course, Lesson, Question, Quiz } from '../types';

/** Deterministic UUID-shaped id from a key (FNV-1a based, version nibble 4). */
export function idFor(key: string): string {
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  const hex: string[] = [];
  for (let round = 0; round < 4; round++) {
    for (let i = 0; i < key.length; i++) {
      const c = key.charCodeAt(i) + round * 31;
      h1 = Math.imul(h1 ^ c, 0x01000193) >>> 0;
      h2 = Math.imul(h2 ^ (c + h1), 0x5bd1e995) >>> 0;
    }
    hex.push(((h1 ^ h2) >>> 0).toString(16).padStart(8, '0'));
  }
  const s = hex.join('');
  const variant = ((parseInt(s[16], 16) & 0x3) | 0x8).toString(16);
  return `${s.slice(0, 8)}-${s.slice(8, 12)}-4${s.slice(13, 16)}-${variant}${s.slice(17, 20)}-${s.slice(20, 32)}`;
}

interface QSpec {
  text: string;
  options: string[];
  answer: number; // index into options
  explanation: string;
}
interface QuizSpec {
  key: string;
  title: string;
  timeLimit: number | null;
  questions: QSpec[];
}
interface LessonSpec {
  key: string;
  title: string;
  minutes: number;
  content: string;
}
interface UnitSpec {
  key: string;
  title: string;
  description: string;
  lessons: LessonSpec[];
  quizzes: QuizSpec[];
}

const TF = ['True', 'False'];

const UNITS: UnitSpec[] = [
  {
    key: 'unit1',
    title: 'Unit 1: Assessment',
    description: 'Purposes of assessment, reliability, validity, and interpreting test scores.',
    lessons: [
      {
        key: 'u1l1',
        title: 'Foundations of Assessment',
        minutes: 12,
        content: `# Foundations of Assessment

Assessment is the systematic gathering of information about a client to support **screening, diagnosis, treatment planning, and outcome evaluation**. Testing is one part of assessment; interviews, observation, and records are others.

## Norm-referenced and criterion-referenced tests

- A **norm-referenced** test compares a person's score with the scores of a norm group (for example, a percentile rank on an achievement test).
- A **criterion-referenced** test compares a score with a fixed standard or mastery level (for example, a licensure exam cut score).

## Standardization

A **standardized** test uses the same materials, directions, timing, and scoring for everyone. Standardization is what makes comparison with the norm group meaningful.

## Ethical use

Counselors use only tests they are trained and qualified to use, choose instruments normed on groups relevant to the client, and interpret results in context rather than from a single score.`,
      },
      {
        key: 'u1l2',
        title: 'Reliability',
        minutes: 15,
        content: `# Reliability

**Reliability** is the consistency of scores. A reliability coefficient ranges from 0 to 1; higher is more consistent.

## Types of reliability

- **Test-retest:** the same test given twice to the same group; the scores are correlated.
- **Alternate (parallel) forms:** two equivalent forms of the test are correlated.
- **Internal consistency:** how well the items measure the same thing. Split-half reliability is corrected with the **Spearman-Brown** formula. **Cronbach's alpha** is used with multi-point items, and **KR-20** with items scored right or wrong.
- **Inter-rater:** agreement between two or more scorers.

## Standard error of measurement

The **standard error of measurement (SEM)** estimates how much an observed score would vary around the true score. It is calculated as SD x the square root of (1 - reliability). Higher reliability gives a smaller SEM and a narrower confidence band.`,
      },
      {
        key: 'u1l3',
        title: 'Validity',
        minutes: 15,
        content: `# Validity

**Validity** is the degree to which evidence supports the intended interpretation of test scores. A test is not valid in general; it is valid for a particular purpose.

## Sources of validity evidence

- **Content validity:** the items adequately sample the domain being measured.
- **Criterion-related validity:** scores relate to an outside criterion. **Concurrent** validity uses a criterion measured at the same time; **predictive** validity uses a criterion measured later.
- **Construct validity:** the test measures the theoretical trait it claims to. **Convergent** evidence shows strong correlation with measures of the same construct; **discriminant** evidence shows weak correlation with measures of different constructs.

## Face validity

**Face validity** is only whether a test appears to measure what it claims. It is not true validity evidence.

## Reliability and validity

A test can be reliable without being valid, but it cannot be valid without being reliable. Reliability is **necessary but not sufficient** for validity.`,
      },
      {
        key: 'u1l4',
        title: 'Test Scores and the Normal Curve',
        minutes: 18,
        content: `# Test Scores and the Normal Curve

## The normal curve

In a normal distribution, about **68%** of scores fall within 1 standard deviation (SD) of the mean, about **95%** within 2 SD, and about **99.7%** within 3 SD. The mean, median, and mode are equal.

## Standard scores

- **z-score:** mean 0, SD 1.
- **T-score:** mean 50, SD 10.
- **Deviation IQ:** mean 100, SD 15.
- **Stanine:** a 1 to 9 scale with mean 5 and SD of about 2.

A z-score of +1 equals a T-score of 60 and a deviation IQ of 115, and falls at about the **84th percentile**.

## Percentile rank

A **percentile rank** is the percentage of the norm group scoring at or below a score. Percentile ranks are not equal units: differences near the middle of the distribution represent smaller raw-score differences than the same differences at the extremes.

## Skew

In a **positively skewed** distribution the tail points to the right and the mean is greater than the median. In a **negatively skewed** distribution the tail points to the left and the mean is less than the median.`,
      },
    ],
    quizzes: [
      {
        key: 'u1q1',
        title: 'Assessment Basics',
        timeLimit: null,
        questions: [
          {
            text: 'A test that compares a client\'s score with the scores of a representative group is:',
            options: ['Criterion-referenced', 'Norm-referenced', 'Ipsative', 'Projective'],
            answer: 1,
            explanation: 'Norm-referenced tests interpret a score relative to a norm group. Criterion-referenced tests compare it with a fixed standard.',
          },
          {
            text: 'A licensure exam with a fixed passing cut score is best described as criterion-referenced.',
            options: TF,
            answer: 0,
            explanation: 'Passing depends on meeting a set standard, not on how others scored, so it is criterion-referenced.',
          },
          {
            text: 'Giving every examinee the same directions, time limits, and scoring procedures is called:',
            options: ['Standardization', 'Validation', 'Norming', 'Equating'],
            answer: 0,
            explanation: 'Standardization means uniform administration and scoring, which makes comparison with norms meaningful.',
          },
          {
            text: 'Which is NOT a typical purpose of assessment in counseling?',
            options: ['Screening', 'Treatment planning', 'Outcome evaluation', 'Guaranteeing a diagnosis from a single score'],
            answer: 3,
            explanation: 'Sound practice interprets scores in context with other information. No single score guarantees a diagnosis.',
          },
          {
            text: 'Counselors may use any published test as long as it has good reliability.',
            options: TF,
            answer: 1,
            explanation: 'Counselors use only instruments they are qualified to administer and interpret, and that suit the client and purpose.',
          },
        ],
      },
      {
        key: 'u1q2',
        title: 'Reliability and Validity',
        timeLimit: 480,
        questions: [
          {
            text: 'Which reliability estimate is most appropriate for a test whose items are scored right or wrong?',
            options: ['Cronbach\'s alpha only', 'KR-20', 'Test-retest only', 'Inter-rater agreement'],
            answer: 1,
            explanation: 'KR-20 estimates internal consistency for dichotomously scored items. Alpha generalizes it to multi-point items.',
          },
          {
            text: 'The Spearman-Brown formula is used to:',
            options: ['Correct split-half reliability for the full test length', 'Compute the standard error of measurement', 'Estimate predictive validity', 'Convert raw scores to T-scores'],
            answer: 0,
            explanation: 'Split-half reliability is based on half-length tests; Spearman-Brown estimates the reliability of the full-length test.',
          },
          {
            text: 'As a test\'s reliability increases, its standard error of measurement:',
            options: ['Increases', 'Decreases', 'Stays the same', 'Becomes negative'],
            answer: 1,
            explanation: 'SEM = SD x sqrt(1 - r). A larger r makes (1 - r) smaller, so the SEM decreases.',
          },
          {
            text: 'A depression inventory correlates strongly with another depression measure and weakly with a measure of spelling ability. This is evidence of:',
            options: ['Face validity', 'Content validity', 'Construct validity (convergent and discriminant)', 'Test-retest reliability'],
            answer: 2,
            explanation: 'Strong correlation with the same construct (convergent) and weak correlation with an unrelated one (discriminant) support construct validity.',
          },
          {
            text: 'A test can be valid even if it is not reliable.',
            options: TF,
            answer: 1,
            explanation: 'Reliability is necessary but not sufficient for validity. Inconsistent scores cannot support a valid interpretation.',
          },
        ],
      },
      {
        key: 'u1q3',
        title: 'Test Scores and Statistics',
        timeLimit: 600,
        questions: [
          {
            text: 'About what percentage of scores fall within one standard deviation of the mean in a normal distribution?',
            options: ['50%', '68%', '95%', '99.7%'],
            answer: 1,
            explanation: 'About 68% of scores fall within plus or minus 1 SD; about 95% within 2 SD; about 99.7% within 3 SD.',
          },
          {
            text: 'A T-score has a mean and standard deviation of:',
            options: ['0 and 1', '50 and 10', '100 and 15', '5 and 2'],
            answer: 1,
            explanation: 'T-scores have a mean of 50 and an SD of 10.',
          },
          {
            text: 'A z-score of +1.0 falls at approximately which percentile?',
            options: ['50th', '68th', '84th', '98th'],
            answer: 2,
            explanation: '50% of scores lie below the mean plus about 34% between the mean and +1 SD, giving about the 84th percentile.',
          },
          {
            text: 'In a positively skewed distribution:',
            options: ['The mean is greater than the median', 'The mean is less than the median', 'The mean equals the mode', 'Most scores are high'],
            answer: 0,
            explanation: 'The long tail to the right pulls the mean above the median. Most scores cluster at the low end.',
          },
          {
            text: 'A stanine of 5 represents an average score.',
            options: TF,
            answer: 0,
            explanation: 'Stanines run from 1 to 9 with a mean of 5 and an SD of about 2.',
          },
        ],
      },
    ],
  },
  {
    key: 'unit2',
    title: 'Unit 2: Human Growth and Development',
    description: 'Cognitive, psychosocial, attachment, and moral development across the lifespan.',
    lessons: [
      {
        key: 'u2l1',
        title: "Piaget's Cognitive Development",
        minutes: 15,
        content: `# Piaget's Cognitive Development

Jean Piaget described children as active learners who build **schemas**. New experiences are either fitted into existing schemas (**assimilation**) or cause schemas to change (**accommodation**).

## The four stages

- **Sensorimotor (birth to about 2):** learning through the senses and movement; **object permanence** develops.
- **Preoperational (about 2 to 7):** symbolic thought and language grow; thinking is **egocentric**, and the child does not yet understand **conservation**.
- **Concrete operational (about 7 to 11):** logical thinking about concrete objects; conservation, classification, and reversibility are mastered.
- **Formal operational (about 11 and up):** abstract and hypothetical reasoning becomes possible.

## For counselors

Match interventions to the client's level of thinking. A young child may understand a feeling better through play and concrete examples than through abstract discussion.`,
      },
      {
        key: 'u2l2',
        title: "Erikson's Psychosocial Stages",
        minutes: 15,
        content: `# Erikson's Psychosocial Stages

Erik Erikson proposed eight stages across the lifespan. Each stage presents a **psychosocial crisis**; resolving it well produces a lasting strength.

- **Trust vs. Mistrust** (infancy)
- **Autonomy vs. Shame and Doubt** (early childhood)
- **Initiative vs. Guilt** (preschool years)
- **Industry vs. Inferiority** (school age)
- **Identity vs. Role Confusion** (adolescence)
- **Intimacy vs. Isolation** (young adulthood)
- **Generativity vs. Stagnation** (middle adulthood)
- **Integrity vs. Despair** (late adulthood)

## Key points

Unlike Freud, Erikson's theory extends across the whole lifespan and emphasizes social relationships. Earlier stages are not "locked": later experiences can help a person rework earlier crises.`,
      },
      {
        key: 'u2l3',
        title: 'Attachment',
        minutes: 12,
        content: `# Attachment

John **Bowlby** described attachment as an inborn system that keeps infants close to caregivers, especially under stress. Early relationships shape **internal working models** of self and others.

## The Strange Situation

Mary **Ainsworth** observed infants during brief separations from and reunions with a caregiver. She described three patterns:

- **Secure:** distressed by separation, comforted on reunion, then returns to play.
- **Insecure-avoidant:** little distress on separation; avoids the caregiver on reunion.
- **Insecure-resistant (ambivalent):** very distressed; seeks contact but resists comfort on reunion.

Mary **Main** and Judith **Solomon** later added a fourth pattern, **disorganized**, marked by contradictory or confused behavior on reunion.

## For counselors

Attachment history can inform how clients approach closeness, trust, and the counseling relationship itself.`,
      },
      {
        key: 'u2l4',
        title: 'Moral Development',
        minutes: 12,
        content: `# Moral Development

## Kohlberg

Lawrence **Kohlberg** studied moral reasoning with dilemmas such as the **Heinz dilemma**. He focused on the reasoning behind an answer, not the answer itself, and described three levels with two stages each:

- **Preconventional:** right and wrong are judged by punishment and reward, then by self-interest and fair exchange.
- **Conventional:** right is what pleases others and gains approval, then what maintains law and social order.
- **Postconventional:** reasoning based on social contract and individual rights, then on universal ethical principles.

## Gilligan

Carol **Gilligan**, a student of Kohlberg, argued that his research relied mainly on male participants and emphasized justice. She described an **ethic of care** that stresses responsibility and relationships.

## For counselors

Understanding a client's level of moral reasoning helps a counselor frame discussions of choices and consequences.`,
      },
    ],
    quizzes: [
      {
        key: 'u2q1',
        title: 'Cognitive Development',
        timeLimit: null,
        questions: [
          {
            text: 'A child who realizes a toy still exists when hidden under a blanket has developed:',
            options: ['Conservation', 'Object permanence', 'Reversibility', 'Formal operations'],
            answer: 1,
            explanation: 'Object permanence develops during the sensorimotor stage.',
          },
          {
            text: 'In which Piagetian stage is conservation typically mastered?',
            options: ['Sensorimotor', 'Preoperational', 'Concrete operational', 'Formal operational'],
            answer: 2,
            explanation: 'Conservation is a hallmark of the concrete operational stage (about ages 7 to 11).',
          },
          {
            text: 'Changing an existing schema to fit new information is called:',
            options: ['Assimilation', 'Accommodation', 'Equilibration', 'Centration'],
            answer: 1,
            explanation: 'Accommodation changes the schema. Assimilation fits new information into an existing schema.',
          },
          {
            text: 'Egocentrism is characteristic of the preoperational stage.',
            options: TF,
            answer: 0,
            explanation: 'Preoperational children have difficulty taking another person\'s point of view.',
          },
          {
            text: 'Reasoning about hypothetical, abstract possibilities first appears in the:',
            options: ['Sensorimotor stage', 'Preoperational stage', 'Concrete operational stage', 'Formal operational stage'],
            answer: 3,
            explanation: 'Abstract and hypothetical reasoning marks the formal operational stage (about age 11 and up).',
          },
        ],
      },
      {
        key: 'u2q2',
        title: 'Psychosocial Development and Attachment',
        timeLimit: 480,
        questions: [
          {
            text: 'According to Erikson, the central task of adolescence is:',
            options: ['Industry vs. Inferiority', 'Identity vs. Role Confusion', 'Intimacy vs. Isolation', 'Initiative vs. Guilt'],
            answer: 1,
            explanation: 'Adolescents work to form a coherent sense of identity.',
          },
          {
            text: 'A 50-year-old focused on mentoring younger colleagues and guiding the next generation is addressing:',
            options: ['Integrity vs. Despair', 'Intimacy vs. Isolation', 'Generativity vs. Stagnation', 'Autonomy vs. Shame and Doubt'],
            answer: 2,
            explanation: 'Generativity, contributing to future generations, is the task of middle adulthood.',
          },
          {
            text: 'In the Strange Situation, an infant who shows little distress at separation and avoids the caregiver at reunion is classified as:',
            options: ['Secure', 'Insecure-avoidant', 'Insecure-resistant', 'Disorganized'],
            answer: 1,
            explanation: 'Avoidant infants show little distress and turn away from the caregiver on reunion.',
          },
          {
            text: 'The disorganized attachment category was added by Main and Solomon.',
            options: TF,
            answer: 0,
            explanation: 'Ainsworth described three patterns; Main and Solomon later identified disorganized attachment.',
          },
          {
            text: 'Bowlby\'s term for the mental representations of self and others formed through early relationships is:',
            options: ['Schemas', 'Internal working models', 'Scripts', 'Ego states'],
            answer: 1,
            explanation: 'Internal working models guide expectations about relationships throughout life.',
          },
        ],
      },
      {
        key: 'u2q3',
        title: 'Moral Development',
        timeLimit: null,
        questions: [
          {
            text: 'Kohlberg classified moral development mainly by:',
            options: ['The decision a person makes', 'The reasoning behind the decision', 'The person\'s age', 'The person\'s emotional response'],
            answer: 1,
            explanation: 'Kohlberg scored the reasoning given for a decision, not the decision itself.',
          },
          {
            text: 'A person who obeys rules mainly to avoid punishment is reasoning at which level?',
            options: ['Preconventional', 'Conventional', 'Postconventional', 'Formal'],
            answer: 0,
            explanation: 'Avoiding punishment is the first stage of the preconventional level.',
          },
          {
            text: 'Reasoning that "laws must be followed to keep social order" reflects the:',
            options: ['Preconventional level', 'Conventional level', 'Postconventional level', 'Sensorimotor stage'],
            answer: 1,
            explanation: 'Law-and-order reasoning is the second stage of the conventional level.',
          },
          {
            text: 'Carol Gilligan described an ethic of care emphasizing relationships and responsibility.',
            options: TF,
            answer: 0,
            explanation: 'Gilligan argued that Kohlberg\'s justice orientation overlooked an ethic of care.',
          },
          {
            text: 'Kohlberg studied moral reasoning with dilemmas such as the:',
            options: ['Heinz dilemma', 'Prisoner\'s dilemma', 'Trolley problem', 'Marshmallow test'],
            answer: 0,
            explanation: 'In the Heinz dilemma, a man considers stealing a drug to save his dying wife.',
          },
        ],
      },
    ],
  },
  {
    key: 'unit3',
    title: 'Unit 3: Counseling and Helping Relationships',
    description: 'Major counseling theories, behavioral principles, and core helping skills.',
    lessons: [
      {
        key: 'u3l1',
        title: 'Person-Centered Counseling',
        minutes: 12,
        content: `# Person-Centered Counseling

Carl **Rogers** held that people have an inherent tendency toward growth (the **actualizing tendency**). Problems arise when a person's self-concept conflicts with experience (**incongruence**).

## The core conditions

Rogers proposed that change occurs when the counselor provides:

- **Congruence (genuineness):** the counselor is real and consistent, not hiding behind a professional role.
- **Unconditional positive regard:** acceptance of the client as a person, without conditions.
- **Accurate empathic understanding:** sensing the client's inner world and communicating that understanding.

## Style

The approach is **nondirective**: the client leads, and the counselor avoids advice-giving and interpretation. The relationship itself is the main agent of change.`,
      },
      {
        key: 'u3l2',
        title: 'Cognitive and Rational Emotive Approaches',
        minutes: 15,
        content: `# Cognitive and Rational Emotive Approaches

## Ellis: Rational Emotive Behavior Therapy (REBT)

Albert **Ellis** taught that emotional upset comes mainly from irrational beliefs about events, not the events themselves. His **ABC model**:

- **A:** Activating event
- **B:** Belief about the event
- **C:** emotional and behavioral Consequence

Treatment adds **D** (Disputing irrational beliefs) and **E** (an Effective new philosophy). Ellis highlighted demanding beliefs such as "must" and "should".

## Beck: Cognitive Therapy

Aaron **Beck** identified **automatic thoughts** and **cognitive distortions** such as catastrophizing, all-or-nothing thinking, and overgeneralization. In depression he described the **cognitive triad**: negative views of the self, the world, and the future.

## Shared features

Both approaches are structured, collaborative, time-limited, and use homework to test and change thinking.`,
      },
      {
        key: 'u3l3',
        title: 'Behavioral Principles',
        minutes: 15,
        content: `# Behavioral Principles

## Classical conditioning

Ivan **Pavlov** showed that a neutral stimulus paired with an unconditioned stimulus comes to produce a conditioned response. **Systematic desensitization** (Joseph **Wolpe**) pairs relaxation with a graded hierarchy of feared situations.

## Operant conditioning

B. F. **Skinner** studied how consequences shape behavior.

- **Positive reinforcement:** adding a pleasant stimulus to **increase** a behavior.
- **Negative reinforcement:** removing an aversive stimulus to **increase** a behavior.
- **Positive punishment:** adding an aversive stimulus to **decrease** a behavior.
- **Negative punishment:** removing a pleasant stimulus to **decrease** a behavior.

## Schedules of reinforcement

A **variable-ratio** schedule (reinforcement after an unpredictable number of responses) produces high response rates that are the **most resistant to extinction**.`,
      },
      {
        key: 'u3l4',
        title: 'Core Counseling Microskills',
        minutes: 12,
        content: `# Core Counseling Microskills

## Attending

Gerard **Egan's SOLER** describes attentive posture: face the client **S**quarely, **O**pen posture, **L**ean toward the client, appropriate **E**ye contact, and a **R**elaxed manner.

## Questions

- **Open questions** ("What was that like for you?") invite the client to explore.
- **Closed questions** ("Did you go to work today?") gather specific facts.

## Reflecting skills

- **Paraphrasing** restates the content of what the client said.
- **Reflection of feeling** names the emotion the client expresses.
- **Summarizing** pulls together several themes, often at transitions or the end of a session.

## Using the skills together

Begin with attending and open questions, reflect often to show understanding, and summarize before moving to goals or problem solving.`,
      },
    ],
    quizzes: [
      {
        key: 'u3q1',
        title: 'Theories of Counseling',
        timeLimit: 480,
        questions: [
          {
            text: 'Which is NOT one of Rogers\' core conditions?',
            options: ['Congruence', 'Unconditional positive regard', 'Accurate empathy', 'Disputing irrational beliefs'],
            answer: 3,
            explanation: 'Disputing irrational beliefs belongs to Ellis\'s REBT, not Rogers\' person-centered approach.',
          },
          {
            text: 'In Ellis\'s ABC model, "B" stands for:',
            options: ['Behavior', 'Belief', 'Barrier', 'Baseline'],
            answer: 1,
            explanation: 'A is the activating event, B the belief about it, and C the consequence.',
          },
          {
            text: 'Beck\'s cognitive triad in depression consists of negative views of the:',
            options: ['Past, present, and future', 'Self, world, and future', 'Family, work, and friends', 'Body, mind, and spirit'],
            answer: 1,
            explanation: 'Beck described negative views of the self, the world, and the future.',
          },
          {
            text: 'Person-centered counseling is primarily nondirective.',
            options: TF,
            answer: 0,
            explanation: 'The client leads; the counselor provides the core conditions rather than directing the session.',
          },
          {
            text: 'A client says, "If I fail this exam, I\'m a total failure at everything." This cognitive distortion is best labeled:',
            options: ['Overgeneralization', 'Personalization', 'Minimization', 'Mind reading'],
            answer: 0,
            explanation: 'Drawing a sweeping conclusion from a single event is overgeneralization.',
          },
        ],
      },
      {
        key: 'u3q2',
        title: 'Behavioral Principles',
        timeLimit: null,
        questions: [
          {
            text: 'Removing an aversive stimulus to increase a behavior is:',
            options: ['Positive reinforcement', 'Negative reinforcement', 'Positive punishment', 'Negative punishment'],
            answer: 1,
            explanation: 'Reinforcement always increases behavior. "Negative" means something is removed.',
          },
          {
            text: 'Which schedule of reinforcement is most resistant to extinction?',
            options: ['Fixed ratio', 'Fixed interval', 'Variable ratio', 'Continuous'],
            answer: 2,
            explanation: 'Unpredictable reinforcement after a varying number of responses makes behavior very persistent.',
          },
          {
            text: 'Systematic desensitization was developed by:',
            options: ['B. F. Skinner', 'Joseph Wolpe', 'Albert Bandura', 'John Watson'],
            answer: 1,
            explanation: 'Wolpe paired relaxation with a graded fear hierarchy.',
          },
          {
            text: 'Taking away a teen\'s phone privileges to reduce curfew violations is negative punishment.',
            options: TF,
            answer: 0,
            explanation: 'A pleasant stimulus is removed to decrease a behavior, which is negative punishment.',
          },
          {
            text: 'In classical conditioning, a previously neutral stimulus that comes to trigger a response is the:',
            options: ['Unconditioned stimulus', 'Conditioned stimulus', 'Unconditioned response', 'Reinforcer'],
            answer: 1,
            explanation: 'After pairing, the neutral stimulus becomes a conditioned stimulus that elicits a conditioned response.',
          },
        ],
      },
      {
        key: 'u3q3',
        title: 'Counseling Microskills',
        timeLimit: 300,
        questions: [
          {
            text: 'In Egan\'s SOLER, the "L" stands for:',
            options: ['Listen', 'Lean toward the client', 'Look away periodically', 'Limit questions'],
            answer: 1,
            explanation: 'SOLER: Squarely, Open posture, Lean toward the client, Eye contact, Relaxed.',
          },
          {
            text: 'Which is an open question?',
            options: ['"Did you sleep well?"', '"Are you married?"', '"How has your week been going?"', '"Is your job stressful?"'],
            answer: 2,
            explanation: 'Open questions cannot be answered with a single word and invite exploration.',
          },
          {
            text: 'Client: "My boss yelled at me in front of everyone." Counselor: "You felt humiliated." This response is a:',
            options: ['Paraphrase', 'Reflection of feeling', 'Summary', 'Closed question'],
            answer: 1,
            explanation: 'Naming the emotion the client expresses is a reflection of feeling.',
          },
          {
            text: 'Summarizing is useful at transitions and at the end of a session.',
            options: TF,
            answer: 0,
            explanation: 'Summaries tie together themes and help move the session forward.',
          },
          {
            text: 'Restating the content of a client\'s message in the counselor\'s own words is:',
            options: ['Paraphrasing', 'Interpreting', 'Confronting', 'Self-disclosure'],
            answer: 0,
            explanation: 'Paraphrasing focuses on content; reflection of feeling focuses on emotion.',
          },
        ],
      },
    ],
  },
];

function buildQuiz(unitId: string, spec: QuizSpec, order: number): Quiz {
  const quizId = idFor(spec.key);
  const questions: Question[] = spec.questions.map((q, qi) => {
    const questionId = idFor(`${spec.key}.q${qi + 1}`);
    const options = q.options.map((text, oi) => ({
      id: idFor(`${spec.key}.q${qi + 1}.o${oi}`),
      questionId,
      text,
      order: oi,
    }));
    return {
      id: questionId,
      quizId,
      text: q.text,
      questionType: q.options === TF ? 'true_false' : 'multiple_choice',
      options,
      correctAnswerId: options[q.answer].id,
      explanation: q.explanation,
    };
  });
  return { id: quizId, unitId, title: spec.title, questions, timeLimit: spec.timeLimit, passingScore: 70, order };
}

/** Course content with derived fields zeroed (progress is applied from the database). */
export function buildCourses(): Course[] {
  return UNITS.map((u) => {
    const unitId = idFor(u.key);
    const lessons: Lesson[] = u.lessons.map((l, i) => ({
      id: idFor(l.key),
      unitId,
      title: l.title,
      content: l.content,
      order: i + 1,
      completed: false,
      estimatedTime: l.minutes,
    }));
    const quizzes = u.quizzes.map((q, i) => buildQuiz(unitId, q, i + 1));
    return {
      id: unitId,
      title: u.title,
      description: u.description,
      totalLessons: lessons.length,
      totalQuizzes: quizzes.length,
      progressPercentage: 0,
      lessons,
      quizzes,
    };
  });
}

/** Bump when the bundled content changes; the database re-seeds content (never progress). */
export const CONTENT_VERSION = 1;
