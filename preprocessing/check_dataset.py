import pandas as pd
import os

dataset_path = os.path.join(os.path.dirname(__file__), "..", "dataset")

for file in os.listdir(dataset_path):
    if file.endswith(".csv"):
        path = os.path.join(dataset_path, file)
        df = pd.read_csv(path)

        print("\n" + "=" * 50)
        print(file)
        print("Rows:", len(df))
        print("Columns:", len(df.columns))
        print("Column names:", list(df.columns))