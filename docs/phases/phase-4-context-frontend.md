# Phase 4-2: Context Panel UI (Frontend)

> Obsidian 플러그인에서 컨텍스트 정보를 표시하는 UI 구현

**예상 시간**: 2~3시간  
**난이도**: ⭐⭐⭐⭐☆

---

## 목표

- API 클라이언트 확장 (Context 조회)
- Context View 구현 (Topics, Projects, Tasks, Related Notes)
- CSS 스타일링
- 노트 저장 시 실시간 업데이트 통합

---

## Step 4-5: API 클라이언트 확장

파일 수정: `didymos-obsidian/src/api/client.ts`

**Interface 추가**:

```typescript
export interface ContextData {
  topics: Array<{
    id: string;
    name: string;
    importance_score: number;
    mention_count: number;
  }>;
  projects: Array<{
    id: string;
    name: string;
    status: string;
    updated_at: string;
  }>;
  tasks: Array<{
    id: string;
    title: string;
    status: string;
    priority: string;
  }>;
  related_notes: Array<{
    note_id: string;
    title: string;
    path: string;
    similarity: number;
  }>;
}
```

**메소드 추가**:

```typescript
async fetchContext(noteId: string): Promise<ContextData> {
  const url = new URL(
    `${this.settings.apiBaseUrl}/notes/context/${encodeURIComponent(noteId)}`
  );
  url.searchParams.set("user_token", this.settings.userToken);

  try {
    const response = await fetch(url.toString());

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to fetch context:", error);
    throw error;
  }
}
```

---

## Step 4-6: Context View 구현

파일 생성: `didymos-obsidian/src/views/contextView.ts`

```typescript
import { ItemView, WorkspaceLeaf } from "obsidian";
import { DidymosSettings } from "../settings";
import { DidymosAPI, ContextData } from "../api/client";

export const CAIRN_CONTEXT_VIEW_TYPE = "didymos-context-view";

export class DidymosContextView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return CAIRN_CONTEXT_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Context";
  }

  getIcon(): string {
    return "mountain";
  }

  async onOpen() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("didymos-context-container");

    container.createEl("h2", { text: "🧭 Didymos Context" });
    container.createEl("p", {
      text: "노트를 저장하면 관련 컨텍스트가 표시됩니다.",
      cls: "didymos-empty-message",
    });
  }

  async updateContext(noteId: string) {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("didymos-context-container");

    // 헤더
    const header = container.createEl("div", { cls: "didymos-context-header" });
    header.createEl("h2", { text: "🧭 Didymos Context" });

    try {
      // 로딩 표시
      const loading = container.createEl("div", {
        text: "Loading context...",
        cls: "didymos-loading",
      });

      // Context 데이터 가져오기
      const context = await this.api.fetchContext(noteId);

      // 로딩 제거
      loading.remove();

      // Topics 섹션
      this.renderTopics(container, context.topics);

      // Projects 섹션
      this.renderProjects(container, context.projects);

      // Tasks 섹션
      this.renderTasks(container, context.tasks);

      // Related Notes 섹션
      this.renderRelatedNotes(container, context.related_notes);
    } catch (error) {
      container.createEl("div", {
        text: `❌ Failed to load context: ${error.message}`,
        cls: "didymos-error",
      });
    }
  }

  renderTopics(
    container: HTMLElement,
    topics: ContextData["topics"]
  ) {
    if (topics.length === 0) return;

    const section = container.createEl("div", { cls: "didymos-section" });
    section.createEl("h3", { text: `📌 Topics (${topics.length})` });

    const list = section.createEl("ul", { cls: "didymos-topic-list" });

    topics.forEach((topic) => {
      const item = list.createEl("li", { cls: "didymos-topic-item" });

      item.createEl("span", {
        text: topic.name,
        cls: "didymos-topic-name",
      });

      item.createEl("span", {
        text: `${Math.round(topic.importance_score * 100)}%`,
        cls: "didymos-topic-score",
      });

      item.createEl("span", {
        text: `(${topic.mention_count})`,
        cls: "didymos-topic-count",
      });
    });
  }

  renderProjects(
    container: HTMLElement,
    projects: ContextData["projects"]
  ) {
    if (projects.length === 0) return;

    const section = container.createEl("div", { cls: "didymos-section" });
    section.createEl("h3", { text: `📂 Projects (${projects.length})` });

    const list = section.createEl("ul", { cls: "didymos-project-list" });

    projects.forEach((project) => {
      const item = list.createEl("li", { cls: "didymos-project-item" });

      item.createEl("span", {
        text: project.name,
        cls: "didymos-project-name",
      });

      const statusClass =
        project.status === "active"
          ? "status-active"
          : project.status === "paused"
          ? "status-paused"
          : "status-done";

      item.createEl("span", {
        text: project.status,
        cls: `didymos-project-status ${statusClass}`,
      });
    });
  }

  renderTasks(
    container: HTMLElement,
    tasks: ContextData["tasks"]
  ) {
    if (tasks.length === 0) return;

    const section = container.createEl("div", { cls: "didymos-section" });
    section.createEl("h3", { text: `✅ Tasks (${tasks.length})` });

    const list = section.createEl("ul", { cls: "didymos-task-list" });

    tasks.forEach((task) => {
      const item = list.createEl("li", { cls: "didymos-task-item" });

      const checkbox = item.createEl("input", {
        type: "checkbox",
        cls: "didymos-task-checkbox",
      });
      checkbox.checked = task.status === "done";

      item.createEl("span", {
        text: task.title,
        cls: "didymos-task-title",
      });

      const priorityClass =
        task.priority === "high"
          ? "priority-high"
          : task.priority === "medium"
          ? "priority-medium"
          : "priority-low";

      item.createEl("span", {
        text: `[${task.priority[0].toUpperCase()}]`,
        cls: `didymos-task-priority ${priorityClass}`,
      });
    });
  }

  renderRelatedNotes(
    container: HTMLElement,
    notes: ContextData["related_notes"]
  ) {
    if (notes.length === 0) return;

    const section = container.createEl("div", { cls: "didymos-section" });
    section.createEl("h3", { text: `🔗 Related Notes (${notes.length})` });

    const list = section.createEl("ul", { cls: "didymos-related-list" });

    notes.forEach((note, index) => {
      const item = list.createEl("li", { cls: "didymos-related-item" });

      item.createEl("span", {
        text: `${index + 1}.`,
        cls: "didymos-related-number",
      });

      const link = item.createEl("a", {
        text: note.title,
        cls: "didymos-related-link",
      });

      link.addEventListener("click", (e) => {
        e.preventDefault();
        this.app.workspace.openLinkText(note.path, "", false);
      });

      item.createEl("span", {
        text: `${Math.round(note.similarity * 100)}%`,
        cls: "didymos-related-similarity",
      });
    });
  }
}
```

---

## Step 4-7: CSS 스타일링

파일 생성: `didymos-obsidian/styles.css`

```css
/* Didymos Context Panel */
.didymos-context-container {
  padding: 16px;
}

.didymos-context-header h2 {
  margin: 0 0 16px 0;
  font-size: 1.5em;
}

.didymos-empty-message {
  color: var(--text-muted);
  font-style: italic;
}

.didymos-loading {
  text-align: center;
  padding: 20px;
  color: var(--text-muted);
}

.didymos-error {
  color: var(--text-error);
  padding: 12px;
  background-color: var(--background-modifier-error);
  border-radius: 4px;
}

/* Section */
.didymos-section {
  margin-bottom: 24px;
}

.didymos-section h3 {
  margin: 0 0 12px 0;
  font-size: 1.1em;
  border-bottom: 1px solid var(--background-modifier-border);
  padding-bottom: 8px;
}

.didymos-section ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.didymos-section li {
  padding: 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Topics */
.didymos-topic-name {
  flex: 1;
}

.didymos-topic-score {
  font-weight: bold;
  color: var(--interactive-accent);
}

.didymos-topic-count {
  color: var(--text-muted);
  font-size: 0.9em;
}

/* Projects */
.didymos-project-name {
  flex: 1;
}

.didymos-project-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: 500;
}

.didymos-project-status.status-active {
  background-color: var(--color-green);
  color: white;
}

.didymos-project-status.status-paused {
  background-color: var(--color-yellow);
  color: black;
}

.didymos-project-status.status-done {
  background-color: var(--text-muted);
  color: white;
}

/* Tasks */
.didymos-task-checkbox {
  margin: 0;
}

.didymos-task-title {
  flex: 1;
}

.didymos-task-priority {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.75em;
  font-weight: bold;
}

.didymos-task-priority.priority-high {
  background-color: var(--color-red);
  color: white;
}

.didymos-task-priority.priority-medium {
  background-color: var(--color-orange);
  color: white;
}

.didymos-task-priority.priority-low {
  background-color: var(--text-muted);
  color: white;
}

/* Related Notes */
.didymos-related-number {
  color: var(--text-muted);
  font-weight: bold;
  min-width: 20px;
}

.didymos-related-link {
  flex: 1;
  cursor: pointer;
  color: var(--link-color);
  text-decoration: none;
}

.didymos-related-link:hover {
  text-decoration: underline;
}

.didymos-related-similarity {
  color: var(--text-accent);
  font-weight: bold;
  font-size: 0.9em;
}
```

빌드에 CSS 포함: `manifest.json`에 `"css": "styles.css"` 추가.

---

## Step 4-8: 메인 플러그인 등록

파일 수정: `didymos-obsidian/main.ts`

**Import**:
```typescript
import {
  DidymosContextView,
  CAIRN_CONTEXT_VIEW_TYPE,
} from "./src/views/contextView";
```

**onload()**:
```typescript
// Context View 등록
this.registerView(
  CAIRN_CONTEXT_VIEW_TYPE,
  (leaf) => new DidymosContextView(leaf, this.settings)
);

// 리본 아이콘 수정
this.addRibbonIcon("mountain", "Open Didymos Context", () => {
  this.activateContextView();
});

// 명령 추가
this.addCommand({
  id: "didymos-open-context",
  name: "Open Context Panel",
  callback: () => {
    this.activateContextView();
  },
});
```

**activateContextView()**:
```typescript
async activateContextView() {
  const { workspace } = this.app;
  let leaf = workspace.getLeavesOfType(CAIRN_CONTEXT_VIEW_TYPE)[0];

  if (!leaf) {
    leaf = workspace.getRightLeaf(false);
    await leaf.setViewState({
      type: CAIRN_CONTEXT_VIEW_TYPE,
      active: true,
    });
  }
  workspace.revealLeaf(leaf);
}
```

**syncNoteFile() 수정** (자동 업데이트):
```typescript
async syncNoteFile(file: TFile) {
  try {
    // ... 기존 코드 ...
    await this.api.syncNote(noteData);
    new Notice(`✅ ${file.basename} synced`);

    // Context Panel 업데이트
    const leaf = this.app.workspace.getLeavesOfType(CAIRN_CONTEXT_VIEW_TYPE)[0];
    if (leaf && leaf.view instanceof DidymosContextView) {
      await (leaf.view as DidymosContextView).updateContext(noteData.note_id);
    }
  } catch (error) { ... }
}
```

---

## Step 4-9: 빌드 및 테스트

```bash
cd didymos-obsidian
npm run dev
cp main.js manifest.json styles.css "../didymos-test-vault/.obsidian/plugins/didymos/"
```

1. Obsidian에서 **"Open Context Panel"** 실행
2. 노트 작성 및 저장
3. Context Panel이 자동으로 업데이트되는지 확인

---

## ✅ 프론트엔드 완료 체크리스트

- [ ] `src/views/contextView.ts` 작성
- [ ] `styles.css` 작성
- [ ] Context View 등록
- [ ] 빌드 성공
- [ ] 통합 테스트 (패널 열기, 자동 업데이트, 링크 이동)

---

**다음 Phase**: [Phase 5-1: Graph API (Backend)](./phase-5-graph-backend.md)

