from flask import Blueprint, request, jsonify, session
from datetime import datetime, date
import cv2
import base64
import numpy as np

from app.database import get_db
from app.utils.auth import get_current_subject, login_required_check
from app.services.face_service import face_service as face_engine

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    student_id = data.get('student_id')
    scan_type = data.get('scan_type', 'student')

    current_subject = get_current_subject()
    if not current_subject:
        return jsonify({'error': 'No active class at this time'}), 400

    subject_id = current_subject['subject_id']
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M:%S')

    db = get_db()
    
    if scan_type == 'student':
        student = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
        if not student:
            db.close()
            return jsonify({'error': 'Student not found'}), 404

        existing = db.execute(
            "SELECT id FROM attendance WHERE student_id = ? AND subject_id = ? AND date = ?", 
            (student_id, subject_id, today)
        ).fetchone()

        if existing:
            db.close()
            return jsonify({'message': 'Already marked for today'}), 200

        db.execute("""
            INSERT INTO attendance (student_id, subject_id, teacher_id, date, time, method, status, verified)
            VALUES (?, ?, ?, ?, ?, 'face', 'present', 0)
        """, (student_id, subject_id, session.get('user_id'), today, current_time))
        db.commit()
        db.close()
        return jsonify({'message': 'Attendance marked (pending verification)', 'verified': 0})

    elif scan_type == 'teacher':
        db.execute("""
            UPDATE attendance
            SET verified = 1
            WHERE subject_id = ? AND date = ? AND verified = 0
        """, (subject_id, today))
        db.commit()
        db.close()
        return jsonify({'message': 'All attendance verified for this class'})

    db.close()
    return jsonify({'error': 'Invalid scan type'}), 400

@api_bp.route('/mark_manual', methods=['POST'])
def mark_manual():
    if not login_required_check('teacher'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    student_id = data.get('student_id')
    subject_id = data.get('subject_id')
    status = data.get('status', 'present')
    
    if not student_id or not subject_id:
        return jsonify({'error': 'Missing data'}), 400
        
    db = get_db()
    today = date.today().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M:%S')
    
    existing = db.execute("SELECT id FROM attendance WHERE student_id=? AND subject_id=? AND date=?", (student_id, subject_id, today)).fetchone()
    
    if existing:
        db.execute("UPDATE attendance SET status=?, method='manual', verified=1, teacher_id=? WHERE id=?", (status, session.get('user_id'), existing['id']))
    else:
        db.execute(
            "INSERT INTO attendance (student_id, subject_id, teacher_id, date, time, method, status, verified) VALUES (?,?,?,?,?,'manual',?,1)",
            (student_id, subject_id, session.get('user_id'), today, current_time, status)
        )
    db.commit()
    db.close()
    
    return jsonify({'message': 'Manual attendance recorded'})

@api_bp.route('/cleanup_unverified', methods=['POST'])
def cleanup_unverified():
    current_subject = get_current_subject()
    if not current_subject:
        data = request.get_json() or {}
        subject_id = data.get('subject_id')
    else:
        subject_id = current_subject['subject_id']

    if not subject_id:
        return jsonify({'error': 'No subject specified'}), 400

    today = date.today().strftime('%Y-%m-%d')
    db = get_db()
    deleted = db.execute("DELETE FROM attendance WHERE subject_id = ? AND date = ? AND verified = 0", (subject_id, today)).rowcount
    db.commit()
    db.close()
    return jsonify({'message': f'Deleted {deleted} unverified records'})

@api_bp.route('/current_subject')
def current_subject_api():
    subject = get_current_subject()
    if subject:
        return jsonify({
            'subject_id': subject['subject_id'],
            'name': subject['name'],
            'course_code': subject['course_code'],
            'start_time': subject['start_time'],
            'end_time': subject['end_time']
        })
    return jsonify({'message': 'No active class right now'}), 404


@api_bp.route('/face/enroll', methods=['POST'])
def face_enroll():
    if not login_required_check('student'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    student_id = session['user_id']
    data = request.get_json()
    
    frame_b64 = data.get('frame') or data.get('image') if data else None
    if not frame_b64:
        return jsonify({'error': 'No frame provided'}), 400
    
    try:
        if ',' in frame_b64:
            frame_b64_data = frame_b64.split(',')[1]
        else:
            frame_b64_data = frame_b64
        nparr = np.frombuffer(base64.b64decode(frame_b64_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'error': 'Failed to decode image'}), 400
        
        encoding = face_engine.enroll_from_frame(student_id, frame)
        
        if encoding is None:
            return jsonify({'error': 'No face detected in frame'}), 400
        
        sid_str = str(student_id)
        if sid_str not in face_engine.known_encodings:
            face_engine.known_encodings[sid_str] = []
        face_engine.known_encodings[sid_str].append(encoding)
        
        sample_count = len(face_engine.known_encodings[sid_str])
        
        if sample_count >= 5 or data.get('final', False):
            face_engine.save_student_encodings(student_id, face_engine.known_encodings[sid_str])
            
            db = get_db()
            existing = db.execute("SELECT id FROM face_encodings WHERE student_id = ?", (student_id,)).fetchone()
            if existing:
                db.execute("UPDATE face_encodings SET status='enrolled', num_encodings=?, enrolled_at=datetime('now') WHERE student_id=?", (sample_count, student_id))
            else:
                db.execute("INSERT INTO face_encodings (student_id, status, num_encodings, enrolled_at) VALUES (?, 'enrolled', ?, datetime('now'))", (student_id, sample_count))
            db.commit()
            db.close()
            return jsonify({'message': 'Face enrolled successfully', 'count': sample_count, 'saved': True})
        
        return jsonify({'message': f'Sample {sample_count} captured', 'count': sample_count, 'saved': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/face/admin_enroll/<int:target_student_id>', methods=['POST'])
def face_admin_enroll(target_student_id):
    """Admin-triggered bulk/compulsory enrollment endpoint"""
    if not login_required_check('admin'):
        return jsonify({'error': 'Admin authenticated required'}), 403
    
    data = request.get_json()
    frame_b64 = data.get('frame') or data.get('image') if data else None
    if not frame_b64:
        return jsonify({'error': 'No frame provided'}), 400
    
    try:
        if ',' in frame_b64:
            frame_b64_data = frame_b64.split(',')[1]
        else:
            frame_b64_data = frame_b64
        nparr = np.frombuffer(base64.b64decode(frame_b64_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'error': 'Failed to decode image'}), 400
        
        encoding = face_engine.enroll_from_frame(target_student_id, frame)
        if encoding is None:
            return jsonify({'error': 'No face detected in frame'}), 400
            
        sid_str = str(target_student_id)
        if sid_str not in face_engine.known_encodings:
            face_engine.known_encodings[sid_str] = []
        face_engine.known_encodings[sid_str].append(encoding)
        
        sample_count = len(face_engine.known_encodings[sid_str])
        
        # Admin flow requires 10 samples
        if sample_count >= 10 or data.get('final', False):
            face_engine.save_student_encodings(target_student_id, face_engine.known_encodings[sid_str])
            
            db = get_db()
            existing = db.execute("SELECT id FROM face_encodings WHERE student_id = ?", (target_student_id,)).fetchone()
            if existing:
                db.execute("UPDATE face_encodings SET status='enrolled', num_encodings=?, enrolled_at=datetime('now') WHERE student_id=?", (sample_count, target_student_id))
            else:
                db.execute("INSERT INTO face_encodings (student_id, status, num_encodings, enrolled_at) VALUES (?, 'enrolled', ?, datetime('now'))", (target_student_id, sample_count))
            db.commit()
            db.close()
            return jsonify({'message': 'Face enrolled successfully', 'count': sample_count, 'saved': True})
            
        return jsonify({'message': f'Sample {sample_count}/10 captured', 'count': sample_count, 'saved': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/face/status/<student_id>')
def face_status(student_id):
    db = get_db()
    status_row = db.execute("SELECT status FROM face_encodings WHERE student_id = ?", (student_id,)).fetchone()
    db.close()
    status = status_row['status'] if status_row else 'pending'
    return jsonify({'status': status})

@api_bp.route('/face/unenroll', methods=['POST'])
def face_unenroll():
    if not login_required_check('student'):
        return jsonify({'error': 'Not authenticated'}), 401
    student_id = session['user_id']
    try:
        db = get_db()
        db.execute("DELETE FROM face_encodings WHERE student_id = ?", (student_id,))
        db.commit()
        db.close()
        face_engine.unenroll_student(student_id)
        return jsonify({'message': 'Face profile removed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/face/recognize', methods=['POST'])
def recognize_face():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    subject_id = data.get('subject_id')
    image_b64 = data.get('image') or data.get('frame')

    if not image_b64 or not subject_id:
        return jsonify({'error': 'Missing image or subject_id'}), 400

    assigned_class_filter = data.get('assigned_class')

    try:
        results = face_engine.recognize_b64(image_b64)

        recognized_students = []
        db = get_db()
        today = date.today().isoformat()
        now_time = datetime.now().strftime('%H:%M:%S')

        for result in results:
            if result.is_unknown or result.student_id is None:
                # Still include unknowns in the response if they have a message (e.g., "Analyzing...")
                if result.message and "..." in result.message:
                    recognized_students.append({
                        'student_id': None,
                        'name': 'Detecting...',
                        'message': result.message,
                        'confidence': float(result.confidence),
                        'status': 'analyzing'
                    })
                continue

            student_id_found = result.student_id
            student = db.execute(
                "SELECT name, class, roll_number, department, semester FROM students WHERE student_id = ?", 
                (student_id_found,)
            ).fetchone()

            if not student:
                continue
                
            # Class strictness
            if assigned_class_filter and assigned_class_filter != 'All':
                if student['class'] != assigned_class_filter:
                    continue

            # Check enrollment status
            enrolled = db.execute("SELECT status FROM face_encodings WHERE student_id = ? AND status='enrolled'", (student_id_found,)).fetchone()
            if not enrolled:
                continue 

            existing = db.execute("SELECT id FROM attendance WHERE student_id=? AND subject_id=? AND date=?", (student_id_found, subject_id, today)).fetchone()

            if not existing:
                db.execute(
                    "INSERT INTO attendance (student_id, subject_id, teacher_id, date, time, method, status, verified) VALUES (?,?,?,?,?,'face','present',1)",
                    (student_id_found, subject_id, session.get('user_id'), today, now_time)
                )
                db.commit()
                marked = True
            else:
                marked = False

            recognized_students.append({
                'student_id': student_id_found,
                'name': student['name'],
                'roll_number': student['roll_number'],
                'department': student['department'],
                'semester': student['semester'],
                'confidence': float(result.confidence),
                'confidence_label': face_engine.get_confidence_level(result.confidence),
                'time': now_time,
                'marked': marked,
                'message': result.message,
                'status': 'confirmed'
            })

        db.close()

        return jsonify({
            'detected': len(recognized_students) > 0,
            'recognized_students': recognized_students,
            'count': len([s for s in recognized_students if s['status'] == 'confirmed'])
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/face/recognize_guest', methods=['POST'])
def recognize_face_guest():
    return recognize_face()

@api_bp.route('/face/reload', methods=['POST'])
def reload_face_service():
    """Admin endpoint to reload encodings"""
    if not login_required_check('admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    face_engine.reload()
    return jsonify({
        'message': f'Reloaded {len(face_engine.known_encodings)} students',
        'students': list(face_engine.known_encodings.keys())
    })
