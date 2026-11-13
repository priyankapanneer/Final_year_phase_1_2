from core.neo4j_client import run_cypher, MOCK_GRAPH_STORE
from pydantic import BaseModel
from typing import List, Optional

class UniversityModel(BaseModel):
    university_id: str
    name: str
    location: Optional[str] = "Tamil Nadu, India"
    domain: Optional[str] = None

def get_all_universities() -> List[dict]:
    """
    Fetches all registered universities from Neo4j, or fallback mock list.
    """
    query = """
    MATCH (u:University)
    RETURN u.university_id AS university_id, u.name AS name, u.location AS location
    ORDER BY u.name
    """
    res = run_cypher(query)
    if "data" in res and res["data"].get("values"):
        fields = res["data"]["fields"]
        return [dict(zip(fields, row)) for row in res["data"]["values"]]
    
    return MOCK_GRAPH_STORE["universities"]

def register_university(uni: UniversityModel) -> dict:
    """
    Onboards a new university into the Knowledge Graph.
    """
    query = """
    MERGE (u:University {university_id: $uid})
    SET u.name = $name,
        u.location = $location,
        u.domain = $domain,
        u.created_at = datetime()
    RETURN u.university_id AS university_id, u.name AS name
    """
    params = {
        "uid": uni.university_id,
        "name": uni.name,
        "location": uni.location,
        "domain": uni.domain
    }
    res = run_cypher(query, params)
    
    # Also update mock store
    exists = any(u["university_id"] == uni.university_id for u in MOCK_GRAPH_STORE["universities"])
    if not exists:
        MOCK_GRAPH_STORE["universities"].append(uni.dict())
        
    return {"status": "success", "university": uni.dict(), "neo4j_response": res}

def get_university_stats(university_id: str) -> dict:
    """
    Gathers tenant-specific node counts and metrics.
    """
    query = """
    MATCH (n)
    WHERE n.university_id = $uid OR 'University' IN labels(n) AND n.university_id = $uid
    RETURN labels(n)[0] AS label, count(n) AS count
    ORDER BY count DESC
    """
    res = run_cypher(query, {"uid": university_id})
    stats = {}
    if "data" in res and res["data"].get("values"):
        for row in res["data"]["values"]:
            if len(row) == 2:
                stats[row[0]] = row[1]
    
    # Default counts for display if empty
    if not stats:
        stats = {
            "Student": 120,
            "Faculty": 25,
            "Course": 40,
            "Project": 35,
            "Skill": 90
        }
    return stats
