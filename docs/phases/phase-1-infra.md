# Phase 1: 백엔드 기본 인프라 (Refactored)

> LangChain + Neo4j 기반의 모던 백엔드 구축

**예상 시간**: 2~3시간  
**난이도**: ⭐⭐⭐☆☆

---

## 목표

- LangChain 및 LangGraph 환경 설정
- Neo4j 연결 (LangChain Wrapper 사용)
- 기본 API 엔드포인트 구현

---

## Step 1-1: 패키지 설치

`requirements.txt`를 최신 스택으로 업데이트합니다.

```txt
# Core Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0

# LangChain Ecosystem (핵심)
langchain==0.1.0
langchain-community==0.0.10
langchain-openai==0.0.2
langchain-neo4j==0.1.0
langgraph==0.0.10

# Database
neo4j==5.16.0

# Utils
httpx==0.26.0
tiktoken==0.5.2
```

설치:
```bash
pip install -r requirements.txt
```

---

## Step 1-2: 설정 및 Neo4j 연결 (LangChain 스타일)

`app/db/neo4j.py`를 수정하여 LangChain의 `Neo4jGraph` 래퍼를 사용합니다. 이렇게 하면 드라이버를 직접 관리할 필요가 줄어듭니다.

**파일**: `didymos-backend/app/db/neo4j.py`

```python
"""
Neo4j 연결 관리 (LangChain Wrapper)
"""
from langchain_neo4j import Neo4jGraph
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def get_graph() -> Neo4jGraph:
    """
    LangChain Neo4jGraph 객체 반환
    """
    try:
        return Neo4jGraph(
            url=settings.neo4j_uri,
            username=settings.neo4j_user,
            password=settings.neo4j_password,
            # 스키마 리프레시는 필요할 때만 수동으로 하는 것이 성능에 좋음
            refresh_schema=False 
        )
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise e

def init_indices():
    """
    초기 인덱스 생성 (벡터 인덱스 등)
    """
    graph = get_graph()
    # 필요한 경우 여기에 인덱스 생성 쿼리 추가
    # graph.query("CREATE INDEX IF NOT EXISTS FOR (n:Note) ON (n.id)")
    logger.info("Graph connection initialized.")
```

**파일**: `didymos-backend/app/main.py`

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.neo4j import init_indices
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_indices()
    yield
    # Shutdown logic if needed

app = FastAPI(title="Didymos API", lifespan=lifespan)

# ... (나머지 CORS 설정 등은 동일)
```

---

## ✅ 완료 체크리스트

- [ ] `requirements.txt`에 langchain 패키지 추가 및 설치
- [ ] `Neo4jGraph`를 이용한 DB 연결 모듈 작성
- [ ] 서버 실행 및 `/health` 체크

---

**다음**: [Phase 3 - AI 온톨로지 추출 (LangChain)](./phase-3-ai.md)
