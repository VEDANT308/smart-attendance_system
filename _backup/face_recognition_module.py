
"""
Face Recognition Module using MediaPipe
Optimized for Windows, Linux, and Raspberry Pi
No C++ compilation required - pre-built binaries
"""

import mediapipe as mp
import cv2
import numpy as np
import os
import pickle
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
import threading

class FaceRecognitionEngine:
    """
    Face detection and recognition using MediaPipe
    Provides face encoding and matching capabilities
    """
    
    def __init__(self, encodings_dir='face_encodings'):
        """Initialize MediaPipe face detection and mesh"""
        self.encodings_dir = encodings_dir
        self.known_encodings = {}
        
        # Initialize MediaPipe solutions
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Create face detection and mesh instances
        self.face_detector = self.mp_face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=0.5
        )
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=10,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Create encodings directory
        Path(self.encodings_dir).mkdir(exist_ok=True)
        
        # Load all saved encodings
        self.load_all_encodings()
    
    def load_all_encodings(self):
        """Load all student face encodings from disk"""
        try:
            for filename in os.listdir(self.encodings_dir):
                if filename.endswith('.pkl'):
                    student_id = filename.replace('.pkl', '')
                    filepath = os.path.join(self.encodings_dir, filename)
                    
                    with open(filepath, 'rb') as f:
                        self.known_encodings[student_id] = pickle.load(f)
        except Exception as e:
            print(f"Error loading encodings: {e}")
    
    def get_face_encoding(self, frame):
        """
        Extract face encoding from frame using MediaPipe
        Returns: encoding vector (468 landmarks as flattened array) and bounding box
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return None, None
        
        # Get first face
        landmarks = results.multi_face_landmarks[0]
        
        # Convert landmarks to normalized coordinates and flatten to encoding vector
        h, w = frame.shape[:2]
        encoding = []
        for landmark in landmarks.landmark:
            encoding.extend([landmark.x, landmark.y, landmark.z])
        
        # Get bounding box from face detection
        detection_results = self.face_detector.process(rgb_frame)
        bbox = None
        if detection_results.detections:
            detection = detection_results.detections[0]
            bbox = detection.location_data.relative_bounding_box
        
        return np.array(encoding), bbox
    
    def capture_face(self, student_id, num_samples=5, video_source=0):
        """
        Capture face samples from webcam
        Returns: List of encodings or None if failed
        """
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            print("Error: Cannot open webcam")
            return None
        
        encodings = []
        frame_count = 0
        
        try:
            while len(encodings) < num_samples:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Resize for faster processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                
                # Get face encoding
                encoding, bbox = self.get_face_encoding(small_frame)
                
                if encoding is not None:
                    encodings.append(encoding)
                    print(f"Captured sample {len(encodings)}/{num_samples}")
                    
                    # Draw face rectangle
                    if bbox:
                        h, w = small_frame.shape[:2]
                        x_min = int(bbox.xmin * w)
                        y_min = int(bbox.ymin * h)
                        x_max = int((bbox.xmin + bbox.width) * w)
                        y_max = int((bbox.ymin + bbox.height) * h)
                        cv2.rectangle(small_frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                    
                    # Show frame
                    cv2.imshow('Face Capture', small_frame)
                    cv2.waitKey(500)
                
                frame_count += 1
                if frame_count > 300:  # Timeout after 300 frames
                    break
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        if len(encodings) < num_samples:
            print(f"Warning: Only captured {len(encodings)}/{num_samples} samples")
        
        return encodings if encodings else None
    
    def encode_face(self, image_path):
        """Encode a face from image file"""
        try:
            frame = cv2.imread(image_path)
            if frame is None:
                return None
            
            encoding, _ = self.get_face_encoding(frame)
            return encoding
        except Exception as e:
            print(f"Error encoding face: {e}")
            return None
    
    def save_student_faces(self, student_id, encodings):
        """
        Save averaged face encoding for a student
        Takes multiple encodings and averages them for robustness
        """
        if not encodings or len(encodings) == 0:
            print("Error: No encodings provided")
            return False
        
        try:
            # Average all encodings
            mean_encoding = np.mean(encodings, axis=0)
            
            # Save to pickle file
            filepath = os.path.join(self.encodings_dir, f'{student_id}.pkl')
            with open(filepath, 'wb') as f:
                pickle.dump(mean_encoding, f)
            
            # Update memory
            self.known_encodings[student_id] = mean_encoding
            print(f"Saved face encoding for student {student_id}")
            return True
        except Exception as e:
            print(f"Error saving face encoding: {e}")
            return False
    
    def recognize_face(self, frame, tolerance=0.3):
        """
        Recognize face in frame
        Returns: (student_id, confidence) or (None, 0) if not recognized
        """
        encoding, _ = self.get_face_encoding(frame)
        
        if encoding is None:
            return None, 0
        
        if not self.known_encodings:
            return None, 0
        
        # Compare with all known encodings
        best_match = None
        best_distance = float('inf')
        
        for student_id, known_encoding in self.known_encodings.items():
            # Calculate cosine similarity
            similarity = cosine_similarity(
                encoding.reshape(1, -1),
                known_encoding.reshape(1, -1)
            )[0][0]
            
            distance = 1 - similarity
            
            if distance < best_distance and distance < tolerance:
                best_distance = distance
                best_match = student_id
        
        confidence = max(0, 1 - best_distance) if best_match else 0
        return best_match, confidence
    
    def mark_attendance_via_face(self, frame, subject_id, db):
        """
        Recognize face and mark attendance in database
        Returns: (success, student_id, confidence)
        """
        from datetime import date
        
        student_id, confidence = self.recognize_face(frame)
        
        if student_id is None:
            return False, None, 0
        
        try:
            # Check if already marked today
            today = date.today()
            
            cursor = db.cursor()
            cursor.execute(
                '''SELECT id FROM attendance 
                   WHERE student_id = ? AND subject_id = ? AND date(date) = ?''',
                (student_id, subject_id, today)
            )
            
            if cursor.fetchone():
                return False, student_id, confidence  # Already marked
            
            # Insert attendance
            cursor.execute(
                '''INSERT INTO attendance (student_id, subject_id, date, status)
                   VALUES (?, ?, CURRENT_TIMESTAMP, 'present')''',
                (student_id, subject_id)
            )
            db.commit()
            
            return True, student_id, confidence
        except Exception as e:
            print(f"Error marking attendance: {e}")
            return False, student_id, confidence
    
    def get_face_detection_visualization(self, frame):
        """
        Get frame with face bounding boxes drawn
        Returns: Annotated frame
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detector.process(rgb_frame)
        
        h, w = frame.shape[:2]
        
        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                
                x_min = int(bbox.xmin * w)
                y_min = int(bbox.ymin * h)
                x_max = int((bbox.xmin + bbox.width) * w)
                y_max = int((bbox.ymin + bbox.height) * h)
                
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                
                # Draw confidence
                confidence = detection.score[0]
                cv2.putText(
                    frame, f'{confidence:.2f}',
                    (x_min, y_min - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                )
        
        return frame
    
    def unenroll_student(self, student_id):
        """Remove face profile for a student"""
        try:
            filepath = os.path.join(self.encodings_dir, f'{student_id}.pkl')
            if os.path.exists(filepath):
                os.remove(filepath)
            
            if student_id in self.known_encodings:
                del self.known_encodings[student_id]
            
            return True
        except Exception as e:
            print(f"Error unenrolling student: {e}")
            return False


class CameraStream:
    """Thread-safe camera stream for real-time processing"""
    
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.grabbed, self.frame = self.stream.read()
        self.stopped = False
        self.lock = threading.Lock()
    
    def start(self):
        """Start camera thread"""
        threading.Thread(target=self.update, daemon=True).start()
        return self
    
    def update(self):
        """Keep reading frames in background"""
        while not self.stopped:
            grabbed, frame = self.stream.read()
            with self.lock:
                self.grabbed = grabbed
                self.frame = frame
    
    def read(self):
        """Get current frame"""
        with self.lock:
            return self.grabbed, self.frame
    
    def stop(self):
        """Stop camera"""
        self.stopped = True
        self.stream.release()
