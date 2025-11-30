import { ItemView, WorkspaceLeaf, Notice } from "obsidian";
import { DidymosSettings } from "../settings";
import { DidymosAPI } from "../api/client";

export const DIDYMOS_DECISION_VIEW_TYPE = "didymos-decision-view";

export class DidymosDecisionView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;
  currentNoteId: string | null = null;

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return DIDYMOS_DECISION_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Decisions";
  }

  getIcon(): string {
    return "list-checks";
  }

  async onOpen() {
    const container = this.containerEl.children[1] as HTMLElement;
    if (!container) return;
    container.empty();
    container.addClass("didymos-decision-container");

    const header = container.createEl("div", { cls: "didymos-decision-header" });
    header.createEl("h2", { text: "🧠 Decision Dashboard" });

    const controls = container.createEl("div", { cls: "didymos-decision-controls" });
    const refreshBtn = controls.createEl("button", { text: "🔄 Refresh" });
    const generateBtn = controls.createEl("button", { text: "💾 Save Decision Note" });
    const chatInput = controls.createEl("input", { type: "text", placeholder: "Ask AI (e.g., What should I do next?)", cls: "didymos-chat-input" });
    const chatBtn = controls.createEl("button", { text: "🤖 Ask AI" });

    const body = container.createEl("div", { cls: "didymos-decision-body" });
    const chatBox = container.createEl("div", { cls: "didymos-chat-box" });
    chatBox.createEl("h3", { text: "Suggested questions" });
    const ul = chatBox.createEl("ul");
    ["What are the top 3 next actions?", "Which project needs attention first?", "Summarize blockers and overdue tasks."].forEach((q) => {
      const li = ul.createEl("li");
      const a = li.createEl("a", { text: q, cls: "didymos-chat-suggest" });
      a.addEventListener("click", () => {
        chatInput.value = q;
      });
    });
    const chatResponse = chatBox.createEl("div", { cls: "didymos-chat-response" });

    const loadData = async () => {
      body.empty();
      const active = this.app.workspace.getActiveFile();
      if (!active) {
        body.createEl("div", { text: "No active note", cls: "didymos-decision-empty" });
        return;
      }
      this.currentNoteId = active.path;

      try {
        const [context, review] = await Promise.all([
          this.api.fetchContext(active.path),
          this.api.fetchWeeklyReview(this.settings.vaultId),
        ]);

        this.renderSection(body, "Key Topics", (context.topics || []).slice(0, 5).map((t) => `${t.name} (${Math.round(t.importance_score * 100)}%)`));
        this.renderSection(body, "Projects", (context.projects || []).slice(0, 5).map((p) => `${p.name} [${p.status}]`));
        this.renderSection(body, "Open Tasks", (context.tasks || []).slice(0, 10).map((t) => `${t.title} [${t.status}/${t.priority}]`));
        this.renderSection(body, "Related Notes", (context.related_notes || []).slice(0, 5).map((r) => `${r.title} (${Math.round(r.similarity * 100)}%)`));

        this.renderSection(body, "Weekly - New Topics", (review.new_topics || []).slice(0, 5).map((t) => `${t.name} (${t.mention_count})`));
        this.renderSection(body, "Weekly - Forgotten Projects", (review.forgotten_projects || []).slice(0, 5).map((p) => `${p.name} (${p.days_inactive}d)`));
        this.renderSection(body, "Weekly - Overdue Tasks", (review.overdue_tasks || []).slice(0, 5).map((t) => `${t.title} [${t.priority}]`));
      } catch (error: any) {
        body.createEl("div", { text: `❌ Failed to load: ${error.message}`, cls: "didymos-decision-error" });
      }
    };

    refreshBtn.addEventListener("click", loadData);
    generateBtn.addEventListener("click", async () => {
      const file = this.app.workspace.getActiveFile();
      if (!file) {
        new Notice("No active note");
        return;
      }
      await (this.app as any).plugins.plugins["didymos-pkm"]?.generateDecisionNote?.(file);
    });

    chatBtn.addEventListener("click", async () => {
      const question = chatInput.value.trim();
      if (!question) {
        new Notice("Enter a question");
        return;
      }
      try {
        chatResponse.textContent = "Thinking...";
        const active = this.app.workspace.getActiveFile();
        if (!active) {
          chatResponse.textContent = "No active note";
          return;
        }
        // 간단히 컨텍스트/리뷰를 묶어 백엔드로 질문을 던진다 (프라이버시 모드에 따름)
        const [context, review] = await Promise.all([
          this.api.fetchContext(active.path),
          this.api.fetchWeeklyReview(this.settings.vaultId),
        ]);
        const payload = {
          question,
          context,
          review,
        };
        // 백엔드에 별도 엔드포인트가 없으므로 임시로 OpenAI 직접 호출 (로컬 키 필요)
        if (!this.settings.localOpenAIApiKey) {
          chatResponse.textContent = "Set Local OpenAI API Key in settings.";
          return;
        }
        const resp = await fetch("https://api.openai.com/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.settings.localOpenAIApiKey}`,
          },
          body: JSON.stringify({
            model: "gpt-4o-mini",
            messages: [
              { role: "system", content: "You are a concise decision assistant. Use the provided context and review signals to suggest next actions." },
              { role: "user", content: `Context: ${JSON.stringify(payload.context)}\nReview: ${JSON.stringify(payload.review)}\nQuestion: ${question}` },
            ],
            temperature: 0.3,
            max_tokens: 300,
          }),
        });
        if (!resp.ok) {
          chatResponse.textContent = `Error: ${resp.status}`;
          return;
        }
        const data = await resp.json();
        chatResponse.textContent = data?.choices?.[0]?.message?.content || "(no answer)";
      } catch (error: any) {
        console.error(error);
        chatResponse.textContent = `Error: ${error.message}`;
      }
    });

    await loadData();
  }

  private renderSection(container: HTMLElement, title: string, items: string[]) {
    const section = container.createEl("div", { cls: "didymos-decision-section" });
    section.createEl("h3", { text: title });
    if (!items.length) {
      section.createEl("div", { text: "(none)", cls: "didymos-decision-empty" });
      return;
    }
    const ul = section.createEl("ul");
    items.forEach((item) => {
      const li = ul.createEl("li");
      li.createSpan({ text: item });
    });
  }
}
