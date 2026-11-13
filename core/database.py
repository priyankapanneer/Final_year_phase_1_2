import sqlite3
import os
import hashlib

DB_FILE = os.path.join("core", "acadgraph.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(plain_password: str) -> str:
    salt = "acadgraph_salt_v1"
    return hashlib.sha256((plain_password + salt).encode('utf-8')).hexdigest()

def init_db():
    """
    Initializes SQLite tables for users, universities, and activity logs.
    Guarantees zero-loss persistence across server restarts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Universities Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS universities (
        university_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT,
        domain TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        hashed_password TEXT NOT NULL,
        role TEXT NOT NULL,
        university_id TEXT NOT NULL,
        student_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (university_id) REFERENCES universities (university_id)
    );
    """)

    # Ingestion & Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id TEXT NOT NULL,
        username TEXT NOT NULL,
        document_snippet TEXT,
        entities_count INTEGER,
        triplets_count INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed Default Universities if empty
    cursor.execute("SELECT COUNT(*) AS cnt FROM universities;")
    if cursor.fetchone()["cnt"] == 0:
        default_unis = [
            ("UNI_ANNA", "Anna University", "Chennai, Tamil Nadu", "annauniv.edu"),
            ("UNI_IITM", "IIT Madras", "Chennai, Tamil Nadu", "iitm.ac.in"),
            ("UNI_SRM", "SRM Institute of Science & Technology", "Kattankulathur, Tamil Nadu", "srmist.edu.in"),
            ("UNI_MIT", "Madras Institute of Technology", "Chromepet, Chennai", "mitindia.edu")
        ]
        cursor.executemany("INSERT INTO universities (university_id, name, location, domain) VALUES (?, ?, ?, ?)", default_unis)

    # Seed Default Users if empty
    cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
    if cursor.fetchone()["cnt"] == 0:
        default_users = [
            ("superadmin@acadgraph.io", "Global Platform Admin", hash_password("admin123"), "SUPER_ADMIN", "ALL", None),
            ("admin@annauniv.edu", "Dean Academic, Anna University", hash_password("anna123"), "UNIVERSITY_ADMIN", "UNI_ANNA", None),
            ("faculty.kumar@annauniv.edu", "Dr. K. Kumar (Professor CSE)", hash_password("kumar123"), "FACULTY", "UNI_ANNA", None),
            ("student.ravi@annauniv.edu", "Ravi S (Student S0001)", hash_password("ravi123"), "STUDENT", "UNI_ANNA", "S0001"),
            ("admin@iitm.ac.in", "HOD CSE, IIT Madras", hash_password("iitm123"), "UNIVERSITY_ADMIN", "UNI_IITM", None),
            ("student.priya@iitm.ac.in", "Priya R (Student S0002)", hash_password("priya123"), "STUDENT", "UNI_IITM", "S0002")
        ]
        cursor.executemany("INSERT INTO users (username, name, hashed_password, role, university_id, student_id) VALUES (?, ?, ?, ?, ?, ?)", default_users)

    conn.commit()
    conn.close()

# Initialize upon module load
init_db()
