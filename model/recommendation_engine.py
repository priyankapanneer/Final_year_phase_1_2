import os
import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")


def run_query(query):
    url = f"{NEO4J_URI.replace('neo4j+s://', 'https://')}/db/{NEO4J_DATABASE}/query/v2"

    response = requests.post(
        url,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        headers={"Content-Type": "application/json"},
        json={
            "statement": query
        }
    )

    response.raise_for_status()

    return response.json()


def recommend_projects(student_id, limit=5):

    query = f"""
    MATCH (s:Student {{student_id: "{student_id}"}})
          -[:HAS_SKILL]->(skill:Skill)
          <-[:REQUIRES_SKILL]-(p:Project)

    WHERE NOT EXISTS {{
        MATCH (s)-[:WORKS_ON]->(p)
    }}

    WITH s, p,
         collect(DISTINCT skill) AS matched_skill_nodes,
         collect(DISTINCT skill.skill_name) AS matched_skills

    MATCH (p)-[:REQUIRES_SKILL]->(required:Skill)

    WITH s, p,
         matched_skill_nodes,
         matched_skills,
         count(DISTINCT required) AS total_required_skills

    WITH s, p,
         matched_skill_nodes,
         matched_skills,
         total_required_skills,
         CASE
             WHEN total_required_skills = 0 THEN 0.0
             ELSE 100.0 * size(matched_skills) / total_required_skills
         END AS skill_match_score

    OPTIONAL MATCH (s)-[:ENROLLED_IN]->(c:Course)
                   -[:RELATED_TO_DOMAIN]->(d:Domain)
                   <-[:HAS_DOMAIN]-(p)

    WITH s, p,
         matched_skill_nodes,
         matched_skills,
         total_required_skills,
         skill_match_score,
         collect(DISTINCT d.domain_name) AS matched_domains,
         count(DISTINCT d) AS domain_evidence_count

    WITH s, p,
         matched_skill_nodes,
         matched_skills,
         total_required_skills,
         skill_match_score,
         matched_domains,
         CASE
             WHEN domain_evidence_count > 0 THEN 100.0
             ELSE 0.0
         END AS course_evidence_score

    UNWIND matched_skill_nodes AS matched_skill

    OPTIONAL MATCH (other:Student)-[:HAS_SKILL]->(matched_skill)

    WITH s, p,
         matched_skills,
         total_required_skills,
         skill_match_score,
         matched_domains,
         course_evidence_score,
         count(DISTINCT other) AS students_with_skill

    WITH s, p,
         matched_skills,
         total_required_skills,
         skill_match_score,
         matched_domains,
         course_evidence_score,
         avg(
             CASE
                 WHEN students_with_skill = 0 THEN 100.0
                 ELSE 100.0 -
                      (100.0 * students_with_skill / 300.0)
             END
         ) AS skill_scarcity_score

    WITH s, p,
         matched_skills,
         total_required_skills,
         skill_match_score,
         matched_domains,
         course_evidence_score,
         skill_scarcity_score,
         (
             0.60 * skill_match_score +
             0.20 * course_evidence_score +
             0.20 * skill_scarcity_score
         ) AS recommendation_score

    WITH *,
         CASE
             WHEN skill_match_score = 100
                  AND course_evidence_score = 100
             THEN
                 "Strong recommendation: all required skills matched and relevant course-domain evidence found."

             WHEN skill_match_score >= 75
                  AND course_evidence_score = 100
             THEN
                 "Good recommendation: strong skill match with relevant course-domain evidence."

             WHEN skill_match_score = 100
             THEN
                 "Strong skill match: all required project skills are available."

             WHEN course_evidence_score = 100
             THEN
                 "Relevant academic-domain evidence found, with partial skill coverage."

             ELSE
                 "Potential recommendation: some required skills are matched."
         END AS recommendation_reason

    RETURN
        s.student_id AS student,
        p.project_id AS project,
        p.project_name AS project_name,
        matched_skills,
        matched_domains,
        total_required_skills,
        round(skill_match_score, 2) AS skill_match_score,
        round(course_evidence_score, 2) AS course_evidence_score,
        round(skill_scarcity_score, 2) AS skill_scarcity_score,
        round(recommendation_score, 2) AS recommendation_score,
        recommendation_reason

    ORDER BY recommendation_score DESC
    LIMIT {limit}
    """

    result = run_query(query)

    return result


if __name__ == "__main__":

    student_id = input("Enter Student ID: ").strip()

    results = recommend_projects(student_id, 5)

    print("\nRecommended Projects")
    print("=" * 60)

    print(results)