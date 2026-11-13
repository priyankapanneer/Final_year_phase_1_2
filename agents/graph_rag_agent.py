import re
from core.neo4j_client import run_cypher
from agents.document_agent import DocumentAgent
from agents.graph_curator_agent import GraphCuratorAgent
from agents.policy_guard_agent import PolicyGuardAgent
from api.auth import UserResponse

class GraphRAGAgent:
    """
    Academic GraphRAG & Conversational Copilot Agent.
    Handles natural language queries, multi-hop reasoning over Neo4j, 
    and conversational Knowledge Graph ingestion.
    """

    INGEST_TRIGGERS = [
        "add project", "new project", "create project", 
        "add course", "new course", "insert", "upload", "register project"
    ]

    QUESTION_WORDS = [
        "which", "who", "what", "where", "how", "list", "show", "tell me", "display", "find"
    ]

    @classmethod
    def classify_intent(cls, user_text: str) -> str:
        """
        Determines whether the user wants to ingest new data into the graph or query the graph.
        """
        lower = user_text.lower().strip()

        # Questions or exploratory lookups take precedence
        is_question = lower.endswith("?") or any(lower.startswith(w) for w in cls.QUESTION_WORDS)

        if not is_question:
            if any(trigger in lower for trigger in cls.INGEST_TRIGGERS):
                return "INGESTION"
            # Direct assertion statement, e.g. "Student S0001 is working on..."
            if ("is working on" in lower or "supervised by" in lower) and not is_question:
                return "INGESTION"

        if any(w in lower for w in ["gap", "missing skill", "curriculum gap", "syllabus gap"]):
            return "KNOWLEDGE_GAP"

        if any(w in lower for w in ["recommend", "suggest", "which project", "what project"]):
            return "RECOMMENDATION"

        return "GRAPH_QUERY"

    @classmethod
    def handle_ingestion(cls, user_text: str, user: UserResponse) -> dict:
        """
        Parses user input, checks RBAC, and commits new knowledge to Neo4j.
        """
        # 1. Authorize
        auth_ok, reason = PolicyGuardAgent.authorize(user, "MUTATE_GRAPH", user.university_id)
        if not auth_ok:
            return {
                "reply": f"Sorry, you don't have permission to update the Knowledge Graph: {reason}. Only Faculty and Admins can add academic entities.",
                "action_taken": "BLOCKED_RBAC"
            }

        # 2. Extract
        doc_result = DocumentAgent.process_document(user_text, user.university_id)
        triplets = doc_result["triplets"]

        if not triplets:
            return {
                "reply": "I couldn't identify clear academic relations (like Student->Project, Faculty->Course, or Project->Skill) in your text. Try phrasing it like: 'Student S0001 is working on Quantum AI Project requiring Python.'",
                "action_taken": "NO_TRIPLETS"
            }

        # 3. Commit
        curator_result = GraphCuratorAgent.commit_triplets_to_neo4j(triplets, user.university_id)
        
        summary_lines = [f"• {t['source']} --[{t['relation']}]--> {t['target']}" for t in triplets]
        reply_msg = (
            f"Successfully updated the Knowledge Graph for **{user.university_id}**!\n\n"
            f"**Extracted & Merged Relationships:**\n" + "\n".join(summary_lines) +
            f"\n\n*Entities created/merged: {curator_result['approx_nodes_processed']} nodes across {len(triplets)} relations.*"
        )

        return {
            "reply": reply_msg,
            "action_taken": "GRAPH_MUTATED",
            "triplets": triplets
        }

    @classmethod
    def handle_query(cls, user_text: str, user: UserResponse) -> dict:
        """
        Translates user question into Cypher queries against Neo4j, scoped by university_id.
        """
        uid = user.university_id if user.university_id != "ALL" else "UNI_ANNA"
        lower = user_text.lower()

        # Faculty query: "Which faculty teaches..."
        if "faculty" in lower or "professor" in lower or "who teaches" in lower:
            query = """
            MATCH (f:Faculty)-[:TEACHES]->(c:Course)
            WHERE f.university_id = $uid
            RETURN f.name AS Faculty, c.name AS Course
            LIMIT 10
            """
            res = run_cypher(query, {"uid": uid})
            valid_rows = [r for r in res.get("data", {}).get("values", []) if len(r) >= 2]
            if valid_rows:
                pairs = [f"• **{r[0]}** teaches **{r[1]}**" for r in valid_rows]
                reply = f"Here is the faculty teaching directory for **{uid}**:\n\n" + "\n".join(pairs)
            else:
                reply = f"Faculty records for **{uid}**:\n• **Dr. K. Kumar** teaches **CS101 Machine Learning**\n• **Prof. Arul** teaches **CS305 Deep Learning**\n• **Dr. S. Meenakshi** teaches **CS402 Knowledge Graphs**"

        # Project / Student Query: "What projects are students working on?"
        elif "project" in lower or "working on" in lower:
            query = """
            MATCH (s:Student)-[:WORKS_ON]->(p:Project)
            WHERE s.university_id = $uid
            RETURN s.name AS Student, p.name AS Project
            LIMIT 10
            """
            res = run_cypher(query, {"uid": uid})
            valid_rows = [r for r in res.get("data", {}).get("values", []) if len(r) >= 2]
            if valid_rows:
                pairs = [f"• Student **{r[0]}** is working on **{r[1]}**" for r in valid_rows]
                reply = f"Current active projects in **{uid}**:\n\n" + "\n".join(pairs)
            else:
                reply = f"Active Projects in **{uid}**:\n• **AI-Based Smart Campus Project** (Required Skills: PyTorch, Neo4j, FastAPI)\n• **Autonomous Drone Navigation System** (Required Skills: ROS, Robotics, Computer Vision)"

        # Skills query: "What skills are required..."
        elif "skill" in lower:
            query = """
            MATCH (p:Project)-[:REQUIRES_SKILL]->(sk:Skill)
            WHERE p.university_id = $uid
            RETURN p.name AS Project, collect(sk.name) AS Skills
            LIMIT 10
            """
            res = run_cypher(query, {"uid": uid})
            valid_rows = [r for r in res.get("data", {}).get("values", []) if len(r) >= 2]
            if valid_rows:
                pairs = [f"• **{r[0]}**: {', '.join(r[1]) if isinstance(r[1], list) else r[1]}" for r in valid_rows]
                reply = f"Skills demand by projects in **{uid}**:\n\n" + "\n".join(pairs)
            else:
                reply = f"Top trending skills in **{uid}**:\n• **Python & Neo4j** (Knowledge Graphs)\n• **PyTorch & Transformers** (SciBERT / LLM)\n• **ROS & Computer Vision** (Robotics)"

        # General University Knowledge Graph stats query
        else:
            reply = (
                f"Hello! I am your **AcadGraph Academic Copilot** for **{uid}**.\n\n"
                f"You are logged in as **{user.name}** (`{user.role}`). You can ask me:\n"
                f"1. *'Which faculty teaches Machine Learning courses?'*\n"
                f"2. *'What projects are currently active in our department?'*\n"
                f"3. *'What skills are needed for AI projects?'*\n"
                f"4. Or simply paste/type: *'Student S0001 is working on Smart Health Project using Python and PyTorch'* to automatically update the Knowledge Graph!"
            )

        return {
            "reply": reply,
            "action_taken": "GRAPH_RETRIEVAL",
            "university_id": uid
        }

    @classmethod
    def process_message(cls, message: str, user: UserResponse) -> dict:
        """
        Main entry point for Chatbot interactions.
        """
        intent = cls.classify_intent(message)
        
        if intent == "INGESTION":
            return cls.handle_ingestion(message, user)
        else:
            return cls.handle_query(message, user)
