import json
from transformers import AutoTokenizer

MODEL_NAME = "allenai/scibert_scivocab_uncased"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

relations = [
    "ENROLLED_IN",
    "TEACHES",
    "HAS_SKILL",
    "REQUIRES_SKILL",
    "WORKS_ON",
    "SUPERVISES"
]

relation_to_id = {
    relation: i
    for i, relation in enumerate(relations)
}


def process_file(input_file, output_file):

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    processed = []

    for item in data:

        encoding = tokenizer(
            item["text"],
            truncation=True,
            padding="max_length",
            max_length=128
        )

        processed.append({
            "input_ids": [int(x) for x in encoding["input_ids"]],
            "attention_mask": [int(x) for x in encoding["attention_mask"]],
            "token_type_ids": [int(x) for x in encoding["token_type_ids"]],
            "label": relation_to_id[item["relation"]]
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed, f)

    print("Created:", output_file)
    print("Records:", len(processed))


process_file(
    "model/relation_train.json",
    "model/relation_tokenized_train.json"
)

process_file(
    "model/relation_test.json",
    "model/relation_tokenized_test.json"
)

print("\nRelation tokenization completed!")