import sqlite3
import json
from datetime import datetime
from database import get_db_connection

def save_quiz_history(format, score, total, excerpt, questions):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO quiz_history (format, score, total, study_material_excerpt, timestamp) VALUES (?, ?, ?, ?, ?)",
        (format, score, total, excerpt[:250], datetime.utcnow()),
    )
    quiz_id = cur.lastrowid

    for q in questions:
        cur.execute(
            "INSERT INTO quiz_questions (quiz_id, question, options, correct_answer, user_answer) VALUES (?, ?, ?, ?, ?)",
            (
                quiz_id,
                q["question"],
                json.dumps(q.get("options")),
                q["answer"],
                q.get("user_answer"),
            ),
        )

    conn.commit()
    conn.close()
    return quiz_id

def get_all_quizzes():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM quiz_history ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_quiz_questions(quiz_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM quiz_questions WHERE quiz_id = ?", (quiz_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
