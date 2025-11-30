"""
간단한 Neo4j 연결 테스트
"""
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

print(f"Connecting to: {uri}")
print(f"Username: {username}")
print(f"Password length: {len(password)}")
print()

# Test 1: Basic driver connection
print("Test 1: Basic driver connection...")
try:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    print("✓ Driver created")

    # Try to verify connectivity
    print("Verifying connectivity...")
    driver.verify_connectivity()
    print("✓ Connectivity verified!")

    # Try a simple query
    print("Running test query...")
    with driver.session(database="neo4j") as session:
        result = session.run("RETURN 1 as num")
        record = result.single()
        print(f"✓ Query successful: {record['num']}")

    driver.close()
    print("✓ All tests passed!")

except Exception as e:
    print(f"✗ Error: {type(e).__name__}")
    print(f"  Message: {str(e)}")

    # Print more details if available
    if hasattr(e, '__cause__'):
        print(f"  Cause: {e.__cause__}")
