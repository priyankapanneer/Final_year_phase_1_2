import sqlite3
import os
import hashlib

DB_FILE = os.path.join("core", "acadgraph.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(plain_password: str) -> str:
    salt = b"acadgraph_secure_salt_2026"
    return "pbkdf2$" + hashlib.pbkdf2_hmac("sha256", plain_password.encode('utf-8'), salt, 100000).hex()

def init_db():
    """
    Initializes SQLite tables for users, universities, projects, courses, and activity logs.
    Guarantees persistence and exact 1-to-1 matching across university tenants and admins.
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

    # Projects Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tenant_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        domain_area TEXT,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(university_id, project_id)
    );
    """)

    # Courses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tenant_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id TEXT NOT NULL,
        course_id TEXT NOT NULL,
        name TEXT NOT NULL,
        department TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(university_id, course_id)
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

    # Ensure 4 Default Universities
    default_unis = [
        ("UNI_ANNA", "Anna University", "Chennai, Tamil Nadu", "annauniv.edu"),
        ("UNI_IITM", "IIT Madras", "Chennai, Tamil Nadu", "iitm.ac.in"),
        ("UNI_SRM", "SRM Institute of Science & Technology", "Kattankulathur, Tamil Nadu", "srmist.edu.in"),
        ("UNI_MIT", "Madras Institute of Technology", "Chromepet, Chennai", "mitindia.edu")
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO universities (university_id, name, location, domain)
    VALUES (?, ?, ?, ?)
    """, default_unis)

    # Ensure Every University Has Exactly 1 Designated University Admin + Real Faculty & Students
    seed_users = [
        # Platform Super Admin
        ("superadmin@acadgraph.io", "Global Platform Admin", hash_password("admin123"), "SUPER_ADMIN", "ALL", None),

        # 1. Anna University
        ("admin@annauniv.edu", "Dr. J. Arumugam (Registrar & Admin)", hash_password("anna123"), "UNIVERSITY_ADMIN", "UNI_ANNA", None),
        ("faculty.kumar@annauniv.edu", "Dr. K. Kumar (Professor, CSE & AI Lab)", hash_password("kumar123"), "FACULTY", "UNI_ANNA", None),
        ("faculty.arul@annauniv.edu", "Dr. M. Arulselvan (Assoc. Prof, Data Science)", hash_password("arul123"), "FACULTY", "UNI_ANNA", None),
        ("faculty.meena@annauniv.edu", "Dr. S. Meenakshi (Professor, IT Dept)", hash_password("meena123"), "FACULTY", "UNI_ANNA", None),
        ("student.ravi@annauniv.edu", "Ravi S (AI Specialization)", hash_password("ravi123"), "STUDENT", "UNI_ANNA", "S0001"),
        ("student.anitha@annauniv.edu", "Anitha M (Data Science)", hash_password("anitha123"), "STUDENT", "UNI_ANNA", "S0002"),
        ("student.karthik@annauniv.edu", "Karthik V (Robotics & IoT)", hash_password("karthik123"), "STUDENT", "UNI_ANNA", "S0003"),
        ("student.deepa@annauniv.edu", "Deepa R (Cloud Architecture)", hash_password("deepa123"), "STUDENT", "UNI_ANNA", "S0004"),

        # 2. IIT Madras
        ("admin@iitm.ac.in", "Prof. Bhaskar Ramamurthi (Dean & Admin)", hash_password("iitm123"), "UNIVERSITY_ADMIN", "UNI_IITM", None),
        ("faculty.shanthi@iitm.ac.in", "Dr. V. Shanthi (Professor, Computer Science)", hash_password("shanthi123"), "FACULTY", "UNI_IITM", None),
        ("faculty.narayan@iitm.ac.in", "Dr. S. Narayanan (Professor, Electrical Engg)", hash_password("narayan123"), "FACULTY", "UNI_IITM", None),
        ("student.priya@iitm.ac.in", "Priya R (Quantum Computing)", hash_password("priya123"), "STUDENT", "UNI_IITM", "S1001"),
        ("student.arun@iitm.ac.in", "Arun K (Autonomous Systems)", hash_password("arun123"), "STUDENT", "UNI_IITM", "S1002"),
        ("student.sneha@iitm.ac.in", "Sneha M (Deep Learning)", hash_password("sneha123"), "STUDENT", "UNI_IITM", "S1003"),

        # 3. SRM Institute of Science & Technology
        ("admin@srmist.edu.in", "Dr. C. Muthamizhchelvan (VC & Admin)", hash_password("srm123"), "UNIVERSITY_ADMIN", "UNI_SRM", None),
        ("faculty.suresh@srmist.edu.in", "Dr. R. Suresh (Professor, Cloud Systems)", hash_password("suresh123"), "FACULTY", "UNI_SRM", None),
        ("faculty.lavanya@srmist.edu.in", "Dr. P. Lavanya (Assoc. Prof, Cyber Security)", hash_password("lavanya123"), "FACULTY", "UNI_SRM", None),
        ("student.vijay@srmist.edu.in", "Vijay Kumar (Full-Stack Dev)", hash_password("vijay123"), "STUDENT", "UNI_SRM", "S2001"),
        ("student.pooja@srmist.edu.in", "Pooja S (Cyber Intelligence)", hash_password("pooja123"), "STUDENT", "UNI_SRM", "S2002"),

        # 4. Madras Institute of Technology (MIT)
        ("admin@mitindia.edu", "Dr. J. Prakash (Dean & Chief Admin)", hash_password("mit123"), "UNIVERSITY_ADMIN", "UNI_MIT", None),
        ("faculty.kalai@mitindia.edu", "Dr. T. Kalaiselvan (Professor, Avionics)", hash_password("kalai123"), "FACULTY", "UNI_MIT", None),
        ("faculty.dinesh@mitindia.edu", "Dr. G. Dinesh (Assoc. Prof, Embedded Systems)", hash_password("dinesh123"), "FACULTY", "UNI_MIT", None),
        ("student.sanjay@mitindia.edu", "Sanjay M (Avionics & EV)", hash_password("sanjay123"), "STUDENT", "UNI_MIT", "S3001"),
        ("student.nandhini@mitindia.edu", "Nandhini K (Embedded Telemetry)", hash_password("nandhini123"), "STUDENT", "UNI_MIT", "S3002")
    ]
    cursor.executemany("""
    INSERT OR REPLACE INTO users (username, name, hashed_password, role, university_id, student_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, seed_users)

    # Seed Real Projects per University
    seed_projects = [
        # Anna University
        ("UNI_ANNA", "P001", "AI-Based Smart Campus Energy Optimization", "Artificial Intelligence"),
        ("UNI_ANNA", "P002", "Autonomous Drone Navigation & Obstacle Avoidance", "Robotics & CV"),
        ("UNI_ANNA", "P003", "Knowledge Graph Conversational Copilot for Syllabus", "NLP & GraphRAG"),

        # IIT Madras
        ("UNI_IITM", "P101", "Quantum Annealing Algorithm Simulator", "Quantum Computing"),
        ("UNI_IITM", "P102", "Robotics Swarm Cooperative Vision Pipeline", "Robotics & Computer Vision"),

        # SRM Institute
        ("UNI_SRM", "P201", "IoT Precision Agriculture Smart Sensing Grid", "Internet of Things"),
        ("UNI_SRM", "P202", "Cloud-Native Microservices Zero-Trust Security Mesh", "Cloud Computing"),

        # MIT Campus
        ("UNI_MIT", "P301", "Electric Vehicle Smart BMS Telemetry & Diagnostics", "Electric Vehicles"),
        ("UNI_MIT", "P302", "Avionics Real-Time Flight Telemetry System", "Avionics Engineering")
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO tenant_projects (university_id, project_id, title, domain_area)
    VALUES (?, ?, ?, ?)
    """, seed_projects)

    # Seed Real Courses per University
    seed_courses = [
        # Anna University
        ("UNI_ANNA", "CS101", "Machine Learning Foundations", "Computer Science"),
        ("UNI_ANNA", "CS305", "Deep Learning & Neural Networks", "Computer Science"),
        ("UNI_ANNA", "CS402", "Knowledge Graph & Ontology Engineering", "Information Technology"),

        # IIT Madras
        ("UNI_IITM", "CS601", "Advanced Graph Algorithms & Complexity", "Computer Science"),
        ("UNI_IITM", "EE502", "Digital Signal & Image Processing", "Electrical Engineering"),

        # SRM Institute
        ("UNI_SRM", "IT204", "Cloud Infrastructure & Distributed Systems", "Information Technology"),
        ("UNI_SRM", "CS302", "Advanced Database Systems & NoSQL", "Computer Science"),

        # MIT Campus
        ("UNI_MIT", "AE401", "Avionics Systems Architecture", "Aeronautical Engineering"),
        ("UNI_MIT", "EC303", "Embedded Microcontrollers & RTOS Design", "Electronics & Comm")
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO tenant_courses (university_id, course_id, name, department)
    VALUES (?, ?, ?, ?)
    """, seed_courses)

    conn.commit()
    conn.close()

# Initialize upon module load
init_db()
