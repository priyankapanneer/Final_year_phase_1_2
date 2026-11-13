from core.neo4j_client import run_cypher
from core.database import get_connection, hash_password
from pydantic import BaseModel
from typing import List, Optional

class UniversityModel(BaseModel):
    university_id: str
    name: str
    location: Optional[str] = "Tamil Nadu, India"
    domain: Optional[str] = None
    admin_name: Optional[str] = None
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None

def get_all_universities() -> List[dict]:
    """
    Fetches all registered universities from persistent SQLite DB.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT university_id, name, location, domain, created_at FROM universities ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def register_university(uni: UniversityModel) -> dict:
    """
    Onboards a new university into SQLite, guarantees creation of its designated
    University Admin, and syncs its tenant node into Neo4j.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO universities (university_id, name, location, domain)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(university_id) DO UPDATE SET
        name=excluded.name,
        location=excluded.location,
        domain=excluded.domain
    """, (uni.university_id, uni.name, uni.location, uni.domain))

    # Check if a designated University Admin exists for this university
    cursor.execute("""
    SELECT COUNT(*) AS cnt FROM users WHERE university_id = ? AND role = 'UNIVERSITY_ADMIN'
    """, (uni.university_id,))
    admin_cnt = cursor.fetchone()["cnt"]

    created_admin = None
    if admin_cnt == 0:
        # Guarantee 1-to-1 matching: create University Admin
        fallback_domain = uni.domain if uni.domain else f"{uni.university_id.lower()}.edu"
        admin_email = uni.admin_email if uni.admin_email else f"admin@{fallback_domain}"
        admin_name = uni.admin_name if uni.admin_name else f"{uni.name} Administrator"
        admin_pw = hash_password(uni.admin_password or "admin123")

        cursor.execute("""
        INSERT OR REPLACE INTO users (username, name, hashed_password, role, university_id, student_id)
        VALUES (?, ?, ?, 'UNIVERSITY_ADMIN', ?, NULL)
        """, (admin_email, admin_name, admin_pw, uni.university_id))
        created_admin = {"username": admin_email, "name": admin_name, "role": "UNIVERSITY_ADMIN"}

    conn.commit()
    conn.close()

    # Sync with Neo4j
    cypher_query = """
    MERGE (u:University {university_id: $uid})
    SET u.name = $name,
        u.location = $location,
        u.domain = $domain,
        u.updated_at = datetime()
    RETURN u.university_id AS university_id, u.name AS name
    """
    params = {
        "uid": uni.university_id,
        "name": uni.name,
        "location": uni.location,
        "domain": uni.domain
    }
    neo_res = run_cypher(cypher_query, params)

    return {
        "status": "success",
        "university": uni.dict(),
        "admin_created": created_admin,
        "neo4j_response": neo_res
    }

def get_university_stats(university_id: str) -> dict:
    """
    Gathers accurate, synchronized counts from SQLite database for the tenant.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE university_id = ? AND role = 'UNIVERSITY_ADMIN'", (university_id,))
    admin_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE university_id = ? AND role = 'FACULTY'", (university_id,))
    faculty_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE university_id = ? AND role = 'STUDENT'", (university_id,))
    student_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM tenant_projects WHERE university_id = ?", (university_id,))
    project_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM tenant_courses WHERE university_id = ?", (university_id,))
    course_count = cursor.fetchone()["cnt"]

    conn.close()

    return {
        "Admin": admin_count,
        "Faculty": faculty_count,
        "Student": student_count,
        "Project": project_count,
        "Course": course_count
    }

def get_university_details(university_id: str) -> dict:
    """
    Retrieves complete multi-entity profile and lists for a university tenant:
    Admins, Faculty, Students, Projects, and Courses.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM universities WHERE university_id = ?", (university_id,))
    uni_row = cursor.fetchone()
    if not uni_row:
        conn.close()
        return {"error": f"University '{university_id}' not found"}

    university = dict(uni_row)

    cursor.execute("SELECT username, name, role, university_id, created_at FROM users WHERE university_id = ? AND role = 'UNIVERSITY_ADMIN'", (university_id,))
    admins = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT username, name, role, university_id, created_at FROM users WHERE university_id = ? AND role = 'FACULTY'", (university_id,))
    faculty = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT username, name, role, university_id, student_id, created_at FROM users WHERE university_id = ? AND role = 'STUDENT'", (university_id,))
    students = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT project_id, title, domain_area, status, created_at FROM tenant_projects WHERE university_id = ?", (university_id,))
    projects = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT course_id, name, department, created_at FROM tenant_courses WHERE university_id = ?", (university_id,))
    courses = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "university": university,
        "admins": admins,
        "faculty": faculty,
        "students": students,
        "projects": projects,
        "courses": courses,
        "counts": {
            "admins_count": len(admins),
            "faculty_count": len(faculty),
            "students_count": len(students),
            "projects_count": len(projects),
            "courses_count": len(courses)
        }
    }
