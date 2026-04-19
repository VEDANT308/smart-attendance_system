import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart_attendance_secret_key_2024'
    DATABASE = os.environ.get('DATABASE') or 'attendance.db'
    # Future config settings like MAIL_SERVER, etc. can go here
