import os
import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")


def run_query(query):

    url = (
        f"{NEO4J_URI.replace('neo4j+s://', 'https://')}"
        f"/db/{NEO4J_DATABASE}/query/v2"
    )

    response = requests.post(
        url,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        headers={
            "Content-Type": "application/json"
        },
        json={
            "statement": query
        }
    )

    response.raise_for_status()

    return response.json()


def get_enrollment_trends():

    query = """
    MATCH ()-[r:ENROLLED_IN]->()
    WHERE r.semester IS NOT NULL

    RETURN
        r.semester AS semester,
        count(r) AS enrollment_count

    ORDER BY semester
    """

    result = run_query(query)

    if "data" not in result:
        return []

    fields = result["data"]["fields"]
    values = result["data"]["values"]

    return [
        dict(zip(fields, row))
        for row in values
    ]


def get_publication_trends():

    query = """
    MATCH ()-[r:AUTHORED]->()
    WHERE r.publication_year IS NOT NULL

    RETURN
        r.publication_year AS year,
        count(r) AS publication_count

    ORDER BY year
    """

    result = run_query(query)

    if "data" not in result:
        return []

    fields = result["data"]["fields"]
    values = result["data"]["values"]

    return [
        dict(zip(fields, row))
        for row in values
    ]


if __name__ == "__main__":

    print("\nEnrollment Trends")
    print("=" * 50)

    for item in get_enrollment_trends():
        print(
            f"{item['semester']} : "
            f"{item['enrollment_count']}"
        )

    print("\nPublication Trends")
    print("=" * 50)

    for item in get_publication_trends():
        print(
            f"{item['year']} : "
            f"{item['publication_count']}"
        )