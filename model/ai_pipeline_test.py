import os
import torch
import joblib
from transformers import AutoTokenizer, AutoModelForTokenClassification


# ============================================================
# PATHS
# ============================================================

MODEL_PATH = "model/scibert_ner_model"
RELATION_MODEL_PATH = "model/relation_model.pkl"
RELATION_VECTORIZER_PATH = "model/relation_vectorizer.pkl"


# ============================================================
# LOAD SCIBERT NER MODEL
# ============================================================

print("Loading SciBERT NER model...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH
)

ner_model = AutoModelForTokenClassification.from_pretrained(
    MODEL_PATH
)

ner_model.eval()

print("SciBERT NER model loaded.")


# ============================================================
# LOAD RELATION MODEL
# ============================================================

print("Loading relation extraction model...")

relation_model = joblib.load(
    RELATION_MODEL_PATH
)

relation_vectorizer = joblib.load(
    RELATION_VECTORIZER_PATH
)

print("Relation model loaded.")


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

        entity_text = text[start:end]

        if prefix == "B":

            if current_entity:
                entities.append(current_entity)

            current_entity = {
                "text": entity_text,
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
# TEST SENTENCE
# ============================================================

text = (
    "Student S001 is working on "
    "AI-Based Smart Campus Project 001 "
    "using PyTorch."
)

print("\n========================================")
print("INPUT TEXT")
print("========================================")

print(text)


# ============================================================
# RUN NER
# ============================================================

entities = extract_entities(text)

print("\n========================================")
print("EXTRACTED ENTITIES")
print("========================================")

if entities:

    for entity in entities:

        print(
            entity["text"],
            "->",
            entity["label"]
        )

else:

    print("No entities detected.")


# ============================================================
# RUN RELATION EXTRACTION
# ============================================================

print("\n========================================")
print("PREDICTED RELATION")
print("========================================")

relation = predict_relation(text)

print(
    text,
    "->",
    relation
)


print("\n========================================")
print("AI PIPELINE TEST COMPLETED")
print("========================================")