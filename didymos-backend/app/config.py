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
    cors_origins: str = '["*"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        # Obsidian Desktop은 app://obsidian.md origin 사용
        # 개발/프로덕션 모두 호환하도록 "*" 허용
        default_origins = [
            "*",  # 모든 origin 허용 (Obsidian Desktop 호환)
            "http://localhost:8000",
            "http://localhost:3000",
            "app://obsidian.md",
            "capacitor://localhost",  # Obsidian Mobile
        ]
        try:
            custom_origins = json.loads(self.cors_origins)
            # "*"가 포함되어 있으면 모든 origin 허용
            if "*" in custom_origins:
                return ["*"]
            return list(set(default_origins + custom_origins))
        except:
            return default_origins

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
