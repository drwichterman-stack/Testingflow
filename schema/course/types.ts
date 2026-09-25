/**
 * Course, quiz, and progress data model.
 *
 * Field names match the specification exactly. Companion files:
 *   course.schema.json  JSON Schema (draft 2020-12) for the same shapes
 *   schema.sql          SQLite storage schema, with views for derived fields
 *
 * Fields marked "derived" are computed, not stored. See README.md.
 */

/** RFC 4122 UUID string, e.g. "3f2b8c1e-9d4a-4e6b-8f0a-1c2d3e4f5a6b". */
export type UUID = string;

/** ISO 8601 timestamp with time zone, e.g. "2026-09-25T14:00:00Z". */
export type ISOTimestamp = string;

export type QuestionType = "multiple_choice" | "true_false";

export interface Course {
  id: UUID;
  /** e.g. "Unit 1: Assessment" */
  title: string;
  description: string;
  /** Derived: lessons.length. */
  totalLessons: number;
  /** Derived: quizzes.length. */
  totalQuizzes: number;
  /** Derived, 0 to 100, for the current user. See README.md for the formula. */
  progressPercentage: number;
  lessons: Lesson[];
  quizzes: Quiz[];
}

export interface Lesson {
  id: UUID;
  /** Foreign key to Course.id. */
  unitId: UUID;
  title: string;
  /** HTML or Markdown. */
  content: string;
  order: number;
  /** Derived, for the current user: id is in UserProgress.lessonsCompleted. */
  completed: boolean;
  /** Minutes. */
  estimatedTime: number;
}

export interface Quiz {
  id: UUID;
  /** Foreign key to Course.id. */
  unitId: UUID;
  title: string;
  questions: Question[];
  /** Seconds; null means no limit. */
  timeLimit: number | null;
  /** Percentage, 0 to 100, e.g. 70. */
  passingScore: number;
  order: number;
}

export interface Question {
  id: UUID;
  /** Foreign key to Quiz.id. */
  quizId: UUID;
  text: string;
  questionType: QuestionType;
  /** 2 options for true_false; 2 to 4 for multiple_choice. */
  options: QuestionOption[];
  /** Must equal the id of one entry in this question's options. */
  correctAnswerId: UUID;
  explanation: string;
}

export interface QuestionOption {
  id: UUID;
  /** Foreign key to Question.id. */
  questionId: UUID;
  text: string;
  /** A=0, B=1, C=2, D=3. */
  order: 0 | 1 | 2 | 3;
}

export interface UserProgress {
  /** Local device ID, not cloud-based. Not necessarily a UUID. */
  userId: string;
  /** Foreign key to Course.id. */
  courseId: UUID;
  /** Lesson ids; each must belong to courseId. */
  lessonsCompleted: UUID[];
  quizAttempts: QuizAttempt[];
  /** Seconds. */
  totalStudyTime: number;
  lastAccessedAt: ISOTimestamp;
}

export interface QuizAnswer {
  questionId: UUID;
  selectedOptionId: UUID;
}

export interface QuizAttempt {
  id: UUID;
  /** Foreign key to Quiz.id; the quiz must belong to UserProgress.courseId. */
  quizId: UUID;
  /** At most one answer per question. */
  answers: QuizAnswer[];
  /** Percentage, 0 to 100. */
  score: number;
  /** score >= the quiz's passingScore. */
  isPassing: boolean;
  completedAt: ISOTimestamp;
  /** Seconds. */
  timeSpent: number;
}

/** Letter label for an option order: 0 -> "A" ... 3 -> "D". */
export function optionLetter(order: QuestionOption["order"]): "A" | "B" | "C" | "D" {
  return (["A", "B", "C", "D"] as const)[order];
}
