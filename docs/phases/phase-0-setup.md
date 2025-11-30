# Phase 0: 환경 설정

> 개발에 필요한 모든 도구와 계정 설정

**예상 시간**: 1~2시간  
**난이도**: ⭐⭐☆☆☆

---

## 목표

- Python, Node.js 개발 환경 구축
- Neo4j AuraDB 계정 및 인스턴스 생성
- OpenAI API 키 발급
- 프로젝트 디렉토리 구조 생성
- Obsidian 테스트 Vault 준비

---

## Step 0-1: 필수 도구 설치

### Python 환경 (3.11+)

```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# Windows
# https://www.python.org/downloads/ 에서 다운로드

# 버전 확인
python3.11 --version  # Python 3.11.x
```

### Node.js 환경 (18+)

```bash
# macOS
brew install node@18

# nvm 사용 (권장)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 버전 확인
node --version  # v18.x.x
npm --version   # 9.x.x
```

### Git

```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt install git

# 설정
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### VSCode (권장 에디터)

- 다운로드: https://code.visualstudio.com/

**필수 확장**:
- Python (Microsoft)
- TypeScript (내장)
- REST Client (API 테스트용)

---

## Step 0-2: Neo4j AuraDB 설정

### 1. 계정 생성

1. https://neo4j.com/cloud/aura/ 접속
2. "Start Free" 클릭
3. 이메일 또는 Google 계정으로 가입

### 2. 인스턴스 생성

1. 대시보드에서 "Create Instance" 클릭
2. **AuraDB Free** 선택
3. 설정:
   - **Instance Name**: `didymos-dev`
   - **Region**: Asia Pacific (Tokyo) 또는 가까운 곳
   - **Database**: Neo4j 5.x (최신)

4. "Create" 클릭
5. ⚠️ **비밀번호 저장** (다시 볼 수 없음!)

### 3. 연결 정보 확보

생성 완료 후 표시되는 정보:

```
URI: neo4j+s://xxxxx.databases.neo4j.io
Username: neo4j
Password: [생성 시 저장한 비밀번호]
```

`.env` 파일에 사용할 것이므로 메모해두세요.

### 4. 연결 테스트

1. AuraDB 대시보드에서 "Open with" → "Neo4j Browser" 클릭
2. 자동 로그인됨
3. 상단 입력창에 다음 입력:

```cypher
RETURN "Connection OK" AS message
```

4. 실행 (▶️ 버튼)
5. "Connection OK" 출력되면 성공!

---

## Step 0-3: OpenAI API 키 발급

### 1. 계정 생성

1. https://platform.openai.com/ 접속
2. 가입 (GitHub/Google 로그인 가능)

### 2. API 키 생성

1. 로그인 후 우측 상단 계정 아이콘 클릭
2. "API keys" 선택
3. "Create new secret key" 클릭
4. 이름: `didymos-dev`
5. **키 복사 후 안전한 곳에 저장** (다시 볼 수 없음)

### 3. 크레딧 확인

- 신규 계정: $5 무료 크레딧 (3개월)
- Settings → Billing에서 확인
- GPT-4o-mini 사용 시 비용 매우 저렴 ($0.15/1M tokens)

### 4. 사용량 제한 설정 (권장)

과금 방지:
1. Settings → Usage limits
2. **Hard limit**: $10 설정
3. Alert threshold: $5 설정

---

## Step 0-4: 프로젝트 구조 생성

### 디렉토리 생성

```bash
# 작업 디렉토리 생성
mkdir didymos-project
cd didymos-project

# Git 초기화
git init

# 백엔드 디렉토리
mkdir -p didymos-backend/app/{api,models,schemas,services,db,tests}

# 프론트엔드 디렉토리
mkdir -p didymos-obsidian/src/{views,api,utils}

# 문서 디렉토리 (옵션)
mkdir docs
```

### .gitignore 생성

```bash
cat > .gitignore << 'EOF'
# Python
venv/
__pycache__/
*.pyc
.env
.pytest_cache/
*.egg-info/
dist/
build/

# Node.js
node_modules/
*.log
dist/
.cache/

# Obsidian
.obsidian/

# IDE
.vscode/
.idea/
*.swp
*.swo

# macOS
.DS_Store

# Environment
.env
.env.local
EOF
```

### 최종 구조

```
didymos-project/
├── didymos-backend/          # FastAPI 백엔드
│   └── app/
│       ├── api/            # API 라우터
│       ├── models/         # 데이터 모델
│       ├── schemas/        # Pydantic 스키마
│       ├── services/       # 비즈니스 로직
│       ├── db/             # 데이터베이스 연결
│       └── tests/          # 테스트 코드
├── didymos-obsidian/         # Obsidian 플러그인
│   └── src/
│       ├── views/          # UI 컴포넌트
│       ├── api/            # API 클라이언트
│       └── utils/          # 유틸리티
├── docs/                   # 문서 (옵션)
└── .gitignore
```

---

## Step 0-5: Obsidian 설치 및 테스트 Vault

### 1. Obsidian 설치

```bash
# macOS
brew install --cask obsidian

# Windows/Linux
# https://obsidian.md/download 에서 다운로드
```

### 2. 테스트 Vault 생성

1. Obsidian 실행
2. "Create new vault" 클릭
3. 설정:
   - **Vault name**: `didymos-test-vault`
   - **Location**: `didymos-project/didymos-test-vault`
4. "Create" 클릭

### 3. 개발자 모드 활성화

1. Settings (⚙️) 열기
2. "Community plugins" 선택
3. "Turn on community plugins" 클릭
4. "Restricted mode" 해제 확인

### 4. 테스트 노트 작성

새 노트 `Test Note.md` 생성:

```markdown
# Test Note

This is a test note for Didymos development.

## Topics
- Productivity
- Knowledge Management
- Note-taking

#test #development
```

---

## Step 0-6: 환경 변수 템플릿

백엔드 디렉토리에 `.env.example` 생성:

```bash
cd didymos-backend
cat > .env.example << 'EOF'
# App Settings
APP_NAME="Didymos API"
ENV="development"
API_PREFIX="/api/v1"

# Neo4j AuraDB
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# CORS
CORS_ORIGINS=["http://localhost:8000", "app://obsidian.md"]
EOF
```

실제 `.env` 파일 생성:

```bash
cp .env.example .env
# 에디터로 .env를 열어 실제 값으로 수정
```

---

## ✅ 완료 체크리스트

모든 항목을 확인하세요:

### 도구 설치
- [ ] Python 3.11+ 설치 및 버전 확인
- [ ] Node.js 18+ 설치 및 버전 확인
- [ ] Git 설치 및 설정
- [ ] VSCode (또는 선호하는 에디터) 설치

### 계정 및 서비스
- [ ] Neo4j AuraDB 계정 생성
- [ ] Neo4j 인스턴스 생성 완료
- [ ] Neo4j Browser에서 연결 테스트 성공
- [ ] Neo4j 연결 정보 (URI, Password) 저장
- [ ] OpenAI 계정 생성
- [ ] OpenAI API 키 발급 및 저장
- [ ] 사용량 제한 설정

### 프로젝트 구조
- [ ] 프로젝트 디렉토리 생성
- [ ] Git 초기화
- [ ] `.gitignore` 작성
- [ ] `.env.example` 작성
- [ ] `.env` 파일 생성 (실제 값 입력)

### Obsidian
- [ ] Obsidian 설치
- [ ] 테스트 Vault 생성
- [ ] 개발자 모드 활성화
- [ ] 테스트 노트 작성

---

## 🎯 다음 단계

환경 설정이 완료되었습니다!

**다음**: [Phase 1 - 백엔드 인프라](./phase-1-infra.md)

백엔드 서버를 구축하고 Neo4j 연결을 확인합니다.

