import os
from flask import Flask
from config import Config

def create_app():
    # Force UTF-8 encoding for Windows console (emoji support)
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Database
    with app.app_context():
        from app.database import init_db
        init_db()
        from app.services.face_service import face_service as face_engine
        print(f"[SmartAttend Base] New architecture loaded — {len(face_engine.known_encodings)} faces ready.")

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.teacher import teacher_bp
    from app.routes.student import student_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)

    return app
