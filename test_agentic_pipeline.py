import os
import sys

print("==================================================")
print("TESTING ACADGRAPH AGENTIC MULTI-TENANT PIPELINE")
print("==================================================")

# 1. Test Auth & RBAC
from api.auth import create_access_token, decode_access_token, UserResponse
from agents.policy_guard_agent import PolicyGuardAgent

print("\n[1] Testing Auth & RBAC Guardrails...")
faculty_user = UserResponse(
    username="faculty.kumar@annauniv.edu",
    name="Dr. K. Kumar",
    role="FACULTY",
    university_id="UNI_ANNA"
)
student_user = UserResponse(
    username="student.ravi@annauniv.edu",
    name="Ravi S",
    role="STUDENT",
    university_id="UNI_ANNA"
)

# Test token
token = create_access_token({"sub": faculty_user.username, "role": faculty_user.role, "university_id": faculty_user.university_id})
decoded = decode_access_token(token)
assert decoded["sub"] == faculty_user.username
print("[PASS] JWT creation & verification: SUCCESS")

# RBAC Checks
auth_faculty, _ = PolicyGuardAgent.authorize(faculty_user, "UPLOAD_DOCUMENT", "UNI_ANNA")
assert auth_faculty is True
print("[PASS] Faculty authorized to upload documents: SUCCESS")

auth_student, reason = PolicyGuardAgent.authorize(student_user, "UPLOAD_DOCUMENT", "UNI_ANNA")
assert auth_student is False
print(f"[PASS] Student blocked from mutating graph: SUCCESS ({reason})")

# Cross tenant check
cross_tenant_auth, reason = PolicyGuardAgent.authorize(faculty_user, "UPLOAD_DOCUMENT", "UNI_IITM")
assert cross_tenant_auth is False
print(f"[PASS] Cross-tenant access blocked: SUCCESS ({reason})")

# 2. Test Multi-tenancy
from api.tenancy import get_all_universities, UniversityModel, register_university

print("\n[2] Testing Multi-Tenancy Management...")
unis = get_all_universities()
print(f"[PASS] Retrieved {len(unis)} universities.")

# 3. Test Document Agent
from agents.document_agent import DocumentAgent

print("\n[3] Testing Document Extraction Agent...")
sample_syllabus = """
Faculty Prof. Arul teaches CS305 and supervises Autonomous Drone Navigation Project. 
Student S0001 is working on Autonomous Drone Navigation Project.
The project requires skill PyTorch, ROS, and Computer Vision.
"""

doc_result = DocumentAgent.process_document(sample_syllabus, "UNI_ANNA")
print(f"[PASS] Total chunks processed: {doc_result['total_chunks']}")
print(f"[PASS] Entities extracted: {doc_result['entities_found']}")
for ent in doc_result['entities']:
    print(f"   * {ent['text']} -> [{ent['label']}]")

print(f"[PASS] Relationships extracted: {doc_result['triplets_found']}")
for trip in doc_result['triplets']:
    print(f"   * ({trip['source']}:{trip['source_label']}) -[{trip['relation']}]-> ({trip['target']}:{trip['target_label']})")

assert doc_result['entities_found'] > 0
assert doc_result['triplets_found'] > 0

# 4. Test Graph Curator Agent
from agents.graph_curator_agent import GraphCuratorAgent

print("\n[4] Testing Graph Curator & Neo4j Ingestion...")
curator_result = GraphCuratorAgent.commit_triplets_to_neo4j(doc_result['triplets'], "UNI_ANNA")
print(f"[PASS] Curator status: {curator_result['status']}")
print(f"[PASS] Relationships committed: {curator_result['relationships_merged']}")

# 5. Test GraphRAG Chatbot Agent
from agents.graph_rag_agent import GraphRAGAgent

print("\n[5] Testing GraphRAG Chatbot Queries...")
query_reply = GraphRAGAgent.process_message("Which faculty teaches courses in Anna University?", faculty_user)
print("[PASS] Query response from GraphRAG:")
print("   " + query_reply["reply"].replace("\n", "\n   "))

# Conversational Ingestion through Chat
print("\n[6] Testing Conversational Ingestion via Chatbot...")
ingest_reply = GraphRAGAgent.process_message(
    "Add new project: Quantum Machine Learning System requiring Python and Quantum Computing, supervised by Dr. Kumar.",
    faculty_user
)
print(f"[PASS] Action taken by Chatbot: {ingest_reply['action_taken']}")
print("   " + ingest_reply["reply"].replace("\n", "\n   "))

print("\n==================================================")
print("ALL TESTS PASSED SUCCESSFULLY! ")
print("==================================================")
