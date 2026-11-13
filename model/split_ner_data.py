import json
from sklearn.model_selection import train_test_split

with open("model/ner_training_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

train_data, test_data = train_test_split(
    data,
    test_size=0.2,
    random_state=42
)

with open("model/ner_train.json", "w", encoding="utf-8") as f:
    json.dump(train_data, f, indent=2, ensure_ascii=False)

with open("model/ner_test.json", "w", encoding="utf-8") as f:
    json.dump(test_data, f, indent=2, ensure_ascii=False)

print("Data split completed!")
print("Training records:", len(train_data))
print("Testing records:", len(test_data))