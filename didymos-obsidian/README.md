# Didymos PKM - Obsidian Plugin

AI-powered Personal Knowledge Management plugin for Obsidian with Neo4j graph backend.

## Features

- 📝 **Auto Sync**: Automatically sync notes to Neo4j backend when modified
- 🤖 **AI Entity Extraction**: Extract entities (Topics, Projects, Tasks, People) from note content
- 🔗 **Graph Relationships**: Automatic relationship detection between entities
- 🌐 **Neo4j Backend**: Store your knowledge in a graph database

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
