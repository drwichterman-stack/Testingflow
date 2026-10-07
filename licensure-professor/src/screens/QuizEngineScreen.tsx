/**
 * Quiz session: question counter, countdown timer (timed quizzes),
 * progress bar, lettered radio options, submit validation, correct answer
 * and explanation, and a completion screen with review and retake.
 *
 * Every submitted answer is written to SQLite at once; the attempt is
 * completed (score, pass/fail, time spent) when the last question is
 * answered or the time runs out. Unanswered questions count as wrong.
 */
import Ionicons from '@expo/vector-icons/Ionicons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ProgressBar } from '../components/ProgressBar';
import * as repo from '../db/repo';
import { formatTimer, OPTION_LETTERS, scoreQuiz } from '../logic/progress';
import { initialQuizState, isLastQuestion, quizReducer, type QuizState } from '../logic/quizMachine';
import type { HomeStackParams, QuizStackParams } from '../navigation/types';
import { useAppData, useCourses } from '../state/AppData';
import { colors, common, hairline, radius, space } from '../theme';
import type { Course, Question, Quiz } from '../types';

type Props =
  | NativeStackScreenProps<HomeStackParams, 'QuizEngine'>
  | NativeStackScreenProps<QuizStackParams, 'QuizEngine'>;

export function QuizEngineScreen({ navigation, route }: Props) {
  const courses = useCourses();
  const unit = courses?.find((c) => c.quizzes.some((q) => q.id === route.params.quizId));
  const quiz = unit?.quizzes.find((q) => q.id === route.params.quizId);
  const [runKey, setRunKey] = useState(0); // new key = fresh attempt (retake)

  useEffect(() => {
    if (quiz) navigation.setOptions({ title: quiz.title });
  }, [quiz?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!unit || !quiz) return <View style={common.screen} />;

  const returnToUnit = () => {
    const names = navigation.getState().routeNames as string[];
    if (names.includes('UnitDetail')) {
      (navigation as NativeStackScreenProps<HomeStackParams, 'QuizEngine'>['navigation'])
        .popTo('UnitDetail', { unitId: unit.id });
    } else {
      // From the Quiz tab: open the unit in the Home tab, keeping the course list beneath it.
      (navigation as any).navigate('HomeTab', {
        screen: 'UnitDetail', params: { unitId: unit.id }, initial: false });
    }
  };

  return <QuizSession key={runKey} unit={unit} quiz={quiz} onRetake={() => setRunKey((k) => k + 1)}
                      onReturn={returnToUnit} />;
}

interface SessionProps {
  unit: Course;
  quiz: Quiz;
  onRetake: () => void;
  onReturn: () => void;
}

function QuizSession({ unit, quiz, onRetake, onReturn }: SessionProps) {
  const app = useAppData();
  const insets = useSafeAreaInsets();
  const [state, dispatch] = useReducer(quizReducer, quiz.questions.map((q) => q.id), initialQuizState);
  const startedAt = useRef(0);
  const attemptId = useRef<string | null>(null);
  const finalized = useRef(false);
  const [remaining, setRemaining] = useState<number | null>(quiz.timeLimit);
  const [result, setResult] = useState<{ score: number; passing: boolean } | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const scroll = useRef<ScrollView>(null);

  const question = quiz.questions[state.index];

  useEffect(() => {
    startedAt.current = Date.now(); // the attempt clock starts when the session mounts
  }, []);

  const ensureAttempt = useCallback(async () => {
    if (!attemptId.current) {
      const id = app.newId();
      attemptId.current = id;
      await repo.startAttempt(app.db, app.userId, quiz.id, id);
    }
    return attemptId.current;
  }, [app, quiz.id]);

  // Countdown for timed quizzes, measured from the start time so it stays
  // correct if the app is briefly in the background.
  useEffect(() => {
    if (!quiz.timeLimit || state.finished) return;
    const tick = () => {
      const left = quiz.timeLimit! - (Date.now() - startedAt.current) / 1000;
      setRemaining(Math.max(0, left));
      if (left <= 0) dispatch({ type: 'timeout' });
    };
    tick();
    const t = setInterval(tick, 250);
    return () => clearInterval(t);
  }, [quiz.timeLimit, state.finished]);

  // Complete the attempt once, when the quiz finishes.
  useEffect(() => {
    if (!state.finished || finalized.current) return;
    finalized.current = true;
    const correct = quiz.questions.filter((q) => state.answers[q.id] === q.correctAnswerId).length;
    const score = scoreQuiz(correct, quiz.questions.length);
    const passing = score >= quiz.passingScore;
    setResult({ score, passing });
    const spent = Math.min((Date.now() - startedAt.current) / 1000, quiz.timeLimit ?? Infinity);
    (async () => {
      const id = await ensureAttempt();
      await repo.finishAttempt(app.db, id, score, passing, spent);
      app.refresh();
    })().catch((e) => setSaveError(String(e)));
  }, [state.finished]); // eslint-disable-line react-hooks/exhaustive-deps

  const onSubmit = async () => {
    const selected = state.selected;
    dispatch({ type: 'submit' });
    if (!selected || state.submitted) return; // reducer shows the inline error
    try {
      const id = await ensureAttempt();
      await repo.saveAnswer(app.db, id, question.id, selected, selected === question.correctAnswerId);
    } catch (e) {
      setSaveError(String(e));
    }
  };

  const onNext = () => {
    dispatch({ type: 'next' });
    scroll.current?.scrollTo({ y: 0, animated: false });
  };

  if (state.finished && result) {
    return <QuizComplete unit={unit} quiz={quiz} state={state} score={result.score}
                         passing={result.passing} onRetake={onRetake} onReturn={onReturn}
                         saveError={saveError} />;
  }

  const n = quiz.questions.length;
  const lowTime = remaining != null && remaining <= 30;
  return (
    <View style={common.screen}>
      <View style={styles.header}>
        <Text style={common.muted} numberOfLines={1}>{unit.title}</Text>
        <Text style={styles.quizTitle} numberOfLines={1}>{quiz.title}</Text>
        <View style={styles.headerRow}>
          <Text style={styles.counter} testID="quiz-counter">{state.index + 1} of {n}</Text>
          {remaining != null && (
            <View style={[styles.timer, lowTime && styles.timerLow]} testID="quiz-timer"
                  accessibilityLabel={`Time remaining ${formatTimer(remaining)}`}>
              <Ionicons name="time-outline" size={15} color={lowTime ? colors.error : colors.text} />
              <Text style={[styles.timerText, lowTime && { color: colors.error }]} testID="quiz-timer-text">
                {formatTimer(remaining)}
              </Text>
            </View>
          )}
        </View>
        <ProgressBar percent={((state.index + (state.submitted ? 1 : 0)) / n) * 100}
                     color={colors.primary} testID="quiz-progress" />
      </View>

      <ScrollView ref={scroll} contentContainerStyle={common.content}>
        <Text style={styles.question} testID="question-text">{question.text}</Text>
        <View style={styles.options} accessibilityRole="radiogroup">
          {question.options.map((o) => (
            <OptionCard key={o.id} question={question} optionId={o.id} text={o.text}
                        letter={OPTION_LETTERS[o.order]} state={state}
                        onPress={() => dispatch({ type: 'select', optionId: o.id })} />
          ))}
        </View>

        {state.error && (
          <Text style={styles.error} testID="quiz-error" accessibilityRole="alert">{state.error}</Text>
        )}

        {state.submitted && (
          <View style={[styles.explain,
                        state.answers[question.id] === question.correctAnswerId ? styles.explainOk : styles.explainBad]}
                testID="quiz-explanation">
            <Text style={styles.explainTitle}>
              {state.answers[question.id] === question.correctAnswerId ? 'Correct' : 'Incorrect'}
              {'  ·  Answer: '}
              {OPTION_LETTERS[question.options.find((o) => o.id === question.correctAnswerId)!.order]}
            </Text>
            <Text style={common.body}>{question.explanation}</Text>
          </View>
        )}
        {saveError && <Text style={styles.error}>Could not save: {saveError}</Text>}
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: 12 + insets.bottom }]}>
        {!state.submitted ? (
          <Pressable onPress={onSubmit} testID="quiz-submit" accessibilityRole="button"
                     style={[styles.btn, styles.btnPrimary]}>
            <Text style={styles.btnPrimaryText}>Submit answer</Text>
          </Pressable>
        ) : (
          <Pressable onPress={onNext} testID="quiz-next" accessibilityRole="button"
                     style={[styles.btn, styles.btnPrimary]}>
            <Text style={styles.btnPrimaryText}>{isLastQuestion(state) ? 'See results' : 'Next question'}</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

function OptionCard({ question, optionId, text, letter, state, onPress }: {
  question: Question; optionId: string; text: string; letter: string; state: QuizState; onPress: () => void;
}) {
  const submitted = state.submitted;
  const chosen = submitted ? state.answers[question.id] === optionId : state.selected === optionId;
  const correct = optionId === question.correctAnswerId;
  const tone = submitted && correct ? 'correct' : submitted && chosen ? 'wrong' : chosen ? 'selected' : 'idle';
  return (
    <Pressable onPress={onPress} disabled={submitted} testID={`option-${letter}`}
               accessibilityRole="radio" accessibilityState={{ checked: chosen, disabled: submitted }}
               accessibilityLabel={`${letter}. ${text}`}
               style={[styles.option, styles[tone]]}>
      <View style={[styles.radio, chosen && styles.radioOn,
                    tone === 'correct' && { borderColor: colors.green },
                    tone === 'wrong' && { borderColor: colors.error }]}>
        {chosen && <View style={[styles.radioDot,
                                 tone === 'correct' && { backgroundColor: colors.green },
                                 tone === 'wrong' && { backgroundColor: colors.error }]} />}
      </View>
      <Text style={styles.letter}>{letter}.</Text>
      <Text style={styles.optionText}>{text}</Text>
      {tone === 'correct' && <Ionicons name="checkmark-circle" size={20} color={colors.green} />}
      {tone === 'wrong' && <Ionicons name="close-circle" size={20} color={colors.error} />}
    </Pressable>
  );
}

function QuizComplete({ unit, quiz, state, score, passing, onRetake, onReturn, saveError }: {
  unit: Course; quiz: Quiz; state: QuizState; score: number; passing: boolean;
  onRetake: () => void; onReturn: () => void; saveError: string | null;
}) {
  const [review, setReview] = useState(false);
  const correct = quiz.questions.filter((q) => state.answers[q.id] === q.correctAnswerId).length;
  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content} testID="quiz-complete">
      <View style={[common.card, styles.resultCard]}>
        <Text style={common.muted}>{unit.title} {'·'} {quiz.title}</Text>
        <Text style={styles.finalScore} testID="final-score">{score}%</Text>
        <View style={[styles.badge, passing ? styles.badgePass : styles.badgeFail]} testID="pass-badge">
          <Text style={[styles.badgeText, { color: passing ? colors.green : colors.error }]}>
            {passing ? 'PASSED' : 'NOT PASSED'}
          </Text>
        </View>
        <Text style={common.muted}>
          {correct} of {quiz.questions.length} correct {'·'} passing score {quiz.passingScore}%
        </Text>
        {state.timedOut && <Text style={[common.muted, { color: colors.error }]}>Time ran out. Unanswered questions count as incorrect.</Text>}
        {saveError && <Text style={styles.error}>Could not save: {saveError}</Text>}
      </View>

      <Text style={common.h2}>Score breakdown</Text>
      <View style={[common.card, { gap: 8 }]}>
        {quiz.questions.map((q, i) => {
          const a = state.answers[q.id];
          const ok = a === q.correctAnswerId;
          return (
            <View key={q.id} style={styles.breakRow}>
              <Ionicons name={a ? (ok ? 'checkmark-circle' : 'close-circle') : 'remove-circle-outline'}
                        size={18} color={a ? (ok ? colors.green : colors.error) : colors.gray} />
              <Text style={[common.body, { flex: 1 }]} numberOfLines={review ? undefined : 1}>
                {i + 1}. {q.text}
              </Text>
            </View>
          );
        })}
      </View>

      {review && (
        <View style={{ gap: space.cardGap, marginTop: 16 }} testID="quiz-review">
          {quiz.questions.map((q, i) => {
            const a = state.answers[q.id];
            const right = q.options.find((o) => o.id === q.correctAnswerId)!;
            const picked = q.options.find((o) => o.id === a);
            return (
              <View key={q.id} style={common.card}>
                <Text style={common.title}>{i + 1}. {q.text}</Text>
                <Text style={[common.body, { marginTop: 6 }]}>
                  Your answer: {picked ? `${OPTION_LETTERS[picked.order]}. ${picked.text}` : 'Not answered'}
                </Text>
                <Text style={[common.body, { color: colors.green }]}>
                  Correct answer: {OPTION_LETTERS[right.order]}. {right.text}
                </Text>
                <Text style={[common.muted, { marginTop: 6 }]}>{q.explanation}</Text>
              </View>
            );
          })}
        </View>
      )}

      <View style={styles.actions}>
        <Pressable onPress={() => setReview((r) => !r)} testID="btn-review" accessibilityRole="button"
                   style={[styles.btn, styles.btnOutline]}>
          <Text style={styles.btnOutlineText}>{review ? 'Hide review' : 'Review answers'}</Text>
        </Pressable>
        <Pressable onPress={onReturn} testID="btn-return" accessibilityRole="button"
                   style={[styles.btn, styles.btnOutline]}>
          <Text style={styles.btnOutlineText}>Return to unit</Text>
        </Pressable>
        <Pressable onPress={onRetake} testID="btn-retake" accessibilityRole="button"
                   style={[styles.btn, styles.btnPrimary]}>
          <Text style={styles.btnPrimaryText}>Retake quiz</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  header: { backgroundColor: colors.surface2, paddingHorizontal: 16, paddingTop: 10, paddingBottom: 12,
            borderBottomWidth: hairline, borderColor: colors.border, gap: 4 },
  quizTitle: { fontSize: 17, fontWeight: '700', color: colors.text },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginVertical: 4 },
  counter: { fontSize: 14, fontWeight: '600', color: colors.muted },
  timer: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 3,
           borderRadius: 8, backgroundColor: colors.track },
  timerLow: { backgroundColor: colors.errorBg },
  timerText: { fontSize: 14, fontWeight: '700', color: colors.text, fontVariant: ['tabular-nums'] },
  question: { fontSize: 16, lineHeight: 24, fontWeight: '600', color: colors.text, marginBottom: 16 },
  options: { gap: space.cardGap },
  option: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14, borderRadius: radius,
            borderWidth: 1, backgroundColor: colors.surface2 },
  idle: { borderColor: colors.border },
  selected: { borderColor: colors.primary, backgroundColor: colors.selected },
  correct: { borderColor: colors.green, backgroundColor: colors.greenBg },
  wrong: { borderColor: colors.error, backgroundColor: colors.errorBg },
  radio: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: colors.gray,
           alignItems: 'center', justifyContent: 'center' },
  radioOn: { borderColor: colors.primary },
  radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary },
  letter: { fontSize: 15, fontWeight: '700', color: colors.text, width: 20 },
  optionText: { flex: 1, fontSize: 15, lineHeight: 21, color: colors.text },
  error: { color: colors.error, fontSize: 13, marginTop: 10 },
  explain: { marginTop: 16, padding: space.pad, borderRadius: radius, borderWidth: hairline, gap: 6 },
  explainOk: { backgroundColor: colors.greenBg, borderColor: colors.green },
  explainBad: { backgroundColor: colors.errorBg, borderColor: colors.error },
  explainTitle: { fontSize: 15, fontWeight: '700', color: colors.text },
  footer: { paddingHorizontal: 16, paddingTop: 12, backgroundColor: colors.surface2,
            borderTopWidth: hairline, borderColor: colors.border },
  btn: { borderRadius: radius, paddingVertical: 14, alignItems: 'center' },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: colors.primaryText, fontSize: 16, fontWeight: '600' },
  btnOutline: { borderWidth: 1, borderColor: colors.primary, backgroundColor: colors.surface2 },
  btnOutlineText: { color: colors.primary, fontSize: 16, fontWeight: '600' },
  resultCard: { alignItems: 'center', gap: 8, paddingVertical: 20 },
  finalScore: { fontSize: 48, fontWeight: '800', color: colors.text },
  badge: { paddingHorizontal: 14, paddingVertical: 5, borderRadius: 999 },
  badgePass: { backgroundColor: colors.greenBg },
  badgeFail: { backgroundColor: colors.errorBg },
  badgeText: { fontSize: 13, fontWeight: '800', letterSpacing: 1 },
  breakRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  actions: { gap: space.cardGap, marginTop: 20 },
});
