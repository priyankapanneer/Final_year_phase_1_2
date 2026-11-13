import pandas as pd
import os

dataset_path = os.path.join(os.path.dirname(__file__), "..", "dataset")
output_path = os.path.join(os.path.dirname(__file__), "..", "processed_data")

os.makedirs(output_path, exist_ok=True)

for file in os.listdir(dataset_path):

    if file.endswith(".csv"):

        input_file = os.path.join(dataset_path, file)
        output_file = os.path.join(output_path, file)

        df = pd.read_csv(input_file)

        # Remove duplicate rows
        df = df.drop_duplicates()

        # Remove extra spaces from text columns
        for column in df.select_dtypes(include="object").columns:
            df[column] = df[column].str.strip()

        # Save cleaned data
        df.to_csv(output_file, index=False)

        print(f"Processed: {file} | Rows: {len(df)}")

print("\nPreprocessing completed successfully!")