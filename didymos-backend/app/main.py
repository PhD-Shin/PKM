"""
Didymos FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from app.db.neo4j import init_indices
from app.config import settings
from app.api import routes_notes, routes_context, routes_tasks, routes_review
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 로직"""
    # Startup
    logger.info("Starting Didymos API...")
    init_indices()
    yield
    # Shutdown logic if needed
    logger.info("Shutting down Didymos API...")


app = FastAPI(
    title=settings.app_name,
    description="PKM with Neo4j and LangChain",
    version="0.1.0",
    lifespan=lifespan
)

# GZip 압축
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(routes_notes.router, prefix=settings.api_prefix)
app.include_router(routes_context.router, prefix=settings.api_prefix)
app.include_router(routes_tasks.router, prefix=settings.api_prefix)
app.include_router(routes_review.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Welcome to Didymos API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "database": "connected"
    }


@app.get("/api/v1/test")
async def test():
    """테스트 엔드포인트"""
    from app.db.neo4j import get_neo4j_client

    try:
        client = get_neo4j_client()
        result = client.query("RETURN 'Connection OK' as message, timestamp() as time")
        return {
            "status": "success",
            "neo4j_connection": "OK",
            "connection_type": "HTTP API",
            "result": result
        }
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
