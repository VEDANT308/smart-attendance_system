import sys
sys.path.insert(0, '.')
print("Testing app import...")
try:
    from database import init_db
    print("  database OK")
except Exception as e:
    print(f"  database FAIL: {e}")

try:
    from services.face_service import face_service
    print(f"  face_service OK, students loaded: {len(face_service.known_encodings)}")
except Exception as e:
    print(f"  face_service FAIL: {e}")

try:
    from app import app
    print("  app OK")
    rules = sorted([r.rule for r in app.url_map.iter_rules()])
    critical = ['/', '/attendance', '/login', '/admin', '/teacher', '/student',
                '/api/face/recognize', '/api/face/enroll', '/api/face/reload']
    for r in critical:
        found = r in rules
        status = "OK" if found else "MISSING"
        print(f"  Route {r!r}: {status}")
except Exception as e:
    print(f"  app FAIL: {e}")
    import traceback; traceback.print_exc()

print("Done.")
