/**
 * All reads and writes. Every progress write runs immediately (no batching),
 * so nothing is lost if the app is closed.
 */

import { buildCourses, CONTENT_VERSION } from '../data/content';
import { overallPercent, startOfWeek, unitPercent } from '../logic/progress';
import type { Course, Lesson, Question, Quiz, QuizAttempt, UserProgress } from '../types';
import { SCHEMA_SQL, SCHEMA_VERSION } from './schema';
import type { Db } from './types';

export const nowIso = () => new Date().toISOString();

async function getMeta(db: Db, key: string): Promise<string | null> {
  const row = await db.getFirstAsync<{ value: string }>('SELECT value FROM meta WHERE key = ?', [key]);
  return row ? row.value : null;
}

async function setMeta(db: Db, key: string, value: string): Promise<void> {
  await db.runAsync(
    'INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
    [key, value],
  );
}

/** Create tables, seed bundled content when it changed, and return the local user id. */
export async function initDatabase(db: Db, newId: () => string): Promise<string> {
  await db.execAsync(SCHEMA_SQL);
  await setMeta(db, 'schema_version', String(SCHEMA_VERSION));
  if ((await getMeta(db, 'content_version')) !== String(CONTENT_VERSION)) {
    await seedContent(db);
  }
  let userId = await getMeta(db, 'user_id');
  if (!userId) {
    userId = newId();
    await setMeta(db, 'user_id', userId);
  }
  return userId;
}

export async function seedContent(db: Db): Promise<void> {
  const courses = buildCourses();
  await db.withTransactionAsync(async () => {
    for (const t of ['question_options', 'questions', 'quizzes', 'lessons', 'units']) {
      await db.runAsync(`DELETE FROM ${t}`, []);
    }
    for (const [ui, c] of courses.entries()) {
      await db.runAsync('INSERT INTO units (id, title, description, sort_order) VALUES (?, ?, ?, ?)',
        [c.id, c.title, c.description, ui + 1]);
      for (const l of c.lessons) {
        await db.runAsync(
          'INSERT INTO lessons (id, unit_id, title, content, sort_order, estimated_time) VALUES (?, ?, ?, ?, ?, ?)',
          [l.id, c.id, l.title, l.content, l.order, l.estimatedTime]);
      }
      for (const q of c.quizzes) {
        await db.runAsync(
          'INSERT INTO quizzes (id, unit_id, title, time_limit, passing_score, sort_order) VALUES (?, ?, ?, ?, ?, ?)',
          [q.id, c.id, q.title, q.timeLimit, q.passingScore, q.order]);
        for (const [qi, qu] of q.questions.entries()) {
          await db.runAsync(
            'INSERT INTO questions (id, quiz_id, text, question_type, correct_answer_id, explanation, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)',
            [qu.id, q.id, qu.text, qu.questionType, qu.correctAnswerId, qu.explanation, qi + 1]);
          for (const o of qu.options) {
            await db.runAsync('INSERT INTO question_options (id, question_id, text, sort_order) VALUES (?, ?, ?, ?)',
              [o.id, qu.id, o.text, o.order]);
          }
        }
      }
    }
    await setMeta(db, 'content_version', String(CONTENT_VERSION));
  });
}

// ---------------------------------------------------------------------------
// Content with the local user's progress applied

interface UnitRow { id: string; title: string; description: string }
interface LessonRow { id: string; unit_id: string; title: string; content: string; sort_order: number; estimated_time: number }
interface QuizRow { id: string; unit_id: string; title: string; time_limit: number | null; passing_score: number; sort_order: number }
interface QuestionRow { id: string; quiz_id: string; text: string; question_type: 'multiple_choice' | 'true_false'; correct_answer_id: string; explanation: string }
interface OptionRow { id: string; question_id: string; text: string; sort_order: number }

export interface QuizStats {
  bestScore: number | null;
  attempts: number;
  lastScore: number | null;
  averageScore: number | null;
}

export async function loadCourses(db: Db, userId: string): Promise<Course[]> {
  const [units, lessons, quizzes, questions, options, done, stats] = await Promise.all([
    db.getAllAsync<UnitRow>('SELECT id, title, description FROM units ORDER BY sort_order', []),
    db.getAllAsync<LessonRow>('SELECT * FROM lessons ORDER BY sort_order', []),
    db.getAllAsync<QuizRow>('SELECT * FROM quizzes ORDER BY sort_order', []),
    db.getAllAsync<QuestionRow>('SELECT * FROM questions ORDER BY sort_order', []),
    db.getAllAsync<OptionRow>('SELECT * FROM question_options ORDER BY sort_order', []),
    db.getAllAsync<{ lesson_id: string }>('SELECT lesson_id FROM lesson_completions WHERE user_id = ?', [userId]),
    quizStats(db, userId),
  ]);
  const completed = new Set(done.map((d) => d.lesson_id));
  const optsByQ = new Map<string, OptionRow[]>();
  for (const o of options) optsByQ.set(o.question_id, [...(optsByQ.get(o.question_id) ?? []), o]);
  const qsByQuiz = new Map<string, Question[]>();
  for (const q of questions) {
    const opts = (optsByQ.get(q.id) ?? []).map((o) => ({ id: o.id, questionId: q.id, text: o.text, order: o.sort_order }));
    const item: Question = { id: q.id, quizId: q.quiz_id, text: q.text, questionType: q.question_type,
      options: opts, correctAnswerId: q.correct_answer_id, explanation: q.explanation };
    qsByQuiz.set(q.quiz_id, [...(qsByQuiz.get(q.quiz_id) ?? []), item]);
  }
  return units.map((u) => {
    const ls: Lesson[] = lessons.filter((l) => l.unit_id === u.id).map((l) => ({
      id: l.id, unitId: u.id, title: l.title, content: l.content, order: l.sort_order,
      completed: completed.has(l.id), estimatedTime: l.estimated_time }));
    const qz: Quiz[] = quizzes.filter((q) => q.unit_id === u.id).map((q) => ({
      id: q.id, unitId: u.id, title: q.title, questions: qsByQuiz.get(q.id) ?? [],
      timeLimit: q.time_limit, passingScore: q.passing_score, order: q.sort_order }));
    const best = qz.map((q) => stats.get(q.id)?.bestScore ?? 0);
    return {
      id: u.id, title: u.title, description: u.description,
      totalLessons: ls.length, totalQuizzes: qz.length,
      progressPercentage: unitPercent(ls.filter((l) => l.completed).length, ls.length, best, qz.length),
      lessons: ls, quizzes: qz,
    };
  });
}

export async function quizStats(db: Db, userId: string): Promise<Map<string, QuizStats>> {
  const rows = await db.getAllAsync<{ quiz_id: string; best: number; n: number; avg: number }>(
    `SELECT quiz_id, MAX(score) AS best, COUNT(*) AS n, AVG(score) AS avg
       FROM quiz_attempts WHERE user_id = ? AND completed_at IS NOT NULL GROUP BY quiz_id`, [userId]);
  const last = await db.getAllAsync<{ quiz_id: string; score: number }>(
    `SELECT a.quiz_id, a.score FROM quiz_attempts a
      WHERE a.user_id = ? AND a.completed_at = (SELECT MAX(b.completed_at) FROM quiz_attempts b
                                               WHERE b.user_id = a.user_id AND b.quiz_id = a.quiz_id)`, [userId]);
  const lastBy = new Map(last.map((r) => [r.quiz_id, r.score]));
  return new Map(rows.map((r) => [r.quiz_id, {
    bestScore: r.best, attempts: r.n, averageScore: Math.round(r.avg), lastScore: lastBy.get(r.quiz_id) ?? null }]));
}

export function overallFromCourses(courses: Course[]): number {
  return overallPercent(courses.map((c) => c.progressPercentage));
}

// ---------------------------------------------------------------------------
// Writes

export async function touchCourse(db: Db, userId: string, courseId: string): Promise<void> {
  await db.runAsync(
    `INSERT INTO course_access (user_id, course_id, last_accessed_at) VALUES (?, ?, ?)
     ON CONFLICT(user_id, course_id) DO UPDATE SET last_accessed_at = excluded.last_accessed_at`,
    [userId, courseId, nowIso()]);
}

export async function setLessonComplete(db: Db, userId: string, lessonId: string, done: boolean): Promise<void> {
  if (done) {
    await db.runAsync(
      'INSERT OR IGNORE INTO lesson_completions (user_id, lesson_id, completed_at) VALUES (?, ?, ?)',
      [userId, lessonId, nowIso()]);
  } else {
    await db.runAsync('DELETE FROM lesson_completions WHERE user_id = ? AND lesson_id = ?', [userId, lessonId]);
  }
}

export async function startAttempt(db: Db, userId: string, quizId: string, attemptId: string): Promise<void> {
  await db.runAsync('INSERT INTO quiz_attempts (id, user_id, quiz_id, started_at) VALUES (?, ?, ?, ?)',
    [attemptId, userId, quizId, nowIso()]);
}

/** Persist one answer the moment it is submitted. */
export async function saveAnswer(db: Db, attemptId: string, questionId: string, optionId: string,
                                 isCorrect: boolean): Promise<void> {
  await db.runAsync(
    `INSERT INTO attempt_answers (attempt_id, question_id, selected_option_id, is_correct, answered_at)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(attempt_id, question_id) DO UPDATE SET selected_option_id = excluded.selected_option_id,
       is_correct = excluded.is_correct, answered_at = excluded.answered_at`,
    [attemptId, questionId, optionId, isCorrect ? 1 : 0, nowIso()]);
}

export async function finishAttempt(db: Db, attemptId: string, score: number, isPassing: boolean,
                                    timeSpent: number): Promise<void> {
  await db.runAsync(
    'UPDATE quiz_attempts SET completed_at = ?, score = ?, is_passing = ?, time_spent = ? WHERE id = ?',
    [nowIso(), score, isPassing ? 1 : 0, Math.max(0, Math.round(timeSpent)), attemptId]);
}

export async function getAttempts(db: Db, userId: string, quizId?: string): Promise<QuizAttempt[]> {
  const rows = await db.getAllAsync<{ id: string; quiz_id: string; score: number; is_passing: number;
                                      completed_at: string; time_spent: number }>(
    `SELECT id, quiz_id, score, is_passing, completed_at, time_spent FROM quiz_attempts
      WHERE user_id = ? AND completed_at IS NOT NULL ${quizId ? 'AND quiz_id = ?' : ''}
      ORDER BY completed_at DESC`, quizId ? [userId, quizId] : [userId]);
  const answers = await db.getAllAsync<{ attempt_id: string; question_id: string; selected_option_id: string }>(
    `SELECT attempt_id, question_id, selected_option_id FROM attempt_answers
      WHERE attempt_id IN (SELECT id FROM quiz_attempts WHERE user_id = ?)`, [userId]);
  return rows.map((r) => ({
    id: r.id, quizId: r.quiz_id, score: r.score, isPassing: r.is_passing === 1,
    completedAt: r.completed_at, timeSpent: r.time_spent,
    answers: answers.filter((a) => a.attempt_id === r.id)
      .map((a) => ({ questionId: a.question_id, selectedOptionId: a.selected_option_id })),
  }));
}

// ---------------------------------------------------------------------------
// Study time

export async function startStudySession(db: Db, userId: string, sessionId: string, at: Date): Promise<void> {
  const t = at.toISOString();
  await db.runAsync('INSERT INTO study_sessions (id, user_id, started_at, ended_at, seconds) VALUES (?, ?, ?, ?, 0)',
    [sessionId, userId, t, t]);
}

/** Extend a session to `at`. Called periodically and when the app goes to the background. */
export async function touchStudySession(db: Db, sessionId: string, at: Date): Promise<void> {
  await db.runAsync(
    `UPDATE study_sessions SET ended_at = ?,
       seconds = MAX(0, CAST(ROUND((julianday(?) - julianday(started_at)) * 86400) AS INTEGER))
     WHERE id = ?`, [at.toISOString(), at.toISOString(), sessionId]);
}

export async function studySeconds(db: Db, userId: string, since?: Date): Promise<number> {
  const row = await db.getFirstAsync<{ s: number | null }>(
    `SELECT SUM(seconds) AS s FROM study_sessions WHERE user_id = ? ${since ? 'AND started_at >= ?' : ''}`,
    since ? [userId, since.toISOString()] : [userId]);
  return row?.s ?? 0;
}

export async function weeklyStudySeconds(db: Db, userId: string, now: Date): Promise<number> {
  return studySeconds(db, userId, startOfWeek(now));
}

export async function unitStudySummary(db: Db, userId: string, course: Course) {
  const stats = await quizStats(db, userId);
  const perQuiz = course.quizzes.map((q) => ({ quiz: q, stats: stats.get(q.id) ?? null }));
  const scores = perQuiz.flatMap((p) => (p.stats?.averageScore != null ? [p.stats.averageScore] : []));
  const attempts = perQuiz.reduce((n, p) => n + (p.stats?.attempts ?? 0), 0);
  const timeRow = await db.getFirstAsync<{ s: number | null }>(
    `SELECT SUM(time_spent) AS s FROM quiz_attempts
      WHERE user_id = ? AND completed_at IS NOT NULL
        AND quiz_id IN (SELECT id FROM quizzes WHERE unit_id = ?)`, [userId, course.id]);
  return {
    perQuiz,
    attempts,
    averageScore: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null,
    quizSeconds: timeRow?.s ?? 0,
    lessonMinutesCompleted: course.lessons.filter((l) => l.completed)
      .reduce((m, l) => m + l.estimatedTime, 0),
  };
}

// ---------------------------------------------------------------------------
// UserProgress (spec shape) and reset

export async function getUserProgress(db: Db, userId: string, course: Course): Promise<UserProgress> {
  const attempts = (await getAttempts(db, userId)).filter((a) =>
    course.quizzes.some((q) => q.id === a.quizId));
  const access = await db.getFirstAsync<{ last_accessed_at: string }>(
    'SELECT last_accessed_at FROM course_access WHERE user_id = ? AND course_id = ?', [userId, course.id]);
  return {
    userId,
    courseId: course.id,
    lessonsCompleted: course.lessons.filter((l) => l.completed).map((l) => l.id),
    quizAttempts: attempts,
    totalStudyTime: await studySeconds(db, userId),
    lastAccessedAt: access?.last_accessed_at ?? '',
  };
}

export async function resetProgress(db: Db): Promise<void> {
  await db.withTransactionAsync(async () => {
    for (const t of ['attempt_answers', 'quiz_attempts', 'lesson_completions', 'study_sessions', 'course_access']) {
      await db.runAsync(`DELETE FROM ${t}`, []);
    }
  });
}
