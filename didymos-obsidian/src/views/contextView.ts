import { ItemView, WorkspaceLeaf } from "obsidian";
import { DidymosSettings } from "../settings";
import { DidymosAPI, ContextData } from "../api/client";

export const DIDYMOS_CONTEXT_VIEW_TYPE = "didymos-context-view";

export class DidymosContextView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return DIDYMOS_CONTEXT_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Context";
  }

  getIcon(): string {
    return "mountain";
  }

  async onOpen() {
    const container = this.containerEl.children[1] as HTMLElement;
    if (!container) return;
    container.empty();
    container.addClass("didymos-context-container");

    container.createEl("h2", { text: "🧭 Didymos Context" });
    container.createEl("p", {
      text: "노트를 저장하면 관련 컨텍스트가 표시됩니다.",
      cls: "didymos-empty-message",
    });
  }

  async updateContext(noteId: string) {
    const container = this.containerEl.children[1] as HTMLElement;
    if (!container) return;
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

  renderTopics(container: HTMLElement, topics: ContextData["topics"]) {
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

  renderProjects(container: HTMLElement, projects: ContextData["projects"]) {
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

  renderTasks(container: HTMLElement, tasks: ContextData["tasks"]) {
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

  renderRelatedNotes(container: HTMLElement, notes: ContextData["related_notes"]) {
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
