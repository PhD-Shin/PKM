# Didymos - Obsidian Plugin

> **"Smart Connections를 넘어선 구조화된 2nd Brain"**
> 의미론적 계층 지식 그래프 + Claude AI 인사이트

**Status**: MVP Phase 11 - Day 11 완료 (의사결정 인사이트 강화), Day 12-13 테스트 진행 중

---

## 개요

Didymos는 Obsidian을 위한 AI 기반 지식 그래프 플러그인입니다. Smart Connections와 달리, 단순히 유사 노트를 찾는 것이 아니라 **의미론적 계층 구조**를 제공하고, **Claude AI가 각 클러스터를 요약**하여 의사결정을 지원합니다.

### 핵심 차별점

| 기능 | Smart Connections | Didymos |
|------|-------------------|---------|
| **검색** | 유사 노트 검색 | ✅ + 구조화된 맥락 |
| **구조** | 평면적 | ✅ 계층적 클러스터 |
| **분석** | 없음 | ✅ 의사결정 인사이트 |
| **LLM** | 임베딩만 | ✅ Claude 클러스터 요약 |

### 실제 사용 예시

**Before (Smart Connections)**:
- "Raman scattering"로 검색 → 유사 노트 10개 리스트
- 전체 구조 파악 어려움

**After (Didymos)**:
- 471개 노트 → 8개 의미론적 클러스터로 자동 구조화
- "Research & Papers" 클러스터 클릭 → Claude가 요약: "이 클러스터는 Raman scattering 관련 연구 논문들로 구성되어 있으며, 최근 7일간 15개 노트가 업데이트되었습니다. HeII line 분석이 핵심이며, RR Tel 관측 데이터 추가 분석이 필요합니다."

---

## 주요 기능

### Phase 0-10 (완료)
- ✅ **자동 동기화**: 노트 수정 시 Neo4j 백엔드로 자동 동기화
- ✅ **AI 온톨로지 추출**: Topic, Project, Task 자동 추출
- ✅ **그래프 시각화**: vis-network 기반 인터랙티브 그래프
- ✅ **패턴 분석**: PageRank, Community Detection
- ✅ **주간 리뷰**: 새 토픽, 잊힌 프로젝트, 미완료 태스크

### Phase 11 (Week 1 완료, Week 2 진행 중)
- ✅ **의미론적 클러스터링**: 471개 노트 → 8-12개 클러스터 (UMAP + HDBSCAN)
- ✅ **GPT-5 Mini 클러스터 요약**: 각 클러스터의 핵심 인사이트 + 다음 행동 제안
- ✅ **계층적 탐색 UI**: 클러스터 상세 패널 슬라이드 애니메이션
- ✅ **의사결정 인사이트**: 최근 업데이트 통계, 실행 가능한 인사이트, Next Actions
- ✅ **성능 최적화**: 백그라운드 캐시 워밍업, 12시간 TTL, 병렬 LLM 처리

## Installation

### Development Mode

1. Clone this repository into your Obsidian vault's plugins folder:
   ```bash
   cd /path/to/your/vault/.obsidian/plugins
   git clone https://github.com/yourusername/didymos-pkm.git
   cd didymos-pkm
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the plugin:
   ```bash
   npm run build
   ```

4. Enable the plugin in Obsidian Settings → Community Plugins

### Manual Installation

1. Download `main.js` and `manifest.json` from the latest release
2. Create a folder named `didymos-pkm` in your vault's `.obsidian/plugins` directory
3. Copy the files into this folder
4. Enable the plugin in Obsidian Settings → Community Plugins

## Configuration

Go to Settings → Didymos PKM and configure:

- **API Endpoint**: Your backend API URL (default: `http://localhost:8000/api/v1`)
- **User Token**: Your user authentication token
- **Vault ID**: Your vault identifier
- **Auto Sync**: Enable/disable automatic note synchronization
- **Privacy Mode**: `full` (원문), `summary` (요약 전송), `metadata` (본문 제외)
- **Excluded Folders**: 쉼표로 구분한 제외 폴더 경로 (예: `Private/,Archive/`)
- **Export Folder**: 온톨로지 스냅샷을 저장할 폴더 (예: `Didymos/Ontology`)
- **Local Mode**: 백엔드로 보내지 않고 로컬 파일만 생성
- **Local OpenAI API Key**: 로컬 모드에서 온톨로지 추출 시 사용할 키
- **Auto export ontology**: 동기화 후 자동으로 스냅샷 생성

## Usage

### Automatic Sync

When Auto Sync is enabled, notes are automatically synced to the backend whenever you modify them.

### Manual Sync

Use the command palette (Cmd/Ctrl + P) and search for "Sync current note to Didymos".

### Export Ontology Snapshot / Decision Note

- Command palette → "Export Ontology Snapshot": 현재 노트의 컨텍스트를 JSON 코드펜스로 저장(Export Folder) 또는 노트 하단에 삽입(옵션). 원본은 수정 없음(append 옵션 제외).
  - Local Mode ON: 백엔드 없이 OpenAI API로 추출해 로컬 파일만 생성
  - Local Mode OFF: 백엔드 컨텍스트 API를 사용

- Command palette → "Generate Decision Note": 컨텍스트/리뷰 데이터를 모아 `Didymos/Decisions`에 결정 노트 생성. Decision Panel에서 새로고침/저장 가능.

- Decision Dashboard: "Open Decision Dashboard"로 뷰를 열어 주요 토픽/프로젝트/태스크/주간 신호를 한 곳에서 확인하고, 결정 노트 생성/갱신 버튼을 사용할 수 있습니다.

## Development

### Build for development with hot reload:
```bash
npm run dev
```

### Build for production:
```bash
npm run build
```

### 패키징(ZIP) 배포:
```bash
npm run package
# dist/didymos-pkm.zip 생성 → Vault의 .obsidian/plugins/didymos-pkm/ 에 압축 해제
```

## Requirements

- Obsidian v0.15.0+
- Didymos backend server running (see `didymos-backend/README.md`)

## License

MIT
