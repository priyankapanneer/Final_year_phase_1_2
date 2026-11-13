import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

QUERY_URL = f"https://46d29c94.databases.neo4j.io/db/{DATABASE}/query/v2"

payload = {
    "statement": "RETURN 1 AS test"
}

try:
    response = requests.post(
        QUERY_URL,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=payload,
        timeout=30
    )

    print("Status code:", response.status_code)
    print("Response:")
    print(response.text)

except Exception as e:
    print("Connection failed.")
    print(e)