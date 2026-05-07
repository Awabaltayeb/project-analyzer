import sqlite3
import os

def setup_db():
    # التأكد من وجود مجلد للقاعدة
    db_path = 'projects.db'
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # جدول المشاريع
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  team_name TEXT NOT NULL,
                  members TEXT NOT NULL,
                  project_title TEXT NOT NULL,
                  status TEXT DEFAULT 'تم الاستلام',
                  submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # جدول الملفات
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER,
                  file_name TEXT NOT NULL,
                  file_path TEXT NOT NULL,
                  FOREIGN KEY(project_id) REFERENCES projects(id))''')

    # جدول الدكتور
    c.execute('''CREATE TABLE IF NOT EXISTS admin
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')

    # إضافة دكتور افتراضي (إذا لم يكن موجودًا)
    c.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)",
              ('college', 'college2026'))

    conn.commit()
    conn.close()
    print("✅ قاعدة البيانات جاهزة!")

if __name__ == '__main__':
    setup_db()
