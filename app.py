import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, session

app = Flask(__name__)
app.secret_key = 'super_secret_key_2024'

# ========== إنشاء قاعدة البيانات ==========
def setup_db():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  team_name TEXT NOT NULL,
                  members TEXT NOT NULL,
                  project_title TEXT NOT NULL,
                  status TEXT DEFAULT 'تم الاستلام',
                  submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER,
                  file_name TEXT NOT NULL,
                  file_path TEXT NOT NULL,
                  FOREIGN KEY(project_id) REFERENCES projects(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS admin
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')

    c.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)",
              ('college', 'college2026'))

    conn.commit()
    conn.close()
    print("✅ قاعدة البيانات جاهزة!")

# ========== واجهة رفع الطالب ==========
STUDENT_PAGE = '''
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title> Systems Analysis and Design Course </title>
    <title>تسليم المشروع النهائي</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f4f8; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 450px; text-align: center; }
        h2 { color: #1a73e8; margin-bottom: 10px; }
        p { color: #666; margin-bottom: 20px; }
        input, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 14px; }
        button { background: #1a73e8; color: white; border: none; padding: 14px; width: 100%; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background: #1557b0; }
        .success { color: green; font-weight: bold; }
        .error { color: red; font-weight: bold; }
        .admin-link { display: block; margin-top: 20px; color: #999; font-size: 13px; text-decoration: none; }
        .admin-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h2> تسليم المشروع </h2>
        <p>أدخل بيانات الفريق وارفع ملفات المشروع</p>
        {% if success %}
            <p class="success">✅ تم استلام المشروع بنجاح!</p>
        {% endif %}
        {% if error %}
            <p class="error">❌ {{ error }}</p>
        {% endif %}
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="team_name" placeholder="اسم الفريق" required>
            <input type="text" name="members" placeholder="أسماء الأعضاء (مفصولة بفاصلة)" required>
            <input type="text" name="project_title" placeholder="عنوان المشروع" required>
            <label style="display:block; text-align:right; margin-top:10px; color:#555;">📎 ملفات المشروع:</label>
            <input type="file" name="files" multiple required style="border:none; padding:10px 0;">
            <button type="submit"> تسليم المشروع</button>
        </form>
        <a href="/admin/login" class="admin-link"> دخول الدكتور</a>
    </div>
</body>
</html>
'''

# ========== صفحة تسجيل دخول الدكتور ==========
ADMIN_LOGIN = '''
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>دخول الدكتور</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f4f8; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 350px; text-align: center; }
        h2 { color: #1a73e8; margin-bottom: 20px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 14px; }
        button { background: #1a73e8; color: white; border: none; padding: 14px; width: 100%; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background: #1557b0; }
        .error { color: red; margin-bottom: 10px; }
        .back-link { display: block; margin-top: 20px; color: #999; font-size: 13px; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2> دخول الدكتور</h2>
        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول</button>
        </form>
        <a href="/" class="back-link"> العودة للرئيسية</a>
    </div>
</body>
</html>
'''

# ========== لوحة تحكم الدكتور ==========
ADMIN_DASHBOARD = '''
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>لوحة التحكم</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f4f8; padding: 30px; }
        .container { max-width: 800px; margin: auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        h2 { color: #1a73e8; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: center; }
        th { background: #1a73e8; color: white; }
        tr:hover { background: #f5f5f5; }
        .btn { background: #1a73e8; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 14px; }
        .btn:hover { background: #1557b0; }
        .logout { float: left; color: red; text-decoration: none; margin-bottom: 20px; }
        p.empty { text-align: center; color: #999; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/admin/logout" class="logout"> خروج</a>
        <h2> المشاريع المستلمة</h2>
        {% if projects %}
        <table>
            <tr><th>#</th><th>الفريق</th><th>المشروع</th><th>الحالة</th><th>تقرير</th></tr>
            {% for p in projects %}
            <tr>
                <td>{{ p[0] }}</td>
                <td>{{ p[1] }}</td>
                <td>{{ p[3] }}</td>
                <td>{{ p[4] }}</td>
                <td><a href="/admin/report/{{ p[0] }}" class="btn"> عرض</a></td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p class="empty"> لا توجد مشاريع مستلمة بعد.</p>
        {% endif %}
    </div>
</body>
</html>
'''

# ========== صفحة تقرير المشروع ==========
REPORT_PAGE = '''
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تقرير المشروع</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f4f8; padding: 20px; }
        .container { max-width: 700px; margin: auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        h2 { color: #1a73e8; text-align: center; }
        .section { background: #f9f9f9; padding: 15px; border-radius: 10px; margin: 15px 0; }
        .section h3 { color: #333; margin-top: 0; }
        .badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 14px; margin: 3px; }
        .green { background: #d4edda; color: #155724; }
        .yellow { background: #fff3cd; color: #856404; }
        .red { background: #f8d7da; color: #721c24; }
        .question { background: #e8f0fe; padding: 15px; border-radius: 10px; border-right: 4px solid #1a73e8; margin: 15px 0; }
        .back-btn { display: inline-block; background: #666; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; margin-top: 20px; }
        .back-btn:hover { background: #444; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/admin/dashboard" class="back-btn">⬅️ العودة للوحة التحكم</a>
        <h2> تقرير المشروع</h2>
        <div class="section">
            <h3> معلومات أساسية</h3>
            <p><strong>الفريق:</strong> {{ report.project[1] }}</p>
            <p><strong>الأعضاء:</strong> {{ report.project[2] }}</p>
            <p><strong>عنوان المشروع:</strong> {{ report.project[3] }}</p>
            <p><strong>تاريخ التسليم:</strong> {{ report.project[5] }}</p>
        </div>
        <div class="section">
            <h3> إحصائيات الكود</h3>
            <p> ملفات Python: <strong>{{ report.python_files }}</strong></p>
            <p> إجمالي الأسطر: <strong>{{ report.total_lines }}</strong></p>
            <p> الدوال: <strong>{{ report.total_functions }}</strong></p>
            <p> الكلاسات: <strong>{{ report.total_classes }}</strong></p>
            <p> صفحات PDF: <strong>{{ report.pdf_pages }}</strong></p>
            <p> فقرات Word: <strong>{{ report.docx_paragraphs }}</strong></p>
        </div>
        <div class="section">
            <h3> أهم الدوال</h3>
            {% if report.all_functions %}
                {% for func in report.all_functions %}
                    <span class="badge green">{{ func }}</span>
                {% endfor %}
            {% else %}
                <p style="color:#999;">لا توجد دوال</p>
            {% endif %}
        </div>
        <div class="section">
            <h3> أهم الكلاسات</h3>
            {% if report.all_classes %}
                {% for cls in report.all_classes %}
                    <span class="badge yellow">{{ cls }}</span>
                {% endfor %}
            {% else %}
                <p style="color:#999;">لا توجد كلاسات</p>
            {% endif %}
        </div>
        <div class="section">
            <h3> نسبة الجاهزية: 
                {% if report.readiness >= 80 %}
                    <span class="badge green">{{ report.readiness }}% - جاهز للمناقشة</span>
                {% elif report.readiness >= 50 %}
                    <span class="badge yellow">{{ report.readiness }}% - يحتاج تحسينات</span>
                {% else %}
                    <span class="badge red">{{ report.readiness }}% - غير مكتمل</span>
                {% endif %}
            </h3>
        </div>
        <div class="question">
            <strong> سؤال مقترح للمناقشة:</strong>
            <p>{{ report.suggested_question }}</p>
        </div>
    </div>
</body>
</html>
'''

# ========== المسارات ==========

@app.route('/', methods=['GET', 'POST'])
def student_upload():
    success = False
    error = None
    if request.method == 'POST':
        try:
            team_name = request.form['team_name']
            members = request.form['members']
            project_title = request.form['project_title']
            files = request.files.getlist('files')

            if not files or len(files) == 0:
                error = "لم يتم اختيار أي ملف."
            else:
                conn = sqlite3.connect('projects.db')
                c = conn.cursor()
                c.execute("INSERT INTO projects (team_name, members, project_title) VALUES (?, ?, ?)",
                          (team_name, members, project_title))
                project_id = c.lastrowid

                folder = f'uploads/project_{project_id}'
                os.makedirs(folder, exist_ok=True)

                for file in files:
                    if file.filename:
                        filepath = os.path.join(folder, file.filename)
                        file.save(filepath)
                        c.execute("INSERT INTO files (project_id, file_name, file_path) VALUES (?, ?, ?)",
                                  (project_id, file.filename, filepath))

                conn.commit()
                conn.close()
                success = True
        except Exception as e:
            error = f"حدث خطأ: {str(e)}"

    return render_template_string(STUDENT_PAGE, success=success, error=error)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('projects.db')
        c = conn.cursor()
        c.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
        admin = c.fetchone()
        conn.close()

        if admin:
            session['admin_logged_in'] = True
            return redirect('/admin/dashboard')
        else:
            error = '❌ اسم المستخدم أو كلمة المرور غير صحيحة.'

    return render_template_string(ADMIN_LOGIN, error=error)


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')

    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects ORDER BY submitted_at DESC")
    projects = c.fetchall()
    conn.close()

    return render_template_string(ADMIN_DASHBOARD, projects=projects)


@app.route('/admin/report/<int:project_id>')
def admin_report(project_id):
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    from analyzer import analyze_project
    report = analyze_project(project_id)
    
    if not report:
        return "المشروع غير موجود", 404
    
    return render_template_string(REPORT_PAGE, report=report)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/')
@app.route('/reset-db')
def reset_db():
    """تفريغ جميع الجداول"""
    try:
        conn = sqlite3.connect('projects.db')
        c = conn.cursor()
        
        # تفريغ الجداول
        c.execute("DELETE FROM files")
        c.execute("DELETE FROM projects")
        # لا تحذف جدول admin حتى لا تفقد بيانات الدخول
        
        conn.commit()
        conn.close()
        
        # حذف مجلد uploads
        import shutil
        if os.path.exists('uploads'):
            shutil.rmtree('uploads')
        os.makedirs('uploads', exist_ok=True)
        
        return "✅ تم تفريغ جميع المشاريع والملفات بنجاح!"
    except Exception as e:
        return f"❌ خطأ: {str(e)}"
# ========== تشغيل ==========
if __name__ == '__main__':
    setup_db()
    os.makedirs('uploads', exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
