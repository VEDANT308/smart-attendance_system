# Smart Attendance System - Production Rebuild TODO

## Phase 1: Face Recognition Fix + Landing Page (Week 1)
- [x] Step 1.1: Update requirements.txt with face_recognition lib
- [x] Step 1.2: Create services/face_service.py (new embedding-based engine)
- [ ] Step 1.3: Migrate dataset/Iswari+Sejal → face_encodings/*.pkl (multi-encoding)
- [x] Step 1.4: Create templates/landing.html (new home with Login + Quick Attendance)
- [ ] Step 1.5: Update app.py: Add / landing route, fix redirects, integrate new face_service
- [ ] Step 1.6: Update face_attendance_marking.html + JS: Confidence thresholds, Unknown Person
- [ ] Step 1.7: Test: Re-enroll, verify no Ishwari→Sejal misID, 85%+ conf only

## Phase 2: Architecture Refactor (Week 2)
- [ ] Step 2.1: Create app/ structure (blueprints, models SQLAlchemy)
- [ ] Step 2.2: Split app.py → auth.py, admin.py, etc.
- [ ] Step 2.3: Add config.py (THRESHOLD=0.6)
- [ ] Step 2.4: Alembic migrations

## Phase 3: Production Features (Week 3)
- [ ] Step 3.1: CSV/Excel export APIs
- [ ] Step 3.2: Chart.js dashboards
- [ ] Step 3.3: Flask-Login + rate limit
- [ ] Step 3.4: SSE real-time attendance

## Phase 4: Deploy (Week 4)
- [ ] Docker + Gunicorn
- [ ] Tests (pytest)
- [ ] Deployment (Render/Vercel/Heroku)

**Current Progress: Phase 1 Starting**
**Est. Completion: 4 weeks → Production Ready**

