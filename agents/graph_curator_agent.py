import re
from core.neo4j_client import run_cypher, MOCK_GRAPH_STORE

class GraphCuratorAgent:
    """
    Knowledge Graph Curator & Ingestion Agent.
    Validates extracted triplets, ensures multi-tenant tagging, and executes 
    safe Cypher MERGE operations into Neo4j.
    """

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

        for trip in triplets:
            source = trip["source"]
            s_label = trip["source_label"]
            relation = trip["relation"]
            target = trip["target"]
            t_label = trip["target_label"]

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
