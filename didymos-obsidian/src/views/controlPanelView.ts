import { ItemView, WorkspaceLeaf, Plugin, Notice } from "obsidian";
import { DidymosSettings } from "../settings";

export const CONTROL_PANEL_VIEW_TYPE = "didymos-control-panel";

export interface ControlPanelAction {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: "views" | "actions" | "templates" | "sync";
  viewType?: string; // For views that should be embedded
  callback: () => void | Promise<void>;
}

export class DidymosControlPanelView extends ItemView {
  private actions: ControlPanelAction[];
  private plugin: Plugin;
  private settings: DidymosSettings;
  private contentArea: HTMLElement | null = null;
  private activeViewType: string | null = null;
  private syncStatusEl: HTMLElement | null = null;

  constructor(leaf: WorkspaceLeaf, actions: ControlPanelAction[], plugin: Plugin, settings: DidymosSettings) {
    super(leaf);
    this.actions = actions;
    this.plugin = plugin;
    this.settings = settings;
  }

  getViewType(): string {
    return CONTROL_PANEL_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Control Panel";
  }

  getIcon(): string {
    return "layout-dashboard";
  }

  async onOpen() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("didymos-control-panel-view");

    // Header
    const header = container.createDiv("control-panel-header");
    header.createEl("h2", { text: "🎛️ Didymos Control Panel" });
    header.createEl("p", {
      text: "모든 Didymos 기능을 한 곳에서 관리하세요",
      cls: "control-panel-subtitle"
    });

    // Sync Status Area
    this.syncStatusEl = header.createDiv("control-panel-sync-status");
    this.updateSyncStatus();

    // Vault Sync Button
    const syncBtn = header.createEl("button", {
      text: "🔄 Sync Vault",
      cls: "control-panel-sync-btn"
    });
    syncBtn.addEventListener("click", async () => {
      await this.syncVault(syncBtn);
    });

    // Group actions by category
    const categories = {
      views: { title: "📊 Views & Panels", actions: [] as ControlPanelAction[] },
      sync: { title: "🔄 Sync", actions: [] as ControlPanelAction[] },
      actions: { title: "⚡ Actions", actions: [] as ControlPanelAction[] },
      templates: { title: "📝 Templates", actions: [] as ControlPanelAction[] },
    };

    this.actions.forEach((action) => {
      categories[action.category].actions.push(action);
    });

    // Actions menu (compact)
    const menuContainer = container.createDiv("control-panel-menu");

    Object.entries(categories).forEach(([key, category]) => {
      if (category.actions.length === 0) return;

      const section = menuContainer.createDiv("control-panel-section");
      section.createEl("h3", { text: category.title });

      const actionList = section.createDiv("control-panel-list");

      category.actions.forEach((action) => {
        this.renderActionItem(actionList, action);
      });
    });

    // Content area (where views will be embedded)
    this.contentArea = container.createDiv("control-panel-content");
    this.contentArea.createEl("div", {
      text: "👆 위에서 원하는 기능을 선택하세요",
      cls: "control-panel-placeholder"
    });
  }

  private renderActionItem(container: HTMLElement, action: ControlPanelAction) {
    const item = container.createDiv("control-panel-item");

    // Icon
    const iconEl = item.createDiv("control-panel-item-icon");
    iconEl.setText(action.icon);

    // Content
    const content = item.createDiv("control-panel-item-content");
    content.createEl("div", { text: action.name, cls: "control-panel-item-name" });

    // Click handler
    item.addEventListener("click", async () => {
      // Always execute callback
      await action.callback();

      // If it's a view, show a confirmation message in content area
      if (action.viewType && this.contentArea) {
        this.contentArea.empty();
        this.contentArea.createEl("div", {
          text: `✓ "${action.name}" 패널이 열렸습니다`,
          cls: "control-panel-success-message"
        });

        setTimeout(() => {
          if (this.contentArea) {
            this.contentArea.empty();
            this.contentArea.createEl("div", {
              text: "👆 위에서 원하는 기능을 선택하세요",
              cls: "control-panel-placeholder"
            });
          }
        }, 2000);
      }
    });

    // Hover effect
    item.addClass("clickable");
  }

  private async syncVault(button: HTMLElement) {
    const originalText = button.textContent || "";

    try {
      button.textContent = "⏳ Syncing...";
      button.setAttribute("disabled", "true");

      // Get all markdown files
      const allMarkdownFiles = this.app.vault.getMarkdownFiles();

      // Incremental sync: filter files modified since last sync
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

      // Batch processing (10 files at a time)
      const batchSize = 10;
      for (let i = 0; i < markdownFiles.length; i += batchSize) {
        const batch = markdownFiles.slice(i, i + batchSize);

        await Promise.all(
          batch.map(async (file) => {
            try {
              // Call the plugin's syncNote method
              await (this.plugin as any).syncNote(file);
              succeeded++;
            } catch (error) {
              failed++;
              console.error(`Failed to sync ${file.path}:`, error);
            } finally {
              processed++;
              // Update UI every 10 files
              if (processed % 10 === 0) {
                button.textContent = `⏳ Syncing... ${processed}/${totalFiles}`;
              }
            }
          })
        );
      }

      // Update last sync time
      this.settings.lastBulkSyncTime = Date.now();
      await (this.plugin as any).saveSettings();

      // Show completion status
      const statusMsg = skippedFiles > 0
        ? `✅ Synced ${succeeded}/${totalFiles} (${skippedFiles} skipped)`
        : `✅ Synced ${succeeded}/${totalFiles}`;
      button.textContent = statusMsg;

      this.updateSyncStatus();

      setTimeout(() => {
        button.textContent = originalText;
        button.removeAttribute("disabled");
      }, 3000);

      new Notice(`Vault sync complete: ${succeeded} files synced`);
    } catch (error) {
      button.textContent = "❌ Sync failed";
      new Notice(`Vault sync failed: ${error}`);
      setTimeout(() => {
        button.textContent = originalText;
        button.removeAttribute("disabled");
      }, 3000);
    }
  }

  private updateSyncStatus() {
    if (!this.syncStatusEl) return;

    const lastSync = this.settings.lastBulkSyncTime;
    if (lastSync) {
      const date = new Date(lastSync);
      const formattedDate = date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
      this.syncStatusEl.setText(`마지막 동기화: ${formattedDate}`);
    } else {
      this.syncStatusEl.setText("동기화된 적 없음");
    }
  }

  async onClose() {
    // Cleanup if needed
  }

  updateActions(actions: ControlPanelAction[]) {
    this.actions = actions;
    this.onOpen(); // Re-render
  }
}
