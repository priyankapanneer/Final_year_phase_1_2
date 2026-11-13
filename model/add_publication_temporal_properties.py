import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

if not all([
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    NEO4J_DATABASE
]):
    raise ValueError("Neo4j environment variables are missing.")

# -----------------------------------------
# Neo4j Query API
# -----------------------------------------

host = (
    NEO4J_URI
    .replace("neo4j+s://", "")
    .replace("neo4j://", "")
)

QUERY_URL = (
    f"https://{host}/db/{NEO4J_DATABASE}/query/v2"
)

HEADERS = {
    "Content-Type": "application/json"
}

AUTH = (
    NEO4J_USERNAME,
    NEO4J_PASSWORD
)


def run_query(cypher, parameters=None):

    payload = {
        "statement": cypher,
        "parameters": parameters or {}
    }

    response = requests.post(
        QUERY_URL,
        json=payload,
        headers=HEADERS,
        auth=AUTH,
        timeout=60
    )

    if response.status_code not in [200, 202]:

        print("\nNeo4j Error:")
        print(response.text)

        return False

    return True


# -----------------------------------------
# Project paths
# -----------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PROCESSED_DATA = os.path.join(
    BASE_DIR,
    "processed_data"
)


# -----------------------------------------
# Load publication data
# -----------------------------------------

print("\n1. Loading publication data...")

publications_file = os.path.join(
    PROCESSED_DATA,
    "publications.csv"
)

publications = pd.read_csv(
    publications_file
)

print(
    f"Loaded {len(publications)} publication records."
)


# -----------------------------------------
# Create publication-year mapping
# -----------------------------------------

publication_records = []

for _, row in publications.iterrows():

    publication_id = str(
        row["publication_id"]
    ).strip()

    year = row["year"]

    if pd.isna(year):
        continue

    publication_records.append({
        "publication_id": publication_id,
        "year": int(year)
    })


print(
    f"Prepared {len(publication_records)} publication-year records."
)


# -----------------------------------------
# Update AUTHORED relationships
# -----------------------------------------

print(
    "\n2. Updating AUTHORED relationships..."
)

cypher_authored = """
UNWIND $records AS record

MATCH (f:Faculty)-[r:AUTHORED]->(p:Publication {
    publication_id: record.publication_id
})

SET r.publication_year = record.year

RETURN count(r) AS updated_relationships
"""

success_authored = run_query(
    cypher_authored,
    {
        "records": publication_records
    }
)

if success_authored:

    print(
        "AUTHORED relationships updated successfully."
    )


# -----------------------------------------
# Update HAS_TOPIC relationships
# -----------------------------------------

print(
    "\n3. Updating HAS_TOPIC relationships..."
)

cypher_topic = """
UNWIND $records AS record

MATCH (p:Publication {
    publication_id: record.publication_id
})-[r:HAS_TOPIC]->(t:Topic)

SET r.publication_year = record.year

RETURN count(r) AS updated_relationships
"""

success_topic = run_query(
    cypher_topic,
    {
        "records": publication_records
    }
)

if success_topic:

    print(
        "HAS_TOPIC relationships updated successfully."
    )


# -----------------------------------------
# Completion
# -----------------------------------------

print("\n==============================================")
print("PUBLICATION TEMPORAL UPDATE COMPLETED")
print("==============================================")

print(
    "\nPublication year was added to existing:"
)

print("- AUTHORED relationships")
print("- HAS_TOPIC relationships")

print("\nNo nodes were deleted.")
print("No relationships were deleted.")
print("The existing graph was not rebuilt.")