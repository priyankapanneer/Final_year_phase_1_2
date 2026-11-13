import json
from collections import Counter

with open("model/ner_training_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

counts = Counter()

for record in data:
    for entity in record["entities"]:
        counts[entity["label"]] += 1

print("Total records:", len(data))
print("\nEntity counts:")

for label, count in counts.items():
    print(label, ":", count)