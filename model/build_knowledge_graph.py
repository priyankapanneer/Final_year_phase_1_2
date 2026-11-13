import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModelForTokenClassification


MODEL_PATH = "model/scibert_ner_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH)

model.eval()


def extract_entities(text):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=128,
        return_offsets_mapping=True
    )

    offsets = inputs.pop("offset_mapping")[0]

    with torch.no_grad():
        outputs = model(**inputs)

    predictions = torch.argmax(
        outputs.logits,
        dim=2
    )[0]

    entities = []

    current_entity = None

    for prediction, (start, end) in zip(predictions, offsets):

        start = start.item()
        end = end.item()

        if start == end:
            continue

        label = model.config.id2label[prediction.item()]

        if label.startswith("B-"):

            if current_entity:
                entities.append(current_entity)

            current_entity = {
                "label": label[2:],
                "start": start,
                "end": end
            }

        elif label.startswith("I-") and current_entity:

            if label[2:] == current_entity["label"]:
                current_entity["end"] = end

            else:
                entities.append(current_entity)

                current_entity = {
                    "label": label[2:],
                    "start": start,
                    "end": end
                }

        else:

            if current_entity:
                entities.append(current_entity)
                current_entity = None

    if current_entity:
        entities.append(current_entity)

    # Convert character positions into actual text
    final_entities = []

    for entity in entities:

        value = text[
            entity["start"]:entity["end"]
        ].strip()

        if value:

            final_entities.append({
                "text": value,
                "label": entity["label"]
            })

    return final_entities


# Test with actual project data

projects = pd.read_csv(
    "processed_data/projects.csv"
)

text = (
    str(projects.iloc[0]["project_name"])
    + " "
    + str(projects.iloc[0]["description"])
)


print("\nInput:")
print(text)

print("\nExtracted entities:")

entities = extract_entities(text)

for entity in entities:

    print(
        entity["text"],
        "->",
        entity["label"]
    )