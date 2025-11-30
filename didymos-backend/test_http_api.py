"""
Neo4j Query API를 사용한 HTTP 연결 테스트
"""
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Query API URL 구성
base_url = "https://fece7c6e.databases.neo4j.io"
database = "neo4j"
query_url = f"{base_url}/db/{database}/query/v2"

username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

print(f"Testing HTTP Query API...")
print(f"URL: {query_url}")
print(f"Username: {username}")
print()

# 간단한 쿼리 실행
query = "RETURN 'Hello from Query API!' as message"

try:
    response = requests.post(
        query_url,
        auth=HTTPBasicAuth(username, password),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json={
            "statement": query
        },
        timeout=10
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Query API 연결 성공!")
        print(f"Result: {json.dumps(result, indent=2)}")
    else:
        print(f"✗ 연결 실패")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"✗ 오류: {type(e).__name__}")
    print(f"  Message: {str(e)}")
