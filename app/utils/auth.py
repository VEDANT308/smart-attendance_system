import hashlib
from flask import session
from datetime import datetime, date, timedelta
from app.database import get_db

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required_check(role=None):
    """Business logic for checking if current session is valid"""
    if 'user_id' not in session:
        return False
    if role and session.get('role') != role:
        return False
    return True

def get_current_subject():
    """Detect current subject based on current time from timetable (with overrides & grace periods)"""
    db = get_db()
    
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    day_of_week = now.weekday()  # Monday=0, Sunday=6
    
    # Get all potential regular slots for today
    base_slots = db.execute("""
        SELECT t.id, t.subject_id, s.name, s.course_code, t.start_time, t.end_time
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.subject_id
        WHERE t.day_of_week = ?
    """, (day_of_week,)).fetchall()
    
    # Get overrides for today
    overrides = db.execute("""
        SELECT subject_id, override_type, new_start_time, new_end_time
        FROM timetable_overrides
        WHERE override_date = ?
    """, (today_str,)).fetchall()
    db.close()
    
    # Convert overrides to a quick lookup
    override_dict = {o['subject_id']: o for o in overrides}
    
    # Build active slots
    active_slots = []
    for slot in base_slots:
        slot_dict = dict(slot)
        # Apply overrides
        over = override_dict.get(slot_dict['subject_id'])
        if over:
            if over['override_type'] in ('cancelled', 'holiday'):
                continue # Skip this slot entirely
            if over['new_start_time']:
                slot_dict['start_time'] = over['new_start_time']
            if over['new_end_time']:
                slot_dict['end_time'] = over['new_end_time']
        active_slots.append(slot_dict)
        
    # Also add "extra" manual override classes that weren't in the base schedule for today
    for over in overrides:
        if over['override_type'] == 'extra':
            # Need to get subject name/code for extra classes
            db = get_db()
            subj = db.execute("SELECT name, course_code FROM subjects WHERE subject_id = ?", (over['subject_id'],)).fetchone()
            db.close()
            if subj:
                active_slots.append({
                    'id': None,
                    'subject_id': over['subject_id'],
                    'name': subj['name'],
                    'course_code': subj['course_code'],
                    'start_time': over['new_start_time'],
                    'end_time': over['new_end_time']
                })
                
    # Check grace periods: 5 min before start, 10 min after end
    current_time_val = now.hour * 60 + now.minute
    
    for slot in active_slots:
        try:
            start_h, start_m = map(int, slot['start_time'].split(':'))
            end_h, end_m = map(int, slot['end_time'].split(':'))
            
            start_val = start_h * 60 + start_m
            end_val = end_h * 60 + end_m
            
            allowed_start = start_val - 5
            allowed_end = end_val + 10
            
            if allowed_start <= current_time_val <= allowed_end:
                return slot
        except Exception:
            continue
            
    return None
