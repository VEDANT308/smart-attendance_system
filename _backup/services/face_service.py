"""
Production Face Recognition Service
Uses MediaPipe Face Mesh for 468-landmark embeddings.
Multi-encoding per student, cosine distance threshold.
Works without dlib/face_recognition (pure Python + OpenCV).
"""

import cv2
import numpy as np
import os
import pickle
import base64
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field

# ── MediaPipe (required) ─────────────────────────────────
import mediapipe as mp

_mp_face_mesh = mp.solutions.face_mesh
_mp_face_detection = mp.solutions.face_detection

# Shared instances (context-manager friendly but kept open for perf)
_face_mesh = _mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
)
_face_detector = _mp_face_detection.FaceDetection(
    model_selection=1,
    min_detection_confidence=0.5,
)


def _extract_encoding_from_frame(frame_bgr: np.ndarray) -> Optional[np.ndarray]:
    """
    Extract a 1404-dim face encoding from a BGR OpenCV frame using MediaPipe.
    Returns None if no face found.
    """
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    results = _face_mesh.process(rgb)
    if not results.multi_face_landmarks:
        return None

    landmarks = results.multi_face_landmarks[0].landmark
    # Flatten x,y,z for all 468 landmarks → 1404 floats
    encoding = np.array(
        [[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32
    ).flatten()

    # ── Normalize: subtract centroid so position-invariant ──
    encoding = encoding - encoding.mean()
    norm = np.linalg.norm(encoding)
    if norm > 0:
        encoding = encoding / norm
    return encoding


def _b64_to_frame(image_b64: str) -> Optional[np.ndarray]:
    """Decode a base64 data-URL to an OpenCV BGR frame."""
    try:
        if ',' in image_b64:
            _, data = image_b64.split(',', 1)
        else:
            data = image_b64
        nparr = np.frombuffer(base64.b64decode(data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        print(f"[face_service] b64 decode error: {e}")
        return None


@dataclass
class RecognitionResult:
    student_id: Optional[int] = None
    name: Optional[str] = None
    confidence: float = 0.0
    is_unknown: bool = False
    message: str = ""


class FaceService:
    """
    Unified face recognition service using MediaPipe.
    Accepts:
      - enroll_student(student_id, image_b64_list) → saves encodings to pkl
      - recognize_b64(image_b64)                  → RecognitionResult
      - recognize_frame(frame_bgr)                → RecognitionResult
    """

    def __init__(self, encodings_dir: str = 'face_encodings', tolerance: float = 0.12):
        """
        tolerance: max cosine distance (lower = stricter).
        For MediaPipe normalized landmarks, good values: 0.10–0.15
        """
        self.encodings_dir = Path(encodings_dir)
        self.encodings_dir.mkdir(exist_ok=True)
        self.tolerance = tolerance

        # student_id (str) → list of np.ndarray encodings
        self.known_encodings: Dict[str, List[np.ndarray]] = {}

        self.load_all_encodings()

    # ── I/O ─────────────────────────────────────────────────

    def load_all_encodings(self):
        """Load all student encodings from pickle files on disk."""
        self.known_encodings.clear()
        for pkl_file in sorted(self.encodings_dir.glob('*.pkl')):
            student_id = pkl_file.stem
            try:
                with open(pkl_file, 'rb') as f:
                    data = pickle.load(f)
                # Support both list-of-encodings and single averaged encoding
                if isinstance(data, np.ndarray):
                    data = [data]
                if isinstance(data, list) and len(data) > 0:
                    self.known_encodings[student_id] = data
                    print(f"[face_service] Loaded {len(data)} encoding(s) for student {student_id}")
            except Exception as e:
                print(f"[face_service] Error loading {pkl_file.name}: {e}")
        print(f"[face_service] Total students loaded: {len(self.known_encodings)}")

    def reload(self):
        """Reload all encodings (call after enrolling a new student)."""
        self.load_all_encodings()

    # ── Enrollment ──────────────────────────────────────────

    def enroll_student(self, student_id: int, image_b64_list: List[str],
                       num_samples: int = 5) -> bool:
        """
        Enroll a student with multiple face images (base64 data-URLs).
        Returns True if at least 2 good encodings were captured.
        """
        encodings = []
        for i, img_b64 in enumerate(image_b64_list[:num_samples]):
            frame = _b64_to_frame(img_b64)
            if frame is None:
                continue
            enc = _extract_encoding_from_frame(frame)
            if enc is not None:
                encodings.append(enc)
                print(f"[face_service] Enroll sample {i+1}: OK")
            else:
                print(f"[face_service] Enroll sample {i+1}: no face")

        if len(encodings) < 2:
            print(f"[face_service] Enroll failed: only {len(encodings)} samples")
            return False

        pkl_path = self.encodings_dir / f"{student_id}.pkl"
        try:
            with open(pkl_path, 'wb') as f:
                pickle.dump(encodings, f)
            self.known_encodings[str(student_id)] = encodings
            print(f"[face_service] Enrolled student {student_id} with {len(encodings)} encodings")
            return True
        except Exception as e:
            print(f"[face_service] Enroll save error: {e}")
            return False

    def enroll_from_frame(self, student_id: int, frame_bgr: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract a single encoding from an OpenCV frame for incremental enrollment.
        Returns the encoding if a face was found, else None.
        Used by /api/face/enroll endpoint (send multiple frames).
        """
        return _extract_encoding_from_frame(frame_bgr)

    def save_student_encodings(self, student_id: int, encodings: List[np.ndarray]) -> bool:
        """Persist a list of encodings to disk and memory."""
        if not encodings:
            return False
        pkl_path = self.encodings_dir / f"{student_id}.pkl"
        try:
            with open(pkl_path, 'wb') as f:
                pickle.dump(encodings, f)
            self.known_encodings[str(student_id)] = encodings
            return True
        except Exception as e:
            print(f"[face_service] Save error: {e}")
            return False

    def unenroll_student(self, student_id: int) -> bool:
        """Remove student's face encodings."""
        pkl_path = self.encodings_dir / f"{student_id}.pkl"
        try:
            if pkl_path.exists():
                pkl_path.unlink()
            self.known_encodings.pop(str(student_id), None)
            return True
        except Exception as e:
            print(f"[face_service] Unenroll error: {e}")
            return False

    # ── Recognition ─────────────────────────────────────────

    def _match_encoding(self, query_enc: np.ndarray) -> RecognitionResult:
        """
        Find best matching student for a query encoding.
        Uses minimum cosine distance across all stored encodings.
        """
        if not self.known_encodings:
            return RecognitionResult(
                is_unknown=True,
                message="No students enrolled yet"
            )

        best_id = None
        best_dist = float('inf')

        for sid, enc_list in self.known_encodings.items():
            for stored_enc in enc_list:
                # Cosine distance = 1 - dot(a,b) (both are unit-normalized)
                dist = float(np.dot(query_enc, stored_enc))
                dist = 1.0 - dist  # Convert similarity → distance
                if dist < best_dist:
                    best_dist = dist
                    best_id = sid

        confidence = max(0.0, 1.0 - best_dist)

        if best_id is not None and best_dist <= self.tolerance:
            return RecognitionResult(
                student_id=int(best_id),
                confidence=confidence,
                is_unknown=False,
                message=f"Recognized (dist={best_dist:.4f})"
            )
        else:
            return RecognitionResult(
                is_unknown=True,
                confidence=confidence,
                message=f"Unknown person (best dist={best_dist:.4f}, threshold={self.tolerance})"
            )

    def recognize_frame(self, frame_bgr: np.ndarray) -> RecognitionResult:
        """Recognize a face in an OpenCV BGR frame."""
        enc = _extract_encoding_from_frame(frame_bgr)
        if enc is None:
            return RecognitionResult(is_unknown=True, message="No face detected in frame")
        return self._match_encoding(enc)

    def recognize_b64(self, image_b64: str) -> RecognitionResult:
        """Recognize a face from a base64 data-URL image."""
        frame = _b64_to_frame(image_b64)
        if frame is None:
            return RecognitionResult(is_unknown=True, message="Failed to decode image")
        return self.recognize_frame(frame)

    # Legacy method kept for backward compatibility with old app.py calls
    def recognize_face(self, image_b64_or_frame, tolerance: float = None):
        """
        Legacy-compatible: accepts base64 string OR OpenCV frame.
        Returns (student_id_or_None, confidence_float).
        """
        if tolerance is not None:
            old_tol = self.tolerance
            self.tolerance = tolerance

        if isinstance(image_b64_or_frame, str):
            result = self.recognize_b64(image_b64_or_frame)
        elif isinstance(image_b64_or_frame, np.ndarray):
            result = self.recognize_frame(image_b64_or_frame)
        else:
            result = RecognitionResult(is_unknown=True, message="Invalid input type")

        if tolerance is not None:
            self.tolerance = old_tol

        if result.is_unknown or result.student_id is None:
            return None, result.confidence
        return result.student_id, result.confidence

    # ── Stats ────────────────────────────────────────────────

    def get_confidence_level(self, confidence: float) -> str:
        """Get UI label for confidence score."""
        if confidence >= 0.90:
            return 'HIGH ✓'
        elif confidence >= 0.80:
            return 'MEDIUM ⚠'
        elif confidence >= 0.70:
            return 'LOW ✗'
        else:
            return 'REJECT'

    def get_enrollment_stats(self) -> Dict:
        """Stats for admin dashboard."""
        total = len(self.known_encodings)
        enc_counts = [len(encs) for encs in self.known_encodings.values()]
        return {
            'total_students': total,
            'total_encodings': sum(enc_counts),
            'avg_encodings_per_student': float(np.mean(enc_counts)) if enc_counts else 0.0,
        }

    # Legacy save_student_faces (called by old face_enroll route)
    def save_student_faces(self, student_id, encodings):
        return self.save_student_encodings(student_id, encodings if isinstance(encodings, list) else [encodings])

    # Legacy get_face_encoding (called by old face_enroll route)
    def get_face_encoding(self, frame_bgr):
        """Returns (encoding_or_None, bbox_or_None) for backward compat."""
        enc = _extract_encoding_from_frame(frame_bgr)
        return enc, None


# ── Global singleton ─────────────────────────────────────
face_service = FaceService()
