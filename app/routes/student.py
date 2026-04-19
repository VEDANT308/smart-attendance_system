from flask import Blueprint, render_template, redirect, url_for, session
from app.database import get_db
from app.utils.auth import login_required_check

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.before_request
def check_student():
    if not login_required_check('student'):
        return redirect(url_for('auth.login'))

@student_bp.route('/')
def dashboard():
    student_id = session['user_id']
    db = get_db()

    student = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    subjects = db.execute("SELECT * FROM subjects").fetchall()
    attendance_data = []
    
    total_lectures_overall = 0
    total_attended_overall = 0

    for subj in subjects:
        total_lectures = db.execute("""
            SELECT COUNT(DISTINCT date) FROM attendance
            WHERE subject_id = ? AND verified = 1
        """, (subj['subject_id'],)).fetchone()[0]

        attended = db.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE student_id = ? AND subject_id = ? AND verified = 1 AND status = 'present'
        """, (student_id, subj['subject_id'])).fetchone()[0]
        
        total_lectures_overall += total_lectures
        total_attended_overall += attended

        percentage = round((attended / total_lectures * 100), 1) if total_lectures > 0 else 0

        recent = db.execute("""
            SELECT date, time, status, verified FROM attendance
            WHERE student_id = ? AND subject_id = ?
            ORDER BY date DESC, time DESC LIMIT 10
        """, (student_id, subj['subject_id'])).fetchall()

        attendance_data.append({
            'subject': subj,
            'total_lectures': total_lectures,
            'attended': attended,
            'percentage': percentage,
            'recent': recent
        })
        
    overall_percentage = round((total_attended_overall / total_lectures_overall * 100), 1) if total_lectures_overall > 0 else 0
    
    import datetime
    today = datetime.date.today().strftime('%A')
    
    timetable = db.execute("""
        SELECT t.*, s.name as subject_name, s.course_code, u.name as teacher_name 
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.subject_id
        LEFT JOIN teacher_subjects ts ON s.subject_id = ts.subject_id
        LEFT JOIN users u ON ts.teacher_id = u.id
        ORDER BY t.day_of_week, t.start_time
    """).fetchall()

    db.close()
    return render_template('student_dashboard.html',
                           student=student,
                           attendance_data=attendance_data,
                           overall_percentage=overall_percentage,
                           timetable=timetable)

@student_bp.route('/face_enrollment')
def face_enrollment():
    """Student face enrollment page"""
    student_id = session['user_id']
    db = get_db()
    
    status_row = db.execute(
        "SELECT status FROM face_encodings WHERE student_id = ?",
        (student_id,)
    ).fetchone()
    db.close()
    
    status = status_row['status'] if status_row else 'pending'
    return render_template('face_enrollment.html', status=status, student_id=student_id)
