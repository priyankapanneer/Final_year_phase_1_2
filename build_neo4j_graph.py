import os
import pandas as pd
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# --------------------------------------------------
# LOAD NEO4J CREDENTIALS
# --------------------------------------------------

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

# Convert neo4j+s:// URI to HTTPS Query API URL
HOST = URI.replace("neo4j+s://", "").replace("neo4j://", "")

QUERY_URL = f"https://{HOST}/db/{DATABASE}/query/v2"

print("Neo4j Query API:")
print(QUERY_URL)


# --------------------------------------------------
# NEO4J QUERY FUNCTION
# --------------------------------------------------

def run_query(statement, parameters=None):

    payload = {
        "statement": statement
    }

    if parameters:
        payload["parameters"] = parameters

    response = requests.post(
        QUERY_URL,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=payload,
        timeout=60
    )

    if response.status_code not in [200, 202]:
        print("Query failed:")
        print(response.text)
        response.raise_for_status()

    return response.json()


# --------------------------------------------------
# LOAD CSV FILE
# --------------------------------------------------

def load_csv(filename):

    path = os.path.join("processed_data", filename)

    df = pd.read_csv(path)

    # Replace NaN with None
    df = df.where(pd.notnull(df), None)

    return df


# --------------------------------------------------
# CREATE CONSTRAINTS
# --------------------------------------------------

print("\nCreating constraints...")

constraints = [

    """
    CREATE CONSTRAINT student_id_unique IF NOT EXISTS
    FOR (s:Student)
    REQUIRE s.student_id IS UNIQUE
    """,

    """
    CREATE CONSTRAINT course_id_unique IF NOT EXISTS
    FOR (c:Course)
    REQUIRE c.course_id IS UNIQUE
    """,

    """
    CREATE CONSTRAINT faculty_id_unique IF NOT EXISTS
    FOR (f:Faculty)
    REQUIRE f.faculty_id IS UNIQUE
    """,

    """
    CREATE CONSTRAINT skill_id_unique IF NOT EXISTS
    FOR (s:Skill)
    REQUIRE s.skill_id IS UNIQUE
    """,

    """
    CREATE CONSTRAINT project_id_unique IF NOT EXISTS
    FOR (p:Project)
    REQUIRE p.project_id IS UNIQUE
    """,

    """
    CREATE CONSTRAINT publication_id_unique IF NOT EXISTS
    FOR (p:Publication)
    REQUIRE p.publication_id IS UNIQUE
    """
]

for constraint in constraints:
    run_query(constraint)

print("Constraints created successfully.")


# --------------------------------------------------
# STUDENTS
# --------------------------------------------------

print("\nLoading students...")

students = load_csv("students.csv")

query = """
UNWIND $rows AS row

MERGE (s:Student {
    student_id: row.student_id
})

SET
    s.student_name = row.student_name,
    s.department = row.department,
    s.year = row.year,
    s.section = row.section,
    s.email = row.email
"""

run_query(query, {
    "rows": students.to_dict("records")
})

print(f"Students loaded: {len(students)}")


# --------------------------------------------------
# COURSES
# --------------------------------------------------

print("\nLoading courses...")

courses = load_csv("courses.csv")

query = """
UNWIND $rows AS row

MERGE (c:Course {
    course_id: row.course_id
})

SET
    c.course_name = row.course_name,
    c.department = row.department,
    c.credits = row.credits
"""

run_query(query, {
    "rows": courses.to_dict("records")
})

print(f"Courses loaded: {len(courses)}")


# --------------------------------------------------
# FACULTY
# --------------------------------------------------

print("\nLoading faculty...")

faculty = load_csv("faculty.csv")

query = """
UNWIND $rows AS row

MERGE (f:Faculty {
    faculty_id: row.faculty_id
})

SET
    f.faculty_name = row.faculty_name,
    f.department = row.department,
    f.designation = row.designation,
    f.specialization = row.specialization
"""

run_query(query, {
    "rows": faculty.to_dict("records")
})

print(f"Faculty loaded: {len(faculty)}")


# --------------------------------------------------
# SKILLS
# --------------------------------------------------

print("\nLoading skills...")

skills = load_csv("skills.csv")

query = """
UNWIND $rows AS row

MERGE (s:Skill {
    skill_id: row.skill_id
})

SET
    s.skill_name = row.skill_name,
    s.category = row.category
"""

run_query(query, {
    "rows": skills.to_dict("records")
})

print(f"Skills loaded: {len(skills)}")


# --------------------------------------------------
# PROJECTS
# --------------------------------------------------

print("\nLoading projects...")

projects = load_csv("projects.csv")

query = """
UNWIND $rows AS row

MERGE (p:Project {
    project_id: row.project_id
})

SET
    p.project_name = row.project_name,
    p.domain = row.domain,
    p.description = row.description,
    p.status = row.status
"""

run_query(query, {
    "rows": projects.to_dict("records")
})

print(f"Projects loaded: {len(projects)}")


# --------------------------------------------------
# PUBLICATIONS
# --------------------------------------------------

print("\nLoading publications...")

publications = load_csv("publications.csv")

query = """
UNWIND $rows AS row

MERGE (p:Publication {
    publication_id: row.publication_id
})

SET
    p.title = row.title,
    p.abstract = row.abstract,
    p.year = row.year,
    p.publication_type = row.publication_type,
    p.topic = row.topic
"""

run_query(query, {
    "rows": publications.to_dict("records")
})

print(f"Publications loaded: {len(publications)}")


# --------------------------------------------------
# ENROLLMENTS
# Student -> Course
# --------------------------------------------------

print("\nCreating ENROLLED_IN relationships...")

enrollments = load_csv("enrollments.csv")

query = """
UNWIND $rows AS row

MATCH (s:Student {
    student_id: row.student_id
})

MATCH (c:Course {
    course_id: row.course_id
})

MERGE (s)-[r:ENROLLED_IN]->(c)

SET r.semester = row.semester
"""

run_query(query, {
    "rows": enrollments.to_dict("records")
})

print(f"ENROLLED_IN relationships: {len(enrollments)}")


# --------------------------------------------------
# TEACHES
# Faculty -> Course
# --------------------------------------------------

print("\nCreating TEACHES relationships...")

teaches = load_csv("teaches.csv")

query = """
UNWIND $rows AS row

MATCH (f:Faculty {
    faculty_id: row.faculty_id
})

MATCH (c:Course {
    course_id: row.course_id
})

MERGE (f)-[:TEACHES]->(c)
"""

run_query(query, {
    "rows": teaches.to_dict("records")
})

print(f"TEACHES relationships: {len(teaches)}")


# --------------------------------------------------
# STUDENT SKILLS
# Student -> Skill
# --------------------------------------------------

print("\nCreating HAS_SKILL relationships...")

student_skills = load_csv("student_skills.csv")

query = """
UNWIND $rows AS row

MATCH (s:Student {
    student_id: row.student_id
})

MATCH (sk:Skill {
    skill_id: row.skill_id
})

MERGE (s)-[r:HAS_SKILL]->(sk)

SET r.proficiency = row.proficiency
"""

run_query(query, {
    "rows": student_skills.to_dict("records")
})

print(f"HAS_SKILL relationships: {len(student_skills)}")


# --------------------------------------------------
# PROJECT SKILLS
# Project -> Skill
# --------------------------------------------------

print("\nCreating REQUIRES_SKILL relationships...")

project_skills = load_csv("project_skills.csv")

query = """
UNWIND $rows AS row

MATCH (p:Project {
    project_id: row.project_id
})

MATCH (sk:Skill {
    skill_id: row.skill_id
})

MERGE (p)-[:REQUIRES_SKILL]->(sk)
"""

run_query(query, {
    "rows": project_skills.to_dict("records")
})

print(f"REQUIRES_SKILL relationships: {len(project_skills)}")


# --------------------------------------------------
# WORKS ON
# Student -> Project
# --------------------------------------------------

print("\nCreating WORKS_ON relationships...")

works_on = load_csv("works_on.csv")

query = """
UNWIND $rows AS row

MATCH (s:Student {
    student_id: row.student_id
})

MATCH (p:Project {
    project_id: row.project_id
})

MERGE (s)-[r:WORKS_ON]->(p)

SET r.role = row.role
"""

run_query(query, {
    "rows": works_on.to_dict("records")
})

print(f"WORKS_ON relationships: {len(works_on)}")


# --------------------------------------------------
# SUPERVISES
# Faculty -> Project
# --------------------------------------------------

print("\nCreating SUPERVISES relationships...")

supervises = load_csv("supervises.csv")

query = """
UNWIND $rows AS row

MATCH (f:Faculty {
    faculty_id: row.faculty_id
})

MATCH (p:Project {
    project_id: row.project_id
})

MERGE (f)-[:SUPERVISES]->(p)
"""

run_query(query, {
    "rows": supervises.to_dict("records")
})

print(f"SUPERVISES relationships: {len(supervises)}")


# --------------------------------------------------
# AUTHORSHIP
# Faculty -> Publication
# --------------------------------------------------

print("\nCreating AUTHORED relationships...")

authorships = load_csv("authorships.csv")

query = """
UNWIND $rows AS row

MATCH (f:Faculty {
    faculty_id: row.faculty_id
})

MATCH (p:Publication {
    publication_id: row.publication_id
})

MERGE (f)-[:AUTHORED]->(p)
"""

run_query(query, {
    "rows": authorships.to_dict("records")
})

print(f"AUTHORED relationships: {len(authorships)}")


# --------------------------------------------------
# PUBLICATION TOPICS
# Publication -> Topic
# --------------------------------------------------

print("\nCreating publication topics...")

publication_topics = load_csv("publication_topics.csv")

query = """
UNWIND $rows AS row

MATCH (p:Publication {
    publication_id: row.publication_id
})

MERGE (t:Topic {
    topic_name: row.topic
})

MERGE (p)-[:HAS_TOPIC]->(t)
"""

run_query(query, {
    "rows": publication_topics.to_dict("records")
})

print(f"HAS_TOPIC relationships: {len(publication_topics)}")


# --------------------------------------------------
# FINAL COUNTS
# --------------------------------------------------

print("\nChecking graph...")

count_query = """
MATCH (n)
RETURN labels(n) AS label, count(n) AS count
ORDER BY label
"""

result = run_query(count_query)

print("\nNode counts:")

for row in result["data"]["values"]:
    print(row)

relationship_query = """
MATCH ()-[r]->()
RETURN type(r) AS relationship, count(r) AS count
ORDER BY relationship
"""

result = run_query(relationship_query)

print("\nRelationship counts:")

for row in result["data"]["values"]:
    print(row)


print("\n========================================")
print("KNOWLEDGE GRAPH CREATED SUCCESSFULLY!")
print("========================================")