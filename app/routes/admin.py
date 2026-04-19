from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.database import get_db
from app.utils.auth import login_required_check
import subprocess
import sys
from app.services.face_service import face_service as face_engine

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def check_admin():
    if not login_required_check('admin'):
        return redirect(url_for('auth.login'))

@admin_bp.route('/')
def dashboard():
    db = get_db()
    students = db.execute("""
        SELECT s.*, fe.status as face_status 
        FROM students s
        LEFT JOIN face_encodings fe ON s.student_id = fe.student_id
        ORDER BY s.name
    """).fetchall()
    subjects = db.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    teachers = db.execute("SELECT * FROM users WHERE role='teacher' ORDER BY name").fetchall()
    
    assignments = db.execute("""
        SELECT ts.id as assignment_id, s.name as subject_name, s.course_code, 
               ts.assigned_class, u.name as teacher_name
        FROM teacher_subjects ts
        JOIN subjects s ON ts.subject_id = s.subject_id
        JOIN users u ON ts.teacher_id = u.id
        ORDER BY s.course_code, ts.assigned_class
    """).fetchall()
    timetable = db.execute("""
        SELECT t.id, s.name as subject_name, s.course_code,
               t.day_of_week, t.start_time, t.end_time,
               u.name as teacher_name
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.subject_id
        LEFT JOIN teacher_subjects ts ON ts.subject_id = s.subject_id
        LEFT JOIN users u ON u.id = ts.teacher_id
        ORDER BY t.day_of_week, t.start_time
    """).fetchall()

    overrides = db.execute("""
        SELECT o.id, s.name as subject_name, s.course_code,
               o.override_date, o.override_type, o.new_start_time, o.new_end_time
        FROM timetable_overrides o
        JOIN subjects s ON o.subject_id = s.subject_id
        ORDER BY o.override_date DESC
    """).fetchall()

    attendance_summary = db.execute("""
        SELECT s.name as subject_name, s.course_code,
               COUNT(a.id) as total_records,
               SUM(CASE WHEN a.verified = 1 THEN 1 ELSE 0 END) as verified_count
        FROM subjects s
        LEFT JOIN attendance a ON a.subject_id = s.subject_id
        GROUP BY s.subject_id
    """).fetchall()

    db.close()
    return render_template('admin_dashboard.html',
                           students=students,
                           subjects=subjects,
                           teachers=teachers,
                           assignments=assignments,
                           timetable=timetable,
                           overrides=overrides,
                           attendance_summary=attendance_summary)

from app.utils.auth import hash_password

@admin_bp.route('/add_student', methods=['POST'])
def add_student():
    name = request.form.get('name', '').strip()
    roll_number = request.form.get('roll_number', '').strip()
    student_class = request.form.get('student_class', '').strip()
    department = request.form.get('department', '').strip()
    semester = request.form.get('semester', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not all([name, roll_number, student_class, department, semester, email, password]):
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.dashboard'))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'student')",
            (name, email, hash_password(password))
        )
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        db.execute(
            "INSERT INTO students (student_id, name, roll_number, class, department, semester, email) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, roll_number, student_class, department, semester, email)
        )
        
        # Initialize face_encodings as 'pending'
        db.execute(
            "INSERT INTO face_encodings (student_id, status) VALUES (?, 'pending')",
            (user_id,)
        )
        
        db.commit()
        flash(f'Student "{name}" added successfully! Now complete mandatory Face Enrollment.', 'success')
        return redirect(url_for('admin.enroll_student_face', student_id=user_id))
        
    except Exception as e:
        db.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))
    finally:
        db.close()

@admin_bp.route('/remove_student/<int:student_id>', methods=['POST'])
def remove_student(student_id):
    db = get_db()
    try:
        db.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        db.execute("DELETE FROM users WHERE id = ?", (student_id,))
        db.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        db.commit()
        flash('Student removed successfully.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        db.close()

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form.get('name', '').strip()
    course_code = request.form.get('course_code', '').strip()

    if not all([name, course_code]):
        flash('Subject name and course code are required.', 'error')
        return redirect(url_for('admin.dashboard'))

    db = get_db()
    try:
        db.execute("INSERT INTO subjects (name, course_code) VALUES (?, ?)", (name, course_code))
        db.commit()
        flash(f'Subject "{name}" added successfully!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error adding subject: {str(e)}', 'error')
    finally:
        db.close()

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/assign_teacher', methods=['POST'])
def assign_teacher():
    teacher_id = request.form.get('teacher_id')
    subject_id = request.form.get('subject_id')
    assigned_class = request.form.get('assigned_class', 'All').strip()

    db = get_db()
    try:
        db.execute("INSERT INTO teacher_subjects (teacher_id, subject_id, assigned_class) VALUES (?, ?, ?)",
                   (teacher_id, subject_id, assigned_class))
        db.commit()
        flash('Teacher assigned successfully!', 'success')
    except Exception as e:
        db.rollback()
        flash('Assignment failed: Check if this combination already exists.', 'error')
    finally:
        db.close()

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/remove_assignment/<int:assignment_id>', methods=['POST'])
def remove_assignment(assignment_id):
    db = get_db()
    db.execute("DELETE FROM teacher_subjects WHERE id = ?", (assignment_id,))
    db.commit()
    db.close()
    flash('Assignment removed successfully.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/add_teacher', methods=['POST'])
def add_teacher():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    if not all([name, email, password]):
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    db = get_db()
    try:
        db.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'teacher')",
                   (name, email, hash_password(password)))
        db.commit()
        flash('Teacher added successfully.', 'success')
    except Exception as e:
        db.rollback()
        flash('Email might already exist.', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/toggle_teacher/<int:teacher_id>', methods=['POST'])
def toggle_teacher(teacher_id):
    db = get_db()
    teacher = db.execute("SELECT is_active FROM users WHERE id = ?", (teacher_id,)).fetchone()
    if teacher:
        new_status = 0 if teacher['is_active'] == 1 else 1
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, teacher_id))
        db.commit()
        flash('Teacher status updated.', 'success')
    db.close()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_teacher/<int:teacher_id>', methods=['POST'])
def delete_teacher(teacher_id):
    db = get_db()
    
    # Check dependencies (attendance linked to this teacher via their subjects and dates)
    # Wait, Attendance only links student_id and subject_id, not teacher_id.
    # Assignments (teacher_subjects) link them. We just drop assignments, because attendance is independent of teacher directly.
    # To truly see if a teacher has "historical records", we'd check assignments if they supervised any verified lectures.
    # Safest is to check if this teacher is in teacher_subjects.
    has_assignments = db.execute("SELECT id FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,)).fetchone()
    if has_assignments:
        flash('Cannot delete teacher with active historical assignments. Deactivate them instead.', 'error')
    else:
        db.execute("DELETE FROM users WHERE id = ?", (teacher_id,))
        db.commit()
        flash('Teacher permanently deleted.', 'success')
    db.close()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/add_timetable', methods=['POST'])
def add_timetable():
    subject_id = request.form.get('subject_id')
    day_of_week = request.form.get('day_of_week')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    if not all([subject_id, day_of_week, start_time, end_time]):
        flash('All timetable fields are required.', 'error')
        return redirect(url_for('admin.dashboard'))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO timetable (subject_id, day_of_week, start_time, end_time) VALUES (?, ?, ?, ?)",
            (subject_id, day_of_week, start_time, end_time)
        )
        db.commit()
        flash('Timetable entry added!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        db.close()

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/remove_timetable/<int:entry_id>', methods=['POST'])
def remove_timetable(entry_id):
    db = get_db()
    db.execute("DELETE FROM timetable WHERE id = ?", (entry_id,))
    db.commit()
    db.close()
    flash('Timetable entry removed.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/add_override', methods=['POST'])
def add_override():
    subject_id = request.form.get('subject_id')
    override_date = request.form.get('override_date')
    override_type = request.form.get('override_type')
    new_start_time = request.form.get('new_start_time')
    new_end_time = request.form.get('new_end_time')

    if not all([subject_id, override_date, override_type]):
        flash('Required fields missing.', 'error')
        return redirect(url_for('admin.dashboard'))

    db = get_db()
    # If cancelled/holiday, times can be null
    db.execute(
        "INSERT INTO timetable_overrides (subject_id, override_date, override_type, new_start_time, new_end_time) VALUES (?, ?, ?, ?, ?)",
        (subject_id, override_date, override_type, new_start_time or None, new_end_time or None)
    )
    db.commit()
    db.close()
    flash('Schedule override added successfully.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/remove_override/<int:override_id>', methods=['POST'])
def remove_override(override_id):
    db = get_db()
    db.execute("DELETE FROM timetable_overrides WHERE id = ?", (override_id,))
    db.commit()
    db.close()
    flash('Override entry removed.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/attendance_records')
def attendance_records():
    db = get_db()
    records = db.execute("""
        SELECT a.id, st.name as student_name, s.name as subject_name,
               s.course_code, a.date, a.time, a.status, a.verified, a.method, u.name as teacher_name
        FROM attendance a
        JOIN students st ON st.student_id = a.student_id
        JOIN subjects s ON s.subject_id = a.subject_id
        LEFT JOIN users u ON u.id = a.teacher_id
        ORDER BY a.date DESC, a.time DESC
        LIMIT 200
    """).fetchall()
    db.close()
    return render_template('attendance_records.html', records=records)

import csv
from io import StringIO
from flask import Response

@admin_bp.route('/export_attendance')
def export_attendance():
    db = get_db()
    records = db.execute("""
        SELECT a.date, a.time, st.name as student_name, st.roll_number, st.class,
               s.course_code, s.name as subject, a.status, a.method, a.verified
        FROM attendance a
        JOIN students st ON st.student_id = a.student_id
        JOIN subjects s ON s.subject_id = a.subject_id
        ORDER BY a.date DESC, a.time DESC
    """).fetchall()
    db.close()

    def generate():
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(['Date', 'Time', 'Student', 'Roll Number', 'Class', 'Subject Code', 'Subject Name', 'Status', 'Method', 'Verified'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        for r in records:
            writer.writerow([r['date'], r['time'], r['student_name'], r['roll_number'], r['class'], 
                             r['course_code'], r['subject'], r['status'], r['method'], 'Yes' if r['verified'] else 'No'])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="attendance_export.csv")
    return response

@admin_bp.route('/face_enrollment_stats')
def face_enrollment_stats():
    db = get_db()
    # Template iterates over `stats` and accesses .status, .student_id, .name, .enrolled_at
    stats = db.execute("""
        SELECT 
            s.student_id,
            s.name,
            s.email,
            COALESCE(fe.status, 'pending') as status,
            fe.enrolled_at
        FROM students s
        LEFT JOIN face_encodings fe ON s.student_id = fe.student_id
        ORDER BY s.name
    """).fetchall()
    db.close()
    
    return render_template('face_enrollment_stats.html', stats=stats)

import os
@admin_bp.route('/enroll_student_face/<int:student_id>')
def enroll_student_face(student_id):
    """Compulsory face enrollment UI for Admin"""
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    face_status = db.execute("SELECT status FROM face_encodings WHERE student_id = ?", (student_id,)).fetchone()
    db.close()
    
    if not student:
        flash('Student not found for enrollment.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    status = face_status['status'] if face_status else 'pending'
    return render_template('admin_enroll_face.html', student=student, status=status)

@admin_bp.route('/enroll_from_dataset', methods=['POST'])
def admin_enroll_from_dataset():
    # In modular structure, enroll_from_dataset.py needs to be at root or reachable
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'enroll_from_dataset.py')
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout + result.stderr
        flash(f'Dataset enrollment complete:\n{output[:500]}', 'success')
    except Exception as e:
        flash(f'Enrollment error: {str(e)}', 'error')

    face_engine.reload()
    flash(f'Face service reloaded — {len(face_engine.known_encodings)} students in memory', 'success')
    return redirect(url_for('admin.face_enrollment_stats'))

