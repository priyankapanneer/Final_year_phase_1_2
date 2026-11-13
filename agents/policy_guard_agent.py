from api.auth import UserResponse

class PolicyGuardAgent:
    """
    RBAC & Security Guardrail Agent.
    Validates permissions before any graph read, write, or recommendation action is executed.
    Ensures strict tenant isolation across universities.
    """
    
    ACTION_PERMISSIONS = {
        "READ_GRAPH": ["STUDENT", "FACULTY", "UNIVERSITY_ADMIN", "SUPER_ADMIN"],
        "QUERY_CHATBOT": ["STUDENT", "FACULTY", "UNIVERSITY_ADMIN", "SUPER_ADMIN"],
        "GET_RECOMMENDATIONS": ["STUDENT", "FACULTY", "UNIVERSITY_ADMIN", "SUPER_ADMIN"],
        "UPLOAD_DOCUMENT": ["FACULTY", "UNIVERSITY_ADMIN", "SUPER_ADMIN"],
        "MUTATE_GRAPH": ["FACULTY", "UNIVERSITY_ADMIN", "SUPER_ADMIN"],
        "APPROVE_CURRICULUM": ["UNIVERSITY_ADMIN", "SUPER_ADMIN"],
        "MANAGE_TENANTS": ["SUPER_ADMIN"]
    }

    @classmethod
    def authorize(cls, user: UserResponse, action: str, target_university_id: str = None) -> tuple[bool, str]:
        """
        Returns (is_authorized, reason)
        """
        # Super admin has unrestricted access
        if user.role == "SUPER_ADMIN":
            return True, "Authorized as Super Admin"
        
        # Check action role permissions
        allowed_roles = cls.ACTION_PERMISSIONS.get(action, [])
        if user.role not in allowed_roles:
            return False, f"Action '{action}' is not permitted for role '{user.role}'. Required: {allowed_roles}"
        
        # Check tenant isolation
        if target_university_id and target_university_id != user.university_id:
            return False, f"Cross-tenant violation: User belongs to '{user.university_id}' but attempted access on '{target_university_id}'."
        
        return True, "Authorization granted"
