#!/usr/bin/env python3
"""
Dataset Migration Script: Convert raw images -> face_recognition encodings
Run: python migrate_dataset.py
"""

import os
import sys
sys.path.append('.')

from services.face_service import FaceService
from PIL import Image
import base64

def image_to_b64(img_path):
    """Convert image file to base64 for service"""
    with open(img_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def migrate_student_dir(student_dir, student_id):
    """Process all images in student directory"""
    service = FaceService()
    
    img_files = []
    for file in os.listdir(student_dir):
        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_files.append(os.path.join(student_dir, file))
    
    if not img_files:
        print(f"No images found in {student_dir}")
        return False
    
    print(f"Processing {len(img_files)} images for student {student_id}...")
    
    b64_images = [image_to_b64(img_path) for img_path in img_files[:5]]  # Max 5
    
    success = service.enroll_student(student_id, b64_images)
    
    if success:
        print(f"✅ Successfully migrated student {student_id}")
        service.load_all_encodings()  # Reload
        print(f"📊 Now {len(service.known_encodings)} students enrolled")
    else:
        print(f"❌ Migration failed for student {student_id}")
    
    return success

if __name__ == '__main__':
    print("Smart Attendance Dataset Migration")
    print("=" * 50)
    
    # Student mappings (from dataset folders)
    students = {
        'Iswari': 1,  # Assign IDs based on DB students table
        'Sejal': 2
    }
    
    for name, student_id in students.items():
        student_dir = f"dataset/{name}"
        if os.path.exists(student_dir):
            migrate_student_dir(student_dir, student_id)
        else:
            print(f"⚠️ Directory not found: {student_dir}")
    
    print("\\n✅ Migration complete!")
    print("Next: python run.py")
    print("Test enrollment at /student/face_enrollment")

