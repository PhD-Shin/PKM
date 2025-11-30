"""
Neo4j 연결 테스트 스크립트
"""
import sys
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수 확인
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

print("=== 환경 변수 확인 ===")
print(f"NEO4J_URI: {neo4j_uri}")
print(f"NEO4J_USERNAME: {neo4j_username}")
print(f"NEO4J_PASSWORD: {'*' * len(neo4j_password) if neo4j_password else 'None'}")
print(f"NEO4J_DATABASE: {neo4j_database}")
print()

# Neo4j 드라이버로 직접 연결 테스트
print("=== Neo4j 드라이버 연결 테스트 ===")
try:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_username, neo4j_password)
    )

    # 연결 확인
    driver.verify_connectivity()
    print("✓ Neo4j 드라이버 연결 성공!")

    # 간단한 쿼리 실행
    with driver.session() as session:
        result = session.run("RETURN 'Connection OK' as message")
        record = result.single()
        print(f"✓ 쿼리 실행 성공: {record['message']}")

    driver.close()

except Exception as e:
    print(f"✗ 연결 실패: {type(e).__name__}")
    print(f"  상세: {str(e)}")
    sys.exit(1)

# LangChain Neo4jGraph 연결 테스트
print()
print("=== LangChain Neo4jGraph 연결 테스트 ===")
try:
    from langchain_neo4j import Neo4jGraph

    graph = Neo4jGraph(
        url=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        database=neo4j_database,
        refresh_schema=False
    )

    result = graph.query("RETURN 'LangChain OK' as message")
    print(f"✓ LangChain 연결 성공: {result}")

except Exception as e:
    print(f"✗ 연결 실패: {type(e).__name__}")
    print(f"  상세: {str(e)}")
    sys.exit(1)

print()
print("=== 모든 테스트 통과! ===")
