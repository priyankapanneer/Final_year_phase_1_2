import sys
from fastapi.testclient import TestClient
from api.recommendation_api import app

def test_all():
    client = TestClient(app)
    
    pages = [
        ("/", 200, "Dashboard"),
        ("/login", 200, "Sign In"),
        ("/register", 200, "Register"),
        ("/chat", 200, "Copilot"),
        ("/upload", 200, "Document Ingestion"),
        ("/admin/users", 200, "User Access"),
        ("/admin/universities", 200, "University Management"),
        ("/graph", 200, "Knowledge Graph"),
        ("/recommendation", 200, "Recommendations"),
        ("/knowledge-gap", 200, "Knowledge Gap"),
        ("/temporal", 200, "Temporal Insights"),
    ]

    print("=== Testing All 11 HTML Endpoints ===")
    for path, expected_status, text_check in pages:
        res = client.get(path)
        assert res.status_code == expected_status, f"Failed {path}: {res.status_code}"
        assert text_check.lower() in res.text.lower(), f"Failed text check for {path}"
        print(f"[PASS] {path} -> {res.status_code} (Verified '{text_check}')")

    print("\n=== Testing API Endpoints ===")
    api_tests = [
        ("/graph-overview", 200),
        ("/graph-data", 200),
        ("/recommendations/S0001", 200),
        ("/knowledge-gaps", 200),
        ("/temporal-insights", 200),
        ("/api/universities", 200),
        ("/api/admin/users", 200),
    ]
    for path, expected_status in api_tests:
        res = client.get(path)
        assert res.status_code == expected_status, f"Failed API {path}: {res.status_code}"
        print(f"[PASS] API {path} -> {res.status_code}")

    print("\nALL VERIFICATIONS PASSED!")

if __name__ == "__main__":
    test_all()
