import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_PATH = "model/scibert_ner_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH)

model.eval()

texts = [
    "The student has experience in Linux.",
    "The course Database Systems is offered by the department.",
    "Faculty member Dr. Anitha specializes in Machine Learning.",
    "The project Smart Campus focuses on Artificial Intelligence.",
    "The publication Deep Learning for Education discusses NLP.",
    "The topic Natural Language Processing is important in research."
]

for text in texts:

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)

    predictions = torch.argmax(
        outputs.logits,
        dim=2
    )

    tokens = tokenizer.convert_ids_to_tokens(
        inputs["input_ids"][0]
    )

    print("\nText:", text)
    print("Entities:")

    for token, prediction in zip(tokens, predictions[0]):

        label = model.config.id2label[prediction.item()]

        if label != "O":
            print(" ", token, "->", label)