"""
Trust 설정을 변경한 Neo4j Bolt 연결 테스트
"""
from neo4j import GraphDatabase, TRUST_SYSTEM_CA_SIGNED_CERTIFICATES
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

print(f"Connecting to: {uri}")
print(f"Username: {username}")
print()

# Test with different trust configurations
configs = [
    {"name": "Default", "config": {}},
    {"name": "Trust All Certificates", "config": {"encrypted": True, "trust": TRUST_SYSTEM_CA_SIGNED_CERTIFICATES}},
    {"name": "Max Connection Lifetime", "config": {"max_connection_lifetime": 3600, "max_connection_pool_size": 50}},
]

for test in configs:
    print(f"\nTest: {test['name']}")
    print("-" * 50)
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password), **test['config'])
        print("✓ Driver created")

        driver.verify_connectivity()
        print("✓ Connectivity verified!")

        with driver.session(database="neo4j") as session:
            result = session.run("RETURN 1 as num")
            record = result.single()
            print(f"✓ Query successful: {record['num']}")

        driver.close()
        print("✓ SUCCESS!")
        break  # If successful, stop trying other configs

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}")
        print(f"  Message: {str(e)[:200]}")
