import os
import datetime
import jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from core.database import get_connection, hash_password

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "acadgraph_super_secret_jwt_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

security = HTTPBearer(auto_error=False)

import hashlib

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("pbkdf2$"):
        return hash_password(plain_password) == hashed_password
    # Backward compatibility with legacy SHA-256 hashes
    legacy_salt = "acadgraph_salt_v1"
    legacy_hash = hashlib.sha256((plain_password + legacy_salt).encode('utf-8')).hexdigest()
    return legacy_hash == hashed_password

class UserResponse(BaseModel):
    username: str
    name: str
    role: str
    university_id: str
    student_id: Optional[str] = None

class CreateUserRequest(BaseModel):
    name: str
    username: str
    password: str
    role: str
    university_id: str
    student_id: Optional[str] = None

class RegisterRequest(BaseModel):
    name: str
    username: str
    password: str
    role: str = "STUDENT"
    university_id: str = "UNI_ANNA"
    student_id: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

def get_user_from_db(username: str) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Backward compatibility demo users mapping
DEMO_USERS_DB = {
    "superadmin@acadgraph.io": {
        "name": "Super System Admin", "username": "superadmin@acadgraph.io",
        "role": "SUPER_ADMIN", "university_id": "ALL"
    },
    "admin.anna@annauniv.edu": {
        "name": "Anna Univ Administrator", "username": "admin.anna@annauniv.edu",
        "role": "UNIVERSITY_ADMIN", "university_id": "UNI_ANNA"
    },
    "faculty.kumar@annauniv.edu": {
        "name": "Dr. K. Kumar (Professor, AI Lab)", "username": "faculty.kumar@annauniv.edu",
        "role": "FACULTY", "university_id": "UNI_ANNA"
    },
    "student.riya@annauniv.edu": {
        "name": "Riya Sharma (B.Tech CS)", "username": "student.riya@annauniv.edu",
        "role": "STUDENT", "university_id": "UNI_ANNA", "student_id": "S0001"
    }
}

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> UserResponse:
    if not credentials or not credentials.credentials:
        allow_guest = os.getenv("ALLOW_DEV_GUEST", "true").lower() == "true"
        if allow_guest:
            return UserResponse(
                username="admin.anna@annauniv.edu",
                name="Dr. J. Arumugam (University Admin)",
                role="UNIVERSITY_ADMIN",
                university_id="UNI_ANNA"
            )
        raise HTTPException(
            status_code=401,
            detail="Authentication token required. Please sign in to access this resource."
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="User not recognized from token")
    
    user_data = get_user_from_db(username) or DEMO_USERS_DB.get(username)
    if not user_data:
        raise HTTPException(status_code=401, detail="User not found in system")
    
    return UserResponse(
        username=user_data["username"],
        name=user_data["name"],
        role=user_data["role"],
        university_id=user_data["university_id"],
        student_id=user_data.get("student_id")
    )

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role == "SUPER_ADMIN":
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: Role '{current_user.role}' lacks permissions. Required: {allowed_roles}"
            )
        return current_user
    return role_checker

def add_user_record(req: CreateUserRequest) -> UserResponse:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE username = ?", (req.username,))
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="User with this academic email already exists")
    
    hashed = hash_password(req.password)
    cursor.execute("""
    INSERT INTO users (username, name, hashed_password, role, university_id, student_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (req.username, req.name, hashed, req.role, req.university_id, req.student_id))
    conn.commit()
    conn.close()
    
    return UserResponse(
        username=req.username,
        name=req.name,
        role=req.role,
        university_id=req.university_id,
        student_id=req.student_id
    )

def list_all_users(filter_uni: Optional[str] = None) -> List[UserResponse]:
    conn = get_connection()
    cursor = conn.cursor()
    if filter_uni and filter_uni != "ALL":
        cursor.execute("SELECT * FROM users WHERE university_id = ? OR university_id = 'ALL' ORDER BY created_at DESC", (filter_uni,))
    else:
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        UserResponse(
            username=r["username"],
            name=r["name"],
            role=r["role"],
            university_id=r["university_id"],
            student_id=r["student_id"]
        ) for r in rows
    ]

def delete_user_record(username: str) -> bool:
    if username == "superadmin@acadgraph.io":
        raise HTTPException(status_code=400, detail="Cannot delete default Super Admin")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    changes = conn.total_changes
    conn.commit()
    conn.close()
    
    if changes == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return True
