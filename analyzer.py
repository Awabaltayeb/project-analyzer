import os
import ast
import sqlite3

def analyze_python_file(filepath):
    """تحليل ملف بايثون وإرجاع إحصائيات"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        lines = len(content.splitlines())
        
        return {
            'functions': len(functions),
            'function_names': [f.name for f in functions],
            'classes': len(classes),
            'class_names': [c.name for c in classes],
            'imports': len(imports),
            'lines': lines,
            'has_errors': False
        }
    except SyntaxError:
        return {
            'functions': 0,
            'function_names': [],
            'classes': 0,
            'class_names': [],
            'imports': 0,
            'lines': 0,
            'has_errors': True
        }
    except Exception:
        return None

def analyze_pdf_file(filepath):
    """تحليل ملف PDF وإرجاع عدد الصفحات"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        return {'pages': len(reader.pages)}
    except:
        return None

def analyze_docx_file(filepath):
    """تحليل ملف Word وإرجاع عدد الفقرات"""
    try:
        from docx import Document
        doc = Document(filepath)
        paragraphs = len(doc.paragraphs)
        return {'paragraphs': paragraphs}
    except:
        return None

def analyze_project(project_id):
    """تحليل مشروع كامل وإرجاع تقرير"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    # جلب معلومات المشروع
    c.execute("SELECT * FROM projects WHERE id=?", (project_id,))
    project = c.fetchone()
    
    # جلب الملفات
    c.execute("SELECT * FROM files WHERE project_id=?", (project_id,))
    files = c.fetchall()
    conn.close()
    
    if not project:
        return None
    
    total_lines = 0
    total_functions = 0
    total_classes = 0
    all_functions = []
    all_classes = []
    python_files = 0
    pdf_pages = 0
    docx_paragraphs = 0
    other_files = 0
    has_errors = False
    
    for f in files:
        filepath = f[3]
        filename = f[2]
        
        if filename.endswith('.py'):
            result = analyze_python_file(filepath)
            if result:
                python_files += 1
                total_lines += result['lines']
                total_functions += result['functions']
                total_classes += result['classes']
                all_functions.extend(result['function_names'])
                all_classes.extend(result['class_names'])
                if result['has_errors']:
                    has_errors = True
        
        elif filename.endswith('.pdf'):
            result = analyze_pdf_file(filepath)
            if result:
                pdf_pages += result['pages']
        
        elif filename.endswith('.docx'):
            result = analyze_docx_file(filepath)
            if result:
                docx_paragraphs += result['paragraphs']
        
        else:
            other_files += 1
    
    # حساب نسبة الجاهزية التقريبية
    readiness = 100
    if python_files == 0:
        readiness -= 30
    if total_functions < 5:
        readiness -= 20
    if total_classes < 1:
        readiness -= 15
    if pdf_pages == 0 and docx_paragraphs == 0:
        readiness -= 20
    if has_errors:
        readiness -= 30
    
    readiness = max(readiness, 10)  # لا تقل عن 10%
    
    # اقتراح سؤال ذكي
    suggested_question = ""
    if all_functions:
        main_func = max(all_functions, key=len) if all_functions else "رئيسية"
        suggested_question = f"كيف تعمل دالة '{main_func}' وما دورها في النظام؟"
    elif all_classes:
        main_class = all_classes[0]
        suggested_question = f"اشرح تصميم كلاس '{main_class}' وعلاقته ببقية النظام."
    else:
        suggested_question = "ما هي أبرز تحديات المشروع وكيف تغلبت عليها؟"
    
    report = {
        'project': project,
        'python_files': python_files,
        'total_lines': total_lines,
        'total_functions': total_functions,
        'total_classes': total_classes,
        'all_functions': all_functions[:5],  # أهم 5
        'all_classes': all_classes[:5],
        'pdf_pages': pdf_pages,
        'docx_paragraphs': docx_paragraphs,
        'other_files': other_files,
        'readiness': readiness,
        'has_errors': has_errors,
        'suggested_question': suggested_question,
        'files': files
    }
    
    return report