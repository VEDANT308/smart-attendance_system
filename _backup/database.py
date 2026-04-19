
"""
Database Setup and Connection Module
Smart Classroom Attendance System
"""

import sqlite3
import hashlib
import os

DATABASE = 'attendance.db'

def get_db():
    """Get a database connection with row factory"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # Access columns by name
    db.execute("PRAGMA foreign_keys = ON")
    return db

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initialize the database with all tables and seed data"""
    db = get_db()
    cursor = db.cursor()

    # ── USERS TABLE ──────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            email    TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL CHECK(role IN ('admin', 'teacher', 'student'))
        )
    """)

    # ── STUDENTS TABLE ────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            class      TEXT NOT NULL,
            email      TEXT,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Migration: add email column if it doesn't exist yet (safe for existing DBs)
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN email TEXT")
        print("✅ Added 'email' column to students table")
    except Exception:
        pass  # column already exists

    # ── SUBJECTS TABLE ────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            course_code TEXT UNIQUE NOT NULL
        )
    """)

    # ── TEACHER-SUBJECT MAPPING ───────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_subjects (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
            UNIQUE(teacher_id, subject_id)
        )
    """)

    # ── TIMETABLE TABLE ───────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,   -- Format: HH:MM
            end_time   TEXT NOT NULL,   -- Format: HH:MM
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
        )
    """)

    # ── ATTENDANCE TABLE ──────────────────────────────────
    # verified = 0 → temporary (student scanned, teacher not yet)
    # verified = 1 → confirmed (teacher scanned)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date       TEXT    NOT NULL,  -- Format: YYYY-MM-DD
            time       TEXT    NOT NULL,  -- Format: HH:MM:SS
            status     TEXT    NOT NULL DEFAULT 'present' CHECK(status IN ('present', 'absent')),
            verified   INTEGER NOT NULL DEFAULT 0,  -- 0=temporary, 1=verified
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
        )
    """)

    # ── FACE ENCODINGS TABLE (for face recognition) ────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_encodings (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER UNIQUE NOT NULL,
            status     TEXT    NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'enrolled', 'failed')),
            enrolled_at TEXT,  -- Timestamp of enrollment
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    """)

    db.commit()

    # ── SEED DATA (only if empty) ─────────────────────────
    admin_exists = cursor.execute(
        "SELECT COUNT(*) FROM users WHERE role='admin'"
    ).fetchone()[0]

    if admin_exists == 0:
        _seed_data(cursor)
        db.commit()
        print("✅ Database seeded with demo data.")
    else:
        print("✅ Database already initialized.")

    db.close()

def _seed_data(cursor):
    """Insert demo/seed data"""

    # Admin
    cursor.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'admin')",
        ('Admin User', 'admin@school.com', hash_password('admin123'))
    )

    # Teachers
    cursor.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'teacher')",
        ('Dr. Priya Sharma', 'priya@school.com', hash_password('teacher123'))
    )
    teacher1_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'teacher')",
        ('Prof. Rahul Mehta', 'rahul@school.com', hash_password('teacher123'))
    )
    teacher2_id = cursor.lastrowid

    # Students
    students = [
        ('Aarav Patel', 'aarav@school.com', 'CS-3A'),
        ('Sneha Iyer', 'sneha@school.com', 'CS-3A'),
        ('Rohan Desai', 'rohan@school.com', 'CS-3A'),
        ('Meera Nair', 'meera@school.com', 'CS-3B'),
        ('Kabir Singh', 'kabir@school.com', 'CS-3B'),
    ]

    student_ids = []
    for name, email, cls in students:
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'student')",
            (name, email, hash_password('student123'))
        )
        user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO students (student_id, name, class, email) VALUES (?, ?, ?, ?)",
            (user_id, name, cls, email)
        )
        student_ids.append(user_id)

    # Subjects
    subjects_data = [
        ('Data Structures', 'CS301'),
        ('Operating Systems', 'CS302'),
        ('Database Management', 'CS303'),
        ('Computer Networks', 'CS304'),
    ]

    subject_ids = []
    for name, code in subjects_data:
        cursor.execute(
            "INSERT INTO subjects (name, course_code) VALUES (?, ?)", (name, code)
        )
        subject_ids.append(cursor.lastrowid)

    # Assign teachers
    cursor.execute(
        "INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
        (teacher1_id, subject_ids[0])
    )
    cursor.execute(
        "INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
        (teacher1_id, subject_ids[2])
    )
    cursor.execute(
        "INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
        (teacher2_id, subject_ids[1])
    )
    cursor.execute(
        "INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
        (teacher2_id, subject_ids[3])
    )

    # Timetable
    timetable_data = [
        (subject_ids[0], '09:00', '10:00'),
        (subject_ids[1], '10:15', '11:15'),
        (subject_ids[2], '11:30', '12:30'),
        (subject_ids[3], '14:00', '15:00'),
    ]

    for sub_id, start, end in timetable_data:
        cursor.execute(
            "INSERT INTO timetable (subject_id, start_time, end_time) VALUES (?, ?, ?)",
            (sub_id, start, end)
        )

    # Sample attendance records (past dates)
    import random
    from datetime import date, timedelta

    past_dates = [
        (date.today() - timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(1, 8)
    ]

    for past_date in past_dates:
        for subj_id in subject_ids[:2]:
            for std_id in student_ids:
                status = 'present' if random.random() > 0.2 else 'absent'
                if status == 'present':
                    cursor.execute("""
                        INSERT INTO attendance (student_id, subject_id, date, time, status, verified)
                        VALUES (?, ?, ?, '09:30:00', 'present', 1)
                    """, (std_id, subj_id, past_date))

    print("Demo Accounts:")
    print("  Admin    → admin@school.com     / admin123")
    print("  Teacher  → priya@school.com     / teacher123")
    print("  Teacher  → rahul@school.com     / teacher123")
    print("  Student  → aarav@school.com     / student123")
    print("  Student  → sneha@school.com     / student123")

if __name__ == '__main__':
    init_db()
