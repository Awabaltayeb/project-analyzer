import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.environ.get('DB_PATH', 'projects.db')

def get_conn():
    return sqlite3.connect(DB_PATH)

def setup_db():
    conn = get_conn()
    c = conn.cursor()

    # ========== جدول الدكاترة ==========
    c.execute('''CREATE TABLE IF NOT EXISTS doctors
                 (id       INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT    UNIQUE NOT NULL,
                  password TEXT    NOT NULL,
                  name     TEXT    NOT NULL,
                  slug     TEXT    UNIQUE NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # ========== جدول المشاريع ==========
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id            INTEGER PRIMARY KEY AUTOINCREMENT,
                  doctor_id     INTEGER NOT NULL,
                  team_name     TEXT    NOT NULL,
                  members       TEXT    NOT NULL,
                  project_title TEXT    NOT NULL,
                  status        TEXT    DEFAULT 'تم الاستلام',
                  submitted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(doctor_id) REFERENCES doctors(id))''')

    # ========== جدول الملفات ==========
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id         INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER NOT NULL,
                  file_name  TEXT    NOT NULL,
                  file_path  TEXT    NOT NULL,
                  FOREIGN KEY(project_id) REFERENCES projects(id))''')

    # ========== دكتور افتراضي ==========
    default_pass = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'college2026')
    hashed = generate_password_hash(default_pass)
    c.execute("""INSERT OR IGNORE INTO doctors (username, password, name, slug)
                 VALUES (?, ?, ?, ?)""",
              ('college', hashed, 'الدكتور الافتراضي', 'college'))

    conn.commit()
    conn.close()
    print("✅ قاعدة البيانات جاهزة!")

if __name__ == '__main__':
    setup_db()
