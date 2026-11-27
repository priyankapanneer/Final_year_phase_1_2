import re
from core.neo4j_client import run_cypher, MOCK_GRAPH_STORE

class GraphCuratorAgent:
    """
    Knowledge Graph Curator & Ingestion Agent.
    Validates extracted triplets, ensures multi-tenant tagging, whitelists Cypher elements,
    and executes safe Cypher MERGE operations into Neo4j while persisting to SQLite.
    """

    ALLOWED_LABELS = {
        "STUDENT": "Student",
        "FACULTY": "Faculty",
        "COURSE": "Course",
        "PROJECT": "Project",
        "SKILL": "Skill",
        "TOPIC": "Topic",
        "UNIVERSITY": "University",
        "DEPARTMENT": "Department"
    }

    ALLOWED_RELATIONS = {
        "WORKS_ON", "TEACHES", "SUPERVISES", "REQUIRES_SKILL", 
        "HAS_SKILL", "ENROLLED_IN", "OFFERED_BY", "HOSTED_BY", 
        "AFFILIATED_WITH", "RELATED_TO"
    }

    @classmethod
    def sanitize_id(cls, text: str) -> str:
        """
        Creates a clean alphanumeric ID for Neo4j nodes.
        """
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', text.strip()).upper()
        return clean[:40]

    @classmethod
    def commit_triplets_to_neo4j(cls, triplets: list[dict], university_id: str) -> dict:
        """
        Executes Cypher MERGE commands for each triplet with strict tenant scoping.
        Persists to both Neo4j and SQLite for multi-tenant offline persistence.
        """
        created_nodes = 0
        created_relationships = 0
        logs = []

        # 1. Ensure University node exists
        uni_query = """
        MERGE (u:University {university_id: $uid})
        ON CREATE SET u.name = $uid, u.created_at = datetime()
        RETURN u
        """
        run_cypher(uni_query, {"uid": university_id})

        # 2. SQLite Persistent Synchronization
        try:
            from core.database import get_connection
            conn = get_connection()
            cur = conn.cursor()
            for trip in triplets:
                s_name = str(trip["source"]).strip()
                t_name = str(trip["target"]).strip()
                s_lbl = cls.ALLOWED_LABELS.get(trip.get("source_label", "").upper(), "Entity")
                t_lbl = cls.ALLOWED_LABELS.get(trip.get("target_label", "").upper(), "Entity")
                s_uid = cls.sanitize_id(s_name)
                t_uid = cls.sanitize_id(t_name)

                if s_lbl == "Project":
                    cur.execute("""
                        INSERT OR IGNORE INTO tenant_projects (university_id, project_id, title, domain_area, status)
                        VALUES (?, ?, ?, 'Academic Proposal', 'Active')
                    """, (university_id, s_uid, s_name))
                if t_lbl == "Project":
                    cur.execute("""
                        INSERT OR IGNORE INTO tenant_projects (university_id, project_id, title, domain_area, status)
                        VALUES (?, ?, ?, 'Academic Proposal', 'Active')
                    """, (university_id, t_uid, t_name))

                if s_lbl == "Course":
                    cur.execute("""
                        INSERT OR IGNORE INTO tenant_courses (university_id, course_id, name, department, credits)
                        VALUES (?, ?, ?, 'Computer Science', 3)
                    """, (university_id, s_uid, s_name))
                if t_lbl == "Course":
                    cur.execute("""
                        INSERT OR IGNORE INTO tenant_courses (university_id, course_id, name, department, credits)
                        VALUES (?, ?, ?, 'Computer Science', 3)
                    """, (university_id, t_uid, t_name))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"[GraphCurator SQLite Sync Notice]: {db_err}")

        # 3. Cypher Graph Ingestion with Strict Whitelisting
        for trip in triplets:
            source = trip["source"]
            target = trip["target"]

            # Strict Whitelist Validation
            s_label = cls.ALLOWED_LABELS.get(trip.get("source_label", "").upper(), "Entity")
            t_label = cls.ALLOWED_LABELS.get(trip.get("target_label", "").upper(), "Entity")
            raw_rel = re.sub(r'[^a-zA-Z0-9_]', '_', trip.get("relation", "").upper())
            relation = raw_rel if raw_rel in cls.ALLOWED_RELATIONS else "RELATED_TO"

            s_id = cls.sanitize_id(source)
            t_id = cls.sanitize_id(target)

            # Determine if target or source is a Global node (e.g. Skill is global)
            is_target_global = (t_label == "Skill" or t_label == "Topic")
            is_source_global = (s_label == "Skill" or s_label == "Topic")

            # Cypher template with MERGE
            if is_target_global:
                query = f"""
                MERGE (s:{s_label} {{university_id: $uid, id: $s_id}})
                ON CREATE SET s.name = $s_name, s.created_at = datetime()
                
                MERGE (t:{t_label} {{name: $t_name}})
                ON CREATE SET t.id = $t_id, t.created_at = datetime()
                
                MERGE (s)-[r:{relation}]->(t)
                RETURN type(r)
                """
            elif is_source_global:
                query = f"""
                MERGE (s:{s_label} {{name: $s_name}})
                ON CREATE SET s.id = $s_id, s.created_at = datetime()
                
                MERGE (t:{t_label} {{university_id: $uid, id: $t_id}})
                ON CREATE SET t.name = $t_name, t.created_at = datetime()
                
                MERGE (s)-[r:{relation}]->(t)
                RETURN type(r)
                """
            else:
                query = f"""
                MERGE (s:{s_label} {{university_id: $uid, id: $s_id}})
                ON CREATE SET s.name = $s_name, s.created_at = datetime()
                
                MERGE (t:{t_label} {{university_id: $uid, id: $t_id}})
                ON CREATE SET t.name = $t_name, t.created_at = datetime()
                
                MERGE (s)-[r:{relation}]->(t)
                RETURN type(r)
                """

            params = {
                "uid": university_id,
                "s_id": s_id,
                "s_name": source,
                "t_id": t_id,
                "t_name": target
            }

            res = run_cypher(query, params)
            created_relationships += 1
            created_nodes += 2
            logs.append(f"Merged: ({source}:{s_label}) -[{relation}]-> ({target}:{t_label}) [Tenant: {university_id}]")

            # Record in Mock Store for offline visualization
            MOCK_GRAPH_STORE["nodes"].append({"id": s_id, "label": s_label, "name": source, "university_id": university_id})
            MOCK_GRAPH_STORE["nodes"].append({"id": t_id, "label": t_label, "name": target, "university_id": "GLOBAL" if is_target_global else university_id})
            MOCK_GRAPH_STORE["relationships"].append({
                "source": s_id, "target": t_id, "type": relation, "university_id": university_id
            })

        return {
            "status": "success",
            "university_id": university_id,
            "relationships_merged": created_relationships,
            "approx_nodes_processed": created_nodes,
            "execution_logs": logs
        }
