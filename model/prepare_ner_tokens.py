import json
from transformers import AutoTokenizer

MODEL_NAME = "allenai/scibert_scivocab_uncased"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

labels = [
    "O",
    "B-STUDENT", "I-STUDENT",
    "B-FACULTY", "I-FACULTY",
    "B-COURSE", "I-COURSE",
    "B-SKILL", "I-SKILL",
    "B-PROJECT", "I-PROJECT",
    "B-PUBLICATION", "I-PUBLICATION",
    "B-TOPIC", "I-TOPIC"
]

label_to_id = {label: i for i, label in enumerate(labels)}


def process_file(input_file, output_file):

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    processed = []

    for item in data:

        text = item["text"]
        entities = item["entities"]

        encoding = tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=128,
            return_offsets_mapping=True
        )

        offsets = encoding.pop("offset_mapping")

        token_labels = []

        for start, end in offsets:

            if start == end:
                token_labels.append(-100)
                continue

            label = "O"

            for entity in entities:

                entity_start = entity["start"]
                entity_end = entity["end"]
                entity_label = entity["label"]

                if start >= entity_start and end <= entity_end:

                    if start == entity_start:
                        label = "B-" + entity_label
                    else:
                        label = "I-" + entity_label

                    break

            token_labels.append(label_to_id[label])

        processed.append({
            "input_ids": [int(x) for x in encoding["input_ids"]],
            "attention_mask": [int(x) for x in encoding["attention_mask"]],
            "token_type_ids": [int(x) for x in encoding["token_type_ids"]],
            "labels": [int(x) for x in token_labels]
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed, f)

    print("Created:", output_file)
    print("Records:", len(processed))


process_file(
    "model/ner_train.json",
    "model/tokenized_train.json"
)

process_file(
    "model/ner_test.json",
    "model/tokenized_test.json"
)

print("\nToken preparation completed!")