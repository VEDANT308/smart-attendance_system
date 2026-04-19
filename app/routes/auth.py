from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from app.database import get_db
from app.utils.auth import hash_password, get_current_subject

auth_bp = Blueprint('auth', __name__)

@auth_bp.before_app_request
def check_setup_required():
    """Globally check if first-time setup is needed"""
    if request.endpoint and request.endpoint.startswith('static'):
        return None
    if request.path == '/setup':
        return None
        
    db = get_db()
    admin_exists = db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone()
    db.close()
    
    if not admin_exists:
        return redirect(url_for('auth.setup'))
    return None

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    db = get_db()
    admin_exists = db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone()
    
    if admin_exists:
        db.close()
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if all([name, email, password]):
            db.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'admin')",
                (name, email, hash_password(password))
            )
            db.commit()
            db.close()
            flash('Master Admin setup complete. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('All fields are required.', 'error')
            
    db.close()
    return render_template('setup.html')

@auth_bp.route('/')
def index():
    return render_template('landing.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (username, hash_password(password))
        ).fetchone()
        db.close()

        if user:
            user_dict = dict(user)
            if user_dict.get('is_active', 1) == 0:
                flash('Your account has been deactivated. Please contact Admin.', 'error')
                return render_template('login.html')
            session['user_id'] = user_dict['id']
            session['name'] = user_dict['name']
            session['role'] = user_dict['role']
            session['email'] = user_dict['email']
            return redirect(url_for(f"{user_dict['role']}.dashboard"))
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))

@auth_bp.route('/attendance')
def guest_attendance():
    """Public quick-attendance page — no login required"""
    db = get_db()
    subjects = db.execute("SELECT subject_id, name, course_code FROM subjects ORDER BY name").fetchall()
    db.close()
    current_subject = get_current_subject()
    return render_template('guest_attendance.html', subjects=subjects, current_subject=current_subject)
