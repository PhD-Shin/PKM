# Phase 5-2: Graph Panel UI (Frontend)

> Obsidian 플러그인에서 지식 그래프를 시각화하는 UI 구현

**예상 시간**: 2~3시간  
**난이도**: ⭐⭐⭐⭐⭐

---

## 목표

- vis-network 라이브러리 연동
- Graph View 구현 (노드/엣지 렌더링)
- 인터랙션 구현 (클릭, 더블클릭, 1/2 hop 전환)
- CSS 스타일링

---

## Step 5-4: vis-network 설치

```bash
cd didymos-obsidian
npm install vis-network
```

---

## Step 5-5: API 클라이언트 확장

파일 수정: `didymos-obsidian/src/api/client.ts`

**Interface 추가**:

```typescript
export interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    shape: string;
    color: any;
    size: number;
    group: string;
  }>;
  edges: Array<{
    from: string;
    to: string;
    label: string;
    arrows: string;
    color: string;
    dashes?: boolean;
  }>;
}
```

**메소드 추가**:

```typescript
async fetchGraph(noteId: string, hops: number = 1): Promise<GraphData> {
  const url = new URL(
    `${this.settings.apiBaseUrl}/notes/graph/${encodeURIComponent(noteId)}`
  );
  url.searchParams.set("user_token", this.settings.userToken);
  url.searchParams.set("hops", String(hops));

  try {
    const response = await fetch(url.toString());

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to fetch graph:", error);
    throw error;
  }
}
```

---

## Step 5-6: Graph View 구현

파일 생성: `didymos-obsidian/src/views/graphView.ts`

```typescript
import { ItemView, WorkspaceLeaf } from "obsidian";
import { Network } from "vis-network";
import { DidymosSettings } from "../settings";
import { DidymosAPI, GraphData } from "../api/client";

export const CAIRN_GRAPH_VIEW_TYPE = "didymos-graph-view";

export class DidymosGraphView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;
  network: Network | null = null;
  currentNoteId: string | null = null;
  currentHops: number = 1;

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return CAIRN_GRAPH_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Graph";
  }

  getIcon(): string {
    return "git-branch";
  }

  async onOpen() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("didymos-graph-container");

    // Header
    const header = container.createEl("div", { cls: "didymos-graph-header" });
    header.createEl("h2", { text: "📊 Knowledge Graph" });

    // Controls
    const controls = container.createEl("div", { cls: "didymos-graph-controls" });

    controls.createEl("label", { text: "Depth: " });

    const hopSelect = controls.createEl("select", { cls: "didymos-hop-select" });
    ["1 Hop", "2 Hops"].forEach((label, index) => {
      const option = hopSelect.createEl("option", {
        text: label,
        value: String(index + 1),
      });
      if (index + 1 === this.currentHops) {
        option.selected = true;
      }
    });

    hopSelect.addEventListener("change", async () => {
      this.currentHops = parseInt(hopSelect.value);
      if (this.currentNoteId) {
        await this.renderGraph(this.currentNoteId);
      }
    });

    // Graph Container
    const graphContainer = container.createEl("div", {
      cls: "didymos-graph-network",
    });
    graphContainer.id = "didymos-graph-network";

    // Empty message
    graphContainer.createEl("div", {
      text: "노트를 저장하면 그래프가 표시됩니다.",
      cls: "didymos-graph-empty",
    });
  }

  async renderGraph(noteId: string) {
    this.currentNoteId = noteId;

    const graphContainer = this.containerEl.querySelector(
      "#didymos-graph-network"
    ) as HTMLElement;

    if (!graphContainer) return;

    graphContainer.empty();

    try {
      // 로딩
      graphContainer.createEl("div", {
        text: "Loading graph...",
        cls: "didymos-graph-loading",
      });

      // Graph 데이터 가져오기
      const graphData = await this.api.fetchGraph(noteId, this.currentHops);

      graphContainer.empty();

      // vis-network 옵션
      const options = {
        nodes: {
          font: {
            size: 14,
            face: "Inter, sans-serif",
          },
          borderWidth: 2,
          shadow: true,
        },
        edges: {
          font: {
            size: 10,
            align: "middle",
          },
          arrows: {
            to: {
              enabled: true,
              scaleFactor: 0.5,
            },
          },
          smooth: {
            type: "cubicBezier",
            forceDirection: "none",
          },
        },
        physics: {
          enabled: true,
          barnesHut: {
            gravitationalConstant: -2000,
            springLength: 150,
            springConstant: 0.04,
          },
          stabilization: {
            iterations: 100,
          },
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
        },
      };

      // Network 생성
      this.network = new Network(graphContainer, graphData, options);

      // 클릭 이벤트
      this.network.on("click", (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          this.handleNodeClick(nodeId);
        }
      });

      // 더블클릭 이벤트
      this.network.on("doubleClick", (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          this.handleNodeDoubleClick(nodeId);
        }
      });
    } catch (error) {
      graphContainer.empty();
      graphContainer.createEl("div", {
        text: `❌ Failed to load graph: ${error.message}`,
        cls: "didymos-graph-error",
      });
    }
  }

  handleNodeClick(nodeId: string) {
    console.log("Node clicked:", nodeId);
    
    // Note 노드인 경우 하이라이트
    if (!nodeId.startsWith("topic_") && 
        !nodeId.startsWith("project_") && 
        !nodeId.startsWith("task_")) {
      // 노트 노드
      this.network?.selectNodes([nodeId]);
    }
  }

  handleNodeDoubleClick(nodeId: string) {
    // Note 노드인 경우 열기
    if (!nodeId.startsWith("topic_") && 
        !nodeId.startsWith("project_") && 
        !nodeId.startsWith("task_")) {
      this.app.workspace.openLinkText(nodeId, "", false);
    }
  }

  async onClose() {
    if (this.network) {
      this.network.destroy();
      this.network = null;
    }
  }
}
```

---

## Step 5-7: CSS 스타일링

파일 수정: `didymos-obsidian/styles.css`

```css
/* Graph Panel */
.didymos-graph-container {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.didymos-graph-header h2 {
  margin: 0 0 12px 0;
  font-size: 1.5em;
}

.didymos-graph-controls {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.didymos-hop-select {
  padding: 4px 8px;
  border: 1px solid var(--background-modifier-border);
  border-radius: 4px;
  background-color: var(--background-primary);
  color: var(--text-normal);
}

.didymos-graph-network {
  flex: 1;
  border: 1px solid var(--background-modifier-border);
  border-radius: 8px;
  background-color: var(--background-secondary);
  position: relative;
}

.didymos-graph-empty,
.didymos-graph-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--text-muted);
  font-style: italic;
}

.didymos-graph-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--text-error);
  background-color: var(--background-modifier-error);
  padding: 16px;
  border-radius: 8px;
  max-width: 80%;
  text-align: center;
}
```

---

## Step 5-8: 메인 플러그인 등록

파일 수정: `didymos-obsidian/main.ts`

**Import**:
```typescript
import {
  DidymosGraphView,
  CAIRN_GRAPH_VIEW_TYPE,
} from "./src/views/graphView";
```

**onload()**:
```typescript
// Graph View 등록
this.registerView(
  CAIRN_GRAPH_VIEW_TYPE,
  (leaf) => new DidymosGraphView(leaf, this.settings)
);

// 명령 추가
this.addCommand({
  id: "didymos-open-graph",
  name: "Open Knowledge Graph",
  callback: () => {
    this.activateGraphView();
  },
});
```

**activateGraphView()**:
```typescript
async activateGraphView() {
  const { workspace } = this.app;

  let leaf = workspace.getLeavesOfType(CAIRN_GRAPH_VIEW_TYPE)[0];

  if (!leaf) {
    leaf = workspace.getRightLeaf(false);
    await leaf.setViewState({
      type: CAIRN_GRAPH_VIEW_TYPE,
      active: true,
    });
  }
  workspace.revealLeaf(leaf);
}
```

**syncNoteFile() 수정** (Graph 자동 업데이트):
```typescript
// Graph Panel 업데이트
const graphLeaf = this.app.workspace.getLeavesOfType(CAIRN_GRAPH_VIEW_TYPE)[0];
if (graphLeaf && graphLeaf.view instanceof DidymosGraphView) {
  await (graphLeaf.view as DidymosGraphView).renderGraph(noteData.note_id);
}
```

---

## Step 5-9: 빌드 및 테스트

```bash
cd didymos-obsidian
npm run dev
cp main.js manifest.json styles.css "../didymos-test-vault/.obsidian/plugins/didymos/"
```

1. Obsidian에서 **"Open Knowledge Graph"** 실행
2. Graph Panel이 우측에 열림
3. 노트 저장 시 그래프 렌더링 확인
4. 1 Hop / 2 Hops 전환 테스트
5. 노드 더블클릭 시 해당 노트로 이동하는지 확인

---

## ✅ 프론트엔드 완료 체크리스트

- [ ] vis-network 설치
- [ ] `src/views/graphView.ts` 작성
- [ ] `styles.css` 업데이트
- [ ] Graph View 등록
- [ ] 통합 테스트 (패널 열기, 그래프 렌더링, 인터랙션)

---

**다음 Phase**: [Phase 6: Task 관리](./phase-6-tasks.md)

