import { ItemView, WorkspaceLeaf, Plugin } from "obsidian";
import { Network } from "vis-network";
import { DidymosSettings } from "../settings";
import { DidymosAPI, GraphData } from "../api/client";

export const DIDYMOS_GRAPH_VIEW_TYPE = "didymos-graph-view";

export class DidymosGraphView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;
  plugin: Plugin;
  network: Network | null = null;
  currentNoteId: string | null = null;
  currentHops: number = 1;
  autoHops: boolean = true; // 자동 hop 조정 모드
  showTopics = true;
  showProjects = true;
  showTasks = true;
  showRelated = true;
  layoutPreset: "force" | "hierarchical" = "force";
  themePreset: "default" | "midnight" | "contrast" = "default";
  fontPreset: "normal" | "compact" | "large" = "normal";
  layoutSpacing: "regular" | "compact" = "regular";
  viewMode: "note" | "vault" = "vault";  // 기본값을 vault로 변경
  enableClustering: boolean = true; // Vault 모드에서 클러스터링 활성화

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings, plugin: Plugin) {
    super(leaf);
    this.settings = settings;
    this.plugin = plugin;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return DIDYMOS_GRAPH_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Graph";
  }

  getIcon(): string {
    return "git-branch";
  }

  async onOpen() {
    const container = this.containerEl.children[1] as HTMLElement;
    if (!container) return;

    container.empty();
    container.addClass("didymos-graph-container");

    // Header
    const header = container.createEl("div", { cls: "didymos-graph-header" });
    header.createEl("h2", { text: "📊 Knowledge Graph" });

    // Controls
    const controls = container.createEl("div", { cls: "didymos-graph-controls" });

    // 모드 전환 버튼
    const modeToggle = controls.createEl("div", { cls: "didymos-graph-mode-toggle" });
    const noteBtn = modeToggle.createEl("button", {
      text: "Note",
      cls: this.viewMode === "note" ? "active" : ""
    });
    const vaultBtn = modeToggle.createEl("button", {
      text: "Vault",
      cls: this.viewMode === "vault" ? "active" : ""
    });

    noteBtn.addEventListener("click", async () => {
      this.viewMode = "note";
      noteBtn.addClass("active");
      vaultBtn.removeClass("active");
      const active = this.app.workspace.getActiveFile();
      if (active) {
        await this.renderGraph(active.path);
      }
    });

    vaultBtn.addEventListener("click", async () => {
      this.viewMode = "vault";
      vaultBtn.addClass("active");
      noteBtn.removeClass("active");
      await this.renderVaultGraph();
    });

    // Sync All Notes 버튼
    const syncBtn = controls.createEl("button", {
      text: "🔄 Sync All Notes",
      cls: "didymos-sync-btn"
    });

    syncBtn.addEventListener("click", async () => {
      await this.syncAllNotes(syncBtn);
    });

    // Auto/Manual Hops Toggle
    const hopControlGroup = controls.createEl("div", { cls: "didymos-hop-control-group" });

    const autoHopToggle = hopControlGroup.createEl("label", { cls: "didymos-hop-toggle" });
    const autoCheckbox = autoHopToggle.createEl("input", { type: "checkbox" });
    autoCheckbox.checked = this.autoHops;
    autoHopToggle.createSpan({ text: "Auto Hops" });

    const hopSelect = hopControlGroup.createEl("select", { cls: "didymos-hop-select" });
    ["1 Hop", "2 Hops", "3 Hops", "4 Hops", "5 Hops"].forEach((label, index) => {
      const option = hopSelect.createEl("option", {
        text: label,
        value: String(index + 1),
      });
      if (index + 1 === this.currentHops) {
        option.selected = true;
      }
    });

    // 초기 상태 설정
    if (this.autoHops) {
      hopSelect.setAttribute("disabled", "true");
      hopSelect.style.opacity = "0.5";
    }

    autoCheckbox.addEventListener("change", async () => {
      this.autoHops = autoCheckbox.checked;
      if (this.autoHops) {
        hopSelect.setAttribute("disabled", "true");
        hopSelect.style.opacity = "0.5";
      } else {
        hopSelect.removeAttribute("disabled");
        hopSelect.style.opacity = "1";
      }

      // 그래프 다시 렌더링
      if (this.viewMode === "note" && this.currentNoteId) {
        await this.renderGraph(this.currentNoteId);
      } else if (this.viewMode === "vault") {
        await this.renderVaultGraph();
      }
    });

    hopSelect.addEventListener("change", async () => {
      this.currentHops = parseInt(hopSelect.value);
      if (this.viewMode === "note" && this.currentNoteId) {
        await this.renderGraph(this.currentNoteId);
      } else if (this.viewMode === "vault") {
        await this.renderVaultGraph();
      }
    });

    const toggles = container.createEl("div", { cls: "didymos-graph-toggles" });
    const mkToggle = (
      label: string,
      initial: boolean,
      onChange: (v: boolean) => void
    ) => {
      const wrap = toggles.createEl("label", { cls: "didymos-graph-toggle" });
      const checkbox = wrap.createEl("input", { type: "checkbox" });
      checkbox.checked = initial;
      wrap.createSpan({ text: label });
      checkbox.addEventListener("change", async () => {
        onChange(checkbox.checked);
        if (this.currentNoteId) await this.renderGraph(this.currentNoteId);
      });
    };

    mkToggle("Topics", this.showTopics, (v) => (this.showTopics = v));
    mkToggle("Projects", this.showProjects, (v) => (this.showProjects = v));
    mkToggle("Tasks", this.showTasks, (v) => (this.showTasks = v));
    mkToggle("Related", this.showRelated, (v) => (this.showRelated = v));

    const presets = container.createEl("div", { cls: "didymos-graph-presets" });

    const layoutSelect = presets.createEl("select", { cls: "didymos-graph-select" });
    [
      { label: "Force Layout", value: "force" },
      { label: "Hierarchical", value: "hierarchical" },
    ].forEach((opt) => {
      const o = layoutSelect.createEl("option", { text: opt.label, value: opt.value });
      if (opt.value === this.layoutPreset) o.selected = true;
    });
    layoutSelect.addEventListener("change", async () => {
      this.layoutPreset = layoutSelect.value as typeof this.layoutPreset;
      if (this.currentNoteId) await this.renderGraph(this.currentNoteId);
    });

    const themeSelect = presets.createEl("select", { cls: "didymos-graph-select" });
    [
      { label: "Default", value: "default" },
      { label: "Midnight", value: "midnight" },
      { label: "Contrast", value: "contrast" },
    ].forEach((opt) => {
      const o = themeSelect.createEl("option", { text: opt.label, value: opt.value });
      if (opt.value === this.themePreset) o.selected = true;
    });
    themeSelect.addEventListener("change", async () => {
      this.themePreset = themeSelect.value as typeof this.themePreset;
      if (this.currentNoteId) await this.renderGraph(this.currentNoteId);
    });

    const spacingSelect = presets.createEl("select", { cls: "didymos-graph-select" });
    [
      { label: "Normal Spacing", value: "regular" },
      { label: "Compact", value: "compact" },
    ].forEach((opt) => {
      const o = spacingSelect.createEl("option", { text: opt.label, value: opt.value });
      if (opt.value === this.layoutSpacing) o.selected = true;
    });
    spacingSelect.addEventListener("change", async () => {
      this.layoutSpacing = spacingSelect.value as typeof this.layoutSpacing;
      if (this.currentNoteId) await this.renderGraph(this.currentNoteId);
    });

    const fontSelect = presets.createEl("select", { cls: "didymos-graph-select" });
    [
      { label: "Normal Font", value: "normal" },
      { label: "Compact Font", value: "compact" },
      { label: "Large Font", value: "large" },
    ].forEach((opt) => {
      const o = fontSelect.createEl("option", { text: opt.label, value: opt.value });
      if (opt.value === this.fontPreset) o.selected = true;
    });
    fontSelect.addEventListener("change", async () => {
      this.fontPreset = fontSelect.value as typeof this.fontPreset;
      if (this.currentNoteId) await this.renderGraph(this.currentNoteId);
    });

    // Graph Container
    const graphContainer = container.createEl("div", {
      cls: "didymos-graph-network",
    });
    graphContainer.id = "didymos-graph-network";

    graphContainer.createEl("div", {
      text: "Loading knowledge graph...",
      cls: "didymos-graph-empty",
    });

    // 기본값이 vault이므로 vault 그래프로 초기화
    if (this.viewMode === "vault") {
      await this.renderVaultGraph();
    } else {
      // Note 모드인 경우 현재 활성 노트로 초기화
      const active = this.app.workspace.getActiveFile();
      if (active) {
        await this.renderGraph(active.path);
      }
    }

    // 파일 전환 시 그래프 갱신 (Note 모드일 때만)
    this.registerEvent(
      this.app.workspace.on("file-open", async (file) => {
        if (file && this.viewMode === "note") {
          await this.renderGraph(file.path);
        }
      })
    );
  }

  async syncAllNotes(button: HTMLElement) {
    const originalText = button.textContent || "";

    try {
      button.textContent = "⏳ Syncing...";
      button.setAttribute("disabled", "true");

      // Vault의 모든 .md 파일 가져오기
      const allMarkdownFiles = this.app.vault.getMarkdownFiles();

      // 증분 동기화: 마지막 sync 이후 수정된 파일만 필터링
      const lastSyncTime = this.settings.lastBulkSyncTime || 0;
      const markdownFiles = allMarkdownFiles.filter(file => file.stat.mtime > lastSyncTime);

      const totalFiles = markdownFiles.length;
      const skippedFiles = allMarkdownFiles.length - totalFiles;

      if (totalFiles === 0) {
        button.textContent = `✅ Already up to date (${skippedFiles} files)`;
        setTimeout(() => {
          button.textContent = originalText;
          button.removeAttribute("disabled");
        }, 3000);
        return;
      }

      let processed = 0;
      let succeeded = 0;
      let failed = 0;

      // 배치 처리 (10개씩)
      const batchSize = 10;
      for (let i = 0; i < markdownFiles.length; i += batchSize) {
        const batch = markdownFiles.slice(i, i + batchSize);

        await Promise.all(
          batch.map(async (file) => {
            try {
              const content = await this.app.vault.read(file);
              const noteData = {
                note_id: file.path,
                title: file.basename,
                path: file.path,
                content: content,
                tags: [],
                created_at: new Date(file.stat.ctime).toISOString(),
                updated_at: new Date(file.stat.mtime).toISOString(),
              };

              // 노트 저장 API 호출
              const response = await fetch(
                `${this.settings.apiEndpoint}/notes/sync`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    user_token: this.settings.userToken,
                    vault_id: this.settings.vaultId,
                    note: noteData,
                    privacy_mode: "full", // 전체 내용 전송
                  }),
                }
              );

              if (response.ok) {
                succeeded++;
              } else {
                failed++;
                console.error(`Failed to sync ${file.path}: ${response.status}`);
              }
            } catch (error) {
              failed++;
              console.error(`Error syncing ${file.path}:`, error);
            } finally {
              processed++;
              // 10개 단위로만 업데이트
              if (processed % 10 === 0) {
                button.textContent = `⏳ Syncing... ${processed}/${totalFiles}`;
              }
            }
          })
        );
      }

      // 마지막 sync 시간 업데이트
      this.settings.lastBulkSyncTime = Date.now();
      await (this.plugin as any).saveSettings();

      // 완료
      const statusMsg = skippedFiles > 0
        ? `✅ Synced ${succeeded}/${totalFiles} (${skippedFiles} skipped)`
        : `✅ Synced ${succeeded}/${totalFiles}`;
      button.textContent = statusMsg;
      setTimeout(() => {
        button.textContent = originalText;
        button.removeAttribute("disabled");
      }, 3000);

      // Vault 모드면 그래프 다시 렌더링
      if (this.viewMode === "vault") {
        await this.renderVaultGraph();
      }

    } catch (error: any) {
      button.textContent = `❌ Sync failed`;
      console.error("Sync error:", error);

      setTimeout(() => {
        button.textContent = originalText;
        button.removeAttribute("disabled");
      }, 3000);
    }
  }

  /**
   * 그래프 크기에 따라 자동으로 최적의 hops 결정
   */
  private calculateAutoHops(nodeCount: number): number {
    if (nodeCount < 20) return 5;
    if (nodeCount < 50) return 4;
    if (nodeCount < 100) return 3;
    if (nodeCount < 200) return 2;
    return 1;
  }

  async renderVaultGraph() {
    const graphContainer = this.containerEl.querySelector(
      "#didymos-graph-network"
    ) as HTMLElement;

    if (!graphContainer) return;

    graphContainer.empty();

    try {
      graphContainer.createEl("div", {
        text: "Loading vault graph...",
        cls: "didymos-graph-loading",
      });

      // hops 파라미터 추가
      const hops = this.autoHops ? 3 : this.currentHops; // vault는 기본 3 hops

      // Vault 전체 그래프를 한 번의 API 호출로 가져오기
      // 백엔드 limit 제한: 최대 500
      const graphResponse = await fetch(
        `${this.settings.apiEndpoint}/graph/user/${this.settings.userToken}?vault_id=${this.settings.vaultId}&limit=500`
      );

      if (!graphResponse.ok) {
        const errorText = await graphResponse.text();
        throw new Error(`Failed to fetch vault graph (${graphResponse.status}): ${errorText}`);
      }

      const graphData = await graphResponse.json();

      if (!graphData.nodes || graphData.nodes.length === 0) {
        graphContainer.empty();
        graphContainer.createEl("div", {
          text: "No graph data found in vault",
          cls: "didymos-graph-empty",
        });
        return;
      }

      const mergedGraphData: GraphData = {
        nodes: graphData.nodes || [],
        edges: graphData.edges || [],
      };

      // 필터 적용
      const filtered = this.applyFilters(mergedGraphData);

      // Clustering: 노드에 group 정보 추가
      if (this.enableClustering) {
        filtered.nodes = filtered.nodes.map(node => {
          // group 필드가 이미 있으면 그대로, 없으면 'note'로 설정
          if (!node.group) {
            node.group = 'note';
          }
          return node;
        });
      }

      graphContainer.empty();

      const fontSizes =
        this.fontPreset === "compact"
          ? { node: 12, edge: 9 }
          : this.fontPreset === "large"
          ? { node: 16, edge: 12 }
          : { node: 14, edge: 10 };

      const baseOptions = {
        nodes: {
          font: {
            size: fontSizes.node,
            face: "Inter, sans-serif",
          },
          borderWidth: 2,
          shadow: true,
        },
        edges: {
          font: {
            size: fontSizes.edge,
            align: "middle",
          },
          arrows: {
            to: {
              enabled: true,
              scaleFactor: 0.5,
            },
          },
          smooth: {
            enabled: true,
            type: "cubicBezier",
            forceDirection: "none",
            roundness: 0.5,
          },
        },
        physics: this.layoutSpacing === "compact"
          ? {
              enabled: true,
              barnesHut: {
                gravitationalConstant: -2500,
                springLength: 100,
                springConstant: 0.06,
              },
              stabilization: { iterations: 120 },
            }
          : {
              enabled: true,
              barnesHut: {
                gravitationalConstant: -2000,
                springLength: 150,
                springConstant: 0.04,
              },
              stabilization: { iterations: 100 },
            },
        interaction: {
          hover: true,
          tooltipDelay: 200,
        },
      };
      const themedOptions = this.applyTheme(baseOptions);
      const layoutOptions =
        this.layoutPreset === "hierarchical"
          ? {
              layout: {
                hierarchical: {
                  direction: "LR",
                  sortMethod: "hubsize",
                  levelSeparation: this.layoutSpacing === "compact" ? 80 : 120,
                  nodeSpacing: this.layoutSpacing === "compact" ? 80 : 120,
                },
              },
              physics: { enabled: false },
            }
          : {};

      // Clustering: group별 색상 정의
      const clusteringOptions = this.enableClustering ? {
        groups: {
          topic: {
            color: { background: '#E8F5E9', border: '#4CAF50' },
            shape: 'dot',
            size: 20,
          },
          project: {
            color: { background: '#E3F2FD', border: '#2196F3' },
            shape: 'box',
            size: 25,
          },
          task: {
            color: { background: '#FFF3E0', border: '#FF9800' },
            shape: 'diamond',
            size: 18,
          },
          note: {
            color: { background: '#F5F5F5', border: '#9E9E9E' },
            shape: 'dot',
            size: 12,
          },
        },
      } : {};

      this.network = new Network(graphContainer, filtered, {
        ...themedOptions,
        ...layoutOptions,
        ...clusteringOptions,
      });

      // Vault 모드에서 topic별로 자동 클러스터링
      if (this.enableClustering) {
        const topics = filtered.nodes.filter(n => n.group === 'topic');
        topics.forEach((topic) => {
          // 각 topic과 연결된 노드들을 하나의 클러스터로 묶기
          this.network?.cluster({
            joinCondition: (nodeOptions) => {
              // Topic 자체 또는 topic과 직접 연결된 노드들을 클러스터에 포함
              if (nodeOptions.id === topic.id) return true;
              return filtered.edges.some(e =>
                (e.from === topic.id && e.to === nodeOptions.id) ||
                (e.to === topic.id && e.from === nodeOptions.id)
              );
            },
            clusterNodeProperties: {
              label: topic.label || 'Topic',
              shape: 'dot',
              size: 40,
              font: { size: 16, color: '#2E7D32' },
              color: { background: '#A5D6A7', border: '#4CAF50' },
              borderWidth: 3,
            } as any,
          });
        });
      }

      this.network.on("click", (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          this.handleNodeClick(nodeId);
        }
      });

      this.network.on("doubleClick", (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          // 클러스터를 더블클릭하면 펼치기
          if (this.network?.isCluster(nodeId)) {
            this.network.openCluster(nodeId);
          } else {
            this.handleNodeDoubleClick(nodeId);
          }
        }
      });
    } catch (error: any) {
      console.error("Vault graph rendering error:", error);
      console.error("Error stack:", error.stack);
      console.error("API endpoint used:", `${this.settings.apiEndpoint}/graph/user/${this.settings.userToken}`);
      console.error("Settings:", {
        apiEndpoint: this.settings.apiEndpoint,
        userToken: this.settings.userToken,
        vaultId: this.settings.vaultId
      });

      graphContainer.empty();
      const errorDiv = graphContainer.createEl("div", {
        cls: "didymos-graph-error",
      });
      errorDiv.createEl("p", { text: `❌ Failed to load vault graph` });
      errorDiv.createEl("p", { text: `Error: ${error.message}` });
      errorDiv.createEl("p", { text: `Check console (Ctrl+Shift+I) for details` });
      errorDiv.createEl("p", {
        text: `Endpoint: ${this.settings.apiEndpoint}/graph/user/${this.settings.userToken}?vault_id=${this.settings.vaultId}`,
        cls: "didymos-graph-error-detail"
      });
    }
  }

  async renderGraph(noteId: string) {
    this.currentNoteId = noteId;

    const graphContainer = this.containerEl.querySelector(
      "#didymos-graph-network"
    ) as HTMLElement;

    if (!graphContainer) return;

    graphContainer.empty();

    try {
      graphContainer.createEl("div", {
        text: "Loading graph...",
        cls: "didymos-graph-loading",
      });

      // Auto mode: 먼저 1 hop으로 가져와서 노드 수 확인
      let hops = this.currentHops;
      if (this.autoHops) {
        const previewData: GraphData = await this.api.fetchGraph(noteId, 1);
        hops = this.calculateAutoHops(previewData.nodes.length);
      }

      const graphData: GraphData = await this.api.fetchGraph(noteId, hops);

      // 필터 적용
      const filtered = this.applyFilters(graphData);

      graphContainer.empty();

      const fontSizes =
        this.fontPreset === "compact"
          ? { node: 12, edge: 9 }
          : this.fontPreset === "large"
          ? { node: 16, edge: 12 }
          : { node: 14, edge: 10 };

      const baseOptions = {
        nodes: {
          font: {
            size: fontSizes.node,
            face: "Inter, sans-serif",
          },
          borderWidth: 2,
          shadow: true,
        },
        edges: {
          font: {
            size: fontSizes.edge,
            align: "middle",
          },
          arrows: {
            to: {
              enabled: true,
              scaleFactor: 0.5,
            },
          },
          smooth: {
            enabled: true,
            type: "cubicBezier",
            forceDirection: "none",
            roundness: 0.5,
          },
        },
        physics: this.layoutSpacing === "compact"
          ? {
              enabled: true,
              barnesHut: {
                gravitationalConstant: -2500,
                springLength: 100,
                springConstant: 0.06,
              },
              stabilization: { iterations: 120 },
            }
          : {
              enabled: true,
              barnesHut: {
                gravitationalConstant: -2000,
                springLength: 150,
                springConstant: 0.04,
              },
              stabilization: { iterations: 100 },
            },
        interaction: {
          hover: true,
          tooltipDelay: 200,
        },
      };
      const themedOptions = this.applyTheme(baseOptions);
      const layoutOptions =
        this.layoutPreset === "hierarchical"
          ? {
              layout: {
                hierarchical: {
                  direction: "LR",
                  sortMethod: "hubsize",
                  levelSeparation: this.layoutSpacing === "compact" ? 80 : 120,
                  nodeSpacing: this.layoutSpacing === "compact" ? 80 : 120,
                },
              },
              physics: { enabled: false },
            }
          : {};

      this.network = new Network(graphContainer, filtered, {
        ...themedOptions,
        ...layoutOptions,
      });

      this.network.on("click", (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          this.handleNodeClick(nodeId);
        }
      });

      this.network.on("doubleClick", (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          this.handleNodeDoubleClick(nodeId);
        }
      });
    } catch (error: any) {
      graphContainer.empty();
      graphContainer.createEl("div", {
        text: `❌ Failed to load graph: ${error.message}`,
        cls: "didymos-graph-error",
      });
    }
  }

  handleNodeClick(nodeId: string) {
    if (
      !nodeId.startsWith("topic_") &&
      !nodeId.startsWith("project_") &&
      !nodeId.startsWith("task_")
    ) {
      this.network?.selectNodes([nodeId]);
    }
  }

  handleNodeDoubleClick(nodeId: string) {
    if (
      !nodeId.startsWith("topic_") &&
      !nodeId.startsWith("project_") &&
      !nodeId.startsWith("task_")
    ) {
      this.app.workspace.openLinkText(nodeId, "", false);
    }
  }

  async onClose() {
    if (this.network) {
      this.network.destroy();
      this.network = null;
    }
  }

  private applyFilters(graphData: GraphData): GraphData {
    const allowedNodes = graphData.nodes.filter((n) => {
      if (n.id === this.currentNoteId) return true;
      if (n.group === "topic") return this.showTopics;
      if (n.group === "project") return this.showProjects;
      if (n.group === "task") return this.showTasks;
      return this.showRelated;
    });

    const allowedIds = new Set(allowedNodes.map((n) => n.id));
    const allowedEdges = graphData.edges.filter(
      (e) => allowedIds.has(e.from) && allowedIds.has(e.to)
    );

    return { nodes: allowedNodes, edges: allowedEdges };
  }

  private applyTheme(options: any) {
    if (this.themePreset === "midnight") {
      return {
        ...options,
        nodes: {
          ...options.nodes,
          color: {
            border: "#6EE7FF",
            background: "#0F172A",
            highlight: { border: "#38BDF8", background: "#0B1224" },
          },
          font: { ...options.nodes.font, color: "#E2E8F0" },
        },
        edges: {
          ...options.edges,
          color: { color: "#94A3B8", highlight: "#38BDF8" },
        },
        physics: options.physics,
        interaction: options.interaction,
      };
    }

    if (this.themePreset === "contrast") {
      return {
        ...options,
        nodes: {
          ...options.nodes,
          color: {
            border: "#111827",
            background: "#FACC15",
            highlight: { border: "#0F172A", background: "#FDE68A" },
          },
          font: { ...options.nodes.font, color: "#0F172A" },
        },
        edges: {
          ...options.edges,
          color: { color: "#111827", highlight: "#0F172A" },
        },
        physics: options.physics,
        interaction: options.interaction,
      };
    }

    return options;
  }
}
