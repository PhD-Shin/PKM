import { ItemView, WorkspaceLeaf } from "obsidian";
import { DidymosSettings } from "../settings";
import { DidymosAPI, WeeklyReviewResponse, WeeklyReviewRecord } from "../api/client";

export const DIDYMOS_REVIEW_VIEW_TYPE = "didymos-review-view";

export class DidymosReviewView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;
  history: WeeklyReviewRecord[] = [];

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return DIDYMOS_REVIEW_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Weekly Review";
  }

  getIcon(): string {
    return "calendar-clock";
  }

  async onOpen() {
    await this.renderReview();
  }

  async renderReview() {
    const container = this.containerEl.children[1] as HTMLElement;
    if (!container) return;

    container.empty();
    container.addClass("didymos-review-container");

    container.createEl("h2", { text: "📅 Weekly Review" });
    const actions = container.createEl("div", { cls: "didymos-review-actions" });
    const saveBtn = actions.createEl("button", { text: "💾 Save review" });
    const refreshBtn = actions.createEl("button", { text: "🔄 Refresh" });

    const body = container.createEl("div", { cls: "didymos-review-body" });
    const historyBox = container.createEl("div", { cls: "didymos-review-history" });

    try {
      const data: WeeklyReviewResponse = await this.api.fetchWeeklyReview(
        this.settings.vaultId
      );
      await this.loadHistory(historyBox);

      this.renderList(
        body,
        "🆕 New Topics",
        data.new_topics.map((t) => `${t.name} (${t.mention_count})`)
      );
      this.renderList(
        body,
        "🧭 Forgotten Projects",
        data.forgotten_projects.map(
          (p) => `${p.name} - ${p.status} (${p.days_inactive}d)`
        )
      );
      this.renderList(
        body,
        "⏳ Overdue Tasks",
        data.overdue_tasks.map((t) => `${t.title} [${t.priority}] - ${t.note_title}`)
      );
      this.renderList(
        body,
        "🔥 Most Active Notes",
        data.most_active_notes.map(
          (n) => `${n.title} (${n.update_count})`
        )
      );

      saveBtn.addEventListener("click", async () => {
        try {
          await this.api.saveWeeklyReview(this.settings.vaultId);
          await this.loadHistory(historyBox);
        } catch (err: any) {
          console.error(err);
        }
      });

      refreshBtn.addEventListener("click", async () => {
        await this.renderReview();
      });
    } catch (error: any) {
      body.createEl("div", {
        text: `❌ Failed to load weekly review: ${error.message}`,
        cls: "didymos-review-error",
      });
    }
  }

  renderList(container: HTMLElement, title: string, items: string[]) {
    const section = container.createEl("div", { cls: "didymos-review-section" });
    section.createEl("h3", { text: title });

    if (items.length === 0) {
      section.createEl("div", { text: "No data", cls: "didymos-review-empty" });
      return;
    }

    const ul = section.createEl("ul");
    items.forEach((item) => {
      const li = ul.createEl("li");
      li.createSpan({ text: item });
    });
  }

  private async loadHistory(container: HTMLElement) {
    container.empty();
    container.createEl("h3", { text: "📜 Saved Reviews" });
    try {
      this.history = await this.api.fetchReviewHistory(this.settings.vaultId, 5);
      if (this.history.length === 0) {
        container.createEl("div", { text: "No saved reviews.", cls: "didymos-review-empty" });
        return;
      }
      const list = container.createEl("ul");
      this.history.forEach((r) => {
        const li = list.createEl("li");
        li.createSpan({ text: `${r.created_at} (${r.id})` });
      });
    } catch (err: any) {
      container.createEl("div", {
        text: `❌ Failed to load history: ${err.message}`,
        cls: "didymos-review-error",
      });
    }
  }
}
