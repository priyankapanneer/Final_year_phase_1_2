from agents.policy_guard_agent import PolicyGuardAgent
from agents.document_agent import DocumentAgent
from agents.graph_curator_agent import GraphCuratorAgent
from agents.graph_rag_agent import GraphRAGAgent
from api.auth import UserResponse

class AgentOrchestrator:
    """
    Central Agentic AI Orchestrator for AcadGraph.
    Coordinates PolicyGuard, DocumentAgent, GraphCurator, and GraphRAG agents.
    """

    @classmethod
    def process_uploaded_document(cls, text: str, user: UserResponse, target_university_id: str = None) -> dict:
        """
        Full Agentic Pipeline:
        1. Policy Guard checks permissions
        2. Document Agent extracts entities & relations
        3. Graph Curator merges triples into Neo4j
        """
        # Resolve target university
        resolved_uni = target_university_id or user.university_id
        if resolved_uni == "ALL":
            resolved_uni = "UNI_ANNA"

        # 1. Authorization check
        is_auth, reason = PolicyGuardAgent.authorize(user, "UPLOAD_DOCUMENT", resolved_uni)
        if not is_auth:
            return {
                "success": False,
                "error": reason,
                "status_code": 403
            }

        # 2. Document Extraction
        doc_result = DocumentAgent.process_document(text, resolved_uni)

        # 3. Knowledge Graph Ingestion
        curator_result = GraphCuratorAgent.commit_triplets_to_neo4j(
            doc_result["triplets"], 
            resolved_uni
        )

        return {
            "success": True,
            "university_id": resolved_uni,
            "processed_by_agent": "AcadGraph Multi-Agent Swarm",
            "extraction_stats": {
                "chunks": doc_result["total_chunks"],
                "entities_count": doc_result["entities_found"],
                "triplets_count": doc_result["triplets_found"]
            },
            "entities": doc_result["entities"],
            "triplets": doc_result["triplets"],
            "graph_curator_result": curator_result
        }

    @classmethod
    def process_chat_message(cls, message: str, user: UserResponse) -> dict:
        """
        Routes chat message to GraphRAG agent with policy checks.
        """
        is_auth, reason = PolicyGuardAgent.authorize(user, "QUERY_CHATBOT", user.university_id)
        if not is_auth:
            return {
                "reply": f"Access denied: {reason}",
                "action_taken": "BLOCKED_RBAC"
            }

        return GraphRAGAgent.process_message(message, user)
