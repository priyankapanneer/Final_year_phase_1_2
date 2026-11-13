import os
import torch
import joblib
import requests

from transformers import AutoTokenizer, AutoModelForTokenClassification
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

HOST = URI.replace("neo4j+s://", "").replace("neo4j://", "")

QUERY_URL = f"https://{HOST}/db/{DATABASE}/query/v2"


# ============================================================
# LOAD AI MODELS
# ============================================================

print("Loading SciBERT NER model...")

MODEL_PATH = "model/scibert_ner_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

ner_model = AutoModelForTokenClassification.from_pretrained(
    MODEL_PATH
)

ner_model.eval()

print("SciBERT NER model loaded.")


print("Loading relation model...")

relation_model = joblib.load(
    "model/relation_model.pkl"
)

relation_vectorizer = joblib.load(
    "model/relation_vectorizer.pkl"
)

print("Relation model loaded.")


# ============================================================
# NEO4J QUERY FUNCTION
# ============================================================

def run_query(statement, parameters=None):

    payload = {
        "statement": statement
    }

    if parameters:
        payload["parameters"] = parameters

    response = requests.post(
        QUERY_URL,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=payload,
        timeout=60
    )

    if response.status_code not in [200, 202]:
        print("Neo4j query failed:")
        print(response.text)
        response.raise_for_status()

    return response.json()


# ============================================================
# ENTITY EXTRACTION
# ============================================================

def extract_entities(text):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        return_offsets_mapping=True,
        truncation=True
    )

    offset_mapping = inputs.pop("offset_mapping")

    with torch.no_grad():

        outputs = ner_model(**inputs)

    predictions = torch.argmax(
        outputs.logits,
        dim=2
    )[0]

    entities = []

    current_entity = None

    for token_index, prediction in enumerate(predictions):

        label = ner_model.config.id2label[
            prediction.item()
        ]

        start, end = offset_mapping[0][token_index].tolist()

        # Ignore special tokens
        if start == end:
            continue

        if label == "O":

            if current_entity:
                entities.append(current_entity)
                current_entity = None

            continue

        entity_type = label.split("-")[-1]
        prefix = label.split("-")[0]

        if prefix == "B":

            if current_entity:
                entities.append(current_entity)

            current_entity = {
                "text": text[start:end],
                "label": entity_type,
                "start": start,
                "end": end
            }

        elif prefix == "I" and current_entity:

            current_entity["text"] = text[
                current_entity["start"]:end
            ]

            current_entity["end"] = end

    if current_entity:
        entities.append(current_entity)

    return entities


# ============================================================
# RELATION PREDICTION
# ============================================================

def predict_relation(text):

    vector = relation_vectorizer.transform(
        [text]
    )

    prediction = relation_model.predict(
        vector
    )[0]

    return prediction


# ============================================================
# INPUT TEXT
# ============================================================

text = (
    "Student S0001 is working on "
    "AI-Based Smart Campus Project 001 "
    "using PyTorch."
)

print("\n========================================")
print("INPUT TEXT")
print("========================================")

print(text)


# ============================================================
# AI ENTITY EXTRACTION
# ============================================================

entities = extract_entities(text)

print("\n========================================")
print("EXTRACTED ENTITIES")
print("========================================")

for entity in entities:

    print(
        entity["text"],
        "->",
        entity["label"]
    )


# ============================================================
# AI RELATION PREDICTION
# ============================================================

relation = predict_relation(text)

print("\n========================================")
print("PREDICTED RELATION")
print("========================================")

print(relation)


# ============================================================
# FIND STUDENT AND PROJECT
# ============================================================

student = None
project = None

for entity in entities:

    if entity["label"] == "STUDENT":
        student = entity["text"]

    elif entity["label"] == "PROJECT":
        project = entity["text"]


print("\n========================================")
print("GRAPH UPDATE")
print("========================================")


if student and project and relation == "WORKS_ON":

    print("Student:", student)
    print("Project:", project)
    print("Relationship:", relation)

    query = """
    MATCH (s:Student)
    WHERE s.student_id = $student_id

    MATCH (p:Project)
    WHERE p.project_name = $project_name

    MERGE (s)-[:WORKS_ON]->(p)

    RETURN
        s.student_id AS student_id,
        p.project_name AS project_name,
        'WORKS_ON' AS relationship
    """

    result = run_query(
        query,
        {
            "student_id": student,
            "project_name": project
        }
    )

    print("\nNeo4j update result:")

    print(result)

else:

    print(
        "Required Student, Project and WORKS_ON "
        "relationship were not detected."
    )


print("\n========================================")
print("AI → NEO4J PIPELINE COMPLETED")
print("========================================")