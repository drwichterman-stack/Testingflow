/**
 * Progress calculations (pure functions; unit tested).
 *
 * Per-unit score = 50% lesson completion + 50% average quiz score.
 * The average quiz score uses each quiz's BEST completed score, and a quiz
 * not yet taken counts as 0, so the unit score reflects how much of the
 * unit is done. Overall score = mean of the unit scores.
 */

export function unitPercent(lessonsCompleted: number, totalLessons: number,
                            bestQuizScores: number[], totalQuizzes: number): number {
  const lessonPart = totalLessons > 0 ? (lessonsCompleted / totalLessons) * 100 : 0;
  const quizPart = totalQuizzes > 0
    ? bestQuizScores.reduce((a, b) => a + b, 0) / totalQuizzes
    : 0;
  if (totalLessons === 0 && totalQuizzes === 0) return 0;
  if (totalLessons === 0) return Math.round(quizPart);
  if (totalQuizzes === 0) return Math.round(lessonPart);
  return Math.round(lessonPart * 0.5 + quizPart * 0.5);
}

export function overallPercent(unitPercents: number[]): number {
  if (unitPercents.length === 0) return 0;
  return Math.round(unitPercents.reduce((a, b) => a + b, 0) / unitPercents.length);
}

export type ProgressTone = 'green' | 'amber' | 'gray';

/** Green above 70%, amber from 40% to 70%, gray below 40%. */
export function progressTone(percent: number): ProgressTone {
  if (percent > 70) return 'green';
  if (percent >= 40) return 'amber';
  return 'gray';
}

/** Quiz score as a whole percentage; unanswered questions count as wrong. */
export function scoreQuiz(correct: number, totalQuestions: number): number {
  if (totalQuestions <= 0) return 0;
  return Math.round((correct / totalQuestions) * 100);
}

/** "h:mm", e.g. 3725 s -> "1:02". */
export function formatStudyTime(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds / 60));
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${h}:${m.toString().padStart(2, '0')}`;
}

/** Countdown "m:ss", e.g. 125 -> "2:05". */
export function formatTimer(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;
}

/** Start of the current week (Monday 00:00, local time). */
export function startOfWeek(now: Date): Date {
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const daysSinceMonday = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - daysSinceMonday);
  return d;
}

export const OPTION_LETTERS = ['A', 'B', 'C', 'D'];
