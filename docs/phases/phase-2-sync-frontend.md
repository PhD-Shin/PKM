# Phase 2-2: Obsidian Plugin (Frontend)

> Obsidian ↔ FastAPI 동기화 플러그인

**예상 시간**: 2~3시간  
**난이도**: ⭐⭐⭐⭐☆

---

## 목표

- Obsidian 플러그인 초기화 (TypeScript + esbuild)
- Settings / API Client / Main Plugin 구현
- 노트 저장 시 자동 동기화 & 알림

---

## Step 2-6: 프로젝트 초기화

```bash
cd didymos-obsidian

# package.json 생성
npm init -y

# 의존성
npm install --save-dev \
  typescript \
  @types/node \
  esbuild \
  obsidian
```

### `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM"],
    "outDir": "./dist",
    "rootDir": "./",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "moduleResolution": "node",
    "resolveJsonModule": true
  },
  "include": ["src/**/*", "main.ts"],
  "exclude": ["node_modules", "dist"]
}
```

### `build.mjs`

```javascript
import esbuild from "esbuild";
import process from "process";

const prod = process.argv[2] === "production";

esbuild.build({
  entryPoints: ["main.ts"],
  bundle: true,
  external: ["obsidian"],
  format: "cjs",
  target: "es2020",
  logLevel: "info",
  sourcemap: prod ? false : "inline",
  treeShaking: true,
  outfile: "main.js",
  minify: prod,
}).catch(() => process.exit(1));
```

### `package.json`

```json
{
  "scripts": {
    "dev": "node build.mjs",
    "build": "node build.mjs production"
  }
}
```

### `manifest.json`

```json
{
  "id": "didymos-plugin",
  "name": "Didymos",
  "version": "0.1.0",
  "minAppVersion": "1.5.0",
  "description": "AI-powered knowledge graph",
  "author": "Your Name",
  "isDesktopOnly": false
}
```

---

## Step 2-7: Settings 모듈

`src/settings.ts`

```typescript
export interface DidymosSettings {
  apiBaseUrl: string;
  userToken: string;
  vaultId: string;
  autoSyncOnSave: boolean;
  syncDebounceMs: number;
}

export const DEFAULT_SETTINGS: DidymosSettings = {
  apiBaseUrl: "http://localhost:8000/api/v1",
  userToken: "test_user_001",
  vaultId: "default-vault",
  autoSyncOnSave: true,
  syncDebounceMs: 2000,
};
```

---

## Step 2-8: API 클라이언트

`src/api/client.ts`

```typescript
import { DidymosSettings } from "../settings";

export interface NoteData {
  note_id: string;
  title: string;
  path: string;
  content: string;
  yaml: Record<string, any>;
  tags: string[];
  links: string[];
  created_at: string;
  updated_at: string;
}

export interface SyncResponse {
  status: string;
  note_id: string;
  message?: string;
}

export class DidymosAPI {
  constructor(private settings: DidymosSettings) {}

  async syncNote(note: NoteData): Promise<SyncResponse> {
    const url = `${this.settings.apiBaseUrl}/notes/sync`;

    const payload = {
      user_token: this.settings.userToken,
      vault_id: this.settings.vaultId,
      note,
    };

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(
        `${this.settings.apiBaseUrl.replace("/api/v1", "")}/health`
      );
      return response.ok;
    } catch (e) {
      console.error(e);
      return false;
    }
  }
}
```

---

## Step 2-9: 메인 플러그인

`main.ts`

```typescript
import {
  App,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  TFile,
} from "obsidian";
import { DidymosSettings, DEFAULT_SETTINGS } from "./src/settings";
import { DidymosAPI, NoteData } from "./src/api/client";

export default class DidymosPlugin extends Plugin {
  settings: DidymosSettings;
  api: DidymosAPI;
  syncTimeout: NodeJS.Timeout | null = null;

  async onload() {
    await this.loadSettings();
    this.api = new DidymosAPI(this.settings);

    this.addRibbonIcon("mountain", "Sync with Didymos", async () => {
      await this.syncCurrentNote();
    });

    this.addCommand({
      id: "didymos-sync-current-note",
      name: "Sync current note",
      callback: async () => {
        await this.syncCurrentNote();
      },
    });

    this.addCommand({
      id: "didymos-test-connection",
      name: "Test API connection",
      callback: async () => {
        const connected = await this.api.testConnection();
        new Notice(connected ? "✅ Connected" : "❌ Connection failed");
      },
    });

    if (this.settings.autoSyncOnSave) {
      this.registerEvent(
        this.app.vault.on("modify", (file) => {
          if (file instanceof TFile && file.extension === "md") {
            this.scheduleSyncDebounced(file);
          }
        })
      );
    }

    this.addSettingTab(new DidymosSettingTab(this.app, this));
    new Notice("Didymos plugin loaded");
  }

  onunload() {
    if (this.syncTimeout) clearTimeout(this.syncTimeout);
  }

  scheduleSyncDebounced(file: TFile) {
    if (this.syncTimeout) clearTimeout(this.syncTimeout);
    this.syncTimeout = setTimeout(async () => {
      await this.syncNoteFile(file);
    }, this.settings.syncDebounceMs);
  }

  async syncCurrentNote() {
    const file = this.app.workspace.getActiveFile();
    if (!file) {
      new Notice("No active note");
      return;
    }
    await this.syncNoteFile(file);
  }

  async syncNoteFile(file: TFile) {
    try {
      new Notice("Syncing...");

      const content = await this.app.vault.read(file);
      const cache = this.app.metadataCache.getFileCache(file);

      const noteData: NoteData = {
        note_id: file.path,
        title: file.basename,
        path: file.path,
        content,
        yaml: cache?.frontmatter ?? {},
        tags: (cache?.tags ?? []).map((t) => t.tag.replace("#", "")),
        links: (cache?.links ?? []).map((l) => l.link),
        created_at: new Date(file.stat.ctime).toISOString(),
        updated_at: new Date(file.stat.mtime).toISOString(),
      };

      await this.api.syncNote(noteData);
      new Notice(`✅ ${file.basename} synced`);
    } catch (error) {
      console.error("Sync failed:", error);
      new Notice("❌ Sync failed");
    }
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

class DidymosSettingTab extends PluginSettingTab {
  constructor(public app: App, public plugin: DidymosPlugin) {
    super(app, plugin);
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Didymos Settings" });

    new Setting(containerEl)
      .setName("API URL")
      .addText((text) =>
        text
          .setValue(this.plugin.settings.apiBaseUrl)
          .onChange(async (value) => {
            this.plugin.settings.apiBaseUrl = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("User Token")
      .addText((text) =>
        text
          .setValue(this.plugin.settings.userToken)
          .onChange(async (value) => {
            this.plugin.settings.userToken = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Vault ID")
      .addText((text) =>
        text
          .setValue(this.plugin.settings.vaultId)
          .onChange(async (value) => {
            this.plugin.settings.vaultId = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Auto sync")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.autoSyncOnSave)
          .onChange(async (value) => {
            this.plugin.settings.autoSyncOnSave = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
```

---

## Step 2-10: 플러그인 설치 & 테스트

```bash
npm run dev
mkdir -p "../didymos-test-vault/.obsidian/plugins/didymos"
cp main.js manifest.json "../didymos-test-vault/.obsidian/plugins/didymos/"
```

1. Obsidian 재시작 → 플러그인 활성화  
2. 노트 작성 후 저장 → “✅ synced” 알림  
3. Neo4j Browser에서 노트 생성 확인

---

## ✅ 체크리스트

- [ ] TypeScript + esbuild 환경 구성
- [ ] Settings / API Client 구현
- [ ] 노트 저장 이벤트 연결 (`modify`)
- [ ] 수동 명령 / 연결 테스트 명령
- [ ] End-to-End 테스트 (알림 + Neo4j)

---

**다음 단계**: [Phase 3 - AI 온톨로지 추출](./phase-3-ai.md)

