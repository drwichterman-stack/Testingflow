# Course and quiz data model

Types and storage schema for courses, lessons, quizzes, and on-device progress. This folder is standalone; nothing in `clinassess/` uses it yet.

| File | Contents |
|---|---|
| `types.ts` | TypeScript interfaces; field names match the specification exactly |
| `course.schema.json` | JSON Schema (draft 2020-12). Root validates a `Course`; other entities are under `$defs` (for example `#/$defs/UserProgress`) |
| `schema.sql` | SQLite tables, integrity triggers, and views for derived fields |
| `example.json` | One course and one user's progress, valid against all three |

Tests: `tests/test_course_schema.py` loads `schema.sql`, inserts `example.json`, checks the derived views, and checks that bad data is rejected. JSON Schema validation runs when the `jsonschema` package is installed and is skipped otherwise.

## Design decisions

- **`unitId` points to `Course.id`.** The specification calls the parent a "unit" in foreign keys and a "course" elsewhere. The name is kept as given; there is no separate Unit entity.
- **Derived fields are not stored.** `totalLessons`, `totalQuizzes`, `progressPercentage`, and `Lesson.completed` are computed. Storing them would let them drift out of sync. `Lesson.completed` and `progressPercentage` are also per user, while lessons and courses are shared content, so they cannot live on those rows.
- **`progressPercentage` formula (assumption).** The specification says "calculated" without a formula. This schema uses:
  `100 × (lessons completed + quizzes passed at least once) ÷ (total lessons + total quizzes)`, or 0 for an empty course. Change `v_user_course_progress` if lessons alone should count.
- **`order` becomes `sort_order` in SQL** because `ORDER` is a reserved word. Orders are unique within their parent.
- **Option limits.** `QuestionOption.order` is 0 to 3 (A to D), so a question has at most 4 options. `true_false` questions allow orders 0 and 1 only.
- **Scores are percentages (0 to 100) stored as REAL,** so values such as 66.67 are allowed.
- **`userId` is a local device ID,** so it is a non-empty string, not a UUID.

## Rules enforced by the SQL schema

| Rule | Mechanism |
|---|---|
| `correctAnswerId` is an option of the same question | Composite foreign key, deferred (questions and options reference each other; insert both in one transaction) |
| A completed lesson belongs to the progress record's course | Composite foreign key on `(lesson_id, course_id)` |
| An attempted quiz belongs to the progress record's course | Composite foreign key on `(quiz_id, course_id)` |
| Each answer's question belongs to the attempt's quiz, and its option belongs to that question | Composite foreign keys on `attempt_answers` |
| One answer per question per attempt | Primary key `(attempt_id, question_id)` |
| `isPassing` equals `score >= passingScore` | Triggers on insert and update |
| `true_false` has at most options A and B | Triggers on options and on question type changes |
| An option that is some question's correct answer cannot be deleted | Foreign key with no cascade |

## Rules JSON Schema cannot express

Check these in application code when accepting JSON:

- `totalLessons == lessons.length` and `totalQuizzes == quizzes.length`
- `correctAnswerId` matches one of the question's `options[].id`
- Each child's `unitId`, `quizId`, or `questionId` equals its parent's `id`
- `order` values are unique within a parent
- `isPassing` agrees with `score` and the quiz's `passingScore`
- Every `lessonsCompleted` id and attempt `quizId` belongs to `courseId`

## Not in the specification

- A minimum of 2 options per question is enforced in JSON Schema but not in SQL (SQLite has no clean way to check a row count at commit).
- There is no field saying whether `Lesson.content` is HTML or Markdown. Add a `contentFormat: "html" | "markdown"` field if the renderer needs to know.
