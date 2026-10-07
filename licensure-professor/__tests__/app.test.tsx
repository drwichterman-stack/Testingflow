import { act, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { buildCourses } from '../src/data/content';
import { renderApp } from './helpers/renderApp';

const courses = buildCourses();
const unit1 = courses[0];
const quiz1 = unit1.quizzes[0]; // untimed, 10 questions

async function openQuiz1() {
  await fireEvent.press(await screen.findByTestId(`unit-${unit1.id}`));
  await fireEvent.press(await screen.findByTestId('quiz-1'));
  await screen.findByTestId('question-text');
}

const letter = (q: (typeof quiz1.questions)[number], optionId: string) =>
  'ABCD'[q.options.find((o) => o.id === optionId)!.order];

describe('Home', () => {
  it('shows the header, stat cards, and 6 units', async () => {
    await renderApp();
    expect(await screen.findByText('NCE Exam Prep')).toBeTruthy();
    expect(screen.getByText("Master's/Doctoral Counseling")).toBeTruthy();
    expect(screen.getByText('This week')).toBeTruthy();
    expect(screen.getByText('Overall')).toBeTruthy();
    for (const c of courses) {
      expect(await screen.findByText(c.title)).toBeTruthy();
    }
    expect(screen.getByText('12 lessons, 12 quizzes')).toBeTruthy();
    expect(screen.getByText('17 lessons, 30 quizzes')).toBeTruthy();
    expect(screen.getAllByText('5 lessons, 9 quizzes')).toHaveLength(1);
    expect(screen.getByTestId('stat-overall')).toHaveTextContent('0%');
  });
});

describe('Lessons', () => {
  it('opens a lesson, marks it complete (saved), and moves to the next', async () => {
    const { db } = await renderApp();
    await fireEvent.press(await screen.findByTestId(`unit-${unit1.id}`));
    await fireEvent.press(await screen.findByTestId('lesson-1'));
    expect(await screen.findByTestId('lesson-counter')).toHaveTextContent('1 of 12');
    expect(screen.getByText('9 min read')).toBeTruthy();
    await fireEvent.press(screen.getByTestId('lesson-complete-next'));
    await waitFor(() => expect(screen.getByTestId('lesson-counter')).toHaveTextContent('2 of 12'));
    const rows = await db.getAllAsync<{ lesson_id: string }>('SELECT lesson_id FROM lesson_completions', []);
    expect(rows.map((r) => r.lesson_id)).toEqual([unit1.lessons[0].id]);
    await fireEvent.press(screen.getByTestId('lesson-prev'));
    await waitFor(() => expect(screen.getByTestId('lesson-counter')).toHaveTextContent('1 of 12'));
    expect(await screen.findByText('✓ Completed')).toBeTruthy();
  });
});

describe('Quiz engine', () => {
  it('blocks submit without an answer and shows the inline error', async () => {
    const { db } = await renderApp();
    await openQuiz1();
    expect(screen.getByTestId('quiz-counter')).toHaveTextContent(`1 of ${quiz1.questions.length}`);
    expect(screen.queryByTestId('quiz-timer')).toBeNull(); // untimed quiz
    await fireEvent.press(screen.getByTestId('quiz-submit'));
    const err = await screen.findByTestId('quiz-error');
    expect(err).toHaveTextContent('Select an answer to continue');
    expect(err).toHaveStyle({ color: '#c62828', fontSize: 13 });
    expect(screen.queryByTestId('quiz-explanation')).toBeNull();
    expect(screen.getByTestId('quiz-counter')).toHaveTextContent(/^1 of /);
    expect(await db.getAllAsync('SELECT * FROM attempt_answers', [])).toHaveLength(0);
    await fireEvent.press(screen.getByTestId('option-A'));
    expect(screen.queryByTestId('quiz-error')).toBeNull();
  });

  it('saves each answer on submit, shows the explanation, and completes with a score', async () => {
    const { db } = await renderApp();
    await openQuiz1();
    for (const [i, q] of quiz1.questions.entries()) {
      // Answer the first question wrong, the rest right: 9 of 10 = 90%.
      const pick = i === 0 ? q.options.find((o) => o.id !== q.correctAnswerId)!.id : q.correctAnswerId;
      await fireEvent.press(screen.getByTestId(`option-${letter(q, pick)}`));
      await fireEvent.press(screen.getByTestId('quiz-submit'));
      expect(await screen.findByTestId('quiz-explanation')).toHaveTextContent(q.explanation.replace(/\s+/g, ' '), { exact: false });
      await waitFor(async () =>
        expect(await db.getAllAsync('SELECT * FROM attempt_answers', [])).toHaveLength(i + 1));
      await fireEvent.press(screen.getByTestId('quiz-next'));
    }
    expect(await screen.findByTestId('final-score')).toHaveTextContent('90%');
    expect(screen.getByTestId('pass-badge')).toHaveTextContent('PASSED');
    await waitFor(async () => {
      const a = await db.getFirstAsync<{ score: number; is_passing: number; completed_at: string | null }>(
        'SELECT score, is_passing, completed_at FROM quiz_attempts', []);
      expect(a).toMatchObject({ score: 90, is_passing: 1 });
      expect(a!.completed_at).not.toBeNull();
    });
    await fireEvent.press(screen.getByTestId('btn-review'));
    expect(await screen.findByTestId('quiz-review')).toBeTruthy();
    await fireEvent.press(screen.getByTestId('btn-retake'));
    expect(await screen.findByTestId('quiz-counter')).toHaveTextContent(/^1 of /);
    await fireEvent.press(screen.getByTestId('quiz-submit'));
    expect(await screen.findByTestId('quiz-error')).toBeTruthy();
  });

  it('returns to the unit and shows the best score', async () => {
    await renderApp();
    await openQuiz1();
    for (const q of quiz1.questions) {
      await fireEvent.press(screen.getByTestId(`option-${letter(q, q.correctAnswerId)}`));
      await fireEvent.press(screen.getByTestId('quiz-submit'));
      await fireEvent.press(await screen.findByTestId('quiz-next'));
    }
    expect(await screen.findByTestId('final-score')).toHaveTextContent('100%');
    await fireEvent.press(screen.getByTestId('btn-return'));
    expect(await screen.findByText('Best 100%')).toBeTruthy();
  });

  it('counts down on timed quizzes and finishes when time runs out', async () => {
    jest.useFakeTimers();
    try {
      const { db } = await renderApp();
      const timed = unit1.quizzes[1]; // 10 items at 67.5 s = 675 s
      await fireEvent.press(await screen.findByTestId(`unit-${unit1.id}`));
      await fireEvent.press(await screen.findByTestId('quiz-2'));
      expect(await screen.findByTestId('quiz-timer-text')).toHaveTextContent('11:15');
      await act(async () => { jest.advanceTimersByTime(61_000); });
      expect(screen.getByTestId('quiz-timer-text')).toHaveTextContent('10:14');
      const q = timed.questions[0];
      await fireEvent.press(screen.getByTestId(`option-${letter(q, q.correctAnswerId)}`));
      await fireEvent.press(screen.getByTestId('quiz-submit'));
      await act(async () => { jest.advanceTimersByTime(675_000); });
      expect(await screen.findByTestId('final-score')).toHaveTextContent('10%'); // 1 of 10
      expect(screen.getByText(/Time ran out/)).toBeTruthy();
      await act(async () => { jest.useRealTimers(); });
      await waitFor(async () => {
        const a = await db.getFirstAsync<{ score: number; time_spent: number }>(
          'SELECT score, time_spent FROM quiz_attempts WHERE completed_at IS NOT NULL', []);
        expect(a).toMatchObject({ score: 10, time_spent: 675 });
      });
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('Progress', () => {
  it('shows overall and per-unit scores after activity', async () => {
    const { db } = await renderApp();
    await fireEvent.press(await screen.findByTestId(`unit-${unit1.id}`));
    await fireEvent.press(await screen.findByTestId('lesson-1'));
    await fireEvent.press(await screen.findByTestId('lesson-complete'));
    await waitFor(async () =>
      expect(await db.getAllAsync('SELECT * FROM lesson_completions', [])).toHaveLength(1));
    await fireEvent.press(screen.getByText('Progress'));
    // Unit 1: 1/12 lessons -> 4.2 -> 4%; overall (4 + 0 + 0 + 0 + 0 + 0) / 6 -> 1%
    expect(await screen.findByTestId('overall-score')).toHaveTextContent('1%');
    expect(screen.getByText('4%')).toBeTruthy();
    await fireEvent.press(screen.getByTestId(`progress-unit-${unit1.id}`));
    expect(await screen.findByText('1 of 12')).toBeTruthy();
  });
});
