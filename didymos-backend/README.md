# Didymos Backend (FastAPI + Neo4j)

로컬/사설 환경에서 Didymos API를 실행하기 위한 간단 가이드입니다.

## 준비
1. Python 3.11+ (여기서는 venv 사용을 권장)
2. Neo4j AuraDB (Bolt/HTTP) 접속 정보
3. OpenAI API Key

## 환경 변수
`.env.example`를 복사해 실제 값을 채워주세요:
```
cp .env.example .env
```

필수 값:
- `NEO4J_URI`: neo4j+s://<your-instance>.databases.neo4j.io
- `NEO4J_USER` / `NEO4J_PASSWORD`
- `OPENAI_API_KEY`

## 설치 & 실행
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker 실행
```bash
# 빌드
docker build -t didymos-api .
# 실행 (로컬 8000 포트 매핑)
docker run --env-file .env -p 8000:8000 didymos-api
```

### docker-compose
```bash
docker-compose up --build -d
```
(Neo4j AuraDB를 사용하므로 DB 컨테이너는 포함하지 않습니다)

## 주요 기능
- 노트 동기화 `/api/v1/notes/sync` (privacy_mode: full/summary/metadata)
- 컨텍스트/그래프/태스크/리뷰 API
- Bolt+SSC 드라이버 사용, 고유 제약 및 벡터 인덱스 자동 생성

## 테스트용 샘플
- `test_note_sync.json`을 활용해 간단한 sync 호출을 할 수 있습니다:
```bash
curl -X POST -H "Content-Type: application/json" \
  -d @test_note_sync.json \
  http://localhost:8000/api/v1/notes/sync
```

## 기타
- 프라이버시 모드: summary(요약 후 처리), metadata(본문 제외) 지원
- 제외된 배포 작업(Docker 등)은 현재 스코프 밖입니다.
