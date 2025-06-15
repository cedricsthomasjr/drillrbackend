import sqlite3
from database import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS quiz_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  format TEXT NOT NULL,
  score INTEGER NOT NULL,
  total INTEGER NOT NULL,
  study_material_excerpt TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

c.execute("""
CREATE TABLE IF NOT EXISTS quiz_questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  quiz_id INTEGER NOT NULL,
  question TEXT NOT NULL,
  options TEXT,
  correct_answer TEXT,
  user_answer TEXT,
  FOREIGN KEY (quiz_id) REFERENCES quiz_history(id) ON DELETE CASCADE
);
""")

conn.commit()
conn.close()
