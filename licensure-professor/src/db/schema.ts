/**
 * SQLite schema. Content tables are replaced when the bundled content
 * version changes. Progress tables do not reference content with foreign
 * keys, so re-seeding content never deletes a user's progress.
 */
export const SCHEMA_VERSION = 1;

export const SCHEMA_SQL = `
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Content (bundled with the app) ------------------------------------------
CREATE TABLE IF NOT EXISTS units (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  sort_order  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS lessons (
  id             TEXT PRIMARY KEY,
  unit_id        TEXT NOT NULL REFERENCES units (id) ON DELETE CASCADE,
  title          TEXT NOT NULL,
  content        TEXT NOT NULL,
  sort_order     INTEGER NOT NULL,
  estimated_time INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quizzes (
  id            TEXT PRIMARY KEY,
  unit_id       TEXT NOT NULL REFERENCES units (id) ON DELETE CASCADE,
  title         TEXT NOT NULL,
  time_limit    INTEGER CHECK (time_limit IS NULL OR time_limit > 0),
  passing_score REAL NOT NULL CHECK (passing_score BETWEEN 0 AND 100),
  sort_order    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
  id                TEXT PRIMARY KEY,
  quiz_id           TEXT NOT NULL REFERENCES quizzes (id) ON DELETE CASCADE,
  text              TEXT NOT NULL,
  question_type     TEXT NOT NULL CHECK (question_type IN ('multiple_choice', 'true_false')),
  correct_answer_id TEXT NOT NULL,
  explanation       TEXT NOT NULL DEFAULT '',
  sort_order        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS question_options (
  id          TEXT PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  sort_order  INTEGER NOT NULL CHECK (sort_order BETWEEN 0 AND 3)
);

-- Progress (local device only) ---------------------------------------------
CREATE TABLE IF NOT EXISTS lesson_completions (
  user_id      TEXT NOT NULL,
  lesson_id    TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY (user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
  id           TEXT PRIMARY KEY,
  user_id      TEXT NOT NULL,
  quiz_id      TEXT NOT NULL,
  started_at   TEXT NOT NULL,
  completed_at TEXT,                 -- NULL while in progress or abandoned
  score        REAL CHECK (score IS NULL OR score BETWEEN 0 AND 100),
  is_passing   INTEGER CHECK (is_passing IS NULL OR is_passing IN (0, 1)),
  time_spent   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_attempts_user_quiz ON quiz_attempts (user_id, quiz_id);

CREATE TABLE IF NOT EXISTS attempt_answers (
  attempt_id         TEXT NOT NULL REFERENCES quiz_attempts (id) ON DELETE CASCADE,
  question_id        TEXT NOT NULL,
  selected_option_id TEXT NOT NULL,
  is_correct         INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
  answered_at        TEXT NOT NULL,
  PRIMARY KEY (attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS study_sessions (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at   TEXT NOT NULL,
  seconds    INTEGER NOT NULL DEFAULT 0 CHECK (seconds >= 0)
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_start ON study_sessions (user_id, started_at);

CREATE TABLE IF NOT EXISTS course_access (
  user_id          TEXT NOT NULL,
  course_id        TEXT NOT NULL,
  last_accessed_at TEXT NOT NULL,
  PRIMARY KEY (user_id, course_id)
);
`;
