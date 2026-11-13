import pandas as pd
import os

base_path = os.path.join(os.path.dirname(__file__), "..", "processed_data")

publications = pd.read_csv(
    os.path.join(base_path, "publications.csv")
)

projects = pd.read_csv(
    os.path.join(base_path, "projects.csv")
)

publication_data = pd.DataFrame({
    "text": publications["title"].fillna("") + " " +
            publications["abstract"].fillna("")
})

project_data = pd.DataFrame({
    "text": projects["project_name"].fillna("") + " " +
            projects["description"].fillna("")
})

training_data = pd.concat(
    [publication_data, project_data],
    ignore_index=True
)

output_path = os.path.join(
    os.path.dirname(__file__),
    "academic_text.csv"
)

training_data.to_csv(output_path, index=False)

print("Training data created successfully!")
print("Total text records:", len(training_data))
print(training_data.head())