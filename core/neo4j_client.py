import os
import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# In-memory mock store fallback for local development or when Neo4j is offline
MOCK_GRAPH_STORE = {
    "universities": [
        {"university_id": "UNI_ANNA", "name": "Anna University", "location": "Chennai, Tamil Nadu"},
        {"university_id": "UNI_IITM", "name": "IIT Madras", "location": "Chennai, Tamil Nadu"},
        {"university_id": "UNI_SRM", "name": "SRM Institute of Science and Technology", "location": "Kattankulathur, Tamil Nadu"}
    ],
    "nodes": [],
    "relationships": []
}

def get_query_url():
    if not NEO4J_URI:
        return None
    host = NEO4J_URI.replace("neo4j+s://", "").replace("neo4j://", "").replace("https://", "")
    return f"https://{host}/db/{NEO4J_DATABASE}/query/v2"

def run_cypher(statement: str, parameters: dict = None) -> dict:
    """
    Executes a Cypher query using Neo4j HTTP Query API v2 with parameters.
    Falls back gracefully if offline or unconfigured.
    """
    query_url = get_query_url()
    
    if query_url and NEO4J_USERNAME and NEO4J_PASSWORD:
        try:
            payload = {"statement": statement}
            if parameters:
                payload["parameters"] = parameters
            
            response = requests.post(
                query_url,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                return response.json()
            else:
                print(f"[Neo4j Error] Status {response.status_code}: {response.text}")
                return {"error": response.text, "data": {"fields": [], "values": []}}
        except Exception as e:
            print(f"[Neo4j Request Exception]: {e}")
            return {"error": str(e), "data": {"fields": [], "values": []}}
    
    # Offline / Fallback mode
    print(f"[Neo4j Fallback Mode] Query intercepted: {statement[:80]}...")
    return {
        "fallback": True,
        "data": {
            "fields": ["result"],
            "values": [["Operation recorded in mock store"]]
        }
    }

def init_multi_tenant_constraints():
    """
    Applies multi-tenant constraints in Neo4j to ensure IDs are unique per university.
    """
    constraints = [
        """
        CREATE CONSTRAINT university_id_unique IF NOT EXISTS
        FOR (u:University)
        REQUIRE u.university_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT student_tenant_unique IF NOT EXISTS
        FOR (s:Student)
        REQUIRE (s.university_id, s.student_id) IS UNIQUE
        """,
        """
        CREATE CONSTRAINT faculty_tenant_unique IF NOT EXISTS
        FOR (f:Faculty)
        REQUIRE (f.university_id, f.faculty_id) IS UNIQUE
        """,
        """
        CREATE CONSTRAINT course_tenant_unique IF NOT EXISTS
        FOR (c:Course)
        REQUIRE (c.university_id, c.course_id) IS UNIQUE
        """,
        """
        CREATE CONSTRAINT project_tenant_unique IF NOT EXISTS
        FOR (p:Project)
        REQUIRE (p.university_id, p.project_id) IS UNIQUE
        """
    ]
    results = []
    for c in constraints:
        res = run_cypher(c)
        results.append(res)
    return results

def seed_default_universities():
    """
    Seeds default universities into Neo4j if they don't already exist.
    """
    query = """
    UNWIND $universities AS uni
    MERGE (u:University {university_id: uni.university_id})
    SET u.name = uni.name,
        u.location = uni.location,
        u.updated_at = datetime()
    RETURN u.university_id AS id, u.name AS name
    """
    return run_cypher(query, {"universities": MOCK_GRAPH_STORE["universities"]})
