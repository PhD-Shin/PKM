import { ItemView, WorkspaceLeaf, Plugin, TFile, Notice } from "obsidian";
import { Network } from "vis-network";
import { DidymosSettings } from "../settings";
import { DidymosAPI, GraphData, ClusteredGraphData, StaleKnowledge, EntityGraphData, EntityClusterData, EntityNoteGraphData, ThinkingInsightsData } from "../api/client";

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
  viewMode: "note" | "entity-clusters" = "entity-clusters";  // 2개 뷰만 (Note, 2nd Brain)
  enableClustering: boolean = true; // Vault 모드에서 클러스터링 활성화
  currentZoomLevel: "out" | "medium" | "in" = "out"; // Zoom 레벨 추적
  clusterMethod: "semantic" | "type_based" = "semantic"; // 클러스터링 방식 선택
  includeClusterLLM: boolean = false; // 클러스터 요약 LLM 사용 여부
  clusterForceRecompute: boolean = false; // 캐시 무시 여부
  clusterStatusEl: HTMLElement | null = null;
  clusterDetailEl: HTMLElement | null = null;
  selectedFolders: string[] = [];  // 선택된 폴더 목록
  availableFolders: Array<{ folder: string; note_count: number }> = [];  // 사용 가능한 폴더 목록
  folderSelectEl: HTMLElement | null = null;
  staleKnowledgePanelEl: HTMLElement | null = null;  // 잊혀진 지식 패널
  staleKnowledgeData: StaleKnowledge[] = [];
  insightsPanelEl: HTMLElement | null = null;  // Thinking Insights 패널
  insightsData: ThinkingInsightsData | null = null;
  insightsCache: { data: ThinkingInsightsData; timestamp: number } | null = null;
  insightsCacheTTL: number = 5 * 60 * 1000;  // 5분 캐시
  // brainViewMode 제거됨 - 2nd Brain은 Clusters 뷰만 사용
  // Sync cancellation
  syncAbortController: AbortController | null = null;
  isSyncing: boolean = false;

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

    // 모드 전환 버튼 (Note, 2nd Brain 2개만)
    const modeToggle = controls.createEl("div", { cls: "didymos-graph-mode-toggle" });
    const noteBtn = modeToggle.createEl("button", {
      text: "Note",
      cls: this.viewMode === "note" ? "active" : ""
    });
    const brainBtn = modeToggle.createEl("button", {
      text: "2nd Brain",
      cls: this.viewMode === "entity-clusters" ? "active" : ""
    });

    const clearActiveButtons = () => {
      noteBtn.removeClass("active");
      brainBtn.removeClass("active");
    };

    noteBtn.addEventListener("click", async () => {
      this.viewMode = "note";
      clearActiveButtons();
      noteBtn.addClass("active");
      const active = this.app.workspace.getActiveFile();
      if (active) {
        await this.renderGraph(active.path);
      }
    });

    brainBtn.addEventListener("click", async () => {
      this.viewMode = "entity-clusters";
      clearActiveButtons();
      brainBtn.addClass("active");
      await this.renderEntityClustersGraph();
    });

    // Sync All Notes 버튼 (Cancel 기능 포함)
    const syncBtn = controls.createEl("button", {
      text: "🔄 Sync All Notes",
      cls: "didymos-sync-btn"
    });

    syncBtn.addEventListener("click", async () => {
      if (this.isSyncing) {
        // Cancel 모드: 진행 중인 sync 취소
        this.cancelSync(syncBtn);
      } else {
        // Sync 모드: sync 시작
        await this.syncAllNotes(syncBtn);
      }
    });

    // 🔴 Reset & Resync 버튼 (엔티티 삭제 + 전체 재동기화)
    const resetBtn = controls.createEl("button", {
      text: "🔴 Reset & Resync",
      cls: "didymos-sync-btn didymos-reset-btn"
    });
    resetBtn.style.backgroundColor = "#dc3545";
    resetBtn.style.color = "white";

    resetBtn.addEventListener("click", async () => {
      const confirmed = confirm(
        "⚠️ 모든 엔티티를 삭제하고 전체 노트를 다시 동기화합니다.\n\n" +
        "1. 기존 엔티티/관계 전부 삭제\n" +
        "2. 모든 노트에서 엔티티 재추출\n\n" +
        "시간이 오래 걸릴 수 있습니다. 계속하시겠습니까?"
      );
      if (!confirmed) return;

      await this.resetAndResync(resetBtn);
    });

    // 💡 잊혀진 지식 버튼
    const staleBtn = controls.createEl("button", {
      text: "💡 Forgotten",
      cls: "didymos-sync-btn didymos-stale-btn"
    });
    staleBtn.style.backgroundColor = "#f39c12";
    staleBtn.style.color = "white";

    staleBtn.addEventListener("click", async () => {
      await this.toggleStaleKnowledgePanel();
    });

    // Thinking Insights 버튼 (Palantir Foundry 스타일)
    const insightsBtn = controls.createEl("button", {
      text: "Insights",
      cls: "didymos-sync-btn didymos-insights-btn"
    });
    insightsBtn.style.backgroundColor = "#9b59b6";
    insightsBtn.style.color = "white";

    insightsBtn.addEventListener("click", async () => {
      await this.toggleInsightsPanel();
    });

    // Note: Entity-Note Graph 토글 제거됨 (2nd Brain은 Clusters 뷰만 사용)

    // 폴더 필터 컨트롤 (PARA 노트 기법 지원)
    const folderControls = controls.createEl("div", { cls: "didymos-folder-controls" });
    folderControls.createEl("span", { text: "📁 Folder" });

    this.folderSelectEl = folderControls.createEl("div", { cls: "didymos-folder-select" });
    this.folderSelectEl.createEl("span", { text: "Loading...", cls: "didymos-folder-loading" });

    // Sync Folder 버튼
    const syncFolderBtn = folderControls.createEl("button", {
      text: "🔄 Sync Folder",
      cls: "didymos-sync-btn didymos-sync-folder-btn"
    });
    syncFolderBtn.style.marginLeft = "8px";
    syncFolderBtn.style.fontSize = "12px";

    syncFolderBtn.addEventListener("click", async () => {
      if (this.selectedFolders.length === 0) {
        alert("폴더를 먼저 선택해주세요.");
        return;
      }
      await this.syncFolderNotes(syncFolderBtn, this.selectedFolders[0]);
    });

    // 폴더 목록 로드
    this.loadFolders();

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

    // 초기 뷰 모드에 따라 그래프 로드 (Note, 2nd Brain 2가지만)
    if (this.viewMode === "entity-clusters") {
      await this.renderEntityClustersGraph();
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

  /**
   * Sync 취소
   */
  cancelSync(button: HTMLElement) {
    if (this.syncAbortController) {
      this.syncAbortController.abort();
      this.syncAbortController = null;
    }
    this.isSyncing = false;
    button.textContent = "🔄 Sync All Notes";
    button.removeClass("syncing");
    console.log("⛔ Sync cancelled by user");
  }

  /**
   * 특정 폴더의 노트만 Sync
   */
  async syncFolderNotes(button: HTMLElement, folderPath: string) {
    if (this.isSyncing) {
      return;
    }

    this.syncAbortController = new AbortController();
    this.isSyncing = true;

    try {
      const originalText = button.textContent || "";
      button.textContent = "⛔ Cancel";
      button.addClass("syncing");

      // 해당 폴더의 .md 파일만 필터링
      const allMarkdownFiles = this.app.vault.getMarkdownFiles();
      const folderFiles = allMarkdownFiles.filter(file =>
        file.path.startsWith(folderPath + "/") || file.path === folderPath
      );

      const totalFiles = folderFiles.length;

      if (totalFiles === 0) {
        button.textContent = `⚠️ No files in ${folderPath}`;
        this.isSyncing = false;
        this.syncAbortController = null;
        setTimeout(() => {
          button.textContent = originalText;
          button.removeClass("syncing");
        }, 3000);
        return;
      }

      let processed = 0;
      let succeeded = 0;
      let failed = 0;

      for (const file of folderFiles) {
        if (this.syncAbortController?.signal.aborted) {
          console.log(`⛔ Folder sync aborted at ${processed}/${totalFiles}`);
          break;
        }

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

          const response = await fetch(
            `${this.settings.apiEndpoint}/notes/sync`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                user_token: this.settings.userToken,
                vault_id: this.settings.vaultId,
                note: noteData,
                privacy_mode: "full",
              }),
              signal: this.syncAbortController?.signal,
            }
          );

          if (response.ok) {
            succeeded++;
          } else {
            failed++;
            console.error(`Failed to sync ${file.path}: ${response.status}`);
          }
        } catch (error: any) {
          if (error.name === "AbortError") {
            console.log(`⛔ Fetch aborted for ${file.path}`);
            break;
          }
          failed++;
          console.error(`Error syncing ${file.path}:`, error);
        }

        processed++;
        if (processed % 5 === 0 || processed === totalFiles) {
          if (!this.syncAbortController?.signal.aborted) {
            button.textContent = `⛔ (${processed}/${totalFiles})`;
          }
        }
      }

      if (this.syncAbortController?.signal.aborted) {
        button.textContent = `⚠️ Cancelled (${succeeded})`;
        setTimeout(() => {
          button.textContent = originalText;
          button.removeClass("syncing");
        }, 3000);
        return;
      }

      button.textContent = `✅ ${succeeded}/${totalFiles}`;
      setTimeout(() => {
        button.textContent = originalText;
        button.removeClass("syncing");
      }, 3000);

      // 그래프 새로고침 (2nd Brain 모드일 때)
      if (this.viewMode === "entity-clusters") {
        await this.renderEntityClustersGraph();
      }

    } catch (error: any) {
      if (error.name !== "AbortError") {
        button.textContent = `❌ Failed`;
        console.error("Folder sync error:", error);
      }
      setTimeout(() => {
        button.textContent = "🔄 Sync Folder";
        button.removeClass("syncing");
      }, 3000);
    } finally {
      this.isSyncing = false;
      this.syncAbortController = null;
    }
  }

  async syncAllNotes(button: HTMLElement, forceFullSync: boolean = false) {
    // 이미 syncing 중이면 무시
    if (this.isSyncing) {
      return;
    }

    // AbortController 생성
    this.syncAbortController = new AbortController();
    this.isSyncing = true;

    try {
      button.textContent = "⛔ Cancel Sync";
      button.addClass("syncing");

      // Vault의 모든 .md 파일 가져오기
      const allMarkdownFiles = this.app.vault.getMarkdownFiles();

      // 증분 동기화: 마지막 sync 이후 수정된 파일만 필터링 (forceFullSync이면 전체 동기화)
      const lastSyncTime = forceFullSync ? 0 : (this.settings.lastBulkSyncTime || 0);
      const markdownFiles = allMarkdownFiles.filter(file => file.stat.mtime > lastSyncTime);

      const totalFiles = markdownFiles.length;
      const skippedFiles = allMarkdownFiles.length - totalFiles;

      if (totalFiles === 0) {
        button.textContent = `✅ Already up to date (${skippedFiles} files)`;
        this.isSyncing = false;
        this.syncAbortController = null;
        setTimeout(() => {
          button.textContent = "🔄 Sync All Notes";
          button.removeClass("syncing");
        }, 3000);
        return;
      }

      let processed = 0;
      let succeeded = 0;
      let failed = 0;

      // 순차 처리 (1개씩) - Railway 서버 안정성 보장
      for (const file of markdownFiles) {
        // 취소 확인
        if (this.syncAbortController?.signal.aborted) {
          console.log(`⛔ Sync aborted at ${processed}/${totalFiles}`);
          break;
        }

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

          const response = await fetch(
            `${this.settings.apiEndpoint}/notes/sync`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                user_token: this.settings.userToken,
                vault_id: this.settings.vaultId,
                note: noteData,
                privacy_mode: "full",
              }),
              signal: this.syncAbortController?.signal,
            }
          );

          if (response.ok) {
            succeeded++;
          } else {
            failed++;
            console.error(`Failed to sync ${file.path}: ${response.status}`);
          }
        } catch (error: any) {
          // AbortError는 무시 (사용자가 취소함)
          if (error.name === "AbortError") {
            console.log(`⛔ Fetch aborted for ${file.path}`);
            break;
          }
          failed++;
          console.error(`Error syncing ${file.path}:`, error);
        }

        processed++;
        if (processed % 10 === 0 || processed === totalFiles) {
          // 취소 상태가 아닐 때만 버튼 텍스트 업데이트
          if (!this.syncAbortController?.signal.aborted) {
            button.textContent = `⛔ Cancel (${processed}/${totalFiles})`;
          }
        }
      }

      // 취소된 경우
      if (this.syncAbortController?.signal.aborted) {
        button.textContent = `⚠️ Cancelled (${succeeded} synced)`;
        setTimeout(() => {
          button.textContent = "🔄 Sync All Notes";
          button.removeClass("syncing");
        }, 3000);
        return;
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
        button.textContent = "🔄 Sync All Notes";
        button.removeClass("syncing");
      }, 3000);

      // 2nd Brain 모드면 그래프 다시 렌더링
      if (this.viewMode === "entity-clusters") {
        await this.renderEntityClustersGraph();
      }

    } catch (error: any) {
      // AbortError는 무시
      if (error.name !== "AbortError") {
        button.textContent = `❌ Sync failed`;
        console.error("Sync error:", error);
      }

      setTimeout(() => {
        button.textContent = "🔄 Sync All Notes";
        button.removeClass("syncing");
      }, 3000);
    } finally {
      this.isSyncing = false;
      this.syncAbortController = null;
    }
  }

  /**
   * 🔴 Reset & Resync: 엔티티 삭제 + 전체 재동기화
   */
  async resetAndResync(button: HTMLElement) {
    const originalText = button.textContent || "";

    try {
      // Step 1: 엔티티 삭제
      button.textContent = "🔴 1/2 Deleting entities...";
      button.setAttribute("disabled", "true");

      const result = await this.api.resetVaultEntities(this.settings.vaultId);
      console.log(`✅ Reset: ${result.deleted_entities} entities deleted`);

      // lastBulkSyncTime 리셋
      this.settings.lastBulkSyncTime = 0;
      await (this.plugin as any).saveSettings();

      // Step 2: 전체 재동기화 (forceFullSync = true)
      button.textContent = "🔄 2/2 Syncing all notes...";

      // Sync All 버튼 찾기
      const syncBtn = this.containerEl.querySelector(".didymos-sync-btn:not(.didymos-reset-btn)") as HTMLElement;
      if (syncBtn) {
        await this.syncAllNotes(syncBtn, true);  // forceFullSync = true
      }

      button.textContent = "✅ Reset & Resync complete";
      button.removeAttribute("disabled");

      setTimeout(() => {
        button.textContent = originalText;
      }, 3000);

      // 그래프 다시 렌더링
      if (this.viewMode === "entity-clusters") {
        await this.renderEntityClustersGraph();
      }

    } catch (error: any) {
      button.textContent = `❌ Reset & Resync failed`;
      console.error("Reset & Resync error:", error);
      button.removeAttribute("disabled");

      setTimeout(() => {
        button.textContent = originalText;
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

  /**
   * 폴더 목록 로드 및 UI 업데이트
   */
  async loadFolders() {
    if (!this.folderSelectEl) return;

    try {
      const foldersData = await this.api.fetchVaultFolders(this.settings.vaultId);
      this.availableFolders = foldersData.folders;

      // UI 업데이트
      this.folderSelectEl.empty();

      if (this.availableFolders.length === 0) {
        this.folderSelectEl.createEl("span", { text: "No folders found", cls: "didymos-folder-empty" });
        return;
      }

      // "All Folders" 옵션
      const allLabel = this.folderSelectEl.createEl("label", { cls: "didymos-folder-option" });
      const allCheckbox = allLabel.createEl("input", { type: "checkbox" });
      allCheckbox.checked = this.selectedFolders.length === 0;
      allLabel.createSpan({ text: `All (${foldersData.folders.reduce((sum, f) => sum + f.note_count, 0)} notes)` });

      allCheckbox.addEventListener("change", async () => {
        if (allCheckbox.checked) {
          this.selectedFolders = [];
          // 다른 체크박스 해제
          this.folderSelectEl?.querySelectorAll("input[type='checkbox']").forEach((cb: HTMLInputElement) => {
            if (cb !== allCheckbox) cb.checked = false;
          });
          // 2nd Brain 모드면 Entity Clusters, 아니면 Vault Graph
          if (this.viewMode === "entity-clusters") {
            await this.renderEntityClustersGraph();
          } else {
            await this.renderVaultGraph();
          }
        }
      });

      // 각 폴더 옵션
      for (const folder of this.availableFolders) {
        const label = this.folderSelectEl.createEl("label", { cls: "didymos-folder-option" });
        const checkbox = label.createEl("input", { type: "checkbox" });
        checkbox.checked = this.selectedFolders.includes(folder.folder);
        label.createSpan({ text: `${folder.folder} (${folder.note_count})` });

        checkbox.addEventListener("change", async () => {
          if (checkbox.checked) {
            // All 체크박스 해제
            allCheckbox.checked = false;
            if (!this.selectedFolders.includes(folder.folder)) {
              this.selectedFolders.push(folder.folder);
            }
          } else {
            this.selectedFolders = this.selectedFolders.filter(f => f !== folder.folder);
            if (this.selectedFolders.length === 0) {
              allCheckbox.checked = true;
            }
          }
          // 2nd Brain 모드면 Entity Clusters, 아니면 Vault Graph
          if (this.viewMode === "entity-clusters") {
            await this.renderEntityClustersGraph();
          } else {
            await this.renderVaultGraph();
          }
        });
      }

    } catch (error) {
      console.error("Failed to load folders:", error);
      this.folderSelectEl.empty();
      this.folderSelectEl.createEl("span", { text: "Failed to load folders", cls: "didymos-folder-error" });
    }
  }

  /**
   * Entity Graph - Entity 노드와 RELATES_TO 관계를 직접 시각화
   * 진정한 Knowledge Graph 뷰
   */
  async renderEntityGraph() {
    const graphContainer = this.containerEl.querySelector(
      "#didymos-graph-network"
    ) as HTMLElement;

    if (!graphContainer) return;

    graphContainer.empty();

    if (this.clusterStatusEl) {
      this.clusterStatusEl.setText("Entity Graph (loading...)");
    }

    try {
      graphContainer.createEl("div", {
        text: "Loading entity graph...",
        cls: "didymos-graph-loading",
      });

      // Entity Graph API 호출
      const entityData: EntityGraphData = await this.api.fetchEntityGraph(
        this.settings.vaultId,
        {
          limit: 300,
          minConnections: 1,
          includeNotes: true
        }
      );

      if (this.clusterStatusEl) {
        const stats = entityData.stats.by_type;
        const typeInfo = Object.entries(stats)
          .map(([type, count]) => `${type}: ${count}`)
          .join(" | ");
        this.clusterStatusEl.setText(
          `Entity Graph: ${entityData.node_count} nodes, ${entityData.edge_count} edges • ${typeInfo}`
        );
      }

      console.log(`✅ Entity graph loaded: ${entityData.node_count} nodes, ${entityData.edge_count} edges`);

      if (entityData.node_count === 0) {
        graphContainer.empty();
        graphContainer.createEl("div", {
          text: "No entities with connections found. Try syncing some notes first.",
          cls: "didymos-graph-empty",
        });
        return;
      }

      // Entity 노드를 vis-network 노드로 변환
      const visNodes = entityData.nodes.map(entity => ({
        id: entity.id,
        label: entity.label,
        shape: 'dot',
        size: entity.size,
        color: {
          background: entity.color,
          border: this.darkenColor(entity.color, 0.3),
          highlight: {
            background: this.lightenColor(entity.color, 0.2),
            border: entity.color
          }
        },
        font: {
          size: 12,
          color: '#333333',
          strokeWidth: 2,
          strokeColor: '#ffffff'
        },
        title: `${entity.label}\n\nType: ${entity.type}\nConnections: ${entity.connections}${entity.summary ? `\n\n${entity.summary}` : ''}${entity.connected_notes && entity.connected_notes.length > 0 ? `\n\nNotes: ${entity.connected_notes.slice(0, 3).join(', ')}...` : ''}`,
        group: entity.type,
        entity_data: entity
      }));

      // RELATES_TO 관계를 vis-network 엣지로 변환
      const visEdges = entityData.edges.map((edge, idx) => ({
        id: `edge_${idx}`,
        from: edge.source,
        to: edge.target,
        label: edge.label || '',
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        color: {
          color: '#cccccc',
          highlight: '#666666',
          opacity: 0.6
        },
        width: 1,
        smooth: { enabled: true, type: 'continuous', roundness: 0.5 } as any,
        title: edge.label || edge.type
      }));

      const graphData: GraphData = {
        nodes: visNodes,
        edges: visEdges
      };

      this.renderEntityNetworkGraph(graphContainer, graphData);

    } catch (error) {
      console.error("Failed to load entity graph:", error);
      graphContainer.empty();
      graphContainer.createEl("div", {
        text: `Failed to load entity graph: ${error}`,
        cls: "didymos-graph-error",
      });
    }
  }

  /**
   * Entity Graph 전용 vis-network 렌더링
   */
  renderEntityNetworkGraph(container: HTMLElement, graphData: GraphData) {
    container.empty();

    const networkContainer = container.createEl("div", {
      cls: "didymos-network-container",
    });
    networkContainer.style.height = "100%";
    networkContainer.style.width = "100%";

    const options = {
      nodes: {
        shape: 'dot',
        scaling: {
          min: 10,
          max: 40
        },
        font: {
          size: 12,
          face: 'Tahoma'
        }
      },
      edges: {
        smooth: {
          enabled: true,
          type: 'continuous',
          roundness: 0.5
        } as any,
        arrows: {
          to: { enabled: true, scaleFactor: 0.5 }
        }
      },
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 100,
          springConstant: 0.08,
          damping: 0.4
        },
        stabilization: {
          enabled: true,
          iterations: 200,
          updateInterval: 25
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: true,
        zoomView: true
      },
      groups: {
        Goal: { color: { background: '#9b59b6', border: '#8e44ad' } },
        Project: { color: { background: '#2ecc71', border: '#27ae60' } },
        Task: { color: { background: '#e74c3c', border: '#c0392b' } },
        Topic: { color: { background: '#3498db', border: '#2980b9' } },
        Concept: { color: { background: '#1abc9c', border: '#16a085' } },
        Question: { color: { background: '#f39c12', border: '#d68910' } },
        Insight: { color: { background: '#e91e63', border: '#c2185b' } },
        Resource: { color: { background: '#607d8b', border: '#455a64' } },
        Person: { color: { background: '#e67e22', border: '#d35400' } }
      }
    };

    if (this.network) {
      this.network.destroy();
    }

    this.network = new Network(
      networkContainer,
      { nodes: graphData.nodes, edges: graphData.edges },
      options
    );

    // 노드 클릭 이벤트 - 연결된 노트 열기
    this.network.on("doubleClick", async (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = graphData.nodes.find(n => n.id === nodeId);
        if (node && (node as any).entity_data?.connected_notes?.length > 0) {
          const notePath = (node as any).entity_data.connected_notes[0];
          const file = this.app.vault.getAbstractFileByPath(notePath);
          if (file) {
            await this.app.workspace.openLinkText(notePath, "", false);
          }
        }
      }
    });
  }

  /**
   * Entity Clusters Graph - 하이브리드 클러스터링 (Graph + Embedding)
   * 2nd Brain 시각화: 시멘틱하게 유사한 Entity들을 그룹으로 표시
   */
  async renderEntityClustersGraph() {
    const graphContainer = this.containerEl.querySelector(
      "#didymos-graph-network"
    ) as HTMLElement;

    if (!graphContainer) return;

    graphContainer.empty();

    if (this.clusterStatusEl) {
      this.clusterStatusEl.setText("Entity Clusters (loading...)");
    }

    try {
      graphContainer.createEl("div", {
        text: "Loading 2nd Brain clusters...",
        cls: "didymos-graph-loading",
      });

      // 선택된 폴더가 있으면 폴더 필터 적용
      const folderPrefix = this.selectedFolders.length > 0 ? this.selectedFolders[0] + "/" : undefined;

      // Entity Clusters API 호출
      const clusterData: EntityClusterData = await this.api.fetchEntityClusters(
        this.settings.vaultId,
        {
          minClusterSize: 3,
          resolution: 1.0,
          folderPrefix: folderPrefix
        }
      );

      if (this.clusterStatusEl) {
        const folderInfo = folderPrefix ? ` • Folder: ${this.selectedFolders[0]}` : "";
        this.clusterStatusEl.setText(
          `2nd Brain: ${clusterData.cluster_count} clusters, ${clusterData.total_entities} entities • Method: ${clusterData.method}${folderInfo}`
        );
      }

      console.log(`✅ Entity clusters loaded: ${clusterData.cluster_count} clusters, ${clusterData.total_entities} entities`);

      if (clusterData.cluster_count === 0) {
        graphContainer.empty();
        graphContainer.createEl("div", {
          text: "No entity clusters found. Try syncing some notes first.",
          cls: "didymos-graph-empty",
        });
        return;
      }

      // 클러스터를 vis-network 노드로 변환
      const clusterNodes = clusterData.clusters.map(cluster => {
        const typeInfo = Object.entries(cluster.type_distribution)
          .map(([type, count]) => `${type}: ${count}`)
          .join(", ");

        const samples = cluster.sample_entities && cluster.sample_entities.length > 0
          ? cluster.sample_entities.slice(0, 5).join(", ")
          : "-";

        // 클러스터 크기에 따른 노드 크기
        const nodeSize = Math.min(60, 20 + Math.sqrt(cluster.entity_count) * 5);

        // 타입 분포에 따른 색상
        const dominantType = Object.entries(cluster.type_distribution)
          .sort((a, b) => b[1] - a[1])[0]?.[0] || "Topic";

        const typeColors: Record<string, string> = {
          Goal: "#9b59b6",
          Project: "#2ecc71",
          Task: "#e74c3c",
          Topic: "#3498db",
          Concept: "#1abc9c",
          Question: "#f39c12",
          Insight: "#e91e63",
          Resource: "#607d8b",
          Person: "#e67e22"
        };

        return {
          id: cluster.id,
          label: `${cluster.name}\n(${cluster.entity_count})`,
          shape: 'dot',
          size: nodeSize,
          color: {
            background: typeColors[dominantType] || "#666666",
            border: this.darkenColor(typeColors[dominantType] || "#666666", 0.3),
            highlight: {
              background: this.lightenColor(typeColors[dominantType] || "#666666", 0.2),
              border: typeColors[dominantType] || "#666666"
            }
          },
          font: {
            size: 14,
            color: '#333333',
            strokeWidth: 3,
            strokeColor: '#ffffff'
          },
          title: `📦 ${cluster.name}\n\n` +
            `Entities: ${cluster.entity_count}\n` +
            `Types: ${typeInfo}\n` +
            `Cohesion: ${(cluster.cohesion_score * 100).toFixed(0)}%\n\n` +
            `Samples: ${samples}`,
          group: dominantType,
          cluster_data: cluster
        };
      });

      // 클러스터 간 엣지를 vis-network 엣지로 변환
      const clusterEdges = clusterData.edges.map((edge, idx) => ({
        id: `edge_${idx}`,
        from: edge.from,
        to: edge.to,
        width: Math.min(5, Math.max(1, Math.log2(edge.weight + 1) * 1.5)),
        color: {
          color: '#888888',
          highlight: '#333333',
          opacity: 0.6
        },
        smooth: { enabled: true, type: 'continuous', roundness: 0.3 } as any,
        title: `${edge.weight} shared connections`,
        label: '',
        arrows: {}
      }));

      const graphData: GraphData = {
        nodes: clusterNodes,
        edges: clusterEdges
      };

      this.renderEntityClusterNetwork(graphContainer, graphData);

    } catch (error) {
      console.error("Failed to load entity clusters:", error);
      graphContainer.empty();
      graphContainer.createEl("div", {
        text: `Failed to load entity clusters: ${error}`,
        cls: "didymos-graph-error",
      });
    }
  }

  /**
   * Entity Cluster Network 전용 vis-network 렌더링
   */
  renderEntityClusterNetwork(container: HTMLElement, graphData: GraphData) {
    container.empty();

    const networkContainer = container.createEl("div", {
      cls: "didymos-network-container",
    });
    networkContainer.style.height = "100%";
    networkContainer.style.width = "100%";

    const options = {
      nodes: {
        shape: 'dot',
        scaling: {
          min: 20,
          max: 60
        },
        font: {
          size: 14,
          face: 'Tahoma'
        }
      },
      edges: {
        smooth: {
          enabled: true,
          type: 'continuous',
          roundness: 0.3
        } as any
      },
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -80,
          centralGravity: 0.01,
          springLength: 150,
          springConstant: 0.05,
          damping: 0.4
        },
        stabilization: {
          enabled: true,
          iterations: 300,
          updateInterval: 25
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: true,
        zoomView: true
      },
      groups: {
        Goal: { color: { background: '#9b59b6', border: '#8e44ad' } },
        Project: { color: { background: '#2ecc71', border: '#27ae60' } },
        Task: { color: { background: '#e74c3c', border: '#c0392b' } },
        Topic: { color: { background: '#3498db', border: '#2980b9' } },
        Concept: { color: { background: '#1abc9c', border: '#16a085' } },
        Question: { color: { background: '#f39c12', border: '#d68910' } },
        Insight: { color: { background: '#e91e63', border: '#c2185b' } },
        Resource: { color: { background: '#607d8b', border: '#455a64' } },
        Person: { color: { background: '#e67e22', border: '#d35400' } }
      }
    };

    if (this.network) {
      this.network.destroy();
    }

    this.network = new Network(
      networkContainer,
      { nodes: graphData.nodes, edges: graphData.edges },
      options
    );

    // 클러스터 클릭 이벤트 - 상세 정보 표시
    this.network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = graphData.nodes.find(n => n.id === nodeId);

        if (node && (node as any).cluster_data) {
          this.showEntityClusterDetails((node as any).cluster_data);
        }
      }
    });

    // 더블클릭: 클러스터 펼치기 (해당 클러스터의 엔티티들만 표시)
    this.network.on("doubleClick", async (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = graphData.nodes.find(n => n.id === nodeId);

        if (node && (node as any).cluster_data) {
          // 클러스터 상세 정보를 가져와서 해당 클러스터의 엔티티들만 표시
          await this.renderClusterEntitiesGraph((node as any).cluster_data);
        }
      }
    });
  }

  /**
   * 클러스터의 엔티티들을 그래프로 표시 (드릴다운 뷰)
   */
  async renderClusterEntitiesGraph(clusterData: any) {
    const graphContainer = this.containerEl.querySelector(
      "#didymos-graph-network"
    ) as HTMLElement;

    if (!graphContainer) return;

    graphContainer.empty();

    if (this.clusterStatusEl) {
      this.clusterStatusEl.setText(`Cluster: ${clusterData.name} (loading entities...)`);
    }

    try {
      graphContainer.createEl("div", {
        text: `Loading entities for "${clusterData.name}"...`,
        cls: "didymos-graph-loading",
      });

      // 클러스터 상세 정보 가져오기 (엔티티 목록 포함)
      // entity_uuids를 직접 전달하여 정확한 클러스터 멤버십 보장
      const detailResponse = await this.api.fetchEntityClusterDetail(
        this.settings.vaultId,
        clusterData.name,
        clusterData.entity_uuids || []
      );

      const detail = detailResponse.cluster;

      if (this.clusterStatusEl) {
        this.clusterStatusEl.setText(
          `Cluster: ${detail.name} • ${detail.entity_count} entities • ${detail.internal_edges.length} connections`
        );
      }

      if (!detail.entities || detail.entities.length === 0) {
        graphContainer.empty();
        graphContainer.createEl("div", {
          text: "No entity details available for this cluster.",
          cls: "didymos-graph-empty",
        });
        return;
      }

      // 타입별 색상
      const typeColors: Record<string, string> = {
        Goal: "#9b59b6",
        Project: "#2ecc71",
        Task: "#e74c3c",
        Topic: "#3498db",
        Concept: "#1abc9c",
        Question: "#f39c12",
        Insight: "#e91e63",
        Resource: "#607d8b",
        Person: "#e67e22"
      };

      // 엔티티를 vis-network 노드로 변환
      const entityNodes = detail.entities.map(entity => ({
        id: entity.uuid,
        label: entity.name,
        shape: 'dot',
        size: 15 + Math.min(25, entity.connections * 2),
        color: {
          background: typeColors[entity.pkm_type] || "#666666",
          border: this.darkenColor(typeColors[entity.pkm_type] || "#666666", 0.3),
          highlight: {
            background: this.lightenColor(typeColors[entity.pkm_type] || "#666666", 0.2),
            border: typeColors[entity.pkm_type] || "#666666"
          }
        },
        font: {
          size: 12,
          color: '#333333',
          strokeWidth: 2,
          strokeColor: '#ffffff'
        },
        title: `${entity.name}\n\nType: ${entity.pkm_type}\nConnections: ${entity.connections}${entity.summary ? `\n\n${entity.summary}` : ''}`,
        group: entity.pkm_type,
        entity_data: entity
      }));

      // 관계 타입별 스타일
      const relTypeStyles: Record<string, { color: string; dashes: boolean; arrows: string; label: string }> = {
        BROADER: { color: '#9b59b6', dashes: false, arrows: 'to', label: 'broader' },
        NARROWER: { color: '#1abc9c', dashes: false, arrows: 'to', label: 'narrower' },
        RELATES_TO: { color: '#cccccc', dashes: false, arrows: '', label: '' }
      };

      // 내부 엣지를 vis-network 엣지로 변환
      const entityEdges = detail.internal_edges.map((edge: any, idx: number) => {
        const relType = edge.type || 'RELATES_TO';
        const style = relTypeStyles[relType] || relTypeStyles.RELATES_TO;
        return {
          id: `edge_${idx}`,
          from: edge.from,
          to: edge.to,
          label: style.label,
          arrows: style.arrows ? { to: { enabled: true, scaleFactor: 0.8 } } : {},
          color: {
            color: style.color,
            highlight: style.color,
            opacity: 0.8
          },
          dashes: style.dashes,
          width: Math.max(1, edge.weight || 1),
          smooth: { enabled: true, type: 'continuous', roundness: 0.5 } as any,
          title: edge.fact || `${relType}`,
          font: { size: 9, color: '#666666', strokeWidth: 1, strokeColor: '#ffffff' }
        };
      });

      const graphData: GraphData = {
        nodes: entityNodes,
        edges: entityEdges
      };

      this.renderClusterEntitiesNetwork(graphContainer, graphData, detail.name, detail.related_notes || []);

    } catch (error) {
      console.error("Failed to load cluster entities:", error);
      graphContainer.empty();
      graphContainer.createEl("div", {
        text: `Failed to load cluster entities: ${error}`,
        cls: "didymos-graph-error",
      });
    }
  }

  /**
   * 클러스터 엔티티 네트워크 렌더링
   */
  renderClusterEntitiesNetwork(container: HTMLElement, graphData: GraphData, clusterName: string, relatedNotes: any[] = []) {
    container.empty();

    // 상단 컨트롤 영역
    const controlBar = container.createEl("div", { cls: "didymos-cluster-control-bar" });
    controlBar.style.display = "flex";
    controlBar.style.justifyContent = "space-between";
    controlBar.style.alignItems = "center";
    controlBar.style.marginBottom = "10px";

    // 뒤로가기 버튼
    const backBtn = controlBar.createEl("button", {
      text: "← Back to Clusters",
      cls: "didymos-back-btn"
    });
    backBtn.addEventListener("click", async () => {
      await this.renderEntityClustersGraph();
    });

    // 관계 타입 범례
    const legend = controlBar.createEl("div", { cls: "didymos-relation-legend" });
    legend.style.display = "flex";
    legend.style.gap = "12px";
    legend.style.fontSize = "11px";
    legend.innerHTML = `
      <span style="display:flex;align-items:center;gap:4px;"><span style="width:20px;height:2px;background:#9b59b6;display:inline-block;"></span>broader</span>
      <span style="display:flex;align-items:center;gap:4px;"><span style="width:20px;height:2px;background:#1abc9c;display:inline-block;"></span>narrower</span>
      <span style="display:flex;align-items:center;gap:4px;"><span style="width:20px;height:2px;background:#cccccc;display:inline-block;"></span>relates_to</span>
    `;

    // 메인 컨텐츠 영역 (그래프 + 관련 노트)
    const mainContent = container.createEl("div", { cls: "didymos-cluster-main" });
    mainContent.style.display = "flex";
    mainContent.style.height = "calc(100% - 50px)";
    mainContent.style.gap = "10px";

    // 그래프 컨테이너
    const networkContainer = mainContent.createEl("div", {
      cls: "didymos-network-container",
    });
    networkContainer.style.flex = relatedNotes.length > 0 ? "1 1 65%" : "1 1 100%";
    networkContainer.style.height = "100%";

    // 관련 노트 패널
    if (relatedNotes.length > 0) {
      const notesPanel = mainContent.createEl("div", { cls: "didymos-related-notes-panel" });
      notesPanel.style.flex = "0 0 35%";
      notesPanel.style.height = "100%";
      notesPanel.style.overflowY = "auto";
      notesPanel.style.borderLeft = "1px solid var(--background-modifier-border)";
      notesPanel.style.paddingLeft = "10px";

      const notesHeader = notesPanel.createEl("div", { cls: "didymos-notes-header" });
      notesHeader.style.display = "flex";
      notesHeader.style.justifyContent = "space-between";
      notesHeader.style.alignItems = "center";
      notesHeader.style.marginBottom = "8px";
      notesHeader.createEl("h4", { text: `Related Notes (${relatedNotes.length})` });

      const notesList = notesPanel.createEl("div", { cls: "didymos-notes-list" });

      relatedNotes.forEach((note: any) => {
        const noteItem = notesList.createEl("div", { cls: "didymos-note-item" });
        noteItem.style.padding = "8px";
        noteItem.style.marginBottom = "6px";
        noteItem.style.borderRadius = "6px";
        noteItem.style.backgroundColor = "var(--background-secondary)";
        noteItem.style.cursor = "pointer";
        noteItem.style.transition = "background-color 0.2s";

        noteItem.addEventListener("mouseenter", () => {
          noteItem.style.backgroundColor = "var(--background-modifier-hover)";
        });
        noteItem.addEventListener("mouseleave", () => {
          noteItem.style.backgroundColor = "var(--background-secondary)";
        });

        // 노트 제목
        const title = noteItem.createEl("div", { cls: "note-title" });
        title.style.fontWeight = "500";
        title.style.marginBottom = "4px";
        title.setText(note.title || note.note_id);

        // 연결된 엔티티 수
        const entityBadge = noteItem.createEl("div", { cls: "note-entities" });
        entityBadge.style.fontSize = "11px";
        entityBadge.style.color = "var(--text-muted)";
        entityBadge.setText(`${note.entity_count} entities: ${(note.entity_names || []).slice(0, 3).join(", ")}${note.entity_count > 3 ? "..." : ""}`);

        // 클릭 시 노트 열기
        noteItem.addEventListener("click", async () => {
          const path = note.path || note.note_id;
          const file = this.app.vault.getAbstractFileByPath(path);
          if (file && file instanceof TFile) {
            await this.app.workspace.getLeaf(false).openFile(file);
          } else {
            new Notice(`Note not found: ${path}`);
          }
        });
      });
    }

    const options = {
      nodes: {
        shape: 'dot',
        scaling: {
          min: 15,
          max: 40
        },
        font: {
          size: 12,
          face: 'Tahoma'
        }
      },
      edges: {
        smooth: {
          enabled: true,
          type: 'continuous',
          roundness: 0.5
        } as any
      },
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 80,
          springConstant: 0.1,
          damping: 0.4
        },
        stabilization: {
          enabled: true,
          iterations: 200,
          updateInterval: 25
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: true,
        zoomView: true
      },
      groups: {
        Goal: { color: { background: '#9b59b6', border: '#8e44ad' } },
        Project: { color: { background: '#2ecc71', border: '#27ae60' } },
        Task: { color: { background: '#e74c3c', border: '#c0392b' } },
        Topic: { color: { background: '#3498db', border: '#2980b9' } },
        Concept: { color: { background: '#1abc9c', border: '#16a085' } },
        Question: { color: { background: '#f39c12', border: '#d68910' } },
        Insight: { color: { background: '#e91e63', border: '#c2185b' } },
        Resource: { color: { background: '#607d8b', border: '#455a64' } },
        Person: { color: { background: '#e67e22', border: '#d35400' } }
      }
    };

    if (this.network) {
      this.network.destroy();
    }

    this.network = new Network(
      networkContainer,
      { nodes: graphData.nodes, edges: graphData.edges },
      options
    );

    // 노드 클릭 이벤트 - 상세 정보 표시
    this.network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = graphData.nodes.find(n => n.id === nodeId);
        if (node && (node as any).entity_data) {
          console.log("Entity clicked:", (node as any).entity_data);
        }
      }
    });
  }

  /**
   * Entity Cluster 상세 정보 표시
   */
  private showEntityClusterDetails(clusterData: any) {
    if (this.clusterDetailEl) {
      this.clusterDetailEl.remove();
    }

    const container = this.containerEl.querySelector(".didymos-graph-container") as HTMLElement;
    const detail = container.createEl("div", { cls: "didymos-cluster-detail" });
    this.clusterDetailEl = detail;

    const header = detail.createEl("div", { cls: "didymos-cluster-detail__header" });
    header.createEl("h3", { text: `🧠 ${clusterData.name}` });
    const closeBtn = header.createEl("button", { text: "Close" });
    closeBtn.addEventListener("click", () => {
      detail.remove();
      this.clusterDetailEl = null;
    });

    const meta = detail.createEl("div", { cls: "didymos-cluster-detail__meta" });
    meta.createSpan({ text: `Entities: ${clusterData.entity_count}` });
    meta.createSpan({ text: `Cohesion: ${(clusterData.cohesion_score * 100).toFixed(0)}%` });
    meta.createSpan({ text: `Internal Edges: ${clusterData.internal_edges}` });

    // 타입 분포
    const typesWrap = detail.createEl("div", { cls: "didymos-cluster-detail__types" });
    typesWrap.createEl("h4", { text: "타입 분포" });
    const typeList = typesWrap.createEl("div", { cls: "type-badges" });
    for (const [type, count] of Object.entries(clusterData.type_distribution || {})) {
      typeList.createEl("span", {
        text: `${type}: ${count}`,
        cls: `type-badge type-${type.toLowerCase()}`
      });
    }

    // 샘플 엔티티
    const samplesWrap = detail.createEl("div", { cls: "didymos-cluster-detail__samples" });
    samplesWrap.createEl("h4", { text: "포함된 엔티티" });
    const sampleEntities = clusterData.sample_entities || [];
    if (sampleEntities.length > 0) {
      const list = samplesWrap.createEl("ul");
      sampleEntities.forEach((name: string) => {
        list.createEl("li", { text: name });
      });
    } else {
      samplesWrap.createEl("p", { text: "-" });
    }

    // 힌트
    const hint = detail.createEl("div", { cls: "didymos-cluster-detail__hint" });
    hint.createSpan({ text: "Tip: Double-click the cluster to view its entities" });
  }

  // 색상 유틸리티 함수들
  darkenColor(hex: string, percent: number): string {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent * 100);
    const R = Math.max((num >> 16) - amt, 0);
    const G = Math.max((num >> 8 & 0x00FF) - amt, 0);
    const B = Math.max((num & 0x0000FF) - amt, 0);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
  }

  lightenColor(hex: string, percent: number): string {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent * 100);
    const R = Math.min((num >> 16) + amt, 255);
    const G = Math.min((num >> 8 & 0x00FF) + amt, 255);
    const B = Math.min((num & 0x0000FF) + amt, 255);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
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
        // 선택된 폴더가 있으면 첫 번째 폴더로 필터링 (여러 폴더 선택 시 첫 번째만 사용)
        const folderPrefix = this.selectedFolders.length > 0 ? this.selectedFolders[0] + "/" : undefined;

        const clusteredData: ClusteredGraphData = await this.api.fetchClusteredGraph(
          this.settings.vaultId,
          {
            targetClusters: 10,
            includeLLM: this.includeClusterLLM,
            forceRecompute: this.clusterForceRecompute,
            method: this.clusterMethod,
            folderPrefix: folderPrefix
          }
        );
        this.clusterForceRecompute = false;

        const folderInfo = folderPrefix ? ` • Folder: ${this.selectedFolders[0]}` : "";
        if (this.clusterStatusEl) {
          this.clusterStatusEl.setText(
            `Clusters: ${clusteredData.cluster_count} • Nodes: ${clusteredData.total_nodes} • Method: ${clusteredData.computation_method}${this.includeClusterLLM ? " + LLM" : ""}${folderInfo}`
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
          width: Math.min(5, Math.max(1.5, Math.log2(edge.weight + 1) * 1.5)),  // 로그 스케일 (1.5~5px)
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

  // ============================================
  // 잊혀진 지식 (Stale Knowledge) 기능
  // ============================================

  async toggleStaleKnowledgePanel() {
    const container = this.containerEl.children[1] as HTMLElement;
    if (!container) return;

    // 패널이 이미 있으면 토글
    if (this.staleKnowledgePanelEl) {
      this.staleKnowledgePanelEl.remove();
      this.staleKnowledgePanelEl = null;
      return;
    }

    // 패널 생성
    this.staleKnowledgePanelEl = container.createEl("div", {
      cls: "didymos-stale-panel"
    });

    const panelHeader = this.staleKnowledgePanelEl.createEl("div", {
      cls: "didymos-stale-panel__header"
    });
    panelHeader.createEl("h3", { text: "💡 잊혀진 지식" });

    const closeBtn = panelHeader.createEl("button", { text: "✕" });
    closeBtn.addEventListener("click", () => {
      if (this.staleKnowledgePanelEl) {
        this.staleKnowledgePanelEl.remove();
        this.staleKnowledgePanelEl = null;
      }
    });

    // 필터 버튼
    const filterRow = this.staleKnowledgePanelEl.createEl("div", {
      cls: "didymos-stale-panel__filters"
    });

    const btn30 = filterRow.createEl("button", { text: "30일+", cls: "active" });
    const btn60 = filterRow.createEl("button", { text: "60일+" });

    btn30.addEventListener("click", async () => {
      btn30.addClass("active");
      btn60.removeClass("active");
      await this.loadStaleKnowledge(30);
    });

    btn60.addEventListener("click", async () => {
      btn60.addClass("active");
      btn30.removeClass("active");
      await this.loadStaleKnowledge(60);
    });

    // 일괄 확인 버튼
    const markAllBtn = filterRow.createEl("button", {
      text: "✓ 모두 확인",
      cls: "didymos-mark-all-btn"
    });
    markAllBtn.addEventListener("click", async () => {
      await this.markAllReviewed();
    });

    // 콘텐츠 영역
    const contentEl = this.staleKnowledgePanelEl.createEl("div", {
      cls: "didymos-stale-panel__content"
    });
    contentEl.createEl("p", { text: "로딩 중...", cls: "didymos-stale-loading" });

    // 데이터 로드
    await this.loadStaleKnowledge(30);
  }

  async loadStaleKnowledge(days: number) {
    if (!this.staleKnowledgePanelEl) return;

    const contentEl = this.staleKnowledgePanelEl.querySelector(".didymos-stale-panel__content") as HTMLElement;
    if (!contentEl) return;

    contentEl.empty();
    contentEl.createEl("p", { text: "로딩 중...", cls: "didymos-stale-loading" });

    try {
      const response = await this.api.fetchStaleKnowledge(days, 30);
      this.staleKnowledgeData = response.stale_knowledge;

      contentEl.empty();

      if (this.staleKnowledgeData.length === 0) {
        contentEl.createEl("p", {
          text: `${days}일 이상 된 잊혀진 지식이 없습니다! 🎉`,
          cls: "didymos-stale-empty"
        });
        return;
      }

      contentEl.createEl("p", {
        text: response.message,
        cls: "didymos-stale-message"
      });

      const list = contentEl.createEl("ul", { cls: "didymos-stale-list" });

      for (const item of this.staleKnowledgeData) {
        const li = list.createEl("li", {
          cls: `didymos-stale-item priority-${item.priority}`
        });

        const header = li.createEl("div", { cls: "didymos-stale-item__header" });

        const nameEl = header.createEl("span", {
          text: item.name,
          cls: "didymos-stale-item__name"
        });

        const daysEl = header.createEl("span", {
          text: `${item.days_since_access}일`,
          cls: `didymos-stale-item__days ${item.priority}`
        });

        if (item.summary) {
          li.createEl("p", {
            text: item.summary.length > 100 ? item.summary.slice(0, 100) + "..." : item.summary,
            cls: "didymos-stale-item__summary"
          });
        }

        // 확인 버튼
        const reviewBtn = li.createEl("button", {
          text: "✓ 확인",
          cls: "didymos-stale-item__review-btn"
        });
        reviewBtn.addEventListener("click", async () => {
          await this.markKnowledgeReviewed(item.uuid, li);
        });
      }

    } catch (error) {
      console.error("Failed to load stale knowledge:", error);
      contentEl.empty();
      contentEl.createEl("p", {
        text: "잊혀진 지식을 불러오는데 실패했습니다.",
        cls: "didymos-stale-error"
      });
    }
  }

  async markKnowledgeReviewed(uuid: string, listItem: HTMLElement) {
    try {
      await this.api.markKnowledgeReviewed(uuid);

      // UI에서 항목 제거 (애니메이션)
      listItem.addClass("reviewed");
      setTimeout(() => {
        listItem.remove();

        // 데이터에서도 제거
        this.staleKnowledgeData = this.staleKnowledgeData.filter(k => k.uuid !== uuid);

        // 목록이 비었으면 메시지 표시
        if (this.staleKnowledgeData.length === 0 && this.staleKnowledgePanelEl) {
          const contentEl = this.staleKnowledgePanelEl.querySelector(".didymos-stale-panel__content") as HTMLElement;
          if (contentEl) {
            contentEl.empty();
            contentEl.createEl("p", {
              text: "모든 지식을 복습했습니다! 🎉",
              cls: "didymos-stale-empty"
            });
          }
        }
      }, 300);

    } catch (error) {
      console.error("Failed to mark knowledge as reviewed:", error);
    }
  }

  async markAllReviewed() {
    if (this.staleKnowledgeData.length === 0) return;

    const confirmed = confirm(
      `${this.staleKnowledgeData.length}개의 지식을 모두 복습 완료로 표시하시겠습니까?`
    );
    if (!confirmed) return;

    try {
      const uuids = this.staleKnowledgeData.map(k => k.uuid);
      await this.api.markKnowledgeReviewedBatch(uuids);

      // UI 업데이트
      if (this.staleKnowledgePanelEl) {
        const contentEl = this.staleKnowledgePanelEl.querySelector(".didymos-stale-panel__content") as HTMLElement;
        if (contentEl) {
          contentEl.empty();
          contentEl.createEl("p", {
            text: "모든 지식을 복습했습니다! 🎉",
            cls: "didymos-stale-empty"
          });
        }
      }

      this.staleKnowledgeData = [];

    } catch (error) {
      console.error("Failed to mark all as reviewed:", error);
    }
  }

  // ============================================
  // Thinking Insights (Palantir Foundry Style)
  // ============================================

  async toggleInsightsPanel() {
    const container = this.containerEl.children[1] as HTMLElement;
    if (!container) return;

    // 패널이 이미 있으면 토글
    if (this.insightsPanelEl) {
      this.insightsPanelEl.remove();
      this.insightsPanelEl = null;
      return;
    }

    // 패널 생성
    this.insightsPanelEl = container.createEl("div", {
      cls: "didymos-insights-panel"
    });

    const panelHeader = this.insightsPanelEl.createEl("div", {
      cls: "didymos-insights-panel__header"
    });
    panelHeader.createEl("h3", { text: "Thinking Insights" });

    const closeBtn = panelHeader.createEl("button", { text: "✕" });
    closeBtn.addEventListener("click", () => {
      if (this.insightsPanelEl) {
        this.insightsPanelEl.remove();
        this.insightsPanelEl = null;
      }
    });

    // 콘텐츠 영역
    const contentEl = this.insightsPanelEl.createEl("div", {
      cls: "didymos-insights-panel__content"
    });
    contentEl.createEl("p", { text: "Loading insights...", cls: "didymos-insights-loading" });

    // 데이터 로드
    await this.loadThinkingInsights();
  }

  async loadThinkingInsights(forceRefresh: boolean = false) {
    if (!this.insightsPanelEl) return;

    const contentEl = this.insightsPanelEl.querySelector(".didymos-insights-panel__content") as HTMLElement;
    if (!contentEl) return;

    try {
      const folderPrefix = this.selectedFolders.length > 0 ? this.selectedFolders[0] + "/" : undefined;

      // 캐시 확인 (5분 TTL)
      const now = Date.now();
      if (!forceRefresh && this.insightsCache && (now - this.insightsCache.timestamp) < this.insightsCacheTTL) {
        this.insightsData = this.insightsCache.data;
        console.log("Using cached insights data");
      } else {
        this.insightsData = await this.api.fetchThinkingInsights(this.settings.vaultId, { folderPrefix });
        this.insightsCache = { data: this.insightsData, timestamp: now };
        console.log("Fetched fresh insights data");
      }

      contentEl.empty();

      // 0. Knowledge Health Score (상단에 눈에 띄게)
      if (this.insightsData.health_score) {
        const healthSection = contentEl.createEl("div", { cls: "didymos-insights-health" });
        const healthHeader = healthSection.createEl("div", { cls: "health-header" });
        healthHeader.createEl("h4", { text: "Knowledge Health" });

        const score = this.insightsData.health_score.overall;
        const scoreColor = score >= 70 ? "#2ecc71" : score >= 50 ? "#f39c12" : "#e74c3c";

        const scoreDisplay = healthSection.createEl("div", { cls: "health-score-display" });
        scoreDisplay.createEl("span", { text: `${score}`, cls: "score-number" });
        scoreDisplay.style.color = scoreColor;
        scoreDisplay.createEl("span", { text: "/100", cls: "score-max" });

        const metrics = healthSection.createEl("div", { cls: "health-metrics" });
        metrics.createEl("span", { text: `Density: ${(this.insightsData.health_score.connection_density * 100).toFixed(0)}%` });
        metrics.createEl("span", { text: `Isolated: ${(this.insightsData.health_score.isolation_ratio * 100).toFixed(0)}%` });

        if (this.insightsData.health_score.recommendations.length > 0) {
          const recEl = healthSection.createEl("div", { cls: "health-recommendations" });
          for (const rec of this.insightsData.health_score.recommendations.slice(0, 2)) {
            recEl.createEl("p", { text: `💡 ${rec}`, cls: "recommendation" });
          }
        }
      }

      // 요약 통계
      const summary = contentEl.createEl("div", { cls: "didymos-insights-summary" });
      summary.createEl("span", { text: `Entities: ${this.insightsData.summary.total_entities}` });
      summary.createEl("span", { text: `Focus: ${this.insightsData.summary.focus_count}` });
      summary.createEl("span", { text: `Bridges: ${this.insightsData.summary.bridge_count}` });
      summary.createEl("span", { text: `Isolated: ${this.insightsData.summary.isolated_count}` });

      // 1. Time Trends (시간 기반 트렌드)
      if (this.insightsData.time_trends) {
        const trendsSection = contentEl.createEl("div", { cls: "didymos-insights-section trends" });
        trendsSection.createEl("h4", { text: "Topic Trends (7d vs 30d)" });

        // Emerging Topics (새로 등장)
        if (this.insightsData.time_trends.emerging_topics.length > 0) {
          const emergingEl = trendsSection.createEl("div", { cls: "trend-group emerging" });
          emergingEl.createEl("span", { text: "🚀 Emerging: ", cls: "trend-label" });
          emergingEl.createEl("span", {
            text: this.insightsData.time_trends.emerging_topics.map(t => t.name).slice(0, 3).join(", "),
            cls: "trend-topics"
          });
        }

        // Growing Topics (성장 중)
        if (this.insightsData.time_trends.recent_topics.length > 0) {
          const growingEl = trendsSection.createEl("div", { cls: "trend-group growing" });
          growingEl.createEl("span", { text: "📈 Growing: ", cls: "trend-label" });
          growingEl.createEl("span", {
            text: this.insightsData.time_trends.recent_topics.map(t => t.name).slice(0, 3).join(", "),
            cls: "trend-topics"
          });
        }

        // Declining Topics (감소 중)
        if (this.insightsData.time_trends.declining_topics.length > 0) {
          const decliningEl = trendsSection.createEl("div", { cls: "trend-group declining" });
          decliningEl.createEl("span", { text: "📉 Declining: ", cls: "trend-label" });
          decliningEl.createEl("span", {
            text: this.insightsData.time_trends.declining_topics.map(t => t.name).slice(0, 3).join(", "),
            cls: "trend-topics"
          });
        }
      }

      // 2. 집중 영역 (Focus Areas) - 클릭하면 노트 열기
      const focusSection = contentEl.createEl("div", { cls: "didymos-insights-section" });
      focusSection.createEl("h4", { text: "Focus Areas" });
      focusSection.createEl("p", { text: "클릭하여 관련 노트 열기", cls: "section-desc" });

      if (this.insightsData.focus_areas.length > 0) {
        const focusList = focusSection.createEl("div", { cls: "didymos-insights-list" });
        for (const area of this.insightsData.focus_areas.slice(0, 8)) {
          const item = focusList.createEl("div", { cls: "didymos-insights-item focus clickable" });
          item.createEl("span", { text: area.name, cls: "name" });
          item.createEl("span", { text: `${area.strength}`, cls: "badge" });
          item.createEl("span", { text: area.type, cls: `type-badge type-${area.type.toLowerCase()}` });

          // 클릭 시 첫 번째 노트 열기
          if (area.notes && area.notes.length > 0) {
            item.style.cursor = "pointer";
            item.addEventListener("click", () => {
              const notePath = area.notes[0];
              this.app.workspace.openLinkText(notePath, "");
            });
            item.title = `Click to open: ${area.notes[0]}`;
          }
        }
      } else {
        focusSection.createEl("p", { text: "No focus areas found", cls: "empty" });
      }

      // 3. 브릿지 개념 (Bridge Concepts)
      const bridgeSection = contentEl.createEl("div", { cls: "didymos-insights-section" });
      bridgeSection.createEl("h4", { text: "Bridge Concepts" });
      bridgeSection.createEl("p", { text: "여러 영역을 연결하는 핵심 개념", cls: "section-desc" });

      if (this.insightsData.bridge_concepts.length > 0) {
        const bridgeList = bridgeSection.createEl("div", { cls: "didymos-insights-list" });
        for (const bridge of this.insightsData.bridge_concepts.slice(0, 6)) {
          const item = bridgeList.createEl("div", { cls: "didymos-insights-item bridge" });
          item.createEl("span", { text: bridge.name, cls: "name" });
          item.createEl("span", { text: `${bridge.connected_count} connections`, cls: "badge" });
          if (bridge.connects.length > 0) {
            item.createEl("span", { text: bridge.connects.slice(0, 3).join(", "), cls: "connects" });
          }
        }
      } else {
        bridgeSection.createEl("p", { text: "No bridge concepts found", cls: "empty" });
      }

      // 4. 고립된 영역 (Isolated Areas)
      const isolatedSection = contentEl.createEl("div", { cls: "didymos-insights-section" });
      isolatedSection.createEl("h4", { text: "Isolated Areas" });
      isolatedSection.createEl("p", { text: "연결이 적은 주제 - 확장 기회!", cls: "section-desc" });

      if (this.insightsData.isolated_areas.length > 0) {
        const isolatedList = isolatedSection.createEl("div", { cls: "didymos-insights-list" });
        for (const area of this.insightsData.isolated_areas.slice(0, 6)) {
          const item = isolatedList.createEl("div", { cls: "didymos-insights-item isolated" });
          item.createEl("span", { text: area.name, cls: "name" });
          item.createEl("span", { text: area.suggestion, cls: "suggestion" });
        }
      } else {
        isolatedSection.createEl("p", { text: "No isolated areas - great connectivity!", cls: "empty success" });
      }

      // 5. 탐구 제안 (Exploration Suggestions) - 액션 버튼 포함
      if (this.insightsData.exploration_suggestions.length > 0) {
        const exploreSection = contentEl.createEl("div", { cls: "didymos-insights-section" });
        exploreSection.createEl("h4", { text: "Exploration Suggestions" });
        exploreSection.createEl("p", { text: "연결 강화 가능성이 있는 영역", cls: "section-desc" });

        const exploreList = exploreSection.createEl("div", { cls: "didymos-insights-list" });
        for (const sugg of this.insightsData.exploration_suggestions) {
          const item = exploreList.createEl("div", { cls: "didymos-insights-item explore" });
          const textContent = item.createEl("div", { cls: "explore-content" });
          textContent.createEl("span", { text: `${sugg.area1} ↔ ${sugg.area2}`, cls: "name" });
          textContent.createEl("span", { text: sugg.reason, cls: "reason" });

          // 액션 버튼: 연결 노트 작성
          const actionBtn = item.createEl("button", {
            text: "📝 Connect",
            cls: "explore-action-btn"
          });
          actionBtn.title = "Create a note connecting these topics";
          actionBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            // 새 노트 생성하여 두 영역 연결
            const fileName = `${sugg.area1} + ${sugg.area2}.md`;
            const content = `# ${sugg.area1} and ${sugg.area2}\n\n## Connection Ideas\n\n- ${sugg.reason}\n- \n\n## ${sugg.area1}\n\n\n## ${sugg.area2}\n\n\n## Synthesis\n\n`;

            try {
              const file = await this.app.vault.create(fileName, content);
              await this.app.workspace.openLinkText(file.path, "");
            } catch (error) {
              console.error("Failed to create connection note:", error);
            }
          });
        }
      }

      // 6. Refresh 버튼
      const refreshSection = contentEl.createEl("div", { cls: "didymos-insights-refresh" });
      const refreshBtn = refreshSection.createEl("button", { text: "🔄 Refresh Insights", cls: "refresh-btn" });
      refreshBtn.addEventListener("click", async () => {
        refreshBtn.disabled = true;
        refreshBtn.setText("Loading...");
        await this.loadThinkingInsights(true);  // 강제 새로고침
      });

    } catch (error) {
      console.error("Failed to load thinking insights:", error);
      contentEl.empty();
      contentEl.createEl("p", {
        text: "Failed to load insights",
        cls: "didymos-insights-error"
      });
    }
  }

  // ============================================
  // Entity-Note Graph (노트 간 연결 시각화)
  // ============================================

  async renderEntityNoteGraph() {
    const graphContainer = this.containerEl.querySelector(
      "#didymos-graph-network"
    ) as HTMLElement;

    if (!graphContainer) return;

    graphContainer.empty();

    if (this.clusterStatusEl) {
      this.clusterStatusEl.setText("Entity-Note Graph (loading...)");
    }

    try {
      graphContainer.createEl("div", {
        text: "Loading entity-note connections...",
        cls: "didymos-graph-loading",
      });

      const folderPrefix = this.selectedFolders.length > 0 ? this.selectedFolders[0] + "/" : undefined;

      console.log("[2nd Brain] Fetching entity-note graph...");
      console.log("[2nd Brain] API Endpoint:", this.settings.apiEndpoint);
      console.log("[2nd Brain] Vault ID:", this.settings.vaultId);
      console.log("[2nd Brain] Folder prefix:", folderPrefix);

      const data: EntityNoteGraphData = await this.api.fetchEntityNoteGraph(
        this.settings.vaultId,
        {
          folderPrefix: folderPrefix,
          limit: 100,
          minNoteConnections: 2
        }
      );

      console.log("[2nd Brain] Response:", data);
      console.log("[2nd Brain] Entity count:", data.entity_count);

      if (this.clusterStatusEl) {
        const folderInfo = folderPrefix ? ` • Folder: ${this.selectedFolders[0]}` : "";
        this.clusterStatusEl.setText(
          `Entity-Note: ${data.entity_count} entities, ${data.note_count} notes, ${data.edge_count} connections${folderInfo}`
        );
      }

      if (data.entity_count === 0) {
        graphContainer.empty();
        graphContainer.createEl("div", {
          text: "No entity-note connections found. Sync some notes first.",
          cls: "didymos-graph-empty",
        });
        return;
      }

      // 노드 구성: Entity + Note
      const typeColors: Record<string, string> = {
        "Goal": "#9b59b6",
        "Project": "#2ecc71",
        "Task": "#e74c3c",
        "Topic": "#3498db",
        "Concept": "#1abc9c",
        "Question": "#f39c12",
        "Insight": "#e91e63",
        "Resource": "#607d8b",
        "Person": "#e67e22"
      };

      const entityNodes = data.entities.map(e => ({
        id: `entity_${e.id}`,
        label: e.name,
        shape: 'dot',
        size: 15 + Math.min(20, e.note_count * 3),
        color: {
          background: typeColors[e.type] || "#95a5a6",
          border: this.darkenColor(typeColors[e.type] || "#95a5a6", 0.3)
        },
        font: { size: 12, color: '#333' },
        title: `${e.name}\nType: ${e.type}\nNotes: ${e.note_count}`,
        group: 'entity',
        entity_data: e
      }));

      const noteNodes = data.notes.map(n => ({
        id: `note_${n.id}`,
        label: n.title.length > 20 ? n.title.substring(0, 20) + "..." : n.title,
        shape: 'box',
        size: 10,
        color: {
          background: '#f5f5f5',
          border: '#bdbdbd'
        },
        font: { size: 10, color: '#555' },
        title: n.title,
        group: 'note',
        note_data: n
      }));

      // 엣지: Note-Note 연결 (공유 Entity 기반)
      const edges = data.note_note_edges.map((edge, idx) => ({
        id: `edge_${idx}`,
        from: `note_${edge.from}`,
        to: `note_${edge.to}`,
        label: '',
        arrows: '' as any,
        width: Math.min(5, edge.strength),
        color: { color: '#aaa', highlight: '#666' },
        title: `Shared: ${edge.strength} entities`,
        smooth: { enabled: true, type: 'continuous', roundness: 0.3 } as any
      }));

      const graphData: GraphData = {
        nodes: [...entityNodes, ...noteNodes] as any,
        edges: edges
      };

      this.renderEntityNoteNetwork(graphContainer, graphData, data);

    } catch (error) {
      console.error("Failed to load entity-note graph:", error);
      graphContainer.empty();
      graphContainer.createEl("div", {
        text: `Failed to load: ${error}`,
        cls: "didymos-graph-error",
      });
    }
  }

  renderEntityNoteNetwork(container: HTMLElement, graphData: GraphData, rawData: EntityNoteGraphData) {
    container.empty();

    const networkContainer = container.createEl("div", {
      cls: "didymos-network-container",
    });
    networkContainer.style.height = "100%";
    networkContainer.style.width = "100%";

    const options = {
      nodes: {
        shape: 'dot',
        scaling: { min: 10, max: 35 },
        font: { size: 11, face: 'Tahoma' }
      },
      edges: {
        smooth: { enabled: true, type: 'continuous', roundness: 0.3 } as any
      },
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -40,
          centralGravity: 0.01,
          springLength: 80,
          springConstant: 0.1,
          damping: 0.4
        },
        stabilization: { enabled: true, iterations: 200, updateInterval: 25 }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: true,
        zoomView: true
      },
      groups: {
        entity: { shape: 'dot' },
        note: { shape: 'box', color: { background: '#f5f5f5', border: '#bdbdbd' } }
      }
    };

    if (this.network) {
      this.network.destroy();
    }

    this.network = new Network(
      networkContainer,
      { nodes: graphData.nodes, edges: graphData.edges },
      options
    );

    // 노트 더블클릭 시 열기
    this.network.on("doubleClick", async (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        if (nodeId.startsWith("note_")) {
          const noteId = nodeId.replace("note_", "");
          await this.app.workspace.openLinkText(noteId, "", false);
        }
      }
    });
  }
}
