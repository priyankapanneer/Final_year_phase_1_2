import os
import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")


# ============================================================
# NEO4J QUERY
# ============================================================

def run_query(query, parameters=None):
    url = (
        f"{NEO4J_URI.replace('neo4j+s://', 'https://')}"
        f"/db/{NEO4J_DATABASE}/query/v2"
    )

    response = requests.post(
        url,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        headers={"Content-Type": "application/json"},
        json={
            "statement": query,
            "parameters": parameters or {}
        }
    )

    response.raise_for_status()
    return response.json()


# ============================================================
# GET DISPLAY NAME
# ============================================================

def get_display_name_expression(variable):
    return f"""
        coalesce(
            {variable}.student_name,
            {variable}.course_name,
            {variable}.faculty_name,
            {variable}.skill_name,
            {variable}.project_name,
            {variable}.title,
            {variable}.topic,
            {variable}.domain_name,
            {variable}.student_id,
            {variable}.course_id,
            {variable}.faculty_id,
            {variable}.skill_id,
            {variable}.project_id,
            {variable}.publication_id,
            'Unknown'
        )
    """


# ============================================================
# GET GENERAL GRAPH DATA
# ============================================================

def get_graph_data(limit=150):

    query = f"""
    MATCH (a)-[r]->(b)

    RETURN
        elementId(a) AS source_id,
        labels(a)[0] AS source_label,

        {get_display_name_expression("a")} AS source_name,

        coalesce(
            a.student_id,
            a.course_id,
            a.faculty_id,
            a.skill_id,
            a.project_id,
            a.publication_id,
            a.topic,
            a.domain_name
        ) AS source_business_id,

        properties(a) AS source_properties,

        type(r) AS relationship,

        elementId(b) AS target_id,
        labels(b)[0] AS target_label,

        {get_display_name_expression("b")} AS target_name,

        coalesce(
            b.student_id,
            b.course_id,
            b.faculty_id,
            b.skill_id,
            b.project_id,
            b.publication_id,
            b.topic,
            b.domain_name
        ) AS target_business_id,

        properties(b) AS target_properties

    LIMIT {int(limit)}
    """

    result = run_query(query)

    if "data" not in result:
        return {
            "nodes": [],
            "relationships": []
        }

    fields = result["data"]["fields"]
    values = result["data"]["values"]

    rows = [
        dict(zip(fields, row))
        for row in values
    ]

    nodes = {}
    relationships = []

    for row in rows:

        source_id = row["source_id"]
        target_id = row["target_id"]

        # ----------------------------------------------------
        # SOURCE NODE
        # ----------------------------------------------------

        if source_id not in nodes:

            nodes[source_id] = {
                "id": source_id,
                "label": row["source_label"],
                "name": str(row["source_name"]),
                "display_name": str(row["source_name"]),
                "businessId": row["source_business_id"],
                "nodeType": row["source_label"],
                "properties": row["source_properties"] or {}
            }

        # ----------------------------------------------------
        # TARGET NODE
        # ----------------------------------------------------

        if target_id not in nodes:

            nodes[target_id] = {
                "id": target_id,
                "label": row["target_label"],
                "name": str(row["target_name"]),
                "display_name": str(row["target_name"]),
                "businessId": row["target_business_id"],
                "nodeType": row["target_label"],
                "properties": row["target_properties"] or {}
            }

        # ----------------------------------------------------
        # RELATIONSHIP
        # ----------------------------------------------------

        relationships.append({
            "source": source_id,
            "target": target_id,
            "type": row["relationship"]
        })

    return {
        "nodes": list(nodes.values()),
        "relationships": relationships
    }


# ============================================================
# GET ENTITY GRAPH
# ============================================================

def get_entity_graph(entity_id, limit=100):

    query = f"""
    MATCH (center)

    WHERE
        center.student_id = $entity_id
        OR center.course_id = $entity_id
        OR center.faculty_id = $entity_id
        OR center.skill_id = $entity_id
        OR center.project_id = $entity_id
        OR center.publication_id = $entity_id
        OR center.topic = $entity_id
        OR center.domain_name = $entity_id
        OR center.student_name = $entity_id
        OR center.course_name = $entity_id
        OR center.faculty_name = $entity_id
        OR center.skill_name = $entity_id
        OR center.project_name = $entity_id
        OR center.title = $entity_id

    OPTIONAL MATCH (center)-[r]-(connected)

    WITH center, r, connected
    LIMIT {int(limit)}

    RETURN
        elementId(center) AS center_id,

        labels(center)[0] AS center_label,

        {get_display_name_expression("center")}
            AS center_name,

        coalesce(
            center.student_id,
            center.course_id,
            center.faculty_id,
            center.skill_id,
            center.project_id,
            center.publication_id,
            center.topic,
            center.domain_name
        ) AS center_business_id,

        properties(center) AS center_properties,

        elementId(connected) AS connected_id,

        labels(connected)[0] AS connected_label,

        {get_display_name_expression("connected")}
            AS connected_name,

        coalesce(
            connected.student_id,
            connected.course_id,
            connected.faculty_id,
            connected.skill_id,
            connected.project_id,
            connected.publication_id,
            connected.topic,
            connected.domain_name
        ) AS connected_business_id,

        properties(connected) AS connected_properties,

        type(r) AS relationship,

        CASE
            WHEN startNode(r) = center
            THEN 'outgoing'
            ELSE 'incoming'
        END AS direction
    """

    result = run_query(
        query,
        {
            "entity_id": entity_id
        }
    )

    if "data" not in result:
        return {
            "center": None,
            "nodes": [],
            "relationships": []
        }

    fields = result["data"]["fields"]
    values = result["data"]["values"]

    rows = [
        dict(zip(fields, row))
        for row in values
    ]

    if not rows:
        return {
            "center": None,
            "nodes": [],
            "relationships": []
        }

    nodes = {}
    relationships = []

    # ========================================================
    # CENTER NODE
    # ========================================================

    first = rows[0]

    center_id = first["center_id"]

    center_node = {
        "id": center_id,
        "label": first["center_label"],
        "name": str(first["center_name"]),
        "display_name": str(first["center_name"]),
        "businessId": first["center_business_id"],
        "nodeType": first["center_label"],
        "properties": first["center_properties"] or {}
    }

    nodes[center_id] = center_node

    # ========================================================
    # CONNECTED NODES
    # ========================================================

    for row in rows:

        connected_id = row["connected_id"]

        if connected_id is None:
            continue

        if connected_id not in nodes:

            nodes[connected_id] = {
                "id": connected_id,
                "label": row["connected_label"],
                "name": str(row["connected_name"]),
                "display_name": str(row["connected_name"]),
                "businessId": row["connected_business_id"],
                "nodeType": row["connected_label"],
                "properties": row["connected_properties"] or {}
            }

        # ----------------------------------------------------
        # Relationship direction
        # ----------------------------------------------------

        if row["direction"] == "outgoing":

            source = center_id
            target = connected_id

        else:

            source = connected_id
            target = center_id

        relationships.append({
            "source": source,
            "target": target,
            "type": row["relationship"]
        })

    return {
        "center": center_id,
        "center_business_id": first["center_business_id"],
        "nodes": list(nodes.values()),
        "relationships": relationships
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 70)
    print("ACADGRAPH GRAPH DATA ENGINE TEST")
    print("=" * 70)

    print("\nTesting general graph...")

    graph = get_graph_data(20)

    print(f"Nodes: {len(graph['nodes'])}")
    print(f"Relationships: {len(graph['relationships'])}")

    for node in graph["nodes"][:10]:

        print(
            f"{node['label']} | "
            f"{node['display_name']} | "
            f"{node['businessId']}"
        )

    print("\nTesting entity graph for S0001...")

    entity_graph = get_entity_graph("S0001")

    print(
        f"Center: "
        f"{entity_graph['center_business_id']}"
    )

    print(
        f"Nodes: "
        f"{len(entity_graph['nodes'])}"
    )

    print(
        f"Relationships: "
        f"{len(entity_graph['relationships'])}"
    )

    for relationship in entity_graph["relationships"][:10]:

        print(
            f"{relationship['source']} "
            f"--{relationship['type']}--> "
            f"{relationship['target']}"
        )

    print("\nTest completed.")