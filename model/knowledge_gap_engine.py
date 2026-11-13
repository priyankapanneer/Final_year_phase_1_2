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


def detect_knowledge_gaps(limit=10):

    query = f"""
    MATCH (p:Project)-[:REQUIRES_SKILL]->(skill:Skill)

    OPTIONAL MATCH (s:Student)-[:HAS_SKILL]->(skill)

    WITH
        skill,
        count(DISTINCT s) AS student_coverage,
        count(DISTINCT p) AS affected_projects

    WITH
        skill,
        student_coverage,
        affected_projects,
        300.0 AS total_students

    RETURN
        skill.skill_name AS skill,
        student_coverage,
        round(
            100.0 * student_coverage / total_students,
            2
        ) AS coverage_percentage,

        round(
            100.0 *
            (1.0 - toFloat(student_coverage) / total_students),
            2
        ) AS gap_severity,

        affected_projects

    ORDER BY gap_severity DESC, affected_projects DESC

    LIMIT {limit}
    """

    result = run_query(query)

    if "data" not in result:
        return []

    fields = result["data"]["fields"]
    values = result["data"]["values"]

    gaps = []

    for row in values:
        gaps.append(
            dict(zip(fields, row))
        )

    return gaps


if __name__ == "__main__":

    gaps = detect_knowledge_gaps(10)

    print("\nKnowledge Gaps")
    print("=" * 60)

    for index, gap in enumerate(gaps, start=1):

        print(
            f"{index}. {gap['skill']} | "
            f"Coverage: {gap['coverage_percentage']}% | "
            f"Gap Severity: {gap['gap_severity']}% | "
            f"Affected Projects: {gap['affected_projects']}"
        )