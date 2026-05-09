import os
import secrets
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database import setup_db, get_conn

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

ALLOWED_EXTENSIONS = {'.py', '.pdf', '.docx', '.txt', '.zip', '.ipynb'}

def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

# ══════════════════════════════════════════════════════
# القوالب
# ══════════════════════════════════════════════════════

BASE_STYLE = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8;
         min-height: 100vh; display: flex; justify-content: center;
         align-items: center; padding: 20px; }
  .card { background: white; border-radius: 16px;
          box-shadow: 0 4px 24px rgba(0,0,0,.1); padding: 40px; width: 100%;
          max-width: 480px; }
  h2 { color: #1a73e8; margin-bottom: 8px; }
  p.sub { color: #777; margin-bottom: 24px; font-size: 14px; }
  input, select { width: 100%; padding: 12px; margin: 6px 0 14px;
                  border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
  input:focus { outline: none; border-color: #1a73e8; }
  .btn { background: #1a73e8; color: white; border: none; padding: 13px;
         width: 100%; border-radius: 8px; font-size: 15px; cursor: pointer;
         margin-top: 6px; transition: background .2s; }
  .btn:hover { background: #1557b0; }
  .btn-sm { padding: 7px 16px; font-size: 13px; width: auto; border-radius: 6px; }
  .btn-red { background: #dc3545; }
  .btn-red:hover { background: #b02a37; }
  .btn-gray { background: #6c757d; }
  .btn-gray:hover { background: #5a6268; }
  .msg-ok  { color: #155724; background: #d4edda; padding: 10px 14px;
              border-radius: 8px; margin-bottom: 14px; }
  .msg-err { color: #721c24; background: #f8d7da; padding: 10px 14px;
              border-radius: 8px; margin-bottom: 14px; }
  a.quiet { color: #999; font-size: 13px; text-decoration: none;
            display: block; margin-top: 16px; text-align: center; }
  a.quiet:hover { text-decoration: underline; }
  label { font-size: 13px; color: #555; display: block; margin-bottom: 4px; }
</style>
"""

# ── صفحة رفع الطالب ──────────────────────────────────
STUDENT_PAGE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <title>تسليم المشروع — {{ doctor_name }}</title>
  """ + BASE_STYLE + """
</head>
<body>
<div class="card">
  <h2>📤 تسليم المشروع</h2>
  <p class="sub">{{ doctor_name }} — أدخل بيانات فريقك وارفع الملفات</p>

  {% if success %}
    <div class="msg-ok">✅ تم استلام مشروعك بنجاح!</div>
  {% endif %}
  {% if error %}
    <div class="msg-err">❌ {{ error }}</div>
  {% endif %}

  <form method="POST" enctype="multipart/form-data">
    <label>اسم الفريق</label>
    <input type="text" name="team_name" placeholder="مثال: الفريق الأول" required>
    <label>أسماء الأعضاء (مفصولة بفاصلة)</label>
    <input type="text" name="members" placeholder="أحمد، سارة، محمد" required>
    <label>عنوان المشروع</label>
    <input type="text" name="project_title" placeholder="نظام إدارة..." required>
    <label>📎 ملفات المشروع (py, pdf, docx, zip)</label>
    <input type="file" name="files" multiple required style="border:none;padding:8px 0;">
    <button type="submit" class="btn">📨 تسليم المشروع</button>
  </form>
  <a href="/admin/login" class="quiet">🔒 دخول الدكتور</a>
</div>
</body>
</html>
"""

# ── تسجيل دخول الدكتور ───────────────────────────────
ADMIN_LOGIN = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <title>دخول الدكتور</title>
  """ + BASE_STYLE + """
</head>
<body>
<div class="card">
  <h2>🔐 دخول الدكتور</h2>
  <p class="sub">أدخل بيانات حسابك للمتابعة</p>

  {% if error %}<div class="msg-err">{{ error }}</div>{% endif %}

  <form method="POST">
    <label>اسم المستخدم</label>
    <input type="text" name="username" required>
    <label>كلمة المرور</label>
    <input type="password" name="password" required>
    <button type="submit" class="btn">دخول</button>
  </form>
  <a href="/" class="quiet">⬅️ العودة للرئيسية</a>
</div>
</body>
</html>
"""

# ── إنشاء حساب دكتور جديد ────────────────────────────
REGISTER_PAGE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <title>إنشاء حساب دكتور</title>
  """ + BASE_STYLE + """
</head>
<body>
<div class="card" style="max-width:520px">
  <h2>➕ حساب دكتور جديد</h2>
  <p class="sub">بعد الإنشاء ستحصل على رابط تسليم خاص بك</p>

  {% if error %}<div class="msg-err">{{ error }}</div>{% endif %}

  <form method="POST">
    <label>الاسم الكامل للدكتور</label>
    <input type="text" name="name" placeholder="د. أحمد محمد" required>
    <label>اسم المستخدم (إنجليزي بدون مسافات)</label>
    <input type="text" name="username" placeholder="dr_ahmed" required>
    <label>كلمة المرور</label>
    <input type="password" name="password" required>
    <button type="submit" class="btn">إنشاء الحساب</button>
  </form>
  <a href="/admin/login" class="quiet">← العودة لتسجيل الدخول</a>
</div>
</body>
</html>
"""

# ── لوحة التحكم ───────────────────────────────────────
DASHBOARD = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <title>لوحة التحكم — {{ doctor.name }}</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; }
    .topbar { background: #1a73e8; color: white; padding: 14px 28px;
              display: flex; justify-content: space-between; align-items: center; }
    .topbar h1 { font-size: 18px; }
    .topbar .right { display: flex; gap: 12px; align-items: center; font-size: 14px; }
    .topbar a { color: white; text-decoration: none; padding: 6px 14px;
                border-radius: 6px; border: 1px solid rgba(255,255,255,.4); }
    .topbar a:hover { background: rgba(255,255,255,.15); }
    .container { max-width: 900px; margin: 30px auto; padding: 0 20px; }
    .info-box { background: #e8f0fe; border-radius: 12px; padding: 16px 20px;
                margin-bottom: 24px; font-size: 14px; color: #333; }
    .info-box strong { color: #1a73e8; }
    .info-box code { background: #d2e3fc; padding: 3px 8px; border-radius: 5px;
                     font-size: 13px; user-select: all; }
    .card { background: white; border-radius: 14px; padding: 24px;
            box-shadow: 0 2px 12px rgba(0,0,0,.08); }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 12px 14px; text-align: right; border-bottom: 1px solid #eee; }
    th { background: #f8f9fa; color: #555; font-size: 13px; font-weight: 600; }
    tr:last-child td { border: none; }
    tr:hover td { background: #f8f9fa; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 20px;
             font-size: 12px; background: #d4edda; color: #155724; }
    .btn { display: inline-block; padding: 7px 16px; border-radius: 6px;
           background: #1a73e8; color: white; text-decoration: none;
           font-size: 13px; border: none; cursor: pointer; }
    .btn:hover { background: #1557b0; }
    .empty { text-align: center; color: #aaa; padding: 40px; }
  </style>
</head>
<body>
<div class="topbar">
  <h1>📋 المشاريع المستلمة</h1>
  <div class="right">
    <span>👤 {{ doctor.name }}</span>
    <a href="/admin/logout">خروج</a>
  </div>
</div>

<div class="container">
  <div class="info-box">
    🔗 رابط التسليم الخاص بك:
    <code>{{ base_url }}/submit/{{ doctor.slug }}</code>
    — شارك هذا الرابط مع طلابك فقط.
  </div>

  <div class="card">
    {% if projects %}
    <table>
      <tr>
        <th>#</th><th>الفريق</th><th>المشروع</th>
        <th>تاريخ التسليم</th><th>الحالة</th><th>تقرير</th>
      </tr>
      {% for p in projects %}
      <tr>
        <td>{{ loop.index }}</td>
        <td><strong>{{ p[2] }}</strong></td>
        <td>{{ p[4] }}</td>
        <td style="font-size:13px;color:#888;">{{ p[6][:16] }}</td>
        <td><span class="badge">{{ p[5] }}</span></td>
        <td><a href="/admin/report/{{ p[0] }}" class="btn">📊 عرض</a></td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <div class="empty">📭 لا توجد مشاريع مستلمة بعد.</div>
    {% endif %}
  </div>
</div>
</body>
</html>
"""

# ── صفحة التقرير ─────────────────────────────────────
REPORT_PAGE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <title>تقرير المشروع</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; padding: 24px; }
    .container { max-width: 760px; margin: auto; }
    h2 { color: #1a73e8; margin-bottom: 20px; text-align: center; }
    .section { background: white; border-radius: 14px; padding: 22px 26px;
               margin-bottom: 18px; box-shadow: 0 2px 10px rgba(0,0,0,.07); }
    .section h3 { font-size: 15px; color: #444; margin-bottom: 14px;
                  border-bottom: 1px solid #eee; padding-bottom: 8px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .stat { background: #f8f9fa; border-radius: 10px; padding: 12px 16px; }
    .stat .val { font-size: 22px; font-weight: bold; color: #1a73e8; }
    .stat .lbl { font-size: 12px; color: #777; margin-top: 2px; }
    .badge { display: inline-block; padding: 5px 12px; border-radius: 20px;
             font-size: 13px; margin: 3px; }
    .green  { background: #d4edda; color: #155724; }
    .yellow { background: #fff3cd; color: #856404; }
    .red    { background: #f8d7da; color: #721c24; }
    .blue   { background: #cce5ff; color: #004085; }
    .purple { background: #e2d9f3; color: #4a235a; }
    .question { background: #e8f0fe; padding: 16px 20px; border-radius: 12px;
                border-right: 4px solid #1a73e8; font-size: 15px; line-height: 1.7; }
    .back { display: inline-block; background: #6c757d; color: white;
            padding: 9px 20px; border-radius: 8px; text-decoration: none;
            font-size: 14px; margin-bottom: 20px; }
    .back:hover { background: #5a6268; }
    .readiness-bar { background: #eee; border-radius: 8px; height: 14px;
                     overflow: hidden; margin-top: 8px; }
    .readiness-fill { height: 100%; border-radius: 8px; transition: width .6s; }
  </style>
</head>
<body>
<div class="container">
  <a href="/admin/dashboard" class="back">⬅️ لوحة التحكم</a>
  <h2>📊 تقرير المشروع</h2>

  <!-- معلومات الفريق -->
  <div class="section">
    <h3>👥 معلومات الفريق</h3>
    <p><strong>الفريق:</strong> {{ r.project[2] }}</p>
    <p style="margin-top:8px"><strong>الأعضاء:</strong> {{ r.project[3] }}</p>
    <p style="margin-top:8px"><strong>المشروع:</strong> {{ r.project[4] }}</p>
    <p style="margin-top:8px;font-size:13px;color:#888;">
      <strong>التسليم:</strong> {{ r.project[6][:16] }}
    </p>
  </div>

  <!-- إحصائيات الكود -->
  {% if r.python_files > 0 %}
  <div class="section">
    <h3>🐍 إحصائيات Python</h3>
    <div class="grid">
      <div class="stat"><div class="val">{{ r.python_files }}</div><div class="lbl">ملفات Python</div></div>
      <div class="stat"><div class="val">{{ r.total_lines }}</div><div class="lbl">إجمالي الأسطر</div></div>
      <div class="stat"><div class="val">{{ r.total_functions }}</div><div class="lbl">الدوال</div></div>
      <div class="stat"><div class="val">{{ r.total_classes }}</div><div class="lbl">الكلاسات</div></div>
    </div>
    {% if r.total_comments > 0 %}
    <p style="margin-top:12px;font-size:13px;color:#555;">
      💬 عدد أسطر التعليقات: <strong>{{ r.total_comments }}</strong>
    </p>
    {% endif %}

    {% if r.all_functions %}
    <div style="margin-top:14px">
      <strong style="font-size:13px;">أبرز الدوال:</strong><br>
      {% for fn in r.all_functions %}
        <span class="badge green">{{ fn }}</span>
      {% endfor %}
    </div>
    {% endif %}

    {% if r.all_classes %}
    <div style="margin-top:10px">
      <strong style="font-size:13px;">الكلاسات:</strong><br>
      {% for cls in r.all_classes %}
        <span class="badge yellow">{{ cls }}</span>
      {% endfor %}
    </div>
    {% endif %}

    {% if r.libraries %}
    <div style="margin-top:10px">
      <strong style="font-size:13px;">المكتبات المستخدمة:</strong><br>
      {% for lib in r.libraries %}
        <span class="badge blue">{{ lib }}</span>
      {% endfor %}
    </div>
    {% endif %}

    {% if r.patterns %}
    <div style="margin-top:10px">
      <strong style="font-size:13px;">أنماط البرمجة:</strong><br>
      {% for pat in r.patterns %}
        <span class="badge purple">{{ pat }}</span>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endif %}

  <!-- إحصائيات PDF -->
  {% if r.pdf_pages > 0 %}
  <div class="section">
    <h3>📄 ملف PDF</h3>
    <div class="grid">
      <div class="stat"><div class="val">{{ r.pdf_pages }}</div><div class="lbl">صفحات</div></div>
      <div class="stat"><div class="val">{{ r.pdf_words }}</div><div class="lbl">كلمة تقريباً</div></div>
    </div>
    {% if r.pdf_has_images %}
    <p style="margin-top:10px;font-size:13px;color:#155724;">✅ يحتوي على صور ومخططات</p>
    {% endif %}
  </div>
  {% endif %}

  <!-- إحصائيات Word -->
  {% if r.docx_paragraphs > 0 %}
  <div class="section">
    <h3>📝 ملف Word</h3>
    <div class="grid">
      <div class="stat"><div class="val">{{ r.docx_paragraphs }}</div><div class="lbl">فقرة</div></div>
      <div class="stat"><div class="val">{{ r.docx_words }}</div><div class="lbl">كلمة</div></div>
    </div>
    {% if r.docx_tables > 0 %}
    <p style="margin-top:10px;font-size:13px;color:#004085;">📊 يحتوي على {{ r.docx_tables }} جدول</p>
    {% endif %}
    {% if r.docx_headings %}
    <div style="margin-top:10px">
      <strong style="font-size:13px;">أقسام التقرير:</strong><br>
      {% for h in r.docx_headings %}
        <span class="badge blue">{{ h }}</span>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endif %}

  <!-- نسبة الجاهزية -->
  <div class="section">
    <h3>📈 نسبة الجاهزية</h3>
    <div class="readiness-bar">
      <div class="readiness-fill" style="
        width: {{ r.readiness }}%;
        background: {% if r.readiness >= 80 %}#28a745{% elif r.readiness >= 50 %}#ffc107{% else %}#dc3545{% endif %};
      "></div>
    </div>
    <p style="margin-top:10px">
      {% if r.readiness >= 80 %}
        <span class="badge green">{{ r.readiness }}% — جاهز للمناقشة ✅</span>
      {% elif r.readiness >= 50 %}
        <span class="badge yellow">{{ r.readiness }}% — يحتاج تحسينات ⚠️</span>
      {% else %}
        <span class="badge red">{{ r.readiness }}% — غير مكتمل ❌</span>
      {% endif %}
    </p>
  </div>

  <!-- سؤال المناقشة -->
  <div class="section">
    <h3>💬 سؤال مقترح للمناقشة</h3>
    <div class="question">{{ r.suggested_question }}</div>
  </div>

</div>
</body>
</html>
"""

# ══════════════════════════════════════════════════════
# المسارات
# ══════════════════════════════════════════════════════

def current_doctor():
    """إرجاع بيانات الدكتور المسجّل دخوله أو None"""
    doc_id = session.get('doctor_id')
    if not doc_id:
        return None
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM doctors WHERE id=?", (doc_id,))
    doc = c.fetchone()
    conn.close()
    return doc


# ── صفحة رفع الطالب (عامة) ───────────────────────────
@app.route('/')
def index():
    return redirect('/admin/login')


@app.route('/submit/<slug>', methods=['GET', 'POST'])
def student_upload(slug):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM doctors WHERE slug=?", (slug,))
    doctor = c.fetchone()
    conn.close()

    if not doctor:
        abort(404)

    success = False
    error   = None

    if request.method == 'POST':
        try:
            team_name     = request.form['team_name'].strip()
            members       = request.form['members'].strip()
            project_title = request.form['project_title'].strip()
            files         = request.files.getlist('files')

            if not files or all(f.filename == '' for f in files):
                error = "لم يتم اختيار أي ملف."
            else:
                conn = get_conn()
                c    = conn.cursor()
                c.execute("""INSERT INTO projects (doctor_id, team_name, members, project_title)
                             VALUES (?, ?, ?, ?)""",
                          (doctor[0], team_name, members, project_title))
                project_id = c.lastrowid

                folder = os.path.join('uploads', f'doc_{doctor[0]}', f'project_{project_id}')
                os.makedirs(folder, exist_ok=True)

                for file in files:
                    if file.filename and allowed_file(file.filename):
                        filepath = os.path.join(folder, file.filename)
                        file.save(filepath)
                        c.execute("""INSERT INTO files (project_id, file_name, file_path)
                                     VALUES (?, ?, ?)""",
                                  (project_id, file.filename, filepath))

                conn.commit()
                conn.close()
                success = True
        except Exception as e:
            error = f"حدث خطأ: {str(e)}"

    return render_template_string(
        STUDENT_PAGE,
        doctor_name=doctor[3],
        success=success,
        error=error
    )


# ── تسجيل دخول ────────────────────────────────────────
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_conn()
        c    = conn.cursor()
        c.execute("SELECT * FROM doctors WHERE username=?", (username,))
        doc = c.fetchone()
        conn.close()

        if doc and check_password_hash(doc[2], password):
            session['doctor_id'] = doc[0]
            return redirect('/admin/dashboard')
        else:
            error = '❌ اسم المستخدم أو كلمة المرور غير صحيحة.'

    return render_template_string(ADMIN_LOGIN, error=error)


# ── إنشاء حساب دكتور ──────────────────────────────────
@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    error = None
    if request.method == 'POST':
        name     = request.form['name'].strip()
        username = request.form['username'].strip().lower().replace(' ', '_')
        password = request.form['password']

        if len(password) < 6:
            error = "كلمة المرور يجب أن تكون 6 أحرف على الأقل."
        else:
            slug   = username
            hashed = generate_password_hash(password)
            try:
                conn = get_conn()
                c    = conn.cursor()
                c.execute("""INSERT INTO doctors (username, password, name, slug)
                             VALUES (?, ?, ?, ?)""",
                          (username, hashed, name, slug))
                conn.commit()
                doc_id = c.lastrowid
                conn.close()
                session['doctor_id'] = doc_id
                return redirect('/admin/dashboard')
            except sqlite3.IntegrityError:
                error = "اسم المستخدم موجود مسبقاً، اختر اسماً آخر."

    return render_template_string(REGISTER_PAGE, error=error)


# ── لوحة التحكم ───────────────────────────────────────
@app.route('/admin/dashboard')
def admin_dashboard():
    doc = current_doctor()
    if not doc:
        return redirect('/admin/login')

    conn = get_conn()
    c    = conn.cursor()
    c.execute("""SELECT * FROM projects WHERE doctor_id=?
                 ORDER BY submitted_at DESC""", (doc[0],))
    projects = c.fetchall()
    conn.close()

    base_url = request.host_url.rstrip('/')
    return render_template_string(DASHBOARD, doctor=_doc_obj(doc),
                                  projects=projects, base_url=base_url)


# ── التقرير ───────────────────────────────────────────
@app.route('/admin/report/<int:project_id>')
def admin_report(project_id):
    doc = current_doctor()
    if not doc:
        return redirect('/admin/login')

    # التحقق أن المشروع يخص هذا الدكتور فقط
    conn = get_conn()
    c    = conn.cursor()
    c.execute("SELECT doctor_id FROM projects WHERE id=?", (project_id,))
    row = c.fetchone()
    conn.close()

    if not row or row[0] != doc[0]:
        abort(403)

    from analyzer import analyze_project
    report = analyze_project(project_id)
    if not report:
        abort(404)

    return render_template_string(REPORT_PAGE, r=report)


# ── تسجيل الخروج ──────────────────────────────────────
@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')


# ── مساعد ─────────────────────────────────────────────
def _doc_obj(row):
    """تحويل tuple قاعدة البيانات إلى object بسيط"""
    class D: pass
    d = D()
    d.id, d.username, d.password, d.name, d.slug = row[0], row[1], row[2], row[3], row[4]
    return d


# ══════════════════════════════════════════════════════
if __name__ == '__main__':
    setup_db()
    os.makedirs('uploads', exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
