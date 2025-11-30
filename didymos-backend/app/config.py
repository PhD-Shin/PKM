"""
애플리케이션 설정 관리
"""
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """환경 변수 기반 설정"""

    # App Settings
    app_name: str = "Didymos API"
    env: str = "development"
    api_prefix: str = "/api/v1"

    # Neo4j AuraDB
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str = "neo4j"
    aura_instanceid: str = ""
    aura_instancename: str = ""

    # OpenAI
    openai_api_key: str

    # CORS
    cors_origins: str = '["http://localhost:8000", "app://obsidian.md"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        try:
            return json.loads(self.cors_origins)
        except:
            return ["http://localhost:8000", "app://obsidian.md"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
