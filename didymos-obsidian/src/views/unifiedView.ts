import { ItemView, WorkspaceLeaf } from "obsidian";
import { DidymosSettings } from "../settings";
import { DidymosContextView } from "./contextView";
import { DidymosGraphView } from "./graphView";
import { DidymosTaskView } from "./taskView";
import { DidymosReviewView } from "./reviewView";
import { DidymosInsightsView } from "./insightsView";

export const UNIFIED_VIEW_TYPE = "didymos-unified-view";

type TabType = "context" | "graph" | "tasks" | "review" | "insights";

export class DidymosUnifiedView extends ItemView {
  settings: DidymosSettings;
  currentTab: TabType = "context";

  // 각 뷰의 인스턴스를 저장
  contextView: DidymosContextView | null = null;
  graphView: DidymosGraphView | null = null;
  taskView: DidymosTaskView | null = null;
  reviewView: DidymosReviewView | null = null;
  insightsView: DidymosInsightsView | null = null;

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
  }

  getViewType(): string {
    return UNIFIED_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos";
  }

  getIcon(): string {
    return "layout-dashboard";
  }

  async onOpen() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("didymos-unified-container");

    // Header with Tabs
    const header = container.createEl("div", { cls: "didymos-unified-header" });
    header.createEl("h2", { text: "🧠 Didymos PKM" });

    // Tab Navigation
    const tabNav = container.createEl("div", { cls: "didymos-tab-nav" });

    const tabs: Array<{ id: TabType; icon: string; label: string }> = [
      { id: "context", icon: "🔍", label: "Context" },
      { id: "graph", icon: "🕸️", label: "Graph" },
      { id: "tasks", icon: "✓", label: "Tasks" },
      { id: "review", icon: "📝", label: "Review" },
      { id: "insights", icon: "💡", label: "Insights" }
    ];

    tabs.forEach((tab) => {
      const tabBtn = tabNav.createEl("button", {
        cls: `didymos-tab-btn ${this.currentTab === tab.id ? "active" : ""}`,
      });

      tabBtn.createEl("span", { text: tab.icon, cls: "tab-icon" });
      tabBtn.createEl("span", { text: tab.label, cls: "tab-label" });

      tabBtn.addEventListener("click", () => {
        this.switchTab(tab.id);
      });
    });

    // Content Container
    const contentContainer = container.createEl("div", {
      cls: "didymos-unified-content"
    });

    // Render initial tab
    this.renderTabContent(contentContainer);
  }

  switchTab(tabId: TabType) {
    this.currentTab = tabId;

    // Update tab buttons
    const tabButtons = this.containerEl.querySelectorAll(".didymos-tab-btn");
    tabButtons.forEach((btn, index) => {
      if (index === ["context", "graph", "tasks", "review", "insights"].indexOf(tabId)) {
        btn.addClass("active");
      } else {
        btn.removeClass("active");
      }
    });

    // Re-render content
    const contentContainer = this.containerEl.querySelector(
      ".didymos-unified-content"
    ) as HTMLElement;

    if (contentContainer) {
      this.renderTabContent(contentContainer);
    }
  }

  async renderTabContent(container: HTMLElement) {
    container.empty();

    switch (this.currentTab) {
      case "context":
        await this.renderContextTab(container);
        break;
      case "graph":
        await this.renderGraphTab(container);
        break;
      case "tasks":
        await this.renderTasksTab(container);
        break;
      case "review":
        await this.renderReviewTab(container);
        break;
      case "insights":
        await this.renderInsightsTab(container);
        break;
    }
  }

  async renderContextTab(container: HTMLElement) {
    // Context View 임베드
    const contextContainer = container.createEl("div", { cls: "didymos-embedded-view" });

    // ContextView의 내용을 직접 렌더링
    // 간단히 구현: API 호출하여 컨텍스트 표시
    const activeFile = this.app.workspace.getActiveFile();

    if (!activeFile) {
      contextContainer.createEl("p", {
        text: "No active note. Open a note to see its context.",
        cls: "didymos-empty-state"
      });
      return;
    }

    contextContainer.createEl("div", {
      text: "Loading context...",
      cls: "didymos-loading"
    });

    try {
      const response = await fetch(
        `${this.settings.apiEndpoint}/context/retrieve/${this.settings.userToken}/${this.settings.vaultId}/${encodeURIComponent(activeFile.path)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch context: ${response.status}`);
      }

      const data = await response.json();

      contextContainer.empty();

      // Display context
      if (data.context && data.context.length > 0) {
        const contextList = contextContainer.createEl("div", { cls: "didymos-context-list" });

        data.context.forEach((item: any) => {
          const contextItem = contextList.createEl("div", { cls: "didymos-context-item" });

          contextItem.createEl("div", {
            text: item.note_id || item.path,
            cls: "didymos-context-title"
          });

          if (item.content) {
            contextItem.createEl("div", {
              text: item.content.substring(0, 200) + "...",
              cls: "didymos-context-preview"
            });
          }
        });
      } else {
        contextContainer.createEl("p", {
          text: "No context available for this note.",
          cls: "didymos-empty-state"
        });
      }
    } catch (error: any) {
      contextContainer.empty();
      contextContainer.createEl("p", {
        text: `Error loading context: ${error.message}`,
        cls: "didymos-error"
      });
    }
  }

  async renderGraphTab(container: HTMLElement) {
    // Graph View 임베드
    const graphContainer = container.createEl("div", { cls: "didymos-embedded-view" });
    graphContainer.createEl("p", {
      text: "Graph visualization will be embedded here. For now, please use the separate Graph Panel.",
      cls: "didymos-info"
    });

    // TODO: GraphView의 렌더링 로직을 재사용하도록 리팩토링
  }

  async renderTasksTab(container: HTMLElement) {
    // Task View 임베드
    const taskContainer = container.createEl("div", { cls: "didymos-embedded-view" });

    taskContainer.createEl("div", {
      text: "Loading tasks...",
      cls: "didymos-loading"
    });

    try {
      const response = await fetch(
        `${this.settings.apiEndpoint}/tasks/list/${this.settings.userToken}/${this.settings.vaultId}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch tasks: ${response.status}`);
      }

      const data = await response.json();

      taskContainer.empty();

      // Display tasks
      if (data.tasks && data.tasks.length > 0) {
        const taskList = taskContainer.createEl("div", { cls: "didymos-task-list" });

        data.tasks.forEach((task: any) => {
          const taskItem = taskList.createEl("div", { cls: "didymos-task-item" });

          const checkbox = taskItem.createEl("input", { type: "checkbox" });
          checkbox.checked = task.status === "done";

          taskItem.createEl("span", {
            text: task.title || "Untitled task",
            cls: "didymos-task-title"
          });

          if (task.due_date) {
            taskItem.createEl("span", {
              text: ` (Due: ${task.due_date})`,
              cls: "didymos-task-due"
            });
          }
        });
      } else {
        taskContainer.createEl("p", {
          text: "No tasks found.",
          cls: "didymos-empty-state"
        });
      }
    } catch (error: any) {
      taskContainer.empty();
      taskContainer.createEl("p", {
        text: `Error loading tasks: ${error.message}`,
        cls: "didymos-error"
      });
    }
  }

  async renderReviewTab(container: HTMLElement) {
    // Review View 임베드
    const reviewContainer = container.createEl("div", { cls: "didymos-embedded-view" });
    reviewContainer.createEl("p", {
      text: "Review features will be embedded here. For now, please use the separate Review Panel.",
      cls: "didymos-info"
    });
  }

  async renderInsightsTab(container: HTMLElement) {
    // Insights View 임베드
    const insightsContainer = container.createEl("div", { cls: "didymos-embedded-view" });
    insightsContainer.createEl("p", {
      text: "Knowledge Insights will be embedded here. For now, please use the separate Insights Panel.",
      cls: "didymos-info"
    });
  }

  async onClose() {
    // Cleanup
  }
}
