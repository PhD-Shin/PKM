# Phase 8: 프라이버시 & 배포

> 프라이버시 모드, 프로덕션 배포

**예상 시간**: 4~5시간  
**난이도**: ⭐⭐⭐⭐☆

---

## 목표

- 프라이버시 모드 구현 (Full/Summary/Metadata)
- 폴더 제외 설정
- Docker 이미지 생성
- 백엔드 배포 (Railway/Render/Fly.io)
- Obsidian 플러그인 커뮤니티 제출 준비

---

## Part 1: 프라이버시 모드 구현

### Step 8-1: Summary 모드 구현

파일 수정: `didymos-backend/app/services/llm_client.py`

함수 추가:

```python
def summarize_content(content: str) -> str:
    """
    노트 내용 요약 (프라이버시 모드용)
    """
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the following note in 2-3 sentences. Focus on key concepts and topics only."
                },
                {"role": "user", "content": content[:1000]}  # 1000자 제한
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        summary = response.choices[0].message.content
        logger.info(f"Content summarized: {len(content)} -> {len(summary)} chars")
        return summary
        
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return content[:200]  # 실패 시 앞부분만
```

---

### Step 8-2: 프라이버시 모드 적용

파일 수정: `didymos-backend/app/schemas/note.py`

```python
class NoteSyncRequest(BaseModel):
    user_token: str
    vault_id: str
    note: NotePayload
    privacy_mode: str = "full"  # full/summary/metadata
```

파일 수정: `didymos-backend/app/api/routes_notes.py`

```python
from app.services.llm_client import summarize_content

@router.post("/sync", response_model=NoteSyncResponse)
async def sync_note(payload: NoteSyncRequest):
    """
    노트 동기화 (프라이버시 모드 지원)
    """
    try:
        driver = get_neo4j_driver()
        user_id = get_user_id_from_token(payload.user_token)
        
        # 노트 저장
        success = upsert_note(...)
        
        if not success:
            raise HTTPException(...)
        
        # 프라이버시 모드에 따른 처리
        content = payload.note.content or ""
        
        if payload.privacy_mode == "summary":
            content = summarize_content(content)
        elif payload.privacy_mode == "metadata":
            content = ""  # 내용 전송 안 함
        
        # 온톨로지 추출
        ontology_result = upsert_note_ontology(
            driver=driver,
            note_id=payload.note.note_id,
            content=content,
            metadata={
                "tags": payload.note.tags,
                "links": payload.note.links,
                "yaml": payload.note.yaml
            }
        )
        
        return NoteSyncResponse(...)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(...)
```

---

### Step 8-3: 플러그인 설정 확장

파일 수정: `didymos-obsidian/src/settings.ts`

```typescript
export interface DidymosSettings {
  apiBaseUrl: string;
  userToken: string;
  vaultId: string;
  autoSyncOnSave: boolean;
  syncDebounceMs: number;
  privacyMode: "full" | "summary" | "metadata";  // 추가
  excludedFolders: string[];  // 추가
}

export const DEFAULT_SETTINGS: DidymosSettings = {
  apiBaseUrl: "http://localhost:8000/api/v1",
  userToken: "test_user_001",
  vaultId: "default-vault",
  autoSyncOnSave: true,
  syncDebounceMs: 2000,
  privacyMode: "full",
  excludedFolders: [],
};
```

---

### Step 8-4: 폴더 제외 기능

파일 수정: `didymos-obsidian/main.ts`

```typescript
async syncNoteFile(file: TFile) {
  // 제외된 폴더 체크
  const isExcluded = this.settings.excludedFolders.some((folder) =>
    file.path.startsWith(folder)
  );

  if (isExcluded) {
    console.log(`Skipped excluded folder: ${file.path}`);
    return;
  }

  try {
    // ... 기존 코드 ...

    const noteData: NoteData = {
      // ... 기존 필드 ...
    };

    // 프라이버시 모드 포함하여 전송
    await this.api.syncNote(noteData, this.settings.privacyMode);

    // ...
  } catch (error) {
    // ...
  }
}
```

파일 수정: `didymos-obsidian/src/api/client.ts`

```typescript
async syncNote(note: NoteData, privacyMode: string = "full"): Promise<SyncResponse> {
  const url = `${this.settings.apiBaseUrl}/notes/sync`;

  const payload = {
    user_token: this.settings.userToken,
    vault_id: this.settings.vaultId,
    note: note,
    privacy_mode: privacyMode,  // 추가
  };

  // ... 기존 코드 ...
}
```

---

### Step 8-5: 설정 UI 업데이트

파일 수정: `didymos-obsidian/main.ts` (DidymosSettingTab 클래스)

```typescript
display(): void {
  const { containerEl } = this;
  containerEl.empty();
  containerEl.createEl("h2", { text: "Didymos Settings" });

  // ... 기존 설정 ...

  // 프라이버시 모드
  new Setting(containerEl)
    .setName("Privacy Mode")
    .setDesc("Choose how much content to send to the server")
    .addDropdown((dropdown) =>
      dropdown
        .addOption("full", "Full (entire content)")
        .addOption("summary", "Summary (AI-summarized)")
        .addOption("metadata", "Metadata only (tags & links)")
        .setValue(this.plugin.settings.privacyMode)
        .onChange(async (value) => {
          this.plugin.settings.privacyMode = value as any;
          await this.plugin.saveSettings();
        })
    );

  // 제외할 폴더
  new Setting(containerEl)
    .setName("Excluded Folders")
    .setDesc("Folders to exclude from sync (comma-separated)")
    .addTextArea((text) =>
      text
        .setPlaceholder("Private/, Journal/")
        .setValue(this.plugin.settings.excludedFolders.join(", "))
        .onChange(async (value) => {
          this.plugin.settings.excludedFolders = value
            .split(",")
            .map((f) => f.trim())
            .filter((f) => f.length > 0);
          await this.plugin.saveSettings();
        })
    );
}
```

---

## Part 2: 배포 준비

### Step 8-6: Docker 이미지 생성

파일 생성: `didymos-backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY app/ ./app/

# 포트 노출
EXPOSE 8000

# 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

파일 생성: `didymos-backend/docker-compose.yml`

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=${NEO4J_URI}
      - NEO4J_USER=${NEO4J_USER}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    env_file:
      - .env
    restart: unless-stopped
```

테스트:

```bash
cd didymos-backend
docker-compose up --build
```

---

### Step 8-7: Railway 배포

1. **Railway 계정 생성**
   - https://railway.app/ 접속
   - GitHub 연동

2. **New Project 생성**
   - "Deploy from GitHub repo" 선택
   - `didymos-backend` 저장소 선택

3. **환경 변수 설정**
   ```
   NEO4J_URI=neo4j+s://...
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=...
   OPENAI_API_KEY=sk-...
   ```

4. **배포 확인**
   - Railway가 자동으로 Dockerfile 감지 및 빌드
   - 생성된 URL 확인 (예: `https://didymos-api.up.railway.app`)

---

### Step 8-8: 대체 배포 옵션

#### Render.com

1. https://render.com/ 접속
2. "New Web Service" 클릭
3. GitHub 저장소 연결
4. 설정:
   - Environment: Docker
   - Build Command: (자동 감지)
   - Start Command: (자동 감지)
5. 환경 변수 추가

#### Fly.io

```bash
# Fly CLI 설치
curl -L https://fly.io/install.sh | sh

# 로그인
fly auth login

# 앱 생성
cd didymos-backend
fly launch

# 환경 변수 설정
fly secrets set NEO4J_URI=...
fly secrets set NEO4J_PASSWORD=...
fly secrets set OPENAI_API_KEY=...

# 배포
fly deploy
```

---

## Part 3: Obsidian 플러그인 출시 준비

### Step 8-9: README.md 작성

파일 생성: `didymos-obsidian/README.md`

```markdown
# Didymos

AI-powered knowledge graph for Obsidian.

## Features

- 🧠 **AI Ontology Extraction**: Automatically extract topics, projects, and tasks from your notes
- 📊 **Knowledge Graph**: Visualize connections between your notes
- 🔗 **Context Panel**: See related notes, topics, and tasks
- ✅ **Task Management**: Auto-extract and manage tasks
- 📅 **Weekly Review**: Stay on top of your knowledge base

## Installation

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/yourusername/didymos-obsidian/releases)
2. Extract the files to `<vault>/.obsidian/plugins/didymos/`
3. Reload Obsidian
4. Enable the plugin in Settings → Community plugins

### From Community Plugins (Coming Soon)

Search for "Didymos" in Obsidian's Community Plugins.

## Setup

1. Open Settings → Didymos
2. Set your API URL (default: `http://localhost:8000/api/v1`)
3. Configure privacy mode
4. Set excluded folders (optional)

## Backend Setup

Didymos requires a backend server. See [Backend Setup Guide](https://github.com/yourusername/didymos-backend).

## Usage

1. Write your notes as usual
2. Didymos automatically extracts topics, projects, and tasks
3. Open Context Panel (Cmd+P → "Open Didymos Context")
4. View Knowledge Graph (Cmd+P → "Open Knowledge Graph")
5. Manage Tasks (Cmd+P → "Open Task Panel")

## Privacy

Didymos supports three privacy modes:

- **Full**: Send entire content (most accurate)
- **Summary**: Send AI-summarized content
- **Metadata**: Send only tags and links

## License

MIT License

## Support

- GitHub Issues: [Report a bug](https://github.com/yourusername/didymos-obsidian/issues)
- Discussions: [Ask questions](https://github.com/yourusername/didymos-obsidian/discussions)
```

---

### Step 8-10: 스크린샷 추가

1. Context Panel 스크린샷
2. Graph Panel 스크린샷
3. Task Panel 스크린샷
4. Weekly Review 스크린샷

파일 저장: `didymos-obsidian/screenshots/`

---

### Step 8-11: 릴리스 준비

파일 생성: `didymos-obsidian/.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags:
      - '*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Use Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Build
        run: |
          npm install
          npm run build
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            main.js
            manifest.json
            styles.css
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

### Step 8-12: 커뮤니티 제출 준비

체크리스트:

- [ ] README.md 완성
- [ ] 스크린샷 4개 이상 추가
- [ ] manifest.json 정보 완전
- [ ] LICENSE 파일 추가 (MIT)
- [ ] GitHub Release 생성
- [ ] 플러그인 정상 동작 확인

커뮤니티 제출:
1. https://github.com/obsidianmd/obsidian-releases 방문
2. Fork 저장소
3. `community-plugins.json`에 플러그인 정보 추가
4. Pull Request 생성

---

## ✅ 완료 체크리스트

### 프라이버시
- [ ] Summary 모드 구현
- [ ] Metadata 모드 구현
- [ ] 폴더 제외 기능
- [ ] 설정 UI 추가

### 백엔드 배포
- [ ] Dockerfile 작성
- [ ] docker-compose.yml 작성
- [ ] Railway/Render/Fly.io 중 하나 배포
- [ ] 프로덕션 URL 확인
- [ ] 환경 변수 설정

### 플러그인 출시
- [ ] README.md 작성
- [ ] 스크린샷 추가
- [ ] LICENSE 추가
- [ ] GitHub Release 생성
- [ ] 커뮤니티 제출 (선택)

---

## 🎉 축하합니다!

**Didymos MVP가 완성되었습니다!**

### 다음 단계

1. **사용자 피드백 수집**
   - 친구/동료에게 베타 테스트 요청
   - 피드백 수집 및 개선

2. **기능 확장**
   - 벡터 검색 (임베딩 기반)
   - 멀티 Vault 지원
   - 팀 협업 기능

3. **성능 최적화**
   - 캐싱 추가 (Redis)
   - 쿼리 최적화
   - 배치 처리

4. **커뮤니티 구축**
   - Discord 서버 생성
   - 블로그 포스트 작성
   - 데모 비디오 제작

---

## 🚀 프로젝트 완료!

모든 Phase를 완료했습니다. 이제 실제로 사용하고 개선해 나가세요! 💪
