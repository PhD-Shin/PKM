import { ItemView, WorkspaceLeaf } from "obsidian";
import { Network } from "vis-network";
import { DidymosSettings } from "../settings";
import { DidymosAPI, GraphData } from "../api/client";

export const DIDYMOS_GRAPH_VIEW_TYPE = "didymos-graph-view";

export class DidymosGraphView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;
  network: Network | null = null;
  currentNoteId: string | null = null;
  currentHops: number = 1;
  showTopics = true;
  showProjects = true;
  showTasks = true;
  showRelated = true;
  layoutPreset: "force" | "hierarchical" = "force";
  themePreset: "default" | "midnight" | "contrast" = "default";
  fontPreset: "normal" | "compact" | "large" = "normal";
  layoutSpacing: "regular" | "compact" = "regular";

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
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
      graphContainer.createEl("div", {
        text: "Loading graph...",
        cls: "didymos-graph-loading",
      });

      const graphData: GraphData = await this.api.fetchGraph(
        noteId,
        this.currentHops
      );

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
