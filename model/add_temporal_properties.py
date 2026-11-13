import os
import pandas as pd
import requests
from dotenv import load_dotenv

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

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

# ============================================================
# NEO4J QUERY API
# ============================================================

host = NEO4J_URI.replace("neo4j+s://", "").replace("neo4j://", "")

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


# ============================================================
# FUNCTION TO RUN CYPHER QUERY
# ============================================================

def run_query(cypher, parameters=None):

    payload = {
        "statement": cypher,
        "parameters": parameters or {}
    }

    response = requests.post(
        QUERY_URL,
        json=payload,
        headers=HEADERS,
        auth=AUTH
    )

    if response.status_code not in [200, 202]:
        print("Neo4j Error:")
        print(response.text)
        return False

    return True


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROCESSED_DATA = os.path.join(
    BASE_DIR,
    "processed_data"
)


# ============================================================
# 1. ADD SEMESTER TO ENROLLED_IN RELATIONSHIPS
# ============================================================

print("\n1. Updating ENROLLED_IN relationships...")

enrollments_file = os.path.join(
    PROCESSED_DATA,
    "enrollments.csv"
)

enrollments = pd.read_csv(enrollments_file)

for _, row in enrollments.iterrows():

    student_id = str(row["student_id"]).strip()
    course_id = str(row["course_id"]).strip()
    semester = str(row["semester"]).strip()

    cypher = """
    MATCH (s:Student {student_id: $student_id})
    MATCH (c:Course {course_id: $course_id})
    MATCH (s)-[r:ENROLLED_IN]->(c)
    SET r.semester = $semester
    """

    run_query(
        cypher,
        {
            "student_id": student_id,
            "course_id": course_id,
            "semester": semester
        }
    )

print(
    f"ENROLLED_IN relationships processed: {len(enrollments)}"
)


# ============================================================
# 2. ADD YEAR TO AUTHORED RELATIONSHIPS
# ============================================================

print("\n2. Updating AUTHORED relationships...")

authorships_file = os.path.join(
    PROCESSED_DATA,
    "authorships.csv"
)

publications_file = os.path.join(
    PROCESSED_DATA,
    "publications.csv"
)

authorships = pd.read_csv(authorships_file)
publications = pd.read_csv(publications_file)

# Create publication_id -> year mapping

publication_years = dict(
    zip(
        publications["publication_id"].astype(str).str.strip(),
        publications["year"]
    )
)

updated_authored = 0

for _, row in authorships.iterrows():

    faculty_id = str(row["faculty_id"]).strip()
    publication_id = str(row["publication_id"]).strip()

    year = publication_years.get(publication_id)

    if pd.isna(year):
        continue

    cypher = """
    MATCH (f:Faculty {faculty_id: $faculty_id})
    MATCH (p:Publication {publication_id: $publication_id})
    MATCH (f)-[r:AUTHORED]->(p)
    SET r.year = $year
    """

    success = run_query(
        cypher,
        {
            "faculty_id": faculty_id,
            "publication_id": publication_id,
            "year": int(year)
        }
    )

    if success:
        updated_authored += 1

print(
    f"AUTHORED relationships processed: {updated_authored}"
)


# ============================================================
# 3. ADD YEAR TO HAS_TOPIC RELATIONSHIPS
# ============================================================

print("\n3. Updating HAS_TOPIC relationships...")

publication_topics_file = os.path.join(
    PROCESSED_DATA,
    "publication_topics.csv"
)

publication_topics = pd.read_csv(
    publication_topics_file
)

updated_topics = 0

for _, row in publication_topics.iterrows():

    publication_id = str(
        row["publication_id"]
    ).strip()

    topic = str(
        row["topic"]
    ).strip()

    year = publication_years.get(publication_id)

    if pd.isna(year):
        continue

    cypher = """
    MATCH (p:Publication {publication_id: $publication_id})
    MATCH (t:Topic {topic_name: $topic})
    MATCH (p)-[r:HAS_TOPIC]->(t)
    SET r.year = $year
    """

    success = run_query(
        cypher,
        {
            "publication_id": publication_id,
            "topic": topic,
            "year": int(year)
        }
    )

    if success:
        updated_topics += 1

print(
    f"HAS_TOPIC relationships processed: {updated_topics}"
)


# ============================================================
# COMPLETION
# ============================================================

print("\n==============================================")
print("TEMPORAL PROPERTY UPDATE COMPLETED")
print("==============================================")

print("\nExisting Neo4j nodes and relationships were not deleted.")
print("Temporal properties were added to existing relationships.")