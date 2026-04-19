from flask import Blueprint, render_template, redirect, url_for, session
from app.database import get_db
from app.utils.auth import login_required_check, get_current_subject

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

@teacher_bp.before_request
def check_teacher():
    if not login_required_check('teacher'):
        return redirect(url_for('auth.login'))

@teacher_bp.route('/')
def dashboard():
    teacher_id = session['user_id']
    db = get_db()

    subjects = db.execute("""
        SELECT s.subject_id, s.name, s.course_code, ts.assigned_class
        FROM subjects s
        JOIN teacher_subjects ts ON ts.subject_id = s.subject_id
        WHERE ts.teacher_id = ?
    """, (teacher_id,)).fetchall()

    students = db.execute("SELECT * FROM students ORDER BY name").fetchall()
    attendance_stats = []
    
    import datetime
    today = datetime.date.today().strftime('%Y-%m-%d')
    today_attendance_taken = 0

    for subj in subjects:
        records = db.execute("""
            SELECT a.id, st.name as student_name, a.date, a.time, a.status, a.verified
            FROM attendance a
            JOIN students st ON st.student_id = a.student_id
            WHERE a.subject_id = ?
            ORDER BY a.date DESC, a.time DESC
            LIMIT 50
        """, (subj['subject_id'],)).fetchall()

        total = db.execute(
            "SELECT COUNT(DISTINCT date) FROM attendance WHERE subject_id = ? AND verified = 1",
            (subj['subject_id'],)
        ).fetchone()[0]
        
        taken_today = db.execute(
            "SELECT COUNT(DISTINCT subject_id) FROM attendance WHERE subject_id = ? AND date = ? AND verified = 1",
            (subj['subject_id'], today)
        ).fetchone()[0]
        if taken_today > 0:
            today_attendance_taken += 1

        attendance_stats.append({
            'subject': subj,
            'total_lectures': total,
            'records': records
        })
        
    timetable = db.execute("""
        SELECT t.*, s.name as subject_name, s.course_code 
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.subject_id
        JOIN teacher_subjects ts ON ts.subject_id = s.subject_id
        WHERE ts.teacher_id = ?
        ORDER BY t.day_of_week, t.start_time
    """, (teacher_id,)).fetchall()

    db.close()
    return render_template('teacher_dashboard.html',
                           subjects=subjects,
                           students=students,
                           attendance_stats=attendance_stats,
                           timetable=timetable,
                           today_attendance_taken=today_attendance_taken)

@teacher_bp.route('/mark_attendance_face')
def mark_attendance_face():
    """Teacher real-time face recognition interface"""
    db = get_db()
    # Get all active assignments for this teacher
    assignments = db.execute("""
        SELECT ts.subject_id, s.name, s.course_code, ts.assigned_class
        FROM teacher_subjects ts
        JOIN subjects s ON ts.subject_id = s.subject_id
        WHERE ts.teacher_id = ?
    """, (session['user_id'],)).fetchall()
    db.close()
    current_subject = get_current_subject()
    return render_template('face_attendance_marking.html', assignments=assignments, current_subject=current_subject)
