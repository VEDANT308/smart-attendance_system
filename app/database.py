import sqlite3
import hashlib
import os

# We want the database to live in the root `instance` folder or root project folder.
# By default, SQLite creates the db in the current working directory, 
# but it's safer to use an absolute path relative to this file.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(BASE_DIR, 'attendance.db')

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
            role     TEXT    NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ── STUDENTS TABLE ────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id  INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            roll_number TEXT,
            class       TEXT NOT NULL,
            department  TEXT,
            semester    TEXT,
            email       TEXT,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Migration: add columns if they don't exist yet (safe for existing DBs)
    columns_to_add = [
        ('roll_number', 'TEXT'),
        ('department', 'TEXT'),
        ('semester', 'TEXT'),
        ('email', 'TEXT')
    ]
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}")
            print(f"[DB] Added '{col_name}' column to students table")
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
            assigned_class TEXT NOT NULL DEFAULT 'All',
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
            UNIQUE(teacher_id, subject_id, assigned_class)
        )
    """)

    # ── TIMETABLE TABLE ───────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id   INTEGER NOT NULL,
            day_of_week  INTEGER NOT NULL, -- 0=Monday, 6=Sunday
            start_time   TEXT NOT NULL,   -- Format: HH:MM
            end_time     TEXT NOT NULL,   -- Format: HH:MM
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
        )
    """)

    # ── TIMETABLE OVERRIDES ───────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable_overrides (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id   INTEGER,
            override_date TEXT NOT NULL,  -- Format: YYYY-MM-DD
            override_type TEXT NOT NULL CHECK(override_type IN ('cancelled', 'holiday', 'extra', 'rescheduled')),
            new_start_time TEXT, -- Null if cancelled/holiday
            new_end_time   TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
        )
    """)

    # ── ATTENDANCE TABLE ──────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            teacher_id INTEGER,           -- Who verified/took manual roll
            date       TEXT    NOT NULL,  -- Format: YYYY-MM-DD
            time       TEXT    NOT NULL,  -- Format: HH:MM:SS
            method     TEXT    NOT NULL DEFAULT 'face' CHECK(method IN ('face', 'manual', 'system')),
            status     TEXT    NOT NULL DEFAULT 'present' CHECK(status IN ('present', 'absent', 'late')),
            verified   INTEGER NOT NULL DEFAULT 0,  -- 0=temporary, 1=verified
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL,
            UNIQUE(student_id, subject_id, date) -- Prevent duplicate attendance per subject per day
        )
    """)

    # ── FACE ENCODINGS TABLE (for face recognition) ────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_encodings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id   INTEGER UNIQUE NOT NULL,
            status       TEXT    NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'enrolled', 'failed')),
            num_encodings INTEGER DEFAULT 0,
            enrolled_at  TEXT,  -- Timestamp of enrollment
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    """)
    # Migration: add num_encodings if missing
    try:
        cursor.execute("ALTER TABLE face_encodings ADD COLUMN num_encodings INTEGER DEFAULT 0")
    except Exception:
        pass  # already exists

    # ── NOTICES TABLE ─────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            posted_by   INTEGER NOT NULL,
            target_role TEXT DEFAULT 'all',  -- 'all', 'teacher', 'student'
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (posted_by) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ── LEAVE REQUESTS TABLE ──────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            start_date  TEXT NOT NULL,
            end_date    TEXT NOT NULL,
            reason      TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    """)

    # ── ASSIGNMENTS TABLE ─────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id  INTEGER NOT NULL,
            teacher_id  INTEGER NOT NULL,
            title       TEXT NOT NULL,
            description TEXT,
            due_date    TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ── ACTIVITY LOGS TABLE ───────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER, -- Can be null for system tasks
            action      TEXT NOT NULL,
            details     TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    # ── SETTINGS TABLE ────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL
        )
    """)

    db.commit()

    # ── SEED SETTINGS ──────────────────────────────────────
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('recognition_threshold', '0.6')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('dark_mode_default', 'false')")
    db.commit()

    # Note: Initial Admin Setup is now handled dynamically via /setup route
    print("[DB] Database framework ready.")
    db.close()

if __name__ == '__main__':
    init_db()
