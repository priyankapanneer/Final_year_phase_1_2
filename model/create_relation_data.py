import pandas as pd
import os
import json

base_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "processed_data"
)

relation_data = []


def add_relation(text, subject, subject_type, object_name, object_type, relation):

    relation_data.append({
        "text": text,
        "subject": subject,
        "subject_type": subject_type,
        "object": object_name,
        "object_type": object_type,
        "relation": relation
    })


# Student -> Course
df = pd.read_csv(os.path.join(base_path, "enrollments.csv"))

for _, row in df.iterrows():

    add_relation(
        f"Student {row['student_id']} is enrolled in course {row['course_id']}.",
        row["student_id"],
        "STUDENT",
        row["course_id"],
        "COURSE",
        "ENROLLED_IN"
    )


# Faculty -> Course
df = pd.read_csv(os.path.join(base_path, "teaches.csv"))

for _, row in df.iterrows():

    add_relation(
        f"Faculty {row['faculty_id']} teaches course {row['course_id']}.",
        row["faculty_id"],
        "FACULTY",
        row["course_id"],
        "COURSE",
        "TEACHES"
    )


# Student -> Skill
df = pd.read_csv(os.path.join(base_path, "student_skills.csv"))

for _, row in df.iterrows():

    add_relation(
        f"Student {row['student_id']} has skill {row['skill_id']}.",
        row["student_id"],
        "STUDENT",
        row["skill_id"],
        "SKILL",
        "HAS_SKILL"
    )


# Project -> Skill
df = pd.read_csv(os.path.join(base_path, "project_skills.csv"))

for _, row in df.iterrows():

    add_relation(
        f"Project {row['project_id']} requires skill {row['skill_id']}.",
        row["project_id"],
        "PROJECT",
        row["skill_id"],
        "SKILL",
        "REQUIRES_SKILL"
    )


# Student -> Project
df = pd.read_csv(os.path.join(base_path, "works_on.csv"))

for _, row in df.iterrows():

    add_relation(
        f"Student {row['student_id']} works on project {row['project_id']}.",
        row["student_id"],
        "STUDENT",
        row["project_id"],
        "PROJECT",
        "WORKS_ON"
    )


# Faculty -> Project
df = pd.read_csv(os.path.join(base_path, "supervises.csv"))

for _, row in df.iterrows():

    add_relation(
        f"Faculty {row['faculty_id']} supervises project {row['project_id']}.",
        row["faculty_id"],
        "FACULTY",
        row["project_id"],
        "PROJECT",
        "SUPERVISES"
    )


# Save
output_file = os.path.join(
    os.path.dirname(__file__),
    "relation_training_data.json"
)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        relation_data,
        f,
        indent=2
    )

print("Relation training data created!")
print("Total records:", len(relation_data))

print("\nRelations:")

for relation in sorted(
    set(item["relation"] for item in relation_data)
):
    print(relation)