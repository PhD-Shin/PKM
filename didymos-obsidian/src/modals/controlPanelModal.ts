import { App, Modal } from "obsidian";

export interface ControlPanelAction {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: "views" | "actions" | "templates" | "sync";
  callback: () => void | Promise<void>;
}

export class ControlPanelModal extends Modal {
  private actions: ControlPanelAction[];

  constructor(app: App, actions: ControlPanelAction[]) {
    super(app);
    this.actions = actions;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("didymos-control-panel");

    // Header
    const header = contentEl.createDiv("control-panel-header");
    header.createEl("h1", { text: "🎛️ Didymos Control Panel" });
    header.createEl("p", {
      text: "모든 Didymos 기능을 한 곳에서 관리하세요",
    });

    // Group actions by category
    const categories = {
      views: { title: "📊 Views & Panels", actions: [] as ControlPanelAction[] },
      actions: { title: "⚡ Actions", actions: [] as ControlPanelAction[] },
      templates: { title: "📝 Templates", actions: [] as ControlPanelAction[] },
      sync: { title: "🔄 Sync", actions: [] as ControlPanelAction[] },
    };

    this.actions.forEach((action) => {
      categories[action.category].actions.push(action);
    });

    // Render categories
    Object.entries(categories).forEach(([key, category]) => {
      if (category.actions.length === 0) return;

      const section = contentEl.createDiv("control-panel-section");
      section.createEl("h2", { text: category.title });

      const grid = section.createDiv("control-panel-grid");

      category.actions.forEach((action) => {
        this.renderActionCard(grid, action);
      });
    });

    // Footer
    const footer = contentEl.createDiv("control-panel-footer");
    const closeBtn = footer.createEl("button", { text: "닫기" });
    closeBtn.addEventListener("click", () => {
      this.close();
    });
  }

  private renderActionCard(container: HTMLElement, action: ControlPanelAction) {
    const card = container.createDiv("control-panel-card");

    // Icon
    card.createEl("div", { text: action.icon, cls: "control-panel-card-icon" });

    // Content
    const content = card.createDiv("control-panel-card-content");
    content.createEl("h3", { text: action.name });
    content.createEl("p", { text: action.description });

    // Click handler
    card.addEventListener("click", async () => {
      this.close();
      await action.callback();
    });

    // Hover effect
    card.addClass("clickable");
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
