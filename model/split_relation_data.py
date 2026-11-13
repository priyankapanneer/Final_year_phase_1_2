import json
from sklearn.model_selection import train_test_split

with open("model/relation_training_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

train_data, test_data = train_test_split(
    data,
    test_size=0.2,
    random_state=42,
    stratify=[item["relation"] for item in data]
)

with open("model/relation_train.json", "w", encoding="utf-8") as f:
    json.dump(train_data, f, indent=2)

with open("model/relation_test.json", "w", encoding="utf-8") as f:
    json.dump(test_data, f, indent=2)

print("Relation data split completed!")
print("Training records:", len(train_data))
print("Testing records:", len(test_data))