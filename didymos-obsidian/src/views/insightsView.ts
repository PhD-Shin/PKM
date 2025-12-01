import { ItemView, WorkspaceLeaf } from "obsidian";
import { DidymosSettings } from "../settings";

export const INSIGHTS_VIEW_TYPE = "didymos-insights-view";

interface PatternData {
  important_notes: Array<{ note_id: string; score: number }>;
  communities: Array<{ id: number; notes: string[]; size: number }>;
  orphan_notes: string[];
  stats: {
    total_notes: number;
    total_connections: number;
    num_communities: number;
    num_orphans: number;
    avg_connections_per_note: number;
  };
}

interface RecommendationData {
  priority_tasks: Array<{
    task_id: string;
    title: string;
    status: string;
    priority: string;
    due_date?: string;
    note_id: string;
    note_title: string;
    score: number;
    urgency: string;
    connections: number;
  }>;
  missing_connections: Array<{
    note1_id: string;
    note1_title: string;
    note2_id: string;
    note2_title: string;
    shared_topics: string[];
    topic_count: number;
    reason: string;
  }>;
}

interface WeaknessData {
  weaknesses: {
    isolated_topics: WeaknessCategory;
    stale_projects: WeaknessCategory;
    chronic_overdue_tasks: WeaknessCategory;
    weak_clusters: WeaknessCategory;
    knowledge_gaps: WeaknessCategory;
  };
  total_weakness_score: number;
  critical_weakness: {
    category: string;
    severity_score: number;
    count: number;
    top_items: any[];
  };
  strengthening_plan: Array<{
    priority: number;
    action: string;
    reason: string;
    steps: string[];
  }>;
}

interface WeaknessCategory {
  count: number;
  severity_score: number;
  items: any[];
}

export class DidymosInsightsView extends ItemView {
  settings: DidymosSettings;
  patternData: PatternData | null = null;
  recommendationData: RecommendationData | null = null;
  weaknessData: WeaknessData | null = null;

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
  }

  getViewType(): string {
    return INSIGHTS_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Knowledge Insights";
  }

  getIcon(): string {
    return "lightbulb";
  }

  async onOpen() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("didymos-insights-container");

    // Header
    const header = container.createEl("div", { cls: "didymos-insights-header" });
    header.createEl("h2", { text: "💡 Knowledge Insights" });

    // Buttons
    const buttonsDiv = container.createEl("div", { cls: "didymos-insights-buttons" });

    const analyzeBtn = buttonsDiv.createEl("button", {
      text: "🔍 Analyze Patterns",
      cls: "didymos-analyze-btn"
    });

    analyzeBtn.addEventListener("click", async () => {
      await this.analyzePatterns(analyzeBtn);
    });

    const recommendBtn = buttonsDiv.createEl("button", {
      text: "💡 Get Recommendations",
      cls: "didymos-analyze-btn"
    });

    recommendBtn.addEventListener("click", async () => {
      await this.getRecommendations(recommendBtn);
    });

    const weaknessBtn = buttonsDiv.createEl("button", {
      text: "⚠️ Analyze Weaknesses",
      cls: "didymos-analyze-btn"
    });

    weaknessBtn.addEventListener("click", async () => {
      await this.analyzeWeaknesses(weaknessBtn);
    });

    // Results Container
    const resultsContainer = container.createEl("div", {
      cls: "didymos-insights-results"
    });

    resultsContainer.createEl("p", {
      text: "Click 'Analyze Patterns' to discover insights about your knowledge graph.",
      cls: "didymos-insights-empty"
    });
  }

  async analyzePatterns(button: HTMLElement) {
    const originalText = button.textContent || "";
    const container = this.containerEl.querySelector(".didymos-insights-results");

    if (!container) return;

    try {
      button.textContent = "⏳ Analyzing...";
      button.setAttribute("disabled", "true");

      // API 호출
      const response = await fetch(
        `${this.settings.apiEndpoint}/patterns/analyze/${this.settings.userToken}/${this.settings.vaultId}`
      );

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      this.patternData = data.patterns;

      // 결과 렌더링
      this.renderResults(container as HTMLElement);

      button.textContent = "✅ Analysis Complete";
      setTimeout(() => {
        button.textContent = originalText;
        button.removeAttribute("disabled");
      }, 2000);

    } catch (error: any) {
      container.empty();
      container.createEl("div", {
        text: `❌ Analysis failed: ${error.message}`,
        cls: "didymos-insights-error"
      });

      button.textContent = originalText;
      button.removeAttribute("disabled");
    }
  }

  renderResults(container: HTMLElement) {
    if (!this.patternData) return;

    container.empty();

    const { important_notes, communities, orphan_notes, stats } = this.patternData;

    // Stats Overview
    const statsSection = container.createEl("div", { cls: "didymos-insights-section" });
    statsSection.createEl("h3", { text: "📊 Overview" });

    const statsList = statsSection.createEl("ul", { cls: "didymos-stats-list" });
    statsList.createEl("li").innerHTML = `<strong>Total Notes:</strong> ${stats.total_notes}`;
    statsList.createEl("li").innerHTML = `<strong>Connections:</strong> ${stats.total_connections}`;
    statsList.createEl("li").innerHTML = `<strong>Communities:</strong> ${stats.num_communities}`;
    statsList.createEl("li").innerHTML = `<strong>Avg Connections/Note:</strong> ${stats.avg_connections_per_note.toFixed(2)}`;

    // Important Notes (PageRank)
    if (important_notes.length > 0) {
      const importantSection = container.createEl("div", { cls: "didymos-insights-section" });
      importantSection.createEl("h3", { text: "⭐ Most Important Notes" });

      const importantList = importantSection.createEl("ul", { cls: "didymos-important-list" });

      important_notes.forEach((item, index) => {
        const li = importantList.createEl("li", { cls: "didymos-important-item" });

        const rank = li.createEl("span", {
          text: `#${index + 1}`,
          cls: "didymos-rank"
        });

        const link = li.createEl("a", {
          text: item.note_id,
          cls: "didymos-note-link"
        });

        link.addEventListener("click", () => {
          this.app.workspace.openLinkText(item.note_id, "", false);
        });

        li.createEl("span", {
          text: `${(item.score * 100).toFixed(2)}%`,
          cls: "didymos-score"
        });
      });
    }

    // Communities
    if (communities.length > 0) {
      const commSection = container.createEl("div", { cls: "didymos-insights-section" });
      commSection.createEl("h3", { text: "🔗 Knowledge Clusters" });

      communities.slice(0, 3).forEach((community, index) => {
        const commDiv = commSection.createEl("div", { cls: "didymos-community" });

        commDiv.createEl("h4", {
          text: `Cluster ${index + 1} (${community.size} notes)`
        });

        const notesList = commDiv.createEl("ul", { cls: "didymos-community-notes" });

        community.notes.slice(0, 5).forEach(noteId => {
          const li = notesList.createEl("li");
          const link = li.createEl("a", {
            text: noteId,
            cls: "didymos-note-link"
          });

          link.addEventListener("click", () => {
            this.app.workspace.openLinkText(noteId, "", false);
          });
        });

        if (community.size > 5) {
          notesList.createEl("li", {
            text: `... and ${community.size - 5} more`,
            cls: "didymos-more"
          });
        }
      });
    }

    // Orphan Notes
    if (orphan_notes.length > 0) {
      const orphanSection = container.createEl("div", { cls: "didymos-insights-section" });
      orphanSection.createEl("h3", { text: "🏝️ Isolated Notes" });

      orphanSection.createEl("p", {
        text: `${orphan_notes.length} notes have no connections. Consider linking them to related topics.`,
        cls: "didymos-orphan-description"
      });

      const orphanList = orphanSection.createEl("ul", { cls: "didymos-orphan-list" });

      orphan_notes.slice(0, 10).forEach(noteId => {
        const li = orphanList.createEl("li");
        const link = li.createEl("a", {
          text: noteId,
          cls: "didymos-note-link"
        });

        link.addEventListener("click", () => {
          this.app.workspace.openLinkText(noteId, "", false);
        });
      });

      if (orphan_notes.length > 10) {
        orphanList.createEl("li", {
          text: `... and ${orphan_notes.length - 10} more`,
          cls: "didymos-more"
        });
      }
    }
  }

  async getRecommendations(button: HTMLElement) {
    const originalText = button.textContent || "";
    const container = this.containerEl.querySelector(".didymos-insights-results");

    if (!container) return;

    try {
      button.textContent = "⏳ Generating...";
      button.setAttribute("disabled", "true");

      // API 호출
      const response = await fetch(
        `${this.settings.apiEndpoint}/patterns/recommendations/${this.settings.userToken}/${this.settings.vaultId}`
      );

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      this.recommendationData = data.recommendations;

      // 결과 렌더링
      this.renderRecommendations(container as HTMLElement);

      button.textContent = "✅ Recommendations Ready";
      setTimeout(() => {
        button.textContent = originalText;
        button.removeAttribute("disabled");
      }, 2000);

    } catch (error: any) {
      container.empty();
      container.createEl("div", {
        text: `❌ Recommendations failed: ${error.message}`,
        cls: "didymos-insights-error"
      });

      button.textContent = originalText;
      button.removeAttribute("disabled");
    }
  }

  renderRecommendations(container: HTMLElement) {
    if (!this.recommendationData) return;

    container.empty();

    const { priority_tasks, missing_connections } = this.recommendationData;

    // Priority Tasks
    if (priority_tasks.length > 0) {
      const tasksSection = container.createEl("div", { cls: "didymos-insights-section" });
      tasksSection.createEl("h3", { text: "🎯 Priority Tasks" });

      const tasksList = tasksSection.createEl("ul", { cls: "didymos-task-list" });

      priority_tasks.forEach((task, index) => {
        const li = tasksList.createEl("li", { cls: "didymos-task-item" });

        const rank = li.createEl("span", {
          text: `#${index + 1}`,
          cls: "didymos-rank"
        });

        const taskInfo = li.createEl("div", { cls: "didymos-task-info" });

        const title = taskInfo.createEl("div", { cls: "didymos-task-title-row" });

        const taskTitle = title.createEl("span", {
          text: task.title,
          cls: "didymos-task-title"
        });

        const priorityBadge = title.createEl("span", {
          text: task.priority.toUpperCase(),
          cls: `didymos-priority-badge priority-${task.priority}`
        });

        const meta = taskInfo.createEl("div", { cls: "didymos-task-meta" });

        meta.createEl("span", {
          text: task.urgency,
          cls: "didymos-task-urgency"
        });

        const noteLink = meta.createEl("a", {
          text: ` in ${task.note_title}`,
          cls: "didymos-note-link-small"
        });

        noteLink.addEventListener("click", () => {
          this.app.workspace.openLinkText(task.note_id, "", false);
        });

        li.createEl("span", {
          text: `Score: ${task.score}`,
          cls: "didymos-score"
        });
      });
    }

    // Missing Connections
    if (missing_connections.length > 0) {
      const connectSection = container.createEl("div", { cls: "didymos-insights-section" });
      connectSection.createEl("h3", { text: "🔗 Suggested Connections" });

      connectSection.createEl("p", {
        text: "These notes share topics but aren't connected:",
        cls: "didymos-connection-description"
      });

      const connectionsList = connectSection.createEl("ul", { cls: "didymos-connection-list" });

      missing_connections.forEach((conn) => {
        const li = connectionsList.createEl("li", { cls: "didymos-connection-item" });

        const link1 = li.createEl("a", {
          text: conn.note1_title,
          cls: "didymos-note-link"
        });

        link1.addEventListener("click", () => {
          this.app.workspace.openLinkText(conn.note1_id, "", false);
        });

        li.createEl("span", {
          text: " ↔️ ",
          cls: "didymos-connection-arrow"
        });

        const link2 = li.createEl("a", {
          text: conn.note2_title,
          cls: "didymos-note-link"
        });

        link2.addEventListener("click", () => {
          this.app.workspace.openLinkText(conn.note2_id, "", false);
        });

        li.createEl("div", {
          text: conn.reason,
          cls: "didymos-connection-reason"
        });
      });
    }

    // 둘 다 없으면
    if (priority_tasks.length === 0 && missing_connections.length === 0) {
      container.createEl("p", {
        text: "No recommendations available. Try syncing more notes first.",
        cls: "didymos-insights-empty"
      });
    }
  }

  async analyzeWeaknesses(button: HTMLElement) {
    const originalText = button.textContent || "";
    const container = this.containerEl.querySelector(".didymos-insights-results");

    if (!container) return;

    try {
      button.textContent = "⏳ Analyzing...";
      button.setAttribute("disabled", "true");

      // API 호출
      const response = await fetch(
        `${this.settings.apiEndpoint}/patterns/weaknesses/${this.settings.userToken}/${this.settings.vaultId}`
      );

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      this.weaknessData = data.weakness_analysis;

      // 결과 렌더링
      this.renderWeaknesses(container as HTMLElement);

      button.textContent = "✅ Analysis Complete";
      setTimeout(() => {
        button.textContent = originalText;
        button.removeAttribute("disabled");
      }, 2000);

    } catch (error: any) {
      container.empty();
      container.createEl("div", {
        text: `❌ Weakness analysis failed: ${error.message}`,
        cls: "didymos-insights-error"
      });

      button.textContent = originalText;
      button.removeAttribute("disabled");
    }
  }

  renderWeaknesses(container: HTMLElement) {
    if (!this.weaknessData) return;

    container.empty();

    const { weaknesses, total_weakness_score, critical_weakness, strengthening_plan } = this.weaknessData;

    // Header
    const headerSection = container.createEl("div", { cls: "didymos-insights-section" });
    headerSection.createEl("h3", { text: "⚠️ Weakness Analysis" });
    headerSection.createEl("p", {
      text: `"The chain is only as strong as its weakest link"`,
      cls: "didymos-weakness-quote"
    });

    // Overall Score
    const scoreSection = container.createEl("div", { cls: "didymos-weakness-score-section" });
    scoreSection.createEl("div", {
      text: `Total Weakness Score: ${total_weakness_score.toFixed(1)} / 50`,
      cls: "didymos-weakness-total-score"
    });

    // Critical Weakness
    if (critical_weakness && critical_weakness.count > 0) {
      const criticalSection = container.createEl("div", { cls: "didymos-insights-section didymos-critical-weakness" });
      criticalSection.createEl("h3", { text: "🔴 Critical Weakness" });

      const categoryName = this.formatCategoryName(critical_weakness.category);
      criticalSection.createEl("h4", {
        text: `${categoryName} (Score: ${critical_weakness.severity_score.toFixed(1)})`,
        cls: "didymos-weakness-category-title"
      });

      criticalSection.createEl("p", {
        text: `${critical_weakness.count} items detected`,
        cls: "didymos-weakness-count"
      });

      // Top items
      const itemsList = criticalSection.createEl("ul", { cls: "didymos-weakness-items" });
      critical_weakness.top_items.forEach((item: any) => {
        const li = itemsList.createEl("li");
        this.renderWeaknessItem(li, item, critical_weakness.category);
      });
    }

    // Strengthening Plan
    if (strengthening_plan && strengthening_plan.length > 0) {
      const planSection = container.createEl("div", { cls: "didymos-insights-section" });
      planSection.createEl("h3", { text: "💪 Strengthening Plan" });

      strengthening_plan.forEach((plan) => {
        const planDiv = planSection.createEl("div", { cls: "didymos-plan-item" });

        planDiv.createEl("h4", {
          text: `${plan.priority}. ${plan.action}`,
          cls: "didymos-plan-action"
        });

        planDiv.createEl("p", {
          text: plan.reason,
          cls: "didymos-plan-reason"
        });

        if (plan.steps && plan.steps.length > 0) {
          const stepsList = planDiv.createEl("ol", { cls: "didymos-plan-steps" });
          plan.steps.forEach((step: string) => {
            stepsList.createEl("li", { text: step });
          });
        }
      });
    }

    // All Weaknesses Summary
    const summarySection = container.createEl("div", { cls: "didymos-insights-section" });
    summarySection.createEl("h3", { text: "📊 All Weaknesses Summary" });

    const categories = [
      { key: "chronic_overdue_tasks", icon: "⏰", name: "Chronic Overdue Tasks" },
      { key: "stale_projects", icon: "📁", name: "Stale Projects" },
      { key: "isolated_topics", icon: "🏝️", name: "Isolated Topics" },
      { key: "weak_clusters", icon: "🔗", name: "Weak Clusters" },
      { key: "knowledge_gaps", icon: "📚", name: "Knowledge Gaps" }
    ];

    const summaryList = summarySection.createEl("ul", { cls: "didymos-weakness-summary" });

    categories.forEach((cat) => {
      const categoryData = weaknesses[cat.key as keyof typeof weaknesses];
      if (!categoryData) return;

      const li = summaryList.createEl("li", { cls: "didymos-weakness-summary-item" });

      const header = li.createEl("div", { cls: "didymos-weakness-summary-header" });
      header.createEl("span", {
        text: `${cat.icon} ${cat.name}`,
        cls: "didymos-weakness-category-name"
      });

      const badge = header.createEl("span", {
        text: `${categoryData.count} items (${categoryData.severity_score.toFixed(1)})`,
        cls: `didymos-weakness-badge ${this.getSeverityClass(categoryData.severity_score)}`
      });

      if (categoryData.items && categoryData.items.length > 0) {
        const itemsList = li.createEl("ul", { cls: "didymos-weakness-detail-items" });
        categoryData.items.slice(0, 3).forEach((item: any) => {
          const itemLi = itemsList.createEl("li");
          this.renderWeaknessItem(itemLi, item, cat.key);
        });

        if (categoryData.count > 3) {
          itemsList.createEl("li", {
            text: `... and ${categoryData.count - 3} more`,
            cls: "didymos-more"
          });
        }
      }
    });

    // 약점이 하나도 없으면
    if (total_weakness_score === 0) {
      container.empty();
      container.createEl("div", {
        text: "🎉 Great! No significant weaknesses detected. Your knowledge system is well-maintained!",
        cls: "didymos-insights-success"
      });
    }
  }

  renderWeaknessItem(container: HTMLElement, item: any, category: string) {
    const itemDiv = container.createEl("div", { cls: "didymos-weakness-item-content" });

    switch (category) {
      case "chronic_overdue_tasks":
        const taskLink = itemDiv.createEl("a", {
          text: item.title || "Untitled task",
          cls: "didymos-note-link"
        });
        taskLink.addEventListener("click", () => {
          if (item.note_id) {
            this.app.workspace.openLinkText(item.note_id, "", false);
          }
        });

        itemDiv.createEl("span", {
          text: ` - ${item.days_overdue}d overdue`,
          cls: "didymos-weakness-meta"
        });
        break;

      case "stale_projects":
        const projectLink = itemDiv.createEl("a", {
          text: item.title || item.note_id,
          cls: "didymos-note-link"
        });
        projectLink.addEventListener("click", () => {
          this.app.workspace.openLinkText(item.note_id, "", false);
        });

        if (item.days_since_update) {
          itemDiv.createEl("span", {
            text: ` - ${item.days_since_update}d no update`,
            cls: "didymos-weakness-meta"
          });
        }
        break;

      case "isolated_topics":
        itemDiv.createEl("strong", { text: item.topic_name });
        itemDiv.createEl("span", {
          text: ` - ${item.note_count} unconnected notes`,
          cls: "didymos-weakness-meta"
        });
        break;

      case "weak_clusters":
        itemDiv.createEl("span", {
          text: `Cluster with ${item.size} notes, density ${(item.density * 100).toFixed(1)}%`,
          cls: "didymos-weakness-meta"
        });
        break;

      case "knowledge_gaps":
        itemDiv.createEl("strong", { text: item.topic_name });
        itemDiv.createEl("span", {
          text: ` - mentioned ${item.mention_count} times`,
          cls: "didymos-weakness-meta"
        });
        break;
    }

    if (item.recommendation) {
      itemDiv.createEl("div", {
        text: item.recommendation,
        cls: "didymos-weakness-recommendation"
      });
    }
  }

  formatCategoryName(category: string): string {
    const names: Record<string, string> = {
      "chronic_overdue_tasks": "Chronic Overdue Tasks",
      "stale_projects": "Stale Projects",
      "isolated_topics": "Isolated Topics",
      "weak_clusters": "Weak Clusters",
      "knowledge_gaps": "Knowledge Gaps"
    };
    return names[category] || category;
  }

  getSeverityClass(score: number): string {
    if (score >= 8) return "severity-critical";
    if (score >= 5) return "severity-high";
    if (score >= 2) return "severity-medium";
    return "severity-low";
  }

  async onClose() {
    // Cleanup if needed
  }
}
