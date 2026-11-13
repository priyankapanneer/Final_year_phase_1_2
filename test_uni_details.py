from fastapi.testclient import TestClient
from api.recommendation_api import app

client = TestClient(app)

res = client.get("/api/universities")
print("Status /api/universities:", res.status_code)
unis = res.json()
print("Total universities:", len(unis))

for u in unis:
    uid = u["university_id"]
    stat_res = client.get(f"/api/universities/{uid}/stats")
    stats = stat_res.json()
    detail_res = client.get(f"/api/universities/{uid}/details")
    details = detail_res.json()
    
    print(f"\nUniversity: {u['name']} ({uid})")
    print(f"Stats counts: {stats}")
    print(f"Admins in details ({len(details['admins'])}): {[a['name'] for a in details['admins']]}")
    print(f"Faculty in details ({len(details['faculty'])}): {[f['name'] for f in details['faculty']]}")
    print(f"Students in details ({len(details['students'])}): {[s['student_id'] for s in details['students']]}")
    print(f"Projects in details ({len(details['projects'])}): {[p['title'] for p in details['projects']]}")
    
    # Assert counts match exactly
    assert stats["Admin"] == len(details["admins"])
    assert stats["Faculty"] == len(details["faculty"])
    assert stats["Student"] == len(details["students"])
    assert stats["Project"] == len(details["projects"])
    print("[PASS] Stats counts match details records exactly!")

print("\nALL UNIVERSITY DETAILS & COUNTS MATCH 100%!")
