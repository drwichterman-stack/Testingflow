import { parseMarkdown } from '../src/components/Markdown';
import { buildCourses, idFor } from '../src/data/content';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe('bundled course content', () => {
  const courses = buildCourses();
  const lessons = courses.flatMap((c) => c.lessons);
  const quizzes = courses.flatMap((c) => c.quizzes);
  const questions = quizzes.flatMap((q) => q.questions);

  it('has the site\'s 6 units, 64 lessons, 102 quizzes, and 1003 questions', () => {
    expect(courses).toHaveLength(6);
    expect(courses[0].title).toBe('Professional Practice & Ethics');
    expect(courses.map((c) => c.lessons.length)).toEqual([12, 11, 17, 4, 15, 5]);
    expect(courses.map((c) => c.quizzes.length)).toEqual([12, 12, 30, 9, 30, 9]);
    expect(lessons).toHaveLength(64);
    expect(quizzes).toHaveLength(102);
    expect(questions).toHaveLength(1003);
  });

  it('uses unique UUID ids and correct foreign keys', () => {
    const ids = [...courses.map((c) => c.id), ...lessons.map((l) => l.id), ...quizzes.map((q) => q.id),
                 ...questions.map((q) => q.id), ...questions.flatMap((q) => q.options.map((o) => o.id))];
    expect(new Set(ids).size).toBe(ids.length);
    ids.forEach((id) => expect(id).toMatch(UUID));
    for (const c of courses) {
      c.lessons.forEach((l) => expect(l.unitId).toBe(c.id));
      c.quizzes.forEach((q) => expect(q.unitId).toBe(c.id));
    }
    for (const q of quizzes) q.questions.forEach((qu) => expect(qu.quizId).toBe(q.id));
  });

  it('every question has a valid correct answer and lettered options', () => {
    for (const q of questions) {
      expect(q.options.map((o) => o.id)).toContain(q.correctAnswerId);
      q.options.forEach((o, i) => { expect(o.order).toBe(i); expect(o.questionId).toBe(q.id); });
      if (q.questionType === 'true_false') expect(q.options.map((o) => o.text)).toEqual(['True', 'False']);
      else expect(q.options.length).toBeGreaterThanOrEqual(3);
      expect(q.options.length).toBeLessThanOrEqual(4);
      expect(q.explanation.length).toBeGreaterThan(10);
    }
  });

  it('includes timed and untimed quizzes with a 70% passing score', () => {
    expect(quizzes.some((q) => q.timeLimit)).toBe(true);
    expect(quizzes.some((q) => q.timeLimit === null)).toBe(true);
    quizzes.forEach((q) => expect(q.passingScore).toBe(70));
  });

  it('ids are stable', () => {
    expect(idFor('ethics')).toBe(idFor('ethics'));
    expect(idFor('ethics')).not.toBe(idFor('assessment'));
  });

  it('lesson markdown parses into headings, paragraphs, and lists', () => {
    const blocks = parseMarkdown(lessons[1].content);
    expect(blocks[0]).toEqual({ kind: 'h1', text: 'The ACA Code of Ethics: structure, purposes and the six moral principles' });
    expect(blocks.some((b) => b.kind === 'ul')).toBe(true);
    expect(blocks.some((b) => b.kind === 'h2')).toBe(true);
  });
});
