import pandas as pd
import os

dataset_path = os.path.join(os.path.dirname(__file__), "..", "dataset")

files = [
    "students.csv",
    "courses.csv",
    "faculty.csv",
    "skills.csv",
    "projects.csv",
    "publications.csv"
]

for file in files:
    path = os.path.join(dataset_path, file)
    df = pd.read_csv(path)

    print("\n", file)
    print("Shape:", df.shape)
    print("Missing values:")
    print(df.isnull().sum())