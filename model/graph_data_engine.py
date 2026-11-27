import os
import sqlite3
import requests
from dotenv import load_dotenv
from core.database import get_connection

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


# ============================================================
# NEO4J QUERY RUNNER
# ============================================================

def run_query(query, parameters=None):
    if not NEO4J_URI or not NEO4J_USERNAME or not NEO4J_PASSWORD:
        return None

    try:
        url = (
            f"{NEO4J_URI.replace('neo4j+s://', 'https://').replace('neo4j://', 'https://')}"
            f"/db/{NEO4J_DATABASE}/query/v2"
        )
        response = requests.post(
            url,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
            headers={"Content-Type": "application/json"},
            json={"statement": query, "parameters": parameters or {}},
            timeout=15
        )
        if response.status_code in [200, 201, 202]:
            return response.json()
    except Exception as e:
        print(f"[GraphDataEngine Neo4j Notice]: {e}")
    return None


# ============================================================
# COMPREHENSIVE MULTI-TENANT ACADEMIC KNOWLEDGE GRAPH (PERSISTENT & RESILIENT)
# ============================================================

def build_full_knowledge_graph():
    """
    Constructs the interconnected multi-tenant academic graph from SQLite:
    Students, Faculty, Courses, Projects, Skills, and their relationships.
    """
    nodes = {}
    relationships = []

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Universities
        cursor.execute("SELECT * FROM universities")
        for u in cursor.fetchall():
            nodes[u["university_id"]] = {
                "id": u["university_id"],
                "label": "University",
                "name": u["name"],
                "display_name": u["name"],
                "businessId": u["university_id"],
                "nodeType": "University",
                "properties": {"location": u["location"], "domain": u["domain"]}
            }

        # 2. Users (Students, Faculty, Admins)
        cursor.execute("SELECT * FROM users")
        for u in cursor.fetchall():
            role = u["role"]
            label = "Student" if role == "STUDENT" else ("Faculty" if role == "FACULTY" else "Admin")
            uid = u["student_id"] if u["student_id"] else u["username"]

            nodes[uid] = {
                "id": uid,
                "label": label,
                "name": u["name"],
                "display_name": u["name"],
                "businessId": uid,
                "nodeType": label,
                "university_id": u["university_id"],
                "properties": {"email": u["username"], "university_id": u["university_id"]}
            }

            # Connect user to university
            if u["university_id"] in nodes:
                relationships.append({
                    "source": uid,
                    "target": u["university_id"],
                    "type": "AFFILIATED_WITH"
                })

        # 3. Projects
        cursor.execute("SELECT * FROM tenant_projects")
        for p in cursor.fetchall():
            pid = p["project_id"]
            nodes[pid] = {
                "id": pid,
                "label": "Project",
                "name": p["title"],
                "display_name": p["title"],
                "businessId": pid,
                "nodeType": "Project",
                "university_id": p["university_id"],
                "properties": {"domain_area": p["domain_area"], "status": p["status"]}
            }

            if p["university_id"] in nodes:
                relationships.append({
                    "source": pid,
                    "target": p["university_id"],
                    "type": "HOSTED_BY"
                })

        # 4. Courses
        cursor.execute("SELECT * FROM tenant_courses")
        for c in cursor.fetchall():
            cid = c["course_id"]
            nodes[cid] = {
                "id": cid,
                "label": "Course",
                "name": c["name"],
                "display_name": c["name"],
                "businessId": cid,
                "nodeType": "Course",
                "university_id": c["university_id"],
                "properties": {"department": c["department"]}
            }

            if c["university_id"] in nodes:
                relationships.append({
                    "source": cid,
                    "target": c["university_id"],
                    "type": "OFFERED_BY"
                })

        conn.close()
    except Exception as e:
        print(f"[Graph Build DB Error]: {e}")

    # 5. Core Academic Skills
    skills = [
        ("SK_PY", "Python", "Programming"),
        ("SK_ML", "Machine Learning", "AI"),
        ("SK_DL", "Deep Learning", "AI"),
        ("SK_PYTORCH", "PyTorch", "AI Framework"),
        ("SK_CV", "Computer Vision", "Robotics"),
        ("SK_ROS", "ROS Robotics", "Robotics"),
        ("SK_KG", "Neo4j Knowledge Graphs", "Data Science"),
        ("SK_QC", "Quantum Computing", "Quantum Physics"),
        ("SK_IOT", "IoT Sensor Grid", "Embedded Systems"),
        ("SK_CLOUD", "Cloud Microservices", "Cloud Computing"),
        ("SK_AV", "Avionics Telemetry", "Aerospace"),
        ("SK_BMS", "Battery Management (EV)", "Electric Vehicles")
    ]
    for sid, sname, domain in skills:
        nodes[sid] = {
            "id": sid,
            "label": "Skill",
            "name": sname,
            "display_name": sname,
            "businessId": sid,
            "nodeType": "Skill",
            "properties": {"domain": domain}
        }

    # 6. Inter-Entity Academic Semantic Relationships
    # (Student -> Project, Faculty -> Project, Faculty -> Course, Project -> Skill, Course -> Skill, Student -> Skill)
    inter_relations = [
        # Anna University Links
        ("S0001", "P001", "WORKS_ON"),
        ("S0001", "CS101", "ENROLLED_IN"),
        ("S0001", "SK_PY", "HAS_SKILL"),
        ("S0001", "SK_ML", "HAS_SKILL"),
        ("faculty.kumar@annauniv.edu", "P001", "SUPERVISES"),
        ("faculty.kumar@annauniv.edu", "CS101", "TEACHES"),
        ("P001", "SK_PY", "REQUIRES_SKILL"),
        ("P001", "SK_ML", "REQUIRES_SKILL"),
        ("P001", "SK_KG", "REQUIRES_SKILL"),
        ("CS101", "SK_ML", "COVERS_SKILL"),
        ("CS101", "SK_PY", "COVERS_SKILL"),

        ("S0002", "P002", "WORKS_ON"),
        ("S0002", "CS305", "ENROLLED_IN"),
        ("S0002", "SK_PYTORCH", "HAS_SKILL"),
        ("faculty.arul@annauniv.edu", "P002", "SUPERVISES"),
        ("faculty.arul@annauniv.edu", "CS305", "TEACHES"),
        ("P002", "SK_CV", "REQUIRES_SKILL"),
        ("P002", "SK_ROS", "REQUIRES_SKILL"),
        ("P002", "SK_PYTORCH", "REQUIRES_SKILL"),
        ("CS305", "SK_DL", "COVERS_SKILL"),
        ("CS305", "SK_PYTORCH", "COVERS_SKILL"),

        ("S0003", "P003", "WORKS_ON"),
        ("faculty.meena@annauniv.edu", "P003", "SUPERVISES"),
        ("faculty.meena@annauniv.edu", "CS402", "TEACHES"),
        ("P003", "SK_KG", "REQUIRES_SKILL"),
        ("P003", "SK_PY", "REQUIRES_SKILL"),
        ("CS402", "SK_KG", "COVERS_SKILL"),

        # IIT Madras Links
        ("S1001", "P101", "WORKS_ON"),
        ("S1001", "CS601", "ENROLLED_IN"),
        ("faculty.shanthi@iitm.ac.in", "P101", "SUPERVISES"),
        ("faculty.shanthi@iitm.ac.in", "CS601", "TEACHES"),
        ("P101", "SK_QC", "REQUIRES_SKILL"),
        ("P101", "SK_PY", "REQUIRES_SKILL"),

        ("S1002", "P102", "WORKS_ON"),
        ("faculty.narayan@iitm.ac.in", "P102", "SUPERVISES"),
        ("faculty.narayan@iitm.ac.in", "EE502", "TEACHES"),
        ("P102", "SK_CV", "REQUIRES_SKILL"),
        ("P102", "SK_ROS", "REQUIRES_SKILL"),

        # SRM Institute Links
        ("S2001", "P201", "WORKS_ON"),
        ("faculty.suresh@srmist.edu.in", "P201", "SUPERVISES"),
        ("faculty.suresh@srmist.edu.in", "IT204", "TEACHES"),
        ("P201", "SK_IOT", "REQUIRES_SKILL"),
        ("P201", "SK_PY", "REQUIRES_SKILL"),

        ("S2002", "P202", "WORKS_ON"),
        ("faculty.lavanya@srmist.edu.in", "P202", "SUPERVISES"),
        ("faculty.lavanya@srmist.edu.in", "CS302", "TEACHES"),
        ("P202", "SK_CLOUD", "REQUIRES_SKILL"),

        # MIT Campus Links
        ("S3001", "P301", "WORKS_ON"),
        ("faculty.kalai@mitindia.edu", "P301", "SUPERVISES"),
        ("faculty.kalai@mitindia.edu", "AE401", "TEACHES"),
        ("P301", "SK_BMS", "REQUIRES_SKILL"),
        ("P301", "SK_IOT", "REQUIRES_SKILL"),

        ("S3002", "P302", "WORKS_ON"),
        ("faculty.dinesh@mitindia.edu", "P302", "SUPERVISES"),
        ("faculty.dinesh@mitindia.edu", "EC303", "TEACHES"),
        ("P302", "SK_AV", "REQUIRES_SKILL")
    ]

    for src, tgt, rel in inter_relations:
        if src in nodes and tgt in nodes:
            relationships.append({
                "source": src,
                "target": tgt,
                "type": rel
            })

    # 7. Dynamically Ingested Entities from Document Ingestion Agents
    try:
        from core.neo4j_client import MOCK_GRAPH_STORE
        for n in MOCK_GRAPH_STORE.get("nodes", []):
            nid = n.get("id")
            if nid and nid not in nodes:
                nodes[nid] = {
                    "id": nid,
                    "label": n.get("label", "Entity"),
                    "name": n.get("name", nid),
                    "display_name": n.get("name", nid),
                    "businessId": nid,
                    "nodeType": n.get("label", "Entity"),
                    "university_id": n.get("university_id", "GLOBAL"),
                    "properties": {"name": n.get("name", nid), "university_id": n.get("university_id")}
                }
        for r in MOCK_GRAPH_STORE.get("relationships", []):
            s = r.get("source")
            t = r.get("target")
            if s in nodes and t in nodes:
                relationships.append({
                    "source": s,
                    "target": t,
                    "type": r.get("type", "RELATED_TO")
                })
    except Exception as e:
        print(f"[Dynamic Graph Integration Notice]: {e}")

    return nodes, relationships


# ============================================================
# GET GENERAL GRAPH DATA
# ============================================================

def get_graph_data(limit=150):
    """
    Returns general knowledge graph dataset for visualizer.
    """
    # 1. Try Live Neo4j
    query = f"""
    MATCH (a)-[r]->(b)
    RETURN
        elementId(a) AS source_id,
        labels(a)[0] AS source_label,
        coalesce(a.name, a.title, a.student_name, a.faculty_name, 'Unknown') AS source_name,
        coalesce(a.student_id, a.project_id, a.course_id, a.faculty_id, elementId(a)) AS source_business_id,
        properties(a) AS source_properties,
        type(r) AS relationship,
        elementId(b) AS target_id,
        labels(b)[0] AS target_label,
        coalesce(b.name, b.title, b.student_name, b.faculty_name, 'Unknown') AS target_name,
        coalesce(b.student_id, b.project_id, b.course_id, b.faculty_id, elementId(b)) AS target_business_id,
        properties(b) AS target_properties
    LIMIT {int(limit)}
    """
    res = run_query(query)
    if res and "data" in res and res["data"].get("values"):
        nodes = {}
        relationships = []
        fields = res["data"]["fields"]
        for row in res["data"]["values"]:
            item = dict(zip(fields, row))
            src_id = item["source_id"]
            tgt_id = item["target_id"]
            if src_id not in nodes:
                nodes[src_id] = {
                    "id": src_id,
                    "label": item["source_label"],
                    "name": str(item["source_name"]),
                    "display_name": str(item["source_name"]),
                    "businessId": item["source_business_id"],
                    "nodeType": item["source_label"],
                    "properties": item["source_properties"] or {}
                }
            if tgt_id not in nodes:
                nodes[tgt_id] = {
                    "id": tgt_id,
                    "label": item["target_label"],
                    "name": str(item["target_name"]),
                    "display_name": str(item["target_name"]),
                    "businessId": item["target_business_id"],
                    "nodeType": item["target_label"],
                    "properties": item["target_properties"] or {}
                }
            relationships.append({
                "source": src_id,
                "target": tgt_id,
                "type": item["relationship"]
            })
        if nodes:
            return {"nodes": list(nodes.values()), "relationships": relationships}

    # 2. Return Comprehensive Built Graph
    nodes_map, relationships = build_full_knowledge_graph()
    return {
        "nodes": list(nodes_map.values())[:limit],
        "relationships": relationships[:limit * 2]
    }


# ============================================================
# GET ENTITY GRAPH (SEARCH ENGINE)
# ============================================================

def get_entity_graph(entity_id, limit=100):
    """
    Finds the matching entity and retrieves its COMPLETE connected subgraph
    including 1-hop and 2-hop connected nodes and relationships.
    """
    clean_query = str(entity_id).strip().lower()

    # 1. Try Live Neo4j Query first
    cypher_search = f"""
    MATCH (center)
    WHERE toLower(center.student_id) = $q
       OR toLower(center.project_id) = $q
       OR toLower(center.course_id) = $q
       OR toLower(center.faculty_id) = $q
       OR toLower(center.name) CONTAINS $q
       OR toLower(center.title) CONTAINS $q
       OR toLower(center.student_name) CONTAINS $q
       OR toLower(center.faculty_name) CONTAINS $q
    OPTIONAL MATCH (center)-[r]-(connected)
    RETURN
        elementId(center) AS center_id,
        labels(center)[0] AS center_label,
        coalesce(center.name, center.title, center.student_name, center.faculty_name, 'Unknown') AS center_name,
        coalesce(center.student_id, center.project_id, center.course_id, center.faculty_id, elementId(center)) AS center_business_id,
        properties(center) AS center_properties,
        elementId(connected) AS connected_id,
        labels(connected)[0] AS connected_label,
        coalesce(connected.name, connected.title, connected.student_name, connected.faculty_name, 'Unknown') AS connected_name,
        coalesce(connected.student_id, connected.project_id, connected.course_id, connected.faculty_id, elementId(connected)) AS connected_business_id,
        properties(connected) AS connected_properties,
        type(r) AS relationship,
        CASE WHEN startNode(r) = center THEN 'outgoing' ELSE 'incoming' END AS direction
    LIMIT {int(limit)}
    """
    res = run_query(cypher_search, {"q": clean_query})
    if res and "data" in res and res["data"].get("values"):
        nodes = {}
        relationships = []
        center_id = None
        center_business_id = None

        fields = res["data"]["fields"]
        for row in res["data"]["values"]:
            item = dict(zip(fields, row))
            c_id = item["center_id"]
            if center_id is None:
                center_id = c_id
                center_business_id = item["center_business_id"]

            if c_id not in nodes:
                nodes[c_id] = {
                    "id": c_id,
                    "label": item["center_label"],
                    "name": str(item["center_name"]),
                    "display_name": str(item["center_name"]),
                    "businessId": item["center_business_id"],
                    "nodeType": item["center_label"],
                    "properties": item["center_properties"] or {}
                }

            conn_id = item["connected_id"]
            if conn_id:
                if conn_id not in nodes:
                    nodes[conn_id] = {
                        "id": conn_id,
                        "label": item["connected_label"],
                        "name": str(item["connected_name"]),
                        "display_name": str(item["connected_name"]),
                        "businessId": item["connected_business_id"],
                        "nodeType": item["connected_label"],
                        "properties": item["connected_properties"] or {}
                    }
                src = c_id if item["direction"] == "outgoing" else conn_id
                tgt = conn_id if item["direction"] == "outgoing" else c_id
                relationships.append({
                    "source": src,
                    "target": tgt,
                    "type": item["relationship"]
                })

        if center_id and nodes:
            return {
                "center": center_id,
                "center_business_id": center_business_id,
                "nodes": list(nodes.values()),
                "relationships": relationships
            }

    # 2. Resilient Multi-Tenant Knowledge Graph Traversal
    all_nodes, all_relationships = build_full_knowledge_graph()

    # Find matching center node(s)
    matching_center_id = None

    # Priority 1: Exact ID match (e.g. S0001, P001, CS101, UNI_ANNA)
    for nid, node in all_nodes.items():
        if nid.lower() == clean_query or str(node.get("businessId", "")).lower() == clean_query:
            matching_center_id = nid
            break

    # Priority 2: Substring match in name or title (e.g. "Kumar", "Smart Campus", "Python", "Drone")
    if not matching_center_id:
        for nid, node in all_nodes.items():
            name_val = str(node.get("name", "")).lower()
            disp_val = str(node.get("display_name", "")).lower()
            if clean_query in name_val or clean_query in disp_val:
                matching_center_id = nid
                break

    # Priority 3: Word token matching (e.g. "Dr. Kumar" matches "Dr. K. Kumar")
    if not matching_center_id:
        tokens = [w for w in clean_query.replace(".", " ").replace(",", " ").replace("(", " ").replace(")", " ").split() if len(w) > 1]
        if tokens:
            for nid, node in all_nodes.items():
                target_str = f"{nid} {node.get('name', '')} {node.get('display_name', '')}".lower()
                if all(t in target_str for t in tokens):
                    matching_center_id = nid
                    break

    # Priority 4: Search across properties (e.g. email, department, domain)
    if not matching_center_id:
        for nid, node in all_nodes.items():
            props_str = " ".join(str(v).lower() for v in node.get("properties", {}).values())
            if clean_query in props_str:
                matching_center_id = nid
                break

    # If still not found, return empty set rather than isolated empty node
    if not matching_center_id:
        return {
            "center": None,
            "center_business_id": None,
            "nodes": [],
            "relationships": [],
            "message": f"Entity '{entity_id}' not found in Knowledge Graph."
        }

    # Extract 1-hop and 2-hop connected nodes & relationships
    result_nodes = {matching_center_id: all_nodes[matching_center_id]}
    result_relationships = []
    hop1_neighbors = set()

    for rel in all_relationships:
        if rel["source"] == matching_center_id:
            tgt = rel["target"]
            hop1_neighbors.add(tgt)
            if tgt in all_nodes:
                result_nodes[tgt] = all_nodes[tgt]
            result_relationships.append(rel)
        elif rel["target"] == matching_center_id:
            src = rel["source"]
            hop1_neighbors.add(src)
            if src in all_nodes:
                result_nodes[src] = all_nodes[src]
            result_relationships.append(rel)

    # Add relevant 2-hop edges between the neighbors themselves for complete rich graph visualization
    for rel in all_relationships:
        src, tgt = rel["source"], rel["target"]
        if src in hop1_neighbors and tgt in hop1_neighbors:
            if rel not in result_relationships:
                result_relationships.append(rel)
                if src in all_nodes:
                    result_nodes[src] = all_nodes[src]
                if tgt in all_nodes:
                    result_nodes[tgt] = all_nodes[tgt]

    return {
        "center": matching_center_id,
        "center_business_id": all_nodes[matching_center_id].get("businessId", matching_center_id),
        "nodes": list(result_nodes.values()),
        "relationships": result_relationships
    }
