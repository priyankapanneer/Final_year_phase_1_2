import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import joblib


# Load training data
with open("model/relation_train.json", "r", encoding="utf-8") as f:
    train_data = json.load(f)

with open("model/relation_test.json", "r", encoding="utf-8") as f:
    test_data = json.load(f)


# Text and labels
X_train = [item["text"] for item in train_data]
y_train = [item["relation"] for item in train_data]

X_test = [item["text"] for item in test_data]
y_test = [item["relation"] for item in test_data]


# TF-IDF
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2)
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)


# Train Logistic Regression
model = LogisticRegression(
    max_iter=1000
)

print("Starting relation training...")

model.fit(X_train_tfidf, y_train)

print("Training completed!")


# Prediction
predictions = model.predict(X_test_tfidf)


# Evaluation
accuracy = accuracy_score(
    y_test,
    predictions
)

print("\nAccuracy:", round(accuracy, 4))

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)


# Save model
joblib.dump(
    model,
    "model/relation_model.pkl"
)

joblib.dump(
    vectorizer,
    "model/relation_vectorizer.pkl"
)

print("\nRelation model saved successfully!")