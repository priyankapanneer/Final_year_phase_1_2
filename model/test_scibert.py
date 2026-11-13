from transformers import AutoTokenizer, AutoModel

model_name = "allenai/scibert_scivocab_uncased"

print("Loading SciBERT...")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

print("SciBERT loaded successfully!")
print("Tokenizer:", tokenizer.__class__.__name__)
print("Model:", model.__class__.__name__)