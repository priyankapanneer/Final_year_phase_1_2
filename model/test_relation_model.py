import joblib

model = joblib.load(
    "model/relation_model.pkl"
)

vectorizer = joblib.load(
    "model/relation_vectorizer.pkl"
)


texts = [
    "Student S001 is enrolled in course C001.",
    "Faculty F001 teaches course C001.",
    "Student S001 has skill S001.",
    "Project P001 requires skill S001.",
    "Student S001 works on project P001.",
    "Faculty F001 supervises project P001."
]


for text in texts:

    vector = vectorizer.transform([text])

    prediction = model.predict(vector)[0]

    print("\nText:", text)
    print("Predicted relation:", prediction)