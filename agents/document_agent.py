import re
import os
import joblib
import warnings
import difflib

# Suppress sklearn unpickle version warnings
warnings.filterwarnings("ignore")

class DocumentAgent:
    """
    Document Ingestion & Knowledge Extraction Agent.
    Transforms raw uploaded text/PDFs into structured academic entities and relations.
    Features Canonical Entity Disambiguation and Fuzzy Deduplication.
    """
    
    _tokenizer = None
    _ner_model = None
    _relation_model = None
    _relation_vectorizer = None
    _models_loaded = False

    COMMON_SKILLS = [
        "Python", "PyTorch", "TensorFlow", "Neo4j", "Graph Database", "Machine Learning", 
        "Deep Learning", "Natural Language Processing", "NLP", "Computer Vision", 
        "Data Science", "SQL", "Cloud Computing", "AWS", "Docker", "Kubernetes", 
        "Robotics", "ROS", "Cybersecurity", "Blockchain", "Quantum Computing", "React", "FastAPI"
    ]

    CANONICAL_SKILL_MAP = {
        "ml": "Machine Learning",
        "deep-learning": "Deep Learning",
        "dl": "Deep Learning",
        "nlp": "Natural Language Processing",
        "cv": "Computer Vision",
        "k8s": "Kubernetes",
        "graph db": "Neo4j",
        "graph database": "Neo4j"
    }

    @classmethod
    def load_models(cls):
        if cls._models_loaded:
            return

        try:
            rel_model_path = os.path.join("model", "relation_model.pkl")
            vec_model_path = os.path.join("model", "relation_vectorizer.pkl")
            if os.path.exists(rel_model_path) and os.path.exists(vec_model_path):
                cls._relation_model = joblib.load(rel_model_path)
                cls._relation_vectorizer = joblib.load(vec_model_path)
        except Exception as e:
            pass

        try:
            ner_path = os.path.join("model", "scibert_ner_model")
            if os.path.exists(ner_path):
                from transformers import AutoTokenizer, AutoModelForTokenClassification
                cls._tokenizer = AutoTokenizer.from_pretrained(ner_path)
                cls._ner_model = AutoModelForTokenClassification.from_pretrained(ner_path)
                cls._ner_model.eval()
        except Exception:
            pass

        cls._models_loaded = True

    @classmethod
    def normalize_entity_name(cls, name: str, label: str) -> str:
        """
        Entity Disambiguation & Canonical Normalization.
        Resolves variations like 'Dr. Kumar' vs 'Prof. K. Kumar', and 'ML' vs 'Machine Learning'.
        """
        clean = name.strip()
        
        if label == "SKILL":
            lower = clean.lower()
            return cls.CANONICAL_SKILL_MAP.get(lower, clean.title() if len(clean) > 3 else clean.upper())

        if label == "FACULTY":
            # Strip standard prefix variations to get canonical name
            canonical = re.sub(r'^(?:Dr\.|Prof\.|Professor|Mr\.|Mrs\.|Ms\.)\s*', '', clean, flags=re.IGNORECASE).strip()
            # Restore standard academic title for uniform presentation
            return f"Dr. {canonical}" if canonical else clean

        if label == "COURSE":
            return clean.upper().replace(" ", "")

        if label == "STUDENT":
            # Canonicalize S0001
            match = re.search(r'S\d{3,5}', clean, re.IGNORECASE)
            return match.group(0).upper() if match else clean

        return clean

    @classmethod
    def fuzzy_deduplicate(cls, entities: list[dict]) -> list[dict]:
        """
        Fuzzy matches close entity variations (85%+ threshold) within the same category.
        """
        unique = []
        for ent in entities:
            norm_name = cls.normalize_entity_name(ent["text"], ent["label"])
            matched = False
            for u in unique:
                if u["label"] == ent["label"]:
                    # Exact or high fuzzy match
                    ratio = difflib.SequenceMatcher(None, norm_name.lower(), u["text"].lower()).ratio()
                    if ratio > 0.85 or norm_name.lower() in u["text"].lower() or u["text"].lower() in norm_name.lower():
                        matched = True
                        break
            if not matched:
                unique.append({"text": norm_name, "label": ent["label"]})
        return unique

    @classmethod
    def chunk_text(cls, text: str, max_chunk_size: int = 500) -> list[str]:
        sentences = re.split(r'(?<=[.!?\n]) +', text.strip())
        chunks = []
        current_chunk = []
        current_len = 0

        for sent in sentences:
            sent_len = len(sent)
            if current_len + sent_len > max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sent]
                current_len = sent_len
            else:
                current_chunk.append(sent)
                current_len += sent_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks if chunks else [text]

    @classmethod
    def extract_entities_hybrid(cls, text: str) -> list[dict]:
        cls.load_models()
        extracted = []

        # 1. Fast Rule-based & Ontology Matching (Sub-second response)
        # Student pattern
        student_matches = re.finditer(r'\b(S\d{3,5}|Student\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', text, re.IGNORECASE)
        for m in student_matches:
            extracted.append({"text": m.group(0), "label": "STUDENT"})

        # Faculty pattern
        faculty_matches = re.finditer(r'\b(?:Dr\.|Prof\.|Professor)\s+[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)?\b', text)
        for m in faculty_matches:
            extracted.append({"text": m.group(0), "label": "FACULTY"})

        # Course pattern
        course_matches = re.finditer(r'\b(?:CS|IT|EC|EE|ME|AI|DS)\d{3,4}\b', text, re.IGNORECASE)
        for m in course_matches:
            extracted.append({"text": m.group(0).upper(), "label": "COURSE"})

        # Project pattern
        project_matches = re.finditer(r'(?:[A-Z][\w\s-]{3,35}?(?:System|Project|Platform|Framework|Model|Pipeline|Detector|Analyzer|Application))', text)
        for m in project_matches:
            p_text = m.group(0).strip()
            if len(p_text) > 5 and not p_text.startswith("The ") and p_text not in ["Machine Learning", "Deep Learning"]:
                extracted.append({"text": p_text, "label": "PROJECT"})

        # Skills
        for skill in cls.COMMON_SKILLS:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                extracted.append({"text": skill, "label": "SKILL"})

        return cls.fuzzy_deduplicate(extracted)

    @classmethod
    def predict_relation(cls, text: str) -> str:
        cls.load_models()
        if cls._relation_model and cls._relation_vectorizer:
            try:
                vec = cls._relation_vectorizer.transform([text])
                return cls._relation_model.predict(vec)[0]
            except Exception:
                pass

        lower = text.lower()
        if any(w in lower for w in ["works on", "working on", "assigned to", "contributing to"]):
            return "WORKS_ON"
        if any(w in lower for w in ["teaches", "instructor", "taught by", "course faculty"]):
            return "TEACHES"
        if any(w in lower for w in ["supervises", "guided by", "supervisor", "mentor"]):
            return "SUPERVISES"
        if any(w in lower for w in ["requires skill", "using", "built with", "skills required", "prerequisite"]):
            return "REQUIRES_SKILL"
        if any(w in lower for w in ["has skill", "proficient in", "knows"]):
            return "HAS_SKILL"
        if any(w in lower for w in ["enrolled in", "registered for", "taking course"]):
            return "ENROLLED_IN"

        return "RELATED_TO"

    @classmethod
    def process_document(cls, text: str, university_id: str) -> dict:
        chunks = cls.chunk_text(text)
        all_entities = []
        triplets = []

        for chunk in chunks:
            entities = cls.extract_entities_hybrid(chunk)
            all_entities.extend(entities)

            students = [e["text"] for e in entities if e["label"] == "STUDENT"]
            faculties = [e["text"] for e in entities if e["label"] == "FACULTY"]
            courses = [e["text"] for e in entities if e["label"] == "COURSE"]
            projects = [e["text"] for e in entities if e["label"] == "PROJECT"]
            skills = [e["text"] for e in entities if e["label"] == "SKILL"]

            # Student -> Project
            for s in students:
                for p in projects:
                    rel = cls.predict_relation(f"{s} is working on {p}")
                    triplets.append({
                        "source": s, "source_label": "Student",
                        "relation": rel if rel != "RELATED_TO" else "WORKS_ON",
                        "target": p, "target_label": "Project"
                    })

            # Faculty -> Course
            for f in faculties:
                for c in courses:
                    rel = cls.predict_relation(f"{f} teaches {c}")
                    triplets.append({
                        "source": f, "source_label": "Faculty",
                        "relation": rel if rel != "RELATED_TO" else "TEACHES",
                        "target": c, "target_label": "Course"
                    })

            # Faculty -> Project
            for f in faculties:
                for p in projects:
                    rel = cls.predict_relation(f"{f} supervises {p}")
                    triplets.append({
                        "source": f, "source_label": "Faculty",
                        "relation": rel if rel != "RELATED_TO" else "SUPERVISES",
                        "target": p, "target_label": "Project"
                    })

            # Project -> Skill
            for p in projects:
                for sk in skills:
                    rel = cls.predict_relation(f"Project {p} requires skill {sk}")
                    triplets.append({
                        "source": p, "source_label": "Project",
                        "relation": rel if rel != "RELATED_TO" else "REQUIRES_SKILL",
                        "target": sk, "target_label": "Skill"
                    })

        # Deduplicate entities
        unique_entities = cls.fuzzy_deduplicate(all_entities)

        # Deduplicate triplets
        unique_triplets = []
        seen_trips = set()
        for t in triplets:
            key = (t["source"], t["relation"], t["target"])
            if key not in seen_trips:
                seen_trips.add(key)
                unique_triplets.append(t)

        return {
            "university_id": university_id,
            "total_chunks": len(chunks),
            "entities_found": len(unique_entities),
            "entities": unique_entities,
            "triplets_found": len(unique_triplets),
            "triplets": unique_triplets
        }
