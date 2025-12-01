import { ItemView, WorkspaceLeaf, Plugin } from "obsidian";
import { Network } from "vis-network";
import { DidymosSettings } from "../settings";
import { DidymosAPI, GraphData, ClusteredGraphData } from "../api/client";

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
  currentZoomLevel: "out" | "medium" | "in" = "out"; // Zoom 레벨 추적
  clusterMethod: "semantic" | "type_based" = "semantic"; // 클러스터링 방식 선택
  includeClusterLLM: boolean = false; // 클러스터 요약 LLM 사용 여부
  clusterForceRecompute: boolean = false; // 캐시 무시 여부
  clusterStatusEl: HTMLElement | null = null;
  clusterDetailEl: HTMLElement | null = null;

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

    // 클러스터링 옵션 (Vault 모드)
    const clusteringControls = controls.createEl("div", { cls: "didymos-clustering-controls" });
    clusteringControls.createEl("span", { text: "Clustering" });

    const methodSelect = clusteringControls.createEl("select", { cls: "didymos-graph-select" });
    [
      { label: "Semantic (UMAP+HDBSCAN)", value: "semantic" },
      { label: "Type-based (fallback)", value: "type_based" },
    ].forEach((opt) => {
      const option = methodSelect.createEl("option", { text: opt.label, value: opt.value });
      if (opt.value === this.clusterMethod) option.selected = true;
    });
    methodSelect.addEventListener("change", async () => {
      this.clusterMethod = methodSelect.value as typeof this.clusterMethod;
      this.clusterForceRecompute = true; // 캐시 무시하고 재계산
      if (this.viewMode === "vault") {
        await this.renderVaultGraph();
      }
    });

    const llmToggle = clusteringControls.createEl("label", { cls: "didymos-graph-toggle" });
    const llmCheckbox = llmToggle.createEl("input", { type: "checkbox" });
    llmCheckbox.checked = this.includeClusterLLM;
    llmToggle.createSpan({ text: "LLM Summary" });
    llmCheckbox.addEventListener("change", async () => {
      this.includeClusterLLM = llmCheckbox.checked;
      this.clusterForceRecompute = true;
      if (this.viewMode === "vault") {
        await this.renderVaultGraph();
      }
    });

    const recomputeBtn = clusteringControls.createEl("button", {
      text: "Recompute",
      cls: "didymos-sync-btn"
    });
    recomputeBtn.addEventListener("click", async () => {
      this.clusterForceRecompute = true;
      if (this.viewMode === "vault") {
        await this.renderVaultGraph();
      }
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
        if (this.viewMode === "note" && this.currentNoteId) {
          await this.renderGraph(this.currentNoteId);
        } else if (this.viewMode === "vault") {
          await this.renderVaultGraph();
        }
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

    // Status Bar
    const statusBar = container.createEl("div", { cls: "didymos-graph-status" });
    this.clusterStatusEl = statusBar.createSpan({
      text: "Clustering: semantic (cached)",
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

    if (this.clusterStatusEl) {
      this.clusterStatusEl.setText(
        `Clustering: ${this.clusterMethod}${this.includeClusterLLM ? " + LLM" : ""} (loading...)`
      );
    }

    try {
      graphContainer.createEl("div", {
        text: "Loading vault graph...",
        cls: "didymos-graph-loading",
      });

      // 클러스터링 활성화 시 클러스터 API 사용
      if (this.enableClustering) {
        const clusteredData: ClusteredGraphData = await this.api.fetchClusteredGraph(
          this.settings.vaultId,
          {
            targetClusters: 10,
            includeLLM: this.includeClusterLLM,
            forceRecompute: this.clusterForceRecompute,
            method: this.clusterMethod
          }
        );
        this.clusterForceRecompute = false;

        if (this.clusterStatusEl) {
          this.clusterStatusEl.setText(
            `Clusters: ${clusteredData.cluster_count} • Nodes: ${clusteredData.total_nodes} • Method: ${clusteredData.computation_method}${this.includeClusterLLM ? " + LLM" : ""}`
          );
        }

        console.log(`✅ Clustered graph loaded: ${clusteredData.cluster_count} clusters, ${clusteredData.total_nodes} total nodes`);

        // 클러스터를 vis-network 노드로 변환
        const clusterNodes = clusteredData.clusters.map(cluster => {
          const summary = cluster.summary || "No summary yet";
          const insights = (cluster.key_insights && cluster.key_insights.length > 0)
            ? cluster.key_insights.join("\n")
            : "No insights yet";
          const samples = cluster.sample_entities && cluster.sample_entities.length > 0
            ? `Samples: ${cluster.sample_entities.slice(0, 5).join(", ")}`
            : "Samples: -";
          const recent = typeof cluster.recent_updates === "number"
            ? `Recent updates (7d): ${cluster.recent_updates}`
            : "Recent updates (7d): -";

          return {
            id: cluster.id,
            label: `${cluster.name}\n(${cluster.node_count} nodes)`,
            shape: 'box',
            size: 30 + (cluster.importance_score * 5),
            color: {
              background: this.getClusterColor(cluster.contains_types),
              border: '#666666'
            },
            font: { size: 16, color: '#ffffff' },
            group: 'cluster',
            title: `${summary}\n${recent}\n${samples}\n\nInsights:\n${insights}`,
            cluster_data: cluster
          };
        });

        const clusterEdges = clusteredData.edges.map(edge => ({
          from: edge.from,
          to: edge.to,
          label: edge.relation_type,
          arrows: { to: { enabled: true, scaleFactor: 0.4 } },
          color: { color: '#888888', highlight: '#333333' },
          width: Math.max(1, edge.weight * 0.5),  // 얇은 선 (기존 * 2 → * 0.5)
          font: {
            size: 11,
            color: '#555555',
            strokeWidth: 2,
            strokeColor: '#ffffff',
            align: 'horizontal',
            background: 'rgba(255,255,255,0.8)'
          },
          smooth: { type: 'curvedCW', roundness: 0.2 }
        }));

        const filtered: GraphData = {
          nodes: clusterNodes,
          edges: clusterEdges
        };

        this.renderClusteredGraph(graphContainer, filtered);
        return;
      }

      // 일반 모드: 기존 로직
      const hops = this.autoHops ? 3 : this.currentHops;
      const graphResponse = await fetch(
        `${this.settings.apiEndpoint}/graph/user/${this.settings.userToken}?vault_id=${this.settings.vaultId}&limit=500`
      );

      if (!graphResponse.ok) {
        const errorText = await graphResponse.text();
        throw new Error(`Failed to fetch vault graph (${graphResponse.status}): ${errorText}`);
      }

      const graphData = await graphResponse.json();

      if (this.clusterStatusEl) {
        this.clusterStatusEl.setText("Clustering disabled (raw vault graph)");
      }

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

      // Zoom 이벤트 리스너 추가 (동적 클러스터링)
      this.network.on("zoom", () => {
        if (!this.network) return;

        const scale = this.network.getScale();
        this.updateClusteringByZoom(scale, filtered);
      });

      // 초기 클러스터링 적용 (Zoom Out 상태)
      this.updateClusteringByZoom(this.network.getScale(), filtered);

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
      if (this.clusterStatusEl) {
        this.clusterStatusEl.setText(`Clustering failed: ${error.message}`);
      }
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

  /**
   * Zoom 레벨에 따라 동적으로 클러스터링 조정
   * Scale 임계값:
   * - < 0.5: Zoom Out → Topic 클러스터만
   * - 0.5 ~ 1.2: Zoom Medium → Topic + Project 표시
   * - > 1.2: Zoom In → 모든 노드 표시
   */
  private updateClusteringByZoom(scale: number, graphData: GraphData) {
    if (!this.network || !this.enableClustering) return;

    // Zoom 레벨 결정
    let newZoomLevel: "out" | "medium" | "in";
    if (scale < 0.8) {
      newZoomLevel = "out";
    } else if (scale < 1.5) {
      newZoomLevel = "medium";
    } else {
      newZoomLevel = "in";
    }

    // 레벨이 변경되지 않았으면 아무것도 하지 않음
    if (newZoomLevel === this.currentZoomLevel) return;

    console.log(`Zoom level changed: ${this.currentZoomLevel} → ${newZoomLevel} (scale: ${scale.toFixed(2)})`);
    this.currentZoomLevel = newZoomLevel;

    // 모든 클러스터 해제
    const allNodeIds = (this.network as any).body.data.nodes.getIds();
    const clusterIds = allNodeIds.filter((id: string) =>
      this.network?.isCluster(id)
    );
    clusterIds.forEach((clusterId: string) => {
      if (this.network?.isCluster(clusterId)) {
        this.network.openCluster(clusterId);
      }
    });

    // Zoom 레벨에 따라 클러스터링 재적용
    if (newZoomLevel === "out") {
      // Zoom Out: 모든 Note 노드를 숨기고 Topic/Project/Task만 표시
      const noteNodes = graphData.nodes.filter(n => n.group === 'note');

      // 모든 Note를 하나의 큰 클러스터로 묶음
      if (noteNodes.length > 0) {
        this.network?.cluster({
          joinCondition: (nodeOptions) => {
            const node = graphData.nodes.find(n => n.id === nodeOptions.id);
            return node?.group === 'note';
          },
          clusterNodeProperties: {
            id: 'cluster_all_notes',
            label: `Notes (${noteNodes.length})`,
            shape: 'box',
            size: 30,
            font: { size: 14, color: '#616161' },
            color: { background: '#E0E0E0', border: '#9E9E9E' },
            borderWidth: 2,
            hidden: true, // 클러스터를 숨김
          } as any,
        });
      }

    } else if (newZoomLevel === "medium") {
      // Zoom Medium: Topic과 연결된 Note들을 클러스터로 묶음 (Project/Task는 개별 표시)
      const topics = graphData.nodes.filter(n => n.group === 'topic');
      topics.forEach((topic) => {
        // Topic과 연결된 Note만 찾기
        const connectedNotes = graphData.nodes.filter(node => {
          if (node.group !== 'note') return false;
          return graphData.edges.some(e =>
            (e.from === topic.id && e.to === node.id) ||
            (e.to === topic.id && e.from === node.id)
          );
        });

        // 연결된 Note가 있으면 클러스터 생성
        if (connectedNotes.length > 0) {
          this.network?.cluster({
            joinCondition: (nodeOptions) => {
              if (nodeOptions.id === topic.id) return true;
              const node = graphData.nodes.find(n => n.id === nodeOptions.id);
              if (!node || node.group !== 'note') return false;
              return graphData.edges.some(e =>
                (e.from === topic.id && e.to === nodeOptions.id) ||
                (e.to === topic.id && e.from === nodeOptions.id)
              );
            },
            clusterNodeProperties: {
              id: `cluster_topic_${topic.id}`,
              label: `${topic.label}\n(${connectedNotes.length} notes)`,
              shape: 'dot',
              size: 40,
              font: { size: 16, color: '#2E7D32' },
              color: { background: '#A5D6A7', border: '#4CAF50' },
              borderWidth: 3,
            } as any,
          });
        }
      });

    }
    // newZoomLevel === "in": 클러스터링 없음 (모든 노드 표시)
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

  private getClusterColor(containsTypes: Record<string, number>): string {
    /**
     * 클러스터에 포함된 노드 타입에 따라 색상 결정
     */
    const typeColors: Record<string, string> = {
      topic: '#4CAF50',     // 녹색
      project: '#2196F3',   // 파란색
      task: '#FF9800',      // 주황색
      note: '#9E9E9E'       // 회색
    };

    // 가장 많은 타입의 색상 선택
    let maxCount = 0;
    let dominantType = 'note';

    for (const [type, count] of Object.entries(containsTypes)) {
      if (count > maxCount) {
        maxCount = count;
        dominantType = type;
      }
    }

    return typeColors[dominantType] || '#666666';
  }

  private renderClusteredGraph(container: HTMLElement, graphData: GraphData) {
    /**
     * 클러스터 그래프 렌더링
     */
    container.empty();

    const baseOptions = {
      nodes: {
        font: {
          size: 16,
          face: "Inter, sans-serif",
          color: '#ffffff'
        },
        borderWidth: 2,
        shadow: true,
      },
      edges: {
        font: {
          size: 12,
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
        },
      },
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -5000,
          springLength: 200,
          springConstant: 0.01,
        },
        stabilization: { iterations: 150 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: true,
      },
    };

    const themedOptions = this.applyTheme(baseOptions);

    this.network = new Network(container, graphData, themedOptions);

    // 클러스터 클릭 이벤트 - 상세 정보 표시
    this.network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = graphData.nodes.find(n => n.id === nodeId);

        if (node && (node as any).cluster_data) {
          this.showClusterDetails((node as any).cluster_data);
        }
      }
    });

    console.log(`✅ Clustered graph rendered: ${graphData.nodes.length} clusters, ${graphData.edges.length} edges`);
  }

  private showClusterDetails(clusterData: any) {
    /**
     * 클러스터 상세 정보를 모달로 표시
     */
    if (this.clusterDetailEl) {
      this.clusterDetailEl.remove();
    }

    const container = this.containerEl.querySelector(".didymos-graph-container") as HTMLElement;
    const detail = container.createEl("div", { cls: "didymos-cluster-detail" });
    this.clusterDetailEl = detail;

    const header = detail.createEl("div", { cls: "didymos-cluster-detail__header" });
    header.createEl("h3", { text: `📦 ${clusterData.name}` });
    const closeBtn = header.createEl("button", { text: "Close" });
    closeBtn.addEventListener("click", () => {
      detail.remove();
      this.clusterDetailEl = null;
    });

    const meta = detail.createEl("div", { cls: "didymos-cluster-detail__meta" });
    meta.createSpan({ text: `Nodes: ${clusterData.node_count}` });
    meta.createSpan({ text: `Importance: ${(clusterData.importance_score || 0).toFixed(1)}/10` });
    meta.createSpan({ text: `Recent (7d): ${clusterData.recent_updates ?? 0}` });

    const summary = detail.createEl("div", { cls: "didymos-cluster-detail__summary" });
    summary.createEl("h4", { text: "요약" });
    summary.createEl("p", { text: clusterData.summary || "N/A" });

    const insightsWrap = detail.createEl("div", { cls: "didymos-cluster-detail__insights" });
    insightsWrap.createEl("h4", { text: "주요 인사이트" });
    const insightList = insightsWrap.createEl("ul");
    (clusterData.key_insights || ["인사이트 없음"]).forEach((ins: string) => {
      insightList.createEl("li", { text: ins });
    });

    const samplesWrap = detail.createEl("div", { cls: "didymos-cluster-detail__samples" });
    samplesWrap.createEl("h4", { text: "샘플 엔티티" });
    const sampleEntities = clusterData.sample_entities || [];
    samplesWrap.createEl("p", { text: sampleEntities.length ? sampleEntities.slice(0, 8).join(", ") : "-" });

    const notesWrap = detail.createEl("div", { cls: "didymos-cluster-detail__samples" });
    notesWrap.createEl("h4", { text: "샘플 노트" });
    const sampleNotes = clusterData.sample_notes || [];
    const sampleNoteIds = clusterData.note_ids || [];
    if (sampleNotes.length) {
      const list = notesWrap.createEl("ul");
      sampleNotes.slice(0, 5).forEach((title: string, idx: number) => {
        const li = list.createEl("li");
        const btn = li.createEl("button", { text: title });
        btn.addEventListener("click", () => {
          const noteId = sampleNoteIds[idx] || title;
          this.app.workspace.openLinkText(noteId, "", false);
        });
      });
    } else {
      notesWrap.createEl("p", { text: "-" });
    }

    const nextActions = detail.createEl("div", { cls: "didymos-cluster-detail__actions" });
    nextActions.createEl("h4", { text: "다음 액션" });
    const actions = (clusterData.key_insights || []).filter((x: string) => x.toLowerCase().includes("next action"));
    if (actions.length === 0) actions.push("이 클러스터에서 연결이 약한 노트를 검토하세요.");
    const actionList = nextActions.createEl("ul");
    actions.forEach((action: string) => actionList.createEl("li", { text: action }));

    // Drilldown 힌트
    const hint = detail.createEl("div", { cls: "didymos-cluster-detail__hint" });
    hint.createSpan({ text: "Tip: Zoom In to expand clusters, or switch to Note mode for per-note graph." });
  }
}
