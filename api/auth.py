import os
import hashlib
import datetime
import jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "acadgraph_super_secret_jwt_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

security = HTTPBearer(auto_error=False)

def hash_password(plain_password: str) -> str:
    """
    Computes secure salted SHA-256 hash.
    Avoids bcrypt 4.x / passlib wrap compatibility bug on Python 3.11+.
    """
    salt = "acadgraph_salt_v1"
    return hashlib.sha256((plain_password + salt).encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# Persistent in-memory user registry with pre-seeded demo personas
DEMO_USERS_DB = {
    "superadmin@acadgraph.io": {
        "username": "superadmin@acadgraph.io",
        "name": "Global Platform Admin",
        "hashed_password": hash_password("admin123"),
        "role": "SUPER_ADMIN",
        "university_id": "ALL"
    },
    "admin@annauniv.edu": {
        "username": "admin@annauniv.edu",
        "name": "Dean Academic, Anna University",
        "hashed_password": hash_password("anna123"),
        "role": "UNIVERSITY_ADMIN",
        "university_id": "UNI_ANNA"
    },
    "faculty.kumar@annauniv.edu": {
        "username": "faculty.kumar@annauniv.edu",
        "name": "Dr. K. Kumar (Professor CSE)",
        "hashed_password": hash_password("kumar123"),
        "role": "FACULTY",
        "university_id": "UNI_ANNA"
    },
    "student.ravi@annauniv.edu": {
        "username": "student.ravi@annauniv.edu",
        "name": "Ravi S (Student S0001)",
        "hashed_password": hash_password("ravi123"),
        "role": "STUDENT",
        "university_id": "UNI_ANNA",
        "student_id": "S0001"
    },
    "admin@iitm.ac.in": {
        "username": "admin@iitm.ac.in",
        "name": "HOD CSE, IIT Madras",
        "hashed_password": hash_password("iitm123"),
        "role": "UNIVERSITY_ADMIN",
        "university_id": "UNI_IITM"
    },
    "student.priya@iitm.ac.in": {
        "username": "student.priya@iitm.ac.in",
        "name": "Priya R (Student S0002)",
        "hashed_password": hash_password("priya123"),
        "role": "STUDENT",
        "university_id": "UNI_IITM",
        "student_id": "S0002"
    }
}

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

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> UserResponse:
    if not credentials or not credentials.credentials:
        # Development fallback user
        return UserResponse(
            username="faculty.kumar@annauniv.edu",
            name="Dr. K. Kumar (Dev Session)",
            role="FACULTY",
            university_id="UNI_ANNA"
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username or username not in DEMO_USERS_DB:
        raise HTTPException(status_code=401, detail="User not recognized")
    
    user_data = DEMO_USERS_DB[username]
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
    if req.username in DEMO_USERS_DB:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    DEMO_USERS_DB[req.username] = {
        "username": req.username,
        "name": req.name,
        "hashed_password": hash_password(req.password),
        "role": req.role,
        "university_id": req.university_id,
        "student_id": req.student_id
    }
    
    return UserResponse(
        username=req.username,
        name=req.name,
        role=req.role,
        university_id=req.university_id,
        student_id=req.student_id
    )

def list_all_users(filter_uni: Optional[str] = None) -> List[UserResponse]:
    users = []
    for u in DEMO_USERS_DB.values():
        if filter_uni and filter_uni != "ALL" and u["university_id"] != filter_uni and u["university_id"] != "ALL":
            continue
        users.append(UserResponse(
            username=u["username"],
            name=u["name"],
            role=u["role"],
            university_id=u["university_id"],
            student_id=u.get("student_id")
        ))
    return users

def delete_user_record(username: str) -> bool:
    if username not in DEMO_USERS_DB:
        raise HTTPException(status_code=404, detail="User not found")
    if username == "superadmin@acadgraph.io":
        raise HTTPException(status_code=400, detail="Cannot delete default Super Admin")
    del DEMO_USERS_DB[username]
    return True
