# 🎓 AI-Powered Smart Attendance System

An AI-powered web application that automates attendance using real-time face recognition — reducing manual effort and improving accuracy.

---

# 📌 Overview

Smart Attendance System replaces traditional roll-call methods with an automated face recognition pipeline. It helps institutions save time, reduce proxy attendance, and maintain reliable attendance records.

This project is designed as a scalable education management foundation and will expand into a complete institutional management platform.

---

# 📊 Performance Impact

Estimated improvements compared to traditional attendance systems:

⏱ Reduces manual attendance time by ~70–80%  
🚫 Minimizes proxy attendance by ~85%+  
📊 Improves overall attendance accuracy  
📉 Reduces administrative workload  
📈 Improves attendance transparency  

---

# ✨ Features

🎯 Real-time face recognition  
👥 Role-based system (Admin, Teacher, Student)  
🧠 Face enrollment via webcam  
⏱ Timetable-based attendance marking  
📊 Attendance analytics and history  
📁 CSV export support  
🔐 Secure authentication system  
📚 Student attendance tracking  
🧾 Attendance record management  
📊 Role-based dashboards  
🛠 Modular architecture  

---

# 🧠 Planned AI Integration

This project will integrate AI-powered features to enhance automation and analytics.

Planned AI Features:

- Automated attendance summaries  
- Natural language report generation  
- Smart anomaly detection  
- Predictive attendance analysis  
- Intelligent academic insights  
- Automated daily and weekly reports  
- Student attendance risk detection  
- Teacher performance analytics  

These features will reduce manual reporting effort and provide intelligent insights.

---

# 🛠 Tech Stack

Backend:
Python  
Flask  

Face Recognition:
MediaPipe  
OpenCV  
NumPy  

Database:
SQLite  
(Future Migration: PostgreSQL)

Frontend:
HTML  
CSS  
JavaScript  

---

# 🏗 Architecture Overview

The Smart Attendance System follows a modular and scalable architecture.

Frontend:
- HTML, CSS, JavaScript dashboards
- Separate views for Admin, Teacher, and Student roles

Backend:
- Python Flask server
- REST-style API endpoints
- Authentication and authorization system

Face Recognition Engine:
- MediaPipe for face detection
- OpenCV for real-time processing
- NumPy for encoding operations

Database:
- SQLite structured storage
- Future migration to PostgreSQL

Workflow:

User Login  
→ Role Verification  
→ Dashboard Access  
→ Face Recognition  
→ Attendance Processing  
→ Database Storage  
→ Analytics Reporting  

---

# 📁 Project Structure

smart-attendance_system/

├── app.py  
├── config.py  
├── requirements.txt  
├── .gitignore  

├── app/  
│   ├── __init__.py  
│   ├── database.py  
│  
│   ├── routes/  
│   │   ├── auth.py  
│   │   ├── admin.py  
│   │   ├── teacher.py  
│   │   ├── student.py  
│   │   └── api.py  
│  
│   ├── services/  
│   │   ├── face_service.py  
│   │   └── analyze_encs.py  
│  
│   ├── utils/  
│   │   └── auth.py  
│  
│   ├── static/  
│   │   └── css/  
│   │       └── style.css  
│  
│   └── templates/  
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

---

# 📸 Screenshots

(Add images inside screenshots folder)

screenshots/admin_dashboard.png  
screenshots/teacher_dashboard.png  
screenshots/student_dashboard.png  
screenshots/face_enrollment.png  
screenshots/face_recognition.png  
screenshots/attendance_records.png  

## Screenshots

### Admin Dashboard
![Admin Dashboard](screenshots/admin_dashboard.png)

### Teacher Dashboard
![Teacher Dashboard](screenshots/teacher_dashboard.png)

### Student Dashboard
![Student Dashboard](screenshots/student_dashboard.png)

### Face Enrollment
![Face Enrollment](screenshots/face_enrollment.png)

### Face Recognition Attendance
![Face Recognition](screenshots/face_recognition.png)

### Attendance Records
![Attendance Records](screenshots/attendance_records.png)

---

# 🚀 Installation

git clone https://github.com/VEDANT308/smart-attendance_system.git  
cd smart-attendance_system  

python -m venv .venv  
.venv\Scripts\activate  

pip install -r requirements.txt  
python app.py  

Runs on:

http://localhost:5000  

---

# ▶️ Usage

Admin:
- Manage students  
- Manage teachers  
- Manage subjects  
- Configure timetable  
- Monitor attendance  
- Export attendance  

Teacher:
- Mark attendance using face recognition  
- Verify attendance records  
- Manage class attendance  

Student:
- View attendance analytics  
- Enroll face data  
- Check attendance history  

---

# 🔒 Important Notes

Sensitive data excluded:

- Database files (*.db)  
- Face encodings (*.pkl)  
- Image datasets  
- .env files  

These are generated during runtime for security and privacy.

---

# 🚀 Future Roadmap

Upcoming Features:

- Multi-institution support  
- Assignment management system  
- Communication system  
- Advanced analytics dashboard  
- Liveness detection (anti-spoofing)  
- Mobile / PWA support  
- PostgreSQL migration  
- Cloud deployment  
- AI-powered smart analytics  

---

# 🤝 Contributing

1. Fork repository  
2. Create new branch  
3. Make changes  
4. Submit pull request
5. 
---

# 👤 Author

Vedant  
GitHub: https://github.com/VEDANT308  

---
