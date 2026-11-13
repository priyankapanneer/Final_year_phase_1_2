import os
import re
import hashlib
import requests
import joblib
import torch

from dotenv import load_dotenv
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification
)


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")


# ============================================================
# 2. NEO4J QUERY API
# ============================================================

host = (
    NEO4J_URI
    .replace("neo4j+s://", "")
    .replace("neo4j://", "")
)

QUERY_URL = (
    f"https://{host}/db/{NEO4J_DATABASE}/query/v2"
)


def run_cypher(query, parameters=None):

    payload = {
        "statement": query
    }

    if parameters:
        payload["parameters"] = parameters

    response = requests.post(
        QUERY_URL,
        auth=(
            NEO4J_USERNAME,
            NEO4J_PASSWORD
        ),
        json=payload
    )

    if response.status_code not in [200, 202]:

        print("\nNeo4j Error:")
        print(response.text)

        return None

    return response.json()


# ============================================================
# 3. LOAD SCI-BERT NER MODEL
# ============================================================

MODEL_PATH = "model/scibert_ner_model"

print("Loading SciBERT NER model...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH
)

ner_model = AutoModelForTokenClassification.from_pretrained(
    MODEL_PATH
)

ner_model.eval()

print("SciBERT loaded.")


# ============================================================
# 4. LOAD RELATION MODEL
# ============================================================

print("\nLoading relation extraction model...")

relation_model = joblib.load(
    "model/relation_model.pkl"
)

relation_vectorizer = joblib.load(
    "model/relation_vectorizer.pkl"
)

print("Relation model loaded.")


# ============================================================
# 5. ENTITY EXTRACTION
# ============================================================

def extract_entities(text):

    encoding = tokenizer(
        text,
        return_tensors="pt",
        return_offsets_mapping=True,
        truncation=True
    )

    offset_mapping = encoding.pop(
        "offset_mapping"
    )

    with torch.no_grad():

        outputs = ner_model(**encoding)

    predictions = torch.argmax(
        outputs.logits,
        dim=-1
    )[0]

    tokens = tokenizer.convert_ids_to_tokens(
        encoding["input_ids"][0]
    )

    entities = []

    current_entity = None

    for i, (token, prediction) in enumerate(
        zip(tokens, predictions)
    ):

        label = ner_model.config.id2label[
            prediction.item()
        ]

        start, end = offset_mapping[0][i].tolist()

        if start == end:
            continue

        word = text[start:end]

        # ----------------------------------------------------
        # Beginning of entity
        # ----------------------------------------------------

        if label.startswith("B-"):

            if current_entity:
                entities.append(
                    current_entity
                )

            current_entity = {
                "text": word,
                "type": label[2:],
                "start": start,
                "end": end
            }

        # ----------------------------------------------------
        # Continuation of entity
        # ----------------------------------------------------

        elif label.startswith("I-") and current_entity:

            current_entity["text"] = text[
                current_entity["start"]:end
            ]

            current_entity["end"] = end

        # ----------------------------------------------------
        # Outside entity
        # ----------------------------------------------------

        else:

            if current_entity:

                entities.append(
                    current_entity
                )

                current_entity = None

    if current_entity:

        entities.append(
            current_entity
        )

    return entities


# ============================================================
# 6. NORMALIZE STUDENT ID
# ============================================================

def normalize_student_id(student_text):

    match = re.search(
        r"S\d+",
        student_text.upper()
    )

    if not match:

        return None

    number = re.search(
        r"\d+",
        match.group()
    ).group()

    return f"S{int(number):04d}"


# ============================================================
# 7. CHECK STUDENT
# ============================================================

def student_exists(student_id):

    query = """
    MATCH (s:Student {student_id: $student_id})
    RETURN s.student_id AS student_id
    """

    result = run_cypher(
        query,
        {
            "student_id": student_id
        }
    )

    if not result:

        return False

    values = result.get(
        "data",
        {}
    ).get(
        "values",
        []
    )

    return len(values) > 0


# ============================================================
# 8. FIND EXISTING PROJECT
# ============================================================

def find_project(project_name):

    query = """
    MATCH (p:Project)
    WHERE toLower(p.project_name) =
          toLower($project_name)

    RETURN
        p.project_id AS project_id,
        p.project_name AS project_name

    LIMIT 1
    """

    result = run_cypher(
        query,
        {
            "project_name": project_name
        }
    )

    if not result:

        return None

    values = result.get(
        "data",
        {}
    ).get(
        "values",
        []
    )

    if not values:

        return None

    return {
        "project_id": values[0][0],
        "project_name": values[0][1]
    }


# ============================================================
# 9. GENERATE PROJECT ID
# ============================================================

def generate_project_id(project_name):

    normalized_name = (
        project_name
        .strip()
        .lower()
    )

    project_hash = hashlib.sha1(
        normalized_name.encode()
    ).hexdigest()[:10]

    return f"AUTO_PROJECT_{project_hash}"


# ============================================================
# 10. CREATE NEW PROJECT
# ============================================================

def create_project(project_name):

    project_id = generate_project_id(
        project_name
    )

    query = """
    MERGE (
        p:Project {
            project_id: $project_id
        }
    )

    ON CREATE SET
        p.project_name = $project_name,
        p.domain = "Automatically Added",
        p.description =
            "Project created from new academic text",
        p.status = "Active"

    RETURN
        p.project_id AS project_id,
        p.project_name AS project_name
    """

    result = run_cypher(
        query,
        {
            "project_id": project_id,
            "project_name": project_name
        }
    )

    if not result:

        return None

    values = result.get(
        "data",
        {}
    ).get(
        "values",
        []
    )

    if not values:

        return None

    return {
        "project_id": values[0][0],
        "project_name": values[0][1]
    }


# ============================================================
# 11. FIND EXISTING SKILL
# ============================================================

def find_skill(skill_name):

    query = """
    MATCH (s:Skill)
    WHERE toLower(s.skill_name) =
          toLower($skill_name)

    RETURN
        s.skill_id AS skill_id,
        s.skill_name AS skill_name

    LIMIT 1
    """

    result = run_cypher(
        query,
        {
            "skill_name": skill_name
        }
    )

    if not result:

        return None

    values = result.get(
        "data",
        {}
    ).get(
        "values",
        []
    )

    if not values:

        return None

    return {
        "skill_id": values[0][0],
        "skill_name": values[0][1]
    }


# ============================================================
# 12. GENERATE SKILL ID
# ============================================================

def generate_skill_id(skill_name):

    normalized_name = (
        skill_name
        .strip()
        .lower()
    )

    skill_hash = hashlib.sha1(
        normalized_name.encode()
    ).hexdigest()[:10]

    return f"AUTO_SKILL_{skill_hash}"


# ============================================================
# 13. CREATE NEW SKILL
# ============================================================

def create_skill(skill_name):

    skill_id = generate_skill_id(
        skill_name
    )

    query = """
    MERGE (
        s:Skill {
            skill_id: $skill_id
        }
    )

    ON CREATE SET
        s.skill_name = $skill_name,
        s.category = "Automatically Added"

    RETURN
        s.skill_id AS skill_id,
        s.skill_name AS skill_name
    """

    result = run_cypher(
        query,
        {
            "skill_id": skill_id,
            "skill_name": skill_name
        }
    )

    if not result:

        return None

    values = result.get(
        "data",
        {}
    ).get(
        "values",
        []
    )

    if not values:

        return None

    return {
        "skill_id": values[0][0],
        "skill_name": values[0][1]
    }


# ============================================================
# 14. ADD WORKS_ON RELATIONSHIP
# ============================================================

def add_works_on(
    student_id,
    project_id
):

    query = """
    MATCH (
        s:Student {
            student_id: $student_id
        }
    )

    MATCH (
        p:Project {
            project_id: $project_id
        }
    )

    MERGE (s)-[:WORKS_ON]->(p)

    RETURN
        s.student_id AS student_id,
        p.project_name AS project_name
    """

    return run_cypher(
        query,
        {
            "student_id": student_id,
            "project_id": project_id
        }
    )


# ============================================================
# 15. ADD REQUIRES_SKILL RELATIONSHIP
# ============================================================

def add_requires_skill(
    project_id,
    skill_id
):

    query = """
    MATCH (
        p:Project {
            project_id: $project_id
        }
    )

    MATCH (
        s:Skill {
            skill_id: $skill_id
        }
    )

    MERGE (p)-[:REQUIRES_SKILL]->(s)

    RETURN
        p.project_name AS project_name,
        s.skill_name AS skill_name
    """

    return run_cypher(
        query,
        {
            "project_id": project_id,
            "skill_id": skill_id
        }
    )


# ============================================================
# 16. PREDICT RELATION
# ============================================================

def predict_relation(text):

    features = relation_vectorizer.transform(
        [text]
    )

    prediction = relation_model.predict(
        features
    )

    return prediction[0]


# ============================================================
# 17. AUTOMATIC KNOWLEDGE GRAPH UPDATE
# ============================================================

def automatic_update(text):

    print("\n========================================")
    print("AUTOMATIC KNOWLEDGE GRAPH UPDATE")
    print("========================================")

    print("\nNew Academic Text:")
    print(text)

    # --------------------------------------------------------
    # STEP 1: ENTITY EXTRACTION
    # --------------------------------------------------------

    entities = extract_entities(text)

    print("\nExtracted Entities:")

    if not entities:

        print("No entities detected.")

        return

    for entity in entities:

        print(
            f"{entity['text']} -> "
            f"{entity['type']}"
        )

    # --------------------------------------------------------
    # STEP 2: SEPARATE ENTITIES
    # --------------------------------------------------------

    students = [
        entity
        for entity in entities
        if entity["type"] == "STUDENT"
    ]

    projects = [
        entity
        for entity in entities
        if entity["type"] == "PROJECT"
    ]

    skills = [
        entity
        for entity in entities
        if entity["type"] == "SKILL"
    ]

    # --------------------------------------------------------
    # STEP 3: VALIDATE STUDENT
    # --------------------------------------------------------

    valid_students = []

    for student in students:

        student_id = normalize_student_id(
            student["text"]
        )

        if not student_id:

            print(
                f"\nInvalid student ID: "
                f"{student['text']}"
            )

            continue

        if not student_exists(
            student_id
        ):

            print(
                f"\nStudent {student_id} "
                f"does not exist in Neo4j."
            )

            continue

        print(
            f"\nStudent validated: "
            f"{student_id}"
        )

        valid_students.append(
            student_id
        )

    # --------------------------------------------------------
    # STEP 4: CHECK / CREATE PROJECT
    # --------------------------------------------------------

    valid_projects = []

    for project in projects:

        project_name = project["text"]

        project_info = find_project(
            project_name
        )

        if project_info:

            print(
                f"\nProject already exists: "
                f"{project_info['project_name']}"
            )

        else:

            print(
                f"\nNew project detected: "
                f"{project_name}"
            )

            project_info = create_project(
                project_name
            )

            if project_info:

                print(
                    f"New Project Created: "
                    f"{project_info['project_name']}"
                )

                print(
                    f"Project ID: "
                    f"{project_info['project_id']}"
                )

            else:

                print(
                    "Failed to create "
                    "new project."
                )

                continue

        valid_projects.append(
            project_info
        )

    # --------------------------------------------------------
    # STEP 5: STUDENT → PROJECT
    # --------------------------------------------------------

    for student_id in valid_students:

        for project_info in valid_projects:

            relation = predict_relation(
                text
            )

            print(
                f"\nPredicted relation: "
                f"{relation}"
            )

            if relation == "WORKS_ON":

                result = add_works_on(
                    student_id,
                    project_info["project_id"]
                )

                if result:

                    print(
                        "\nKnowledge Graph Updated!"
                    )

                    print(
                        f"{student_id}"
                        f" --WORKS_ON--> "
                        f"{project_info['project_name']}"
                    )

    # --------------------------------------------------------
    # STEP 6: PROJECT → SKILL
    # --------------------------------------------------------

    for project_info in valid_projects:

        for skill in skills:

            skill_name = skill["text"]

            skill_info = find_skill(
                skill_name
            )

            # ------------------------------------------------
            # Existing skill
            # ------------------------------------------------

            if skill_info:

                print(
                    f"\nSkill already exists: "
                    f"{skill_info['skill_name']}"
                )

            # ------------------------------------------------
            # New skill
            # ------------------------------------------------

            else:

                print(
                    f"\nNew skill detected: "
                    f"{skill_name}"
                )

                skill_info = create_skill(
                    skill_name
                )

                if skill_info:

                    print(
                        f"New Skill Created: "
                        f"{skill_info['skill_name']}"
                    )

                    print(
                        f"Skill ID: "
                        f"{skill_info['skill_id']}"
                    )

                else:

                    print(
                        "Failed to create "
                        "new skill."
                    )

                    continue

            # ------------------------------------------------
            # Predict REQUIRES_SKILL
            # ------------------------------------------------

            relation_text = (
                f"Project "
                f"{project_info['project_name']} "
                f"requires skill "
                f"{skill_info['skill_name']}."
            )

            relation = predict_relation(
                relation_text
            )

            print(
                f"Predicted skill relation: "
                f"{relation}"
            )

            if relation == "REQUIRES_SKILL":

                result = add_requires_skill(
                    project_info["project_id"],
                    skill_info["skill_id"]
                )

                if result:

                    print(
                        "\nSkill relationship "
                        "added!"
                    )

                    print(
                        f"{project_info['project_name']}"
                        f" --REQUIRES_SKILL--> "
                        f"{skill_info['skill_name']}"
                    )

            else:

                print(
                    "Skill relationship was "
                    "not added because the "
                    "model predicted "
                    f"{relation}."
                )


# ============================================================
# 18. TEST NEW ACADEMIC DATA
# ============================================================

if __name__ == "__main__":

    new_text = (
        "Student S0001 is working on "
        "AI-Based Smart Campus Project 999 "
        "using Quantum Computing."
    )

    automatic_update(
        new_text
    )