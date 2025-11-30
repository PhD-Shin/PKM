import { ItemView, WorkspaceLeaf, Notice } from "obsidian";
import { DidymosSettings } from "../settings";
import { DidymosAPI, TaskData } from "../api/client";

export const DIDYMOS_TASK_VIEW_TYPE = "didymos-task-view";

export class DidymosTaskView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;
  tasks: TaskData[] = [];
  currentFilter: { status?: string; priority?: string } = {};

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return DIDYMOS_TASK_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Tasks";
  }

  getIcon(): string {
    return "check-square";
  }

  async onOpen() {
    await this.renderTasks();
  }

  async renderTasks() {
    const container = this.containerEl.children[1] as HTMLElement;
    if (!container) return;

    container.empty();
    container.addClass("didymos-task-container");

    const header = container.createEl("div", { cls: "didymos-task-header" });
    header.createEl("h2", { text: "✅ Tasks" });

    const controls = container.createEl("div", { cls: "didymos-task-controls" });

    const statusSelect = controls.createEl("select");
    ["All", "Todo", "In Progress", "Done"].forEach((label) => {
      statusSelect.createEl("option", {
        text: label,
        value: label === "All" ? "" : label.toLowerCase().replace(" ", "_"),
      });
    });

    const prioritySelect = controls.createEl("select");
    ["All", "High", "Medium", "Low"].forEach((label) => {
      prioritySelect.createEl("option", {
        text: label,
        value: label === "All" ? "" : label.toLowerCase(),
      });
    });

    const refreshBtn = controls.createEl("button", { text: "🔄 Refresh" });

    statusSelect.addEventListener("change", async () => {
      this.currentFilter.status = statusSelect.value || undefined;
      await this.loadTasks();
    });

    prioritySelect.addEventListener("change", async () => {
      this.currentFilter.priority = prioritySelect.value || undefined;
      await this.loadTasks();
    });

    refreshBtn.addEventListener("click", async () => {
      await this.loadTasks();
    });

    const listContainer = container.createEl("div", { cls: "didymos-task-list" });
    await this.loadTasks(listContainer);
  }

  async loadTasks(listContainer?: HTMLElement) {
    if (!listContainer) {
      listContainer = this.containerEl.querySelector(
        ".didymos-task-list"
      ) as HTMLElement;
    }
    if (!listContainer) return;

    listContainer.empty();

    try {
      listContainer.createEl("div", {
        text: "Loading tasks...",
        cls: "didymos-task-loading",
      });

      this.tasks = await this.api.listTasks(
        this.settings.vaultId,
        this.currentFilter.status,
        this.currentFilter.priority
      );

      listContainer.empty();

      if (this.tasks.length === 0) {
        listContainer.createEl("div", {
          text: "No tasks found.",
          cls: "didymos-task-empty",
        });
        return;
      }

      const grouped: Record<string, TaskData[]> = {};
      this.tasks.forEach((task) => {
        const key = task.status || "todo";
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(task);
      });

      ["todo", "in_progress", "done"].forEach((status) => {
        if (!grouped[status] || grouped[status].length === 0) return;

        const groupDiv = listContainer!.createEl("div", {
          cls: "didymos-task-group",
        });

        const statusLabel =
          {
            todo: "📋 To Do",
            in_progress: "⏳ In Progress",
            done: "✅ Done",
          }[status] || status;

        groupDiv.createEl("h3", {
          text: `${statusLabel} (${grouped[status].length})`,
        });

        const ul = groupDiv.createEl("ul");

        grouped[status].forEach((task) => {
          const li = ul.createEl("li", { cls: "didymos-task-item" });

          const checkbox = li.createEl("input", {
            type: "checkbox",
            cls: "didymos-task-checkbox",
          });
          checkbox.checked = task.status === "done";
          checkbox.addEventListener("change", async () => {
            await this.handleTaskStatusChange(task.id, checkbox.checked);
          });

          li.createEl("span", { text: task.title, cls: "didymos-task-title" });

          const priorityClass =
            task.priority === "high"
              ? "priority-high"
              : task.priority === "medium"
              ? "priority-medium"
              : "priority-low";

          li.createEl("span", {
            text: `[${task.priority[0].toUpperCase()}]`,
            cls: `didymos-task-priority ${priorityClass}`,
          });

          const noteLink = li.createEl("a", {
            text: `📄 ${task.note_title}`,
            cls: "didymos-task-note-link",
          });
          noteLink.addEventListener("click", (e) => {
            e.preventDefault();
            this.app.workspace.openLinkText(task.note_id, "", false);
          });
        });
      });
    } catch (error: any) {
      listContainer.empty();
      listContainer.createEl("div", {
        text: `❌ Failed to load tasks: ${error.message}`,
        cls: "didymos-task-error",
      });
    }
  }

  async handleTaskStatusChange(taskId: string, checked: boolean) {
    try {
      const newStatus = checked ? "done" : "todo";
      await this.api.updateTask(taskId, { status: newStatus });
      new Notice("✅ Task updated");
      await this.loadTasks();
    } catch (error) {
      console.error(error);
      new Notice("❌ Failed to update task");
    }
  }
}
