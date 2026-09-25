"""Checks for schema/course: SQL loads, example data fits, constraints hold."""
import json
import sqlite3
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema" / "course"


@pytest.fixture
def example():
    return json.loads((SCHEMA_DIR / "example.json").read_text())


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:", isolation_level=None)
    conn.executescript((SCHEMA_DIR / "schema.sql").read_text())
    yield conn
    conn.close()


def load(db, example):
    c, p = example["course"], example["userProgress"]
    db.execute("BEGIN")
    db.execute("INSERT INTO courses VALUES (?, ?, ?)", (c["id"], c["title"], c["description"]))
    for l in c["lessons"]:
        db.execute("INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?)",
                   (l["id"], l["unitId"], l["title"], l["content"], l["order"], l["estimatedTime"]))
    for q in c["quizzes"]:
        db.execute("INSERT INTO quizzes VALUES (?, ?, ?, ?, ?, ?)",
                   (q["id"], q["unitId"], q["title"], q["timeLimit"], q["passingScore"], q["order"]))
        for qu in q["questions"]:
            db.execute("INSERT INTO questions VALUES (?, ?, ?, ?, ?, ?)",
                       (qu["id"], qu["quizId"], qu["text"], qu["questionType"],
                        qu["correctAnswerId"], qu["explanation"]))
            for o in qu["options"]:
                db.execute("INSERT INTO question_options VALUES (?, ?, ?, ?)",
                           (o["id"], o["questionId"], o["text"], o["order"]))
    db.execute("INSERT INTO user_progress VALUES (?, ?, ?, ?)",
               (p["userId"], p["courseId"], p["totalStudyTime"], p["lastAccessedAt"]))
    for lid in p["lessonsCompleted"]:
        db.execute("INSERT INTO lesson_completions VALUES (?, ?, ?)", (p["userId"], p["courseId"], lid))
    for a in p["quizAttempts"]:
        db.execute("INSERT INTO quiz_attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (a["id"], p["userId"], p["courseId"], a["quizId"], a["score"],
                    int(a["isPassing"]), a["completedAt"], a["timeSpent"]))
        for ans in a["answers"]:
            db.execute("INSERT INTO attempt_answers VALUES (?, ?, ?, ?)",
                       (a["id"], a["quizId"], ans["questionId"], ans["selectedOptionId"]))
    db.execute("COMMIT")


def test_json_schema_is_valid_json():
    schema = json.loads((SCHEMA_DIR / "course.schema.json").read_text())
    assert schema["$ref"] == "#/$defs/Course"
    assert {"Course", "Lesson", "Quiz", "Question", "QuestionOption",
            "UserProgress", "QuizAttempt"} <= set(schema["$defs"])


def test_example_matches_json_schema(example):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((SCHEMA_DIR / "course.schema.json").read_text())
    jsonschema.validate(example["course"], schema)
    progress_schema = {**schema, "$ref": "#/$defs/UserProgress"}
    jsonschema.validate(example["userProgress"], progress_schema)


def test_example_cross_field_rules(example):
    c = example["course"]
    assert c["totalLessons"] == len(c["lessons"])
    assert c["totalQuizzes"] == len(c["quizzes"])
    for q in c["quizzes"]:
        for qu in q["questions"]:
            assert qu["correctAnswerId"] in {o["id"] for o in qu["options"]}


def test_example_loads_and_views_derive_fields(db, example):
    load(db, example)
    c, p = example["course"], example["userProgress"]
    assert db.execute("SELECT total_lessons, total_quizzes FROM v_course_summary WHERE id = ?",
                      (c["id"],)).fetchone() == (c["totalLessons"], c["totalQuizzes"])
    pct = db.execute("SELECT progress_percentage FROM v_user_course_progress WHERE user_id = ?",
                     (p["userId"],)).fetchone()[0]
    assert pct == pytest.approx(c["progressPercentage"], abs=0.01)
    status = dict(db.execute("SELECT lesson_id, completed FROM v_user_lesson_status"))
    assert status == {l["id"]: int(l["completed"]) for l in c["lessons"]}


def test_correct_answer_must_be_own_option(db, example):
    load(db, example)
    q1, q2 = example["course"]["quizzes"][0]["questions"]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE questions SET correct_answer_id = ? WHERE id = ?",
                   (q2["options"][0]["id"], q1["id"]))


def test_true_false_rejects_third_option(db, example):
    load(db, example)
    tf = example["course"]["quizzes"][0]["questions"][1]
    with pytest.raises(sqlite3.IntegrityError, match="true_false"):
        db.execute("INSERT INTO question_options VALUES ('x', ?, 'Maybe', 2)", (tf["id"],))


def test_is_passing_must_match_score(db, example):
    load(db, example)
    p = example["userProgress"]
    with pytest.raises(sqlite3.IntegrityError, match="is_passing"):
        db.execute("INSERT INTO quiz_attempts VALUES ('bad', ?, ?, ?, 90, 0, '2026-09-22T00:00:00Z', 60)",
                   (p["userId"], p["courseId"], p["quizAttempts"][0]["quizId"]))


def test_answer_option_must_belong_to_question(db, example):
    load(db, example)
    q1, q2 = example["course"]["quizzes"][0]["questions"]
    attempt = example["userProgress"]["quizAttempts"][0]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE attempt_answers SET selected_option_id = ? "
                   "WHERE attempt_id = ? AND question_id = ?",
                   (q2["options"][0]["id"], attempt["id"], q1["id"]))
