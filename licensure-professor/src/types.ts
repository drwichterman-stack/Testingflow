/**
 * Data model for The Licensure Professor.
 * Field names follow the app specification. Fields marked "derived" are
 * computed from stored progress, never stored themselves.
 */

export type UUID = string;
export type ISOTimestamp = string;
export type QuestionType = 'multiple_choice' | 'true_false';

export interface Course {
  id: UUID;
  title: string;
  description: string;
  /** Derived: lessons.length */
  totalLessons: number;
  /** Derived: quizzes.length */
  totalQuizzes: number;
  /** Derived, 0-100. See logic/progress.ts */
  progressPercentage: number;
  lessons: Lesson[];
  quizzes: Quiz[];
}

export interface Lesson {
  id: UUID;
  unitId: UUID;
  title: string;
  /** Markdown subset: headings, paragraphs, bullet lists, **bold** */
  content: string;
  order: number;
  /** Derived for the local user */
  completed: boolean;
  /** Minutes */
  estimatedTime: number;
}

export interface Quiz {
  id: UUID;
  unitId: UUID;
  title: string;
  questions: Question[];
  /** Seconds; null = no limit */
  timeLimit: number | null;
  /** Percentage needed to pass, e.g. 70 */
  passingScore: number;
  order: number;
}

export interface Question {
  id: UUID;
  quizId: UUID;
  text: string;
  questionType: QuestionType;
  options: QuestionOption[];
  correctAnswerId: UUID;
  explanation: string;
}

export interface QuestionOption {
  id: UUID;
  questionId: UUID;
  text: string;
  /** A=0, B=1, C=2, D=3 */
  order: number;
}

export interface QuizAnswer {
  questionId: UUID;
  selectedOptionId: UUID;
}

export interface QuizAttempt {
  id: UUID;
  quizId: UUID;
  answers: QuizAnswer[];
  score: number;
  isPassing: boolean;
  completedAt: ISOTimestamp;
  timeSpent: number;
}

export interface UserProgress {
  userId: string;
  courseId: UUID;
  lessonsCompleted: UUID[];
  quizAttempts: QuizAttempt[];
  /** Seconds */
  totalStudyTime: number;
  lastAccessedAt: ISOTimestamp;
}
