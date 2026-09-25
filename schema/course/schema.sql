-- Course, quiz, and progress storage schema (SQLite).
--
-- Mirrors types.ts and course.schema.json. Column names are snake_case;
-- "order" is a reserved word, so it is stored as sort_order.
--
-- Derived fields are not stored. They come from views:
--   Course.totalLessons, Course.totalQuizzes  -> v_course_summary
--   Course.progressPercentage                 -> v_user_course_progress
--   Lesson.completed                          -> v_user_lesson_status
--
-- Timestamps are ISO 8601 text. Booleans are 0/1 integers.

PRAGMA foreign_keys = ON;

-- Course (the specification's "unit": Lesson.unitId and Quiz.unitId point here).
CREATE TABLE IF NOT EXISTS courses (
    id           TEXT PRIMARY KEY,               -- UUID
    title        TEXT NOT NULL CHECK (length(title) > 0),
    description  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS lessons (
    id              TEXT PRIMARY KEY,            -- UUID
    unit_id         TEXT NOT NULL REFERENCES courses (id) ON DELETE CASCADE,
    title           TEXT NOT NULL CHECK (length(title) > 0),
    content         TEXT NOT NULL DEFAULT '',    -- HTML or Markdown
    sort_order      INTEGER NOT NULL CHECK (sort_order >= 0),
    estimated_time  INTEGER NOT NULL DEFAULT 0 CHECK (estimated_time >= 0),  -- minutes
    UNIQUE (unit_id, sort_order),
    UNIQUE (id, unit_id)                         -- target for composite foreign keys
);

CREATE TABLE IF NOT EXISTS quizzes (
    id             TEXT PRIMARY KEY,             -- UUID
    unit_id        TEXT NOT NULL REFERENCES courses (id) ON DELETE CASCADE,
    title          TEXT NOT NULL CHECK (length(title) > 0),
    time_limit     INTEGER CHECK (time_limit IS NULL OR time_limit > 0),  -- seconds; NULL = no limit
    passing_score  REAL NOT NULL CHECK (passing_score BETWEEN 0 AND 100),
    sort_order     INTEGER NOT NULL CHECK (sort_order >= 0),
    UNIQUE (unit_id, sort_order),
    UNIQUE (id, unit_id)
);

-- questions and question_options reference each other (correct answer), so
-- both foreign keys are deferred: insert a question and its options in one
-- transaction, in either order.
CREATE TABLE IF NOT EXISTS questions (
    id                 TEXT PRIMARY KEY,         -- UUID
    quiz_id            TEXT NOT NULL REFERENCES quizzes (id) ON DELETE CASCADE,
    text               TEXT NOT NULL CHECK (length(text) > 0),
    question_type      TEXT NOT NULL CHECK (question_type IN ('multiple_choice', 'true_false')),
    correct_answer_id  TEXT NOT NULL,
    explanation        TEXT NOT NULL DEFAULT '',
    UNIQUE (id, quiz_id),
    -- The correct answer must be an option of this same question.
    FOREIGN KEY (correct_answer_id, id)
        REFERENCES question_options (id, question_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS question_options (
    id           TEXT PRIMARY KEY,               -- UUID
    question_id  TEXT NOT NULL
                 REFERENCES questions (id) ON DELETE CASCADE
                 DEFERRABLE INITIALLY DEFERRED,
    text         TEXT NOT NULL CHECK (length(text) > 0),
    sort_order   INTEGER NOT NULL CHECK (sort_order BETWEEN 0 AND 3),  -- A=0 .. D=3
    UNIQUE (question_id, sort_order),            -- also caps options at 4
    UNIQUE (id, question_id)
);

-- true_false questions use orders 0 and 1 only (so at most 2 options).
CREATE TRIGGER IF NOT EXISTS trg_true_false_option_insert
BEFORE INSERT ON question_options
WHEN NEW.sort_order > 1
 AND (SELECT question_type FROM questions WHERE id = NEW.question_id) = 'true_false'
BEGIN
    SELECT RAISE(ABORT, 'true_false questions allow option orders 0 and 1 only');
END;

CREATE TRIGGER IF NOT EXISTS trg_true_false_option_update
BEFORE UPDATE OF sort_order, question_id ON question_options
WHEN NEW.sort_order > 1
 AND (SELECT question_type FROM questions WHERE id = NEW.question_id) = 'true_false'
BEGIN
    SELECT RAISE(ABORT, 'true_false questions allow option orders 0 and 1 only');
END;

CREATE TRIGGER IF NOT EXISTS trg_true_false_question_type
BEFORE UPDATE OF question_type ON questions
WHEN NEW.question_type = 'true_false'
 AND EXISTS (SELECT 1 FROM question_options WHERE question_id = NEW.id AND sort_order > 1)
BEGIN
    SELECT RAISE(ABORT, 'question has options beyond B; cannot become true_false');
END;

-- UserProgress: one row per (local device user, course).
CREATE TABLE IF NOT EXISTS user_progress (
    user_id           TEXT NOT NULL CHECK (length(user_id) > 0),  -- local device ID
    course_id         TEXT NOT NULL REFERENCES courses (id) ON DELETE CASCADE,
    total_study_time  INTEGER NOT NULL DEFAULT 0 CHECK (total_study_time >= 0),  -- seconds
    last_accessed_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, course_id)
);

-- UserProgress.lessonsCompleted. The lesson must belong to the course.
CREATE TABLE IF NOT EXISTS lesson_completions (
    user_id    TEXT NOT NULL,
    course_id  TEXT NOT NULL,
    lesson_id  TEXT NOT NULL,
    PRIMARY KEY (user_id, course_id, lesson_id),
    FOREIGN KEY (user_id, course_id)
        REFERENCES user_progress (user_id, course_id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id, course_id)
        REFERENCES lessons (id, unit_id) ON DELETE CASCADE
);

-- UserProgress.quizAttempts. The quiz must belong to the course.
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id            TEXT PRIMARY KEY,              -- UUID
    user_id       TEXT NOT NULL,
    course_id     TEXT NOT NULL,
    quiz_id       TEXT NOT NULL,
    score         REAL NOT NULL CHECK (score BETWEEN 0 AND 100),
    is_passing    INTEGER NOT NULL CHECK (is_passing IN (0, 1)),
    completed_at  TEXT NOT NULL,
    time_spent    INTEGER NOT NULL CHECK (time_spent >= 0),  -- seconds
    UNIQUE (id, quiz_id),
    FOREIGN KEY (user_id, course_id)
        REFERENCES user_progress (user_id, course_id) ON DELETE CASCADE,
    FOREIGN KEY (quiz_id, course_id)
        REFERENCES quizzes (id, unit_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts (user_id, course_id, quiz_id);

-- is_passing must agree with the quiz's passing score.
CREATE TRIGGER IF NOT EXISTS trg_attempt_passing_insert
BEFORE INSERT ON quiz_attempts
WHEN NEW.is_passing <> (NEW.score >= (SELECT passing_score FROM quizzes WHERE id = NEW.quiz_id))
BEGIN
    SELECT RAISE(ABORT, 'is_passing does not match score >= passing_score');
END;

CREATE TRIGGER IF NOT EXISTS trg_attempt_passing_update
BEFORE UPDATE OF score, is_passing, quiz_id ON quiz_attempts
WHEN NEW.is_passing <> (NEW.score >= (SELECT passing_score FROM quizzes WHERE id = NEW.quiz_id))
BEGIN
    SELECT RAISE(ABORT, 'is_passing does not match score >= passing_score');
END;

-- QuizAttempt.answers. The question must belong to the attempt's quiz, and
-- the selected option must belong to the question. One answer per question.
CREATE TABLE IF NOT EXISTS attempt_answers (
    attempt_id          TEXT NOT NULL,
    quiz_id             TEXT NOT NULL,
    question_id         TEXT NOT NULL,
    selected_option_id  TEXT NOT NULL,
    PRIMARY KEY (attempt_id, question_id),
    FOREIGN KEY (attempt_id, quiz_id)
        REFERENCES quiz_attempts (id, quiz_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id, quiz_id)
        REFERENCES questions (id, quiz_id) ON DELETE CASCADE,
    FOREIGN KEY (selected_option_id, question_id)
        REFERENCES question_options (id, question_id) ON DELETE CASCADE
);

-- Course.totalLessons and Course.totalQuizzes.
CREATE VIEW IF NOT EXISTS v_course_summary AS
SELECT c.id,
       c.title,
       c.description,
       (SELECT COUNT(*) FROM lessons l WHERE l.unit_id = c.id) AS total_lessons,
       (SELECT COUNT(*) FROM quizzes q WHERE q.unit_id = c.id) AS total_quizzes
FROM courses c;

-- Lesson.completed, per user.
CREATE VIEW IF NOT EXISTS v_user_lesson_status AS
SELECT up.user_id,
       l.unit_id AS course_id,
       l.id      AS lesson_id,
       EXISTS (SELECT 1 FROM lesson_completions lc
               WHERE lc.user_id = up.user_id
                 AND lc.course_id = l.unit_id
                 AND lc.lesson_id = l.id) AS completed
FROM user_progress up
JOIN lessons l ON l.unit_id = up.course_id;

-- Course.progressPercentage, per user:
--   100 * (lessons completed + quizzes passed at least once)
--       / (total lessons + total quizzes)
-- 0 when the course has no lessons or quizzes.
CREATE VIEW IF NOT EXISTS v_user_course_progress AS
SELECT up.user_id,
       up.course_id,
       s.total_lessons,
       s.total_quizzes,
       (SELECT COUNT(*) FROM lesson_completions lc
        WHERE lc.user_id = up.user_id AND lc.course_id = up.course_id) AS lessons_completed,
       (SELECT COUNT(DISTINCT qa.quiz_id) FROM quiz_attempts qa
        WHERE qa.user_id = up.user_id AND qa.course_id = up.course_id
          AND qa.is_passing = 1) AS quizzes_passed,
       CASE WHEN s.total_lessons + s.total_quizzes = 0 THEN 0.0
            ELSE 100.0 * (
                (SELECT COUNT(*) FROM lesson_completions lc
                 WHERE lc.user_id = up.user_id AND lc.course_id = up.course_id)
              + (SELECT COUNT(DISTINCT qa.quiz_id) FROM quiz_attempts qa
                 WHERE qa.user_id = up.user_id AND qa.course_id = up.course_id
                   AND qa.is_passing = 1)
            ) / (s.total_lessons + s.total_quizzes)
       END AS progress_percentage
FROM user_progress up
JOIN v_course_summary s ON s.id = up.course_id;
