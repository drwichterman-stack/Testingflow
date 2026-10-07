import { formatStudyTime, formatTimer, overallPercent, progressTone, scoreQuiz, startOfWeek,
         unitPercent } from '../src/logic/progress';
import { initialQuizState, quizReducer, SELECT_ERROR } from '../src/logic/quizMachine';

describe('progress calculation', () => {
  it('weights lessons and quizzes equally', () => {
    // 2 of 4 lessons (50%) and quiz bests 80, 60, not taken (avg 46.67) -> 48.3
    expect(unitPercent(2, 4, [80, 60], 3)).toBe(48);
    expect(unitPercent(4, 4, [100, 100, 100], 3)).toBe(100);
    expect(unitPercent(0, 4, [], 3)).toBe(0);
  });
  it('handles units with only lessons or only quizzes', () => {
    expect(unitPercent(1, 2, [], 0)).toBe(50);
    expect(unitPercent(0, 0, [90], 1)).toBe(90);
    expect(unitPercent(0, 0, [], 0)).toBe(0);
  });
  it('overall is the mean of unit percentages', () => {
    expect(overallPercent([100, 50, 0])).toBe(50);
    expect(overallPercent([])).toBe(0);
  });
  it('colors: green above 70, amber 40 to 70, gray below 40', () => {
    expect(progressTone(71)).toBe('green');
    expect(progressTone(70)).toBe('amber');
    expect(progressTone(40)).toBe('amber');
    expect(progressTone(39)).toBe('gray');
  });
  it('scores quizzes as whole percentages', () => {
    expect(scoreQuiz(4, 5)).toBe(80);
    expect(scoreQuiz(2, 3)).toBe(67);
    expect(scoreQuiz(0, 0)).toBe(0);
  });
  it('formats times', () => {
    expect(formatStudyTime(0)).toBe('0:00');
    expect(formatStudyTime(3725)).toBe('1:02');
    expect(formatTimer(125)).toBe('2:05');
    expect(formatTimer(0.2)).toBe('0:01');
    expect(formatTimer(-3)).toBe('0:00');
  });
  it('weeks start on Monday', () => {
    const sunday = new Date(2026, 8, 27, 15, 0); // Sun 27 Sep 2026
    expect(startOfWeek(sunday)).toEqual(new Date(2026, 8, 21));
    const monday = new Date(2026, 8, 21, 0, 30);
    expect(startOfWeek(monday)).toEqual(new Date(2026, 8, 21));
  });
});

describe('quiz state machine', () => {
  const start = () => initialQuizState(['q1', 'q2']);

  it('blocks submit without a selection and shows the inline error', () => {
    const s = quizReducer(start(), { type: 'submit' });
    expect(s.error).toBe('Select an answer to continue');
    expect(SELECT_ERROR).toBe('Select an answer to continue');
    expect(s.submitted).toBe(false);
    expect(s.index).toBe(0);
  });
  it('clears the error when any option is selected', () => {
    let s = quizReducer(start(), { type: 'submit' });
    s = quizReducer(s, { type: 'select', optionId: 'a' });
    expect(s.error).toBeNull();
  });
  it('records the answer on submit and locks the selection', () => {
    let s = quizReducer(start(), { type: 'select', optionId: 'a' });
    s = quizReducer(s, { type: 'submit' });
    expect(s.submitted).toBe(true);
    expect(s.answers).toEqual({ q1: 'a' });
    s = quizReducer(s, { type: 'select', optionId: 'b' });
    expect(s.answers.q1).toBe('a');
  });
  it('does not advance before submit', () => {
    const s = quizReducer(start(), { type: 'next' });
    expect(s.index).toBe(0);
  });
  it('advances, then finishes after the last question', () => {
    let s = start();
    for (const opt of ['a', 'b']) {
      s = quizReducer(s, { type: 'select', optionId: opt });
      s = quizReducer(s, { type: 'submit' });
      s = quizReducer(s, { type: 'next' });
    }
    expect(s.finished).toBe(true);
    expect(s.answers).toEqual({ q1: 'a', q2: 'b' });
  });
  it('finishes on timeout and ignores later actions until restart', () => {
    let s = quizReducer(start(), { type: 'timeout' });
    expect(s.finished && s.timedOut).toBe(true);
    s = quizReducer(s, { type: 'select', optionId: 'a' });
    expect(s.selected).toBeNull();
    s = quizReducer(s, { type: 'restart' });
    expect(s.finished).toBe(false);
  });
});
