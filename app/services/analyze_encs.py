import pickle
import os
import numpy as np

p = 'face_encodings'
if not os.path.exists(p):
    print("No face_encodings directory found.")
else:
    files = [f for f in os.listdir(p) if f.endswith('.pkl')]
    print(f"Found {len(files)} student encodings.")
    for f in files:
        try:
            with open(os.path.join(p, f), 'rb') as pf:
                data = pickle.load(pf)
                count = len(data) if isinstance(data, list) else 1
                sample_shape = data[0].shape if isinstance(data, list) and len(data) > 0 else (data.shape if isinstance(data, np.ndarray) else "N/A")
                print(f" - {f}: {count} samples, shape: {sample_shape}")
        except Exception as e:
            print(f" - {f}: ERROR - {e}")
