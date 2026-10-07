import { buildCourses, CONTENT_VERSION } from '../src/data/content';
import * as repo from '../src/db/repo';
import { createTestDb, newId } from './helpers/testDb';

async function setup() {
  const db = createTestDb();
  const userId = await repo.initDatabase(db, newId);
  return { db, userId };
}

describe('database', () => {
  it('seeds bundled content and creates a local user id once', async () => {
    const { db, userId } = await setup();
    const courses = await repo.loadCourses(db, userId);
    expect(courses.map((c) => c.title)).toEqual(buildCourses().map((c) => c.title));
    expect(courses.flatMap((c) => c.quizzes.flatMap((q) => q.questions)).length).toBe(1003);
    expect(await repo.initDatabase(db, newId)).toBe(userId);
  });

  it('persists lesson completion immediately and updates unit progress', async () => {
    const { db, userId } = await setup();
    const [unit] = await repo.loadCourses(db, userId);
    await repo.setLessonComplete(db, userId, unit.lessons[0].id, true);
    await repo.setLessonComplete(db, userId, unit.lessons[0].id, true); // idempotent
    const after = (await repo.loadCourses(db, userId))[0];
    expect(after.lessons[0].completed).toBe(true);
    expect(after.progressPercentage).toBe(4); // 1/12 lessons * 50 = 4.2 -> 4
    await repo.setLessonComplete(db, userId, unit.lessons[0].id, false);
    expect((await repo.loadCourses(db, userId))[0].lessons[0].completed).toBe(false);
  });

  it('saves each answer on submit and scores completed attempts', async () => {
    const { db, userId } = await setup();
    const quiz = (await repo.loadCourses(db, userId))[0].quizzes[0];
    const a = newId();
    await repo.startAttempt(db, userId, quiz.id, a);
    await repo.saveAnswer(db, a, quiz.questions[0].id, quiz.questions[0].correctAnswerId, true);
    const saved = await db.getAllAsync('SELECT * FROM attempt_answers WHERE attempt_id = ?', [a]);
    expect(saved).toHaveLength(1);
    // An unfinished attempt does not count.
    expect((await repo.quizStats(db, userId)).get(quiz.id)).toBeUndefined();
    await repo.finishAttempt(db, a, 80, true, 95.6);
    const b = newId();
    await repo.startAttempt(db, userId, quiz.id, b);
    await repo.finishAttempt(db, b, 60, false, 50);
    const s = (await repo.quizStats(db, userId)).get(quiz.id)!;
    expect(s).toMatchObject({ bestScore: 80, attempts: 2, averageScore: 70 });
    const attempts = await repo.getAttempts(db, userId, quiz.id);
    expect(attempts).toHaveLength(2);
    expect(attempts.find((x) => x.id === a)).toMatchObject({ score: 80, isPassing: true, timeSpent: 96 });
    expect(attempts.find((x) => x.id === a)!.answers).toHaveLength(1);
    // Unit: 0 lessons; quiz bests 80 and 11 not taken -> avg 6.67 * 0.5 = 3.3
    expect((await repo.loadCourses(db, userId))[0].progressPercentage).toBe(3);
  });

  it('re-seeding content keeps progress', async () => {
    const { db, userId } = await setup();
    const unit = (await repo.loadCourses(db, userId))[0];
    await repo.setLessonComplete(db, userId, unit.lessons[1].id, true);
    await db.runAsync("UPDATE meta SET value = '0' WHERE key = 'content_version'", []);
    await repo.initDatabase(db, newId);
    expect(await db.getFirstAsync("SELECT value FROM meta WHERE key = 'content_version'", []))
      .toEqual({ value: String(CONTENT_VERSION) });
    expect((await repo.loadCourses(db, userId))[0].lessons[1].completed).toBe(true);
  });

  it('tracks study time per session and per week', async () => {
    const { db, userId } = await setup();
    const now = new Date(2026, 8, 24, 10, 0); // Thu
    await repo.startStudySession(db, userId, 's1', new Date(now.getTime() - 3600_000));
    await repo.touchStudySession(db, 's1', new Date(now.getTime() - 1800_000)); // 30 min
    await repo.startStudySession(db, userId, 's0', new Date(2026, 8, 14, 9, 0)); // last week
    await repo.touchStudySession(db, 's0', new Date(2026, 8, 14, 10, 0));
    expect(await repo.weeklyStudySeconds(db, userId, now)).toBe(1800);
    expect(await repo.studySeconds(db, userId)).toBe(1800 + 3600);
  });

  it('builds the spec UserProgress shape and resets progress', async () => {
    const { db, userId } = await setup();
    let unit = (await repo.loadCourses(db, userId))[0];
    await repo.setLessonComplete(db, userId, unit.lessons[0].id, true);
    await repo.touchCourse(db, userId, unit.id);
    unit = (await repo.loadCourses(db, userId))[0];
    const p = await repo.getUserProgress(db, userId, unit);
    expect(p).toMatchObject({ userId, courseId: unit.id, lessonsCompleted: [unit.lessons[0].id], quizAttempts: [] });
    expect(p.lastAccessedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    await repo.resetProgress(db);
    expect((await repo.loadCourses(db, userId))[0].lessons[0].completed).toBe(false);
  });
});
