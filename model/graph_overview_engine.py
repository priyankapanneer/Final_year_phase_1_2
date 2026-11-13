import os
import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")


def run_query(query):

    url = (
        f"{NEO4J_URI.replace('neo4j+s://', 'https://')}"
        f"/db/{NEO4J_DATABASE}/query/v2"
    )

    response = requests.post(
        url,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        headers={
            "Content-Type": "application/json"
        },
        json={
            "statement": query
        }
    )

    response.raise_for_status()

    return response.json()


def get_graph_overview():

    query = """
    MATCH (n)
    WITH labels(n)[0] AS label, count(n) AS count
    RETURN label, count
    ORDER BY label
    """

    result = run_query(query)

    if "data" not in result:
        return []

    fields = result["data"]["fields"]
    values = result["data"]["values"]

    return [
        dict(zip(fields, row))
        for row in values
    ]


def get_relationship_count():

    query = """
    MATCH ()-[r]->()
    RETURN count(r) AS relationship_count
    """

    result = run_query(query)

    if "data" not in result:
        return 0

    return result["data"]["values"][0][0]


if __name__ == "__main__":

    print("\nAcadGraph Knowledge Graph Overview")
    print("=" * 50)

    nodes = get_graph_overview()

    total_nodes = 0

    for item in nodes:

        print(
            f"{item['label']}: "
            f"{item['count']}"
        )

        total_nodes += item["count"]

    relationships = get_relationship_count()

    print("-" * 50)

    print(f"Total Nodes: {total_nodes}")
    print(f"Total Relationships: {relationships}")