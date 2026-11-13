import os
import json
from fastapi.testclient import TestClient
from api.recommendation_api import app

client = TestClient(app)

print("=" * 65)
print("LIVE EXECUTION & KNOWLEDGE GRAPH PIPELINE DEMONSTRATION")
print("=" * 65)

# STEP 1: Create a realistic sample academic text file
sample_text_content = """
Anna University Department of Computer Science and Engineering.
Dr. K. Kumar teaches CS101 Advanced Machine Learning.
Student S0001 is enrolled in CS101 and is working on AI-Based Smart Campus Project.
The AI-Based Smart Campus Project requires skills in Python, PyTorch, and Neo4j.
Faculty Prof. Arul supervises Autonomous Drone Navigation Project.
Student S0002 is working on Autonomous Drone Navigation Project which requires ROS, Robotics, and Computer Vision.
"""

file_path = "sample_academic_upload.txt"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(sample_text_content)
print(f"\n[STEP 1] Created sample upload text file: '{file_path}'")
print("-" * 50)
print(sample_text_content.strip())
print("-" * 50)

# STEP 2: Execute Document Upload API
print("\n[STEP 2] Executing /api/upload-document Endpoint...")
print("Triggering DocumentAgent (Chunking + SciBERT NER + Relation Model) -> GraphCuratorAgent (Neo4j Cypher Merge)")

upload_payload = {
    "text": sample_text_content,
    "university_id": "UNI_ANNA",
    "username": "faculty.kumar@annauniv.edu"
}

response = client.post("/api/upload-document", json=upload_payload)
assert response.status_code == 200, f"Upload failed: {response.text}"
data = response.json()

print(f"\n>> Upload Result Status: SUCCESS (200 OK)")
print(f">> Target University Tenant: {data['university_id']}")
print(f">> Chunks Processed: {data['extraction_stats']['chunks']}")
print(f">> Entities Discovered: {data['extraction_stats']['entities_count']}")
print(f">> Triplet Relationships Formed: {data['extraction_stats']['triplets_count']}")

print("\n--- EXTRACTED KNOWLEDGE GRAPH ENTITIES (NODES) ---")
for ent in data["entities"]:
    print(f"  Node: {ent['text']:<35} | Label: (:{ent['label']})")

print("\n--- EXTRACTED KNOWLEDGE GRAPH RELATIONSHIPS (EDGES) ---")
for trip in data["triplets"]:
    print(f"  ({trip['source']}:{trip['source_label']}) --[:{trip['relation']}]--> ({trip['target']}:{trip['target_label']})")

print(f"\n>> Neo4j Curator Status: {data['graph_curator_result']['status']}")
print(f">> Relationships Merged in Neo4j: {data['graph_curator_result']['relationships_merged']}")

# STEP 3: Chatbot Q&A via GraphRAG
print("\n" + "=" * 65)
print("[STEP 3] Testing Agentic Chatbot (GraphRAG Retrieval Query)")
print("=" * 65)

chat_query_1 = {
    "message": "Which faculty teaches Machine Learning courses in Anna University?",
    "username": "student.ravi@annauniv.edu"
}
res_chat_1 = client.post("/api/chat", json=chat_query_1)
print(f">> User Query: '{chat_query_1['message']}'")
print(f">> Chatbot Action Taken: {res_chat_1.json().get('action_taken')}")
print(f">> Chatbot Response:\n{res_chat_1.json().get('reply')}\n")

# STEP 4: Conversational Graph Ingestion via Chatbot
print("=" * 65)
print("[STEP 4] Testing Conversational Ingestion via Chatbot (Text -> KG)")
print("=" * 65)

chat_ingest_query = {
    "message": "Add new project: Blockchain Security Framework requiring Python and Blockchain, supervised by Dr. Kumar.",
    "username": "faculty.kumar@annauniv.edu"
}
res_chat_2 = client.post("/api/chat", json=chat_ingest_query)
print(f">> User Ingestion Input: '{chat_ingest_query['message']}'")
print(f">> Chatbot Action Taken: {res_chat_2.json().get('action_taken')}")
print(f">> Chatbot Response:\n{res_chat_2.json().get('reply')}\n")

# STEP 5: Knowledge Graph Visualization Data
print("=" * 65)
print("[STEP 5] Querying /graph-data for Visualization")
print("=" * 65)

res_graph = client.get("/graph-data")
graph_json = res_graph.json()
print(f">> Total Graph Nodes available for UI: {len(graph_json.get('nodes', []))}")
print(f">> Total Graph Edges available for UI: {len(graph_json.get('relationships', []))}")
print("\nSample Graph Nodes:")
for n in graph_json.get("nodes", [])[:5]:
    print(f"  - Node ID: {n.get('id')}, Label: {n.get('label')}, Name: {n.get('name')}")

print("\n" + "=" * 65)
print("LIVE EXECUTION DEMO COMPLETED SUCCESSFULLY!")
print("=" * 65)
