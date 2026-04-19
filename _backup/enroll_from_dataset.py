"""
enroll_from_dataset.py
─────────────────────
Scans the dataset/ folder, generates MediaPipe face encodings for each
student, and saves them to face_encodings/<student_id>.pkl

Folder structure expected:
  dataset/
    <StudentName>/
      image1.jpg
      image2.jpg
      ...

Students are matched to the `students` table by name (case-insensitive).
If no match is found, the student is printed as UNMATCHED and skipped.

Usage:
  .venv\\Scripts\\python.exe enroll_from_dataset.py

You can also pass a custom dataset and encodings directory:
  .venv\\Scripts\\python.exe enroll_from_dataset.py --dataset dataset --encodings face_encodings
"""

import os
import sys
import pickle
import argparse
import cv2
import numpy as np
from pathlib import Path

# ── MediaPipe setup ──────────────────────────────────────
import mediapipe as mp

_mp_face_mesh = mp.solutions.face_mesh
_face_mesh = _mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
)


def extract_encoding(image_path: str):
    """
    Extract a normalized 1404-dim (468×3) face encoding from an image file.
    Returns None if no face is detected.
    """
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"  ✗ Cannot read image: {image_path}")
        return None

    # Resize to max 640px for speed
    h, w = frame.shape[:2]
    if w > 640:
        frame = cv2.resize(frame, (640, int(h * 640 / w)))

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = _face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        print(f"  ✗ No face found: {os.path.basename(image_path)}")
        return None

    landmarks = results.multi_face_landmarks[0].landmark
    encoding = np.array(
        [[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32
    ).flatten()

    # Normalize: subtract centroid, then L2-normalize
    encoding = encoding - encoding.mean()
    norm = np.linalg.norm(encoding)
    if norm > 0:
        encoding = encoding / norm

    return encoding


def enroll_from_dataset(dataset_dir: str = 'dataset', encodings_dir: str = 'face_encodings'):
    dataset_path = Path(dataset_dir)
    encodings_path = Path(encodings_dir)
    encodings_path.mkdir(exist_ok=True)

    if not dataset_path.exists():
        print(f"❌ Dataset directory not found: {dataset_path.absolute()}")
        return

    # ── Load student name → ID mapping from DB ───────────
    import sqlite3
    db = sqlite3.connect('attendance.db')
    db.row_factory = sqlite3.Row
    students = db.execute("SELECT student_id, name FROM students").fetchall()
    db.close()

    name_to_id = {row['name'].strip().lower(): row['student_id'] for row in students}

    print(f"\n{'═'*60}")
    print(f"  SmartAttend — Dataset Enrollment Script")
    print(f"{'═'*60}")
    print(f"  Dataset dir  : {dataset_path.absolute()}")
    print(f"  Encodings dir: {encodings_path.absolute()}")
    print(f"  Students in DB: {len(name_to_id)}")
    print(f"{'─'*60}\n")

    # ── Process each subfolder ────────────────────────────
    subdirs = [d for d in dataset_path.iterdir() if d.is_dir()]
    if not subdirs:
        print("⚠ No subfolders found in dataset/. Create folders named after students.")
        print("  Example: dataset/Ishwari/  with .jpg images inside")
        return

    enrolled = []
    skipped = []

    for student_dir in sorted(subdirs):
        student_name = student_dir.name
        student_id = name_to_id.get(student_name.strip().lower())

        print(f"📁 {student_name}")

        if student_id is None:
            print(f"  ⚠ No matching student found in DB for '{student_name}'")
            print(f"     Available: {list(name_to_id.keys())}")
            skipped.append(student_name)
            print()
            continue

        # Collect image files
        image_files = []
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.webp'):
            image_files.extend(student_dir.glob(ext))
            image_files.extend(student_dir.glob(ext.upper()))

        if not image_files:
            print(f"  ✗ No images found in {student_dir}")
            skipped.append(student_name)
            print()
            continue

        print(f"  Found {len(image_files)} image(s) → extracting encodings...")

        encodings = []
        for img_path in image_files:
            enc = extract_encoding(str(img_path))
            if enc is not None:
                encodings.append(enc)
                print(f"  ✓ {img_path.name}")

        if len(encodings) == 0:
            print(f"  ❌ No valid face encodings from {len(image_files)} images")
            skipped.append(student_name)
            print()
            continue

        # Save pkl
        pkl_path = encodings_path / f"{student_id}.pkl"
        with open(pkl_path, 'wb') as f:
            pickle.dump(encodings, f)

        print(f"  ✅ Saved {len(encodings)} encodings → {pkl_path.name} (student_id={student_id})")
        enrolled.append((student_name, student_id, len(encodings)))
        print()

    # ── Summary ───────────────────────────────────────────
    print(f"{'═'*60}")
    print(f"  ✅ Enrolled: {len(enrolled)} students")
    for name, sid, count in enrolled:
        print(f"     • {name} (ID={sid}) — {count} encodings")

    if skipped:
        print(f"\n  ⚠ Skipped: {len(skipped)}")
        for name in skipped:
            print(f"     • {name}")

    print(f"{'═'*60}\n")

    # ── Reload face_service in-memory if running ──────────
    print("Done! Restart the Flask app to load new encodings,")
    print("or call face_service.reload() from within the app.\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enroll students from dataset images')
    parser.add_argument('--dataset',   default='dataset',       help='Path to dataset directory')
    parser.add_argument('--encodings', default='face_encodings', help='Path to face_encodings directory')
    args = parser.parse_args()

    enroll_from_dataset(args.dataset, args.encodings)
