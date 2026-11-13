import json
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModelForTokenClassification, AutoTokenizer
from torch.optim import AdamW
from seqeval.metrics import classification_report, f1_score


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "allenai/scibert_scivocab_uncased"

LABELS = [
    "O",
    "B-STUDENT", "I-STUDENT",
    "B-FACULTY", "I-FACULTY",
    "B-COURSE", "I-COURSE",
    "B-SKILL", "I-SKILL",
    "B-PROJECT", "I-PROJECT",
    "B-PUBLICATION", "I-PUBLICATION",
    "B-TOPIC", "I-TOPIC"
]

label_to_id = {
    label: i
    for i, label in enumerate(LABELS)
}

id_to_label = {
    i: label
    for i, label in enumerate(LABELS)
}


# CPU-friendly settings
BATCH_SIZE = 4
EPOCHS = 3
LEARNING_RATE = 2e-5


# ============================================================
# DATASET
# ============================================================

class NERDataset(Dataset):

    def __init__(self, file_path):

        with open(file_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):

        item = self.data[index]

        return {
            "input_ids": torch.tensor(
                item["input_ids"],
                dtype=torch.long
            ),

            "attention_mask": torch.tensor(
                item["attention_mask"],
                dtype=torch.long
            ),

            "token_type_ids": torch.tensor(
                item["token_type_ids"],
                dtype=torch.long
            ),

            "labels": torch.tensor(
                item["labels"],
                dtype=torch.long
            )
        }


# ============================================================
# LOAD DATA
# ============================================================

print("Loading datasets...")

train_dataset = NERDataset(
    "model/tokenized_train.json"
)

test_dataset = NERDataset(
    "model/tokenized_test.json"
)

print("Training records:", len(train_dataset))
print("Testing records:", len(test_dataset))


# ============================================================
# DEVICE
# ============================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("\nDevice:", device)


# ============================================================
# LOAD SCIBERT
# ============================================================

print("\nLoading SciBERT...")

model = AutoModelForTokenClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(LABELS),
    id2label=id_to_label,
    label2id=label_to_id
)


# ============================================================
# FREEZE LOWER SCIBERT LAYERS
# ============================================================

print("\nFreezing lower SciBERT layers...")

# Freeze embeddings
for parameter in model.bert.embeddings.parameters():
    parameter.requires_grad = False


# Freeze first 8 transformer layers
for layer in model.bert.encoder.layer[:8]:

    for parameter in layer.parameters():
        parameter.requires_grad = False


# Classification head remains trainable
for parameter in model.classifier.parameters():
    parameter.requires_grad = True


trainable_parameters = sum(
    parameter.numel()
    for parameter in model.parameters()
    if parameter.requires_grad
)

total_parameters = sum(
    parameter.numel()
    for parameter in model.parameters()
)

print(
    f"Trainable parameters: "
    f"{trainable_parameters:,}"
)

print(
    f"Total parameters: "
    f"{total_parameters:,}"
)


model.to(device)


# ============================================================
# DATA LOADERS
# ============================================================

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE
)


# ============================================================
# OPTIMIZER
# ============================================================

optimizer = AdamW(
    filter(
        lambda p: p.requires_grad,
        model.parameters()
    ),
    lr=LEARNING_RATE
)


# ============================================================
# TRAINING
# ============================================================

print("\nStarting training...")

for epoch in range(EPOCHS):

    model.train()

    total_loss = 0

    for step, batch in enumerate(train_loader):

        batch = {
            key: value.to(device)
            for key, value in batch.items()
        }

        optimizer.zero_grad()

        outputs = model(**batch)

        loss = outputs.loss

        loss.backward()

        optimizer.step()

        total_loss += loss.item()

        # Show progress every 50 batches
        if (step + 1) % 50 == 0:

            print(
                f"Epoch {epoch + 1}/{EPOCHS} "
                f"| Step {step + 1}/{len(train_loader)} "
                f"| Loss: {loss.item():.4f}"
            )

    average_loss = (
        total_loss / len(train_loader)
    )

    print(
        f"\nEpoch {epoch + 1}/{EPOCHS} completed "
        f"- Average Loss: {average_loss:.4f}\n"
    )


print("Training completed!")


# ============================================================
# EVALUATION
# ============================================================

print("\nEvaluating model...")

model.eval()

true_labels = []
pred_labels = []


with torch.no_grad():

    for batch in test_loader:

        labels = batch["labels"]

        model_batch = {
            key: value.to(device)
            for key, value in batch.items()
        }

        outputs = model(**model_batch)

        predictions = torch.argmax(
            outputs.logits,
            dim=-1
        )


        for i in range(len(labels)):

            true_sequence = []
            pred_sequence = []

            for j in range(len(labels[i])):

                true_id = labels[i][j].item()

                # Ignore padding/special tokens
                if true_id == -100:
                    continue

                pred_id = predictions[i][j].item()

                true_sequence.append(
                    id_to_label[true_id]
                )

                pred_sequence.append(
                    id_to_label[pred_id]
                )

            true_labels.append(
                true_sequence
            )

            pred_labels.append(
                pred_sequence
            )


# ============================================================
# F1 SCORE
# ============================================================

score = f1_score(
    true_labels,
    pred_labels
)

print("\n========================================")
print("NER EVALUATION")
print("========================================")

print(
    f"F1 Score: {score:.4f}"
)

print(
    f"F1 Score (%): {score * 100:.2f}%"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\nClassification Report:")

print(
    classification_report(
        true_labels,
        pred_labels
    )
)


# ============================================================
# SAVE MODEL
# ============================================================

output_directory = (
    "model/scibert_ner_model"
)

model.save_pretrained(
    output_directory
)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

tokenizer.save_pretrained(
    output_directory
)


print("\nModel saved to:")
print(output_directory)

print("\n========================================")
print("SCI-BERT NER TRAINING FINISHED")
print("========================================")