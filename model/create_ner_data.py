import pandas as pd
import os
import json


base_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "processed_data"
)


def create_record(text, entity, label):

    start = text.find(entity)

    if start == -1:
        return {
            "text": text,
            "entities": []
        }

    return {
        "text": text,
        "entities": [
            {
                "start": start,
                "end": start + len(entity),
                "label": label
            }
        ]
    }


training_data = []


# ============================================================
# STUDENTS
# ============================================================

students = pd.read_csv(
    os.path.join(base_path, "students.csv")
)

for _, row in students.iterrows():

    name = row["student_name"]
    department = row["department"]

    examples = [
        f"Student {name} belongs to the {department} department.",
        f"{name} is a student in the {department} department.",
        f"The academic record belongs to student {name}.",
        f"{name} is studying in the {department} department."
    ]

    for text in examples:

        training_data.append(
            create_record(
                text,
                name,
                "STUDENT"
            )
        )


# ============================================================
# COURSES
# ============================================================

courses = pd.read_csv(
    os.path.join(base_path, "courses.csv")
)

for _, row in courses.iterrows():

    course = row["course_name"]
    department = row["department"]

    examples = [
        f"The course {course} is offered by the {department} department.",
        f"Students can enroll in the {course} course.",
        f"{course} is an academic course in the {department} department.",
        f"The university offers {course}."
    ]

    for text in examples:

        training_data.append(
            create_record(
                text,
                course,
                "COURSE"
            )
        )


# ============================================================
# FACULTY
# ============================================================

faculty = pd.read_csv(
    os.path.join(base_path, "faculty.csv")
)

for _, row in faculty.iterrows():

    name = row["faculty_name"]
    specialization = row["specialization"]

    examples = [
        f"Faculty member {name} specializes in {specialization}.",
        f"{name} is a faculty member with expertise in {specialization}.",
        f"Research in {specialization} is guided by {name}.",
        f"{name} teaches students and specializes in {specialization}."
    ]

    for text in examples:

        training_data.append(
            create_record(
                text,
                name,
                "FACULTY"
            )
        )


# ============================================================
# SKILLS
# ============================================================

skills = pd.read_csv(
    os.path.join(base_path, "skills.csv")
)

for _, row in skills.iterrows():

    skill = row["skill_name"]

    # Multiple sentence patterns
    examples = [
        f"The student has experience in {skill}.",
        f"The student has knowledge of {skill}.",
        f"The student is skilled in {skill}.",
        f"The project requires {skill}.",
        f"Experience with {skill} is useful for the project.",
        f"The student uses {skill} for academic projects.",
        f"The researcher has expertise in {skill}.",
        f"The project was developed using {skill}."
    ]

    for text in examples:

        training_data.append(
            create_record(
                text,
                skill,
                "SKILL"
            )
        )


# ============================================================
# ADD IMPORTANT ACADEMIC / TECHNICAL SKILLS
# ============================================================

additional_skills = [
    "Python",
    "PyTorch",
    "TensorFlow",
    "Java",
    "JavaScript",
    "C++",
    "SQL",
    "Linux",
    "Docker",
    "Kubernetes",
    "Machine Learning",
    "Deep Learning",
    "Natural Language Processing",
    "Computer Vision",
    "Data Science",
    "Artificial Intelligence",
    "Cloud Computing",
    "Quantum Computing",
    "Blockchain",
    "Cyber Security",
    "Data Mining",
    "Big Data",
    "Apache Spark",
    "Scikit-learn",
    "Hugging Face"
]


skill_templates = [
    "The student has experience in {skill}.",
    "The student has knowledge of {skill}.",
    "The student is skilled in {skill}.",
    "The project uses {skill}.",
    "The project was developed using {skill}.",
    "The researcher has expertise in {skill}.",
    "Experience with {skill} is required.",
    "The academic project involves {skill}."
]


for skill in additional_skills:

    for template in skill_templates:

        text = template.format(
            skill=skill
        )

        training_data.append(
            create_record(
                text,
                skill,
                "SKILL"
            )
        )


# ============================================================
# PROJECTS
# ============================================================

projects = pd.read_csv(
    os.path.join(base_path, "projects.csv")
)

for _, row in projects.iterrows():

    project = row["project_name"]
    domain = row["domain"]

    examples = [
        f"The project {project} focuses on {domain}.",
        f"{project} is an academic project.",
        f"The university project is {project}.",
        f"The project titled {project} belongs to the {domain} domain."
    ]

    for text in examples:

        training_data.append(
            create_record(
                text,
                project,
                "PROJECT"
            )
        )


# ============================================================
# PUBLICATIONS
# ============================================================

publications = pd.read_csv(
    os.path.join(base_path, "publications.csv")
)

for _, row in publications.iterrows():

    title = row["title"]

    examples = [
        f"The publication {title} discusses {row['topic']}.",
        f"The research paper titled {title} presents academic research.",
        f"The publication {title} reports research findings.",
        f"A research article called {title} was published."
    ]

    for text in examples:

        training_data.append(
            create_record(
                text,
                title,
                "PUBLICATION"
            )
        )


# ============================================================
# TOPICS
# ============================================================

for _, row in publications.iterrows():

    title = row["title"]
    topic = row["topic"]

    examples = [
        f"The publication {title} discusses {topic}.",
        f"The research topic is {topic}.",
        f"The paper focuses on {topic}.",
        f"This research is related to {topic}."
    ]

    for text in examples:

        training_data.append(
            create_record(
                text,
                topic,
                "TOPIC"
            )
        )


# ============================================================
# REMOVE EMPTY RECORDS
# ============================================================

training_data = [
    record
    for record in training_data
    if len(record["entities"]) > 0
]


# ============================================================
# SAVE TRAINING DATA
# ============================================================

output_file = os.path.join(
    os.path.dirname(__file__),
    "ner_training_data.json"
)

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        training_data,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# INFORMATION
# ============================================================

print(
    "Improved NER training data created!"
)

print(
    "Total training records:",
    len(training_data)
)

print("\nEntity types:")

print("STUDENT")
print("FACULTY")
print("COURSE")
print("SKILL")
print("PROJECT")
print("PUBLICATION")
print("TOPIC")