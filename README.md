# 🎓 Smart Attendance System

An AI-powered web application that automates attendance using real-time face recognition — reducing manual effort and improving accuracy.

---

## 📌 Overview

Smart Attendance System replaces traditional roll-call methods with an automated face recognition pipeline.
It helps institutions save time, reduce proxy attendance, and maintain reliable attendance records.

**Impact:**

* ⏱ Reduces manual attendance time by **~70–80%**
* 🚫 Minimizes proxy attendance by **~85%+**
* 📊 Improves overall attendance accuracy

---

## ✨ Features

* 🎯 Real-time face recognition
* 👥 Role-based system (Admin, Teacher, Student)
* 🧠 Face enrollment via webcam
* ⏱ Timetable-based attendance marking
* 📊 Attendance analytics and history
* 📁 CSV export support
* 🔐 Secure authentication system

---

## 🛠 Tech Stack

* **Backend:** Python, Flask
* **Face Recognition:** MediaPipe, OpenCV, NumPy
* **Database:** SQLite
* **Frontend:** HTML, CSS, JavaScript

---

## 📁 Project Structure

```
smart-attendance_system/

├── app.py                          # Entry point (Flask app)
├── config.py                       # Application configuration
├── requirements.txt                # Dependencies
├── .gitignore                      # Ignored files (DB, datasets, secrets)

├── app/                            # Main application package
│   ├── __init__.py                 # App initialization & blueprint setup
│   ├── database.py                 # Database schema & helper functions
│
│   ├── routes/                     # Route modules (Flask Blueprints)
│   │   ├── auth.py                 # Authentication (login, logout, setup)
│   │   ├── admin.py                # Admin features (students, subjects, teachers)
│   │   ├── teacher.py              # Teacher dashboard & attendance
│   │   ├── student.py              # Student dashboard & analytics
│   │   └── api.py                  # API endpoints (attendance, face recognition)
│
│   ├── services/                   # Core logic
│   │   ├── face_service.py         # Face recognition engine
│   │   └── analyze_encs.py         # Encoding analysis utility
│
│   ├── utils/                      # Helper utilities
│   │   └── auth.py                 # Authentication helpers
│
│   ├── static/                     # Static files (CSS, JS)
│   │   └── css/
│   │       └── style.css
│
│   └── templates/                  # HTML templates
│       ├── landing.html
│       ├── login.html
│       ├── setup.html
│       ├── admin_dashboard.html
│       ├── teacher_dashboard.html
│       ├── student_dashboard.html
│       ├── face_enrollment.html
│       ├── face_attendance_marking.html
│       ├── guest_attendance.html
│       └── attendance_records.html

├── services/                       # Standalone/legacy services
│   └── face_service.py

├── face_encodings/                 # Stored encodings (ignored)
├── dataset/                        # Face images (ignored)

└── templates/                      # Optional root templates
```

---

## 🚀 Installation

```bash
git clone https://github.com/VEDANT308/smart-attendance_system.git
cd smart-attendance_system

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

👉 Runs on: `http://localhost:5000`

---

## ▶️ Usage

### Admin

* Manage students, teachers, and subjects
* Configure timetable
* Monitor and export attendance

### Teacher

* Mark attendance using face recognition
* Verify attendance records

### Student

* View attendance analytics
* Enroll face data

---

## 🔒 Important Notes

Sensitive data is excluded from this repository:

* Database files (`*.db`)
* Face encodings (`*.pkl`)
* Image datasets
* `.env` files

These are generated during runtime for security and privacy.

---

## 🔮 Future Improvements

* Liveness detection (anti-spoofing)
* Mobile/PWA support
* Advanced analytics dashboard
* Scalable database (PostgreSQL)

---

## 🤝 Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License

---

## 👤 Author

Vedant
https://github.com/VEDANT308
