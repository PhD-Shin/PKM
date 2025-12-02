import { Plugin, Notice, TFile, PluginSettingTab, App, Setting, WorkspaceLeaf } from 'obsidian';
import { DidymosAPI, NotePayload } from './api/client';
import { DidymosContextView, DIDYMOS_CONTEXT_VIEW_TYPE } from './views/contextView';
import { DidymosGraphView, DIDYMOS_GRAPH_VIEW_TYPE } from './views/graphView';
import { DidymosTaskView, DIDYMOS_TASK_VIEW_TYPE } from './views/taskView';
import { DidymosReviewView, DIDYMOS_REVIEW_VIEW_TYPE } from './views/reviewView';
import { DidymosDecisionView, DIDYMOS_DECISION_VIEW_TYPE } from './views/decisionView';
import { DidymosInsightsView, INSIGHTS_VIEW_TYPE } from './views/insightsView';
import { DidymosUnifiedView, UNIFIED_VIEW_TYPE } from './views/unifiedView';
import { DidymosSettings, DEFAULT_SETTINGS } from './settings';
import { TemplateService } from './services/templateService';
import { OnboardingModal } from './modals/onboardingModal';
import { TemplateGalleryModal } from './modals/templateGalleryModal';
import { DidymosControlPanelView, CONTROL_PANEL_VIEW_TYPE, ControlPanelAction } from './views/controlPanelView';

export default class DidymosPlugin extends Plugin {
  settings: DidymosSettings;
  api: DidymosAPI;
  templateService: TemplateService;
  hourlyInterval: number | null = null;
  lastRealtimeSync: number = 0;

  async onload() {
    await this.loadSettings();
    await this.ensureDefaultIdentifiers();
    this.ensureUsageReset();
    this.api = new DidymosAPI(this.settings);
    this.templateService = new TemplateService(this.app);

    // 온보딩 제거 - Control Panel에서 수동으로 접근 가능

    // Settings tab
    this.addSettingTab(new DidymosSettingTab(this.app, this));

    // Context View 등록
    this.registerView(
      DIDYMOS_CONTEXT_VIEW_TYPE,
      (leaf) => new DidymosContextView(leaf, this.settings)
    );

    // Graph View 등록
    this.registerView(
      DIDYMOS_GRAPH_VIEW_TYPE,
      (leaf) => new DidymosGraphView(leaf, this.settings, this)
    );

    // Task View 등록
    this.registerView(
      DIDYMOS_TASK_VIEW_TYPE,
      (leaf) => new DidymosTaskView(leaf, this.settings)
    );

    // Review View 등록
    this.registerView(
      DIDYMOS_REVIEW_VIEW_TYPE,
      (leaf) => new DidymosReviewView(leaf, this.settings)
    );

    // Decision View 등록
    this.registerView(
      DIDYMOS_DECISION_VIEW_TYPE,
      (leaf) => new DidymosDecisionView(leaf, this.settings)
    );

    // Insights View 등록
    this.registerView(
      INSIGHTS_VIEW_TYPE,
      (leaf) => new DidymosInsightsView(leaf, this.settings)
    );

    // Unified View 등록
    this.registerView(
      UNIFIED_VIEW_TYPE,
      (leaf) => new DidymosUnifiedView(leaf, this.settings)
    );

    // Control Panel View 등록
    this.registerView(
      CONTROL_PANEL_VIEW_TYPE,
      (leaf) => {
        const actions = this.getControlPanelActions();
        return new DidymosControlPanelView(leaf, actions, this, this.settings);
      }
    );

    // 리본 아이콘 - Control Panel
    this.addRibbonIcon('layout-dashboard', 'Open Didymos Control Panel', async () => {
      await this.activateControlPanelView();
    });

    // 메인 명령: Control Panel (모든 기능을 한 곳에서)
    this.addCommand({
      id: 'open-control-panel',
      name: 'Open Didymos Control Panel',
      callback: async () => {
        await this.activateControlPanelView();
      }
    });

    if (this.settings.bulkProcessOnStart) {
      await this.bulkProcessVault();
    }

    // Auto-sync on file modification
    if (this.settings.autoSync && this.settings.syncMode === 'realtime' && this.settings.premiumRealtime) {
      this.registerEvent(
        this.app.vault.on('modify', async (file) => {
          if (file instanceof TFile && file.extension === 'md') {
            const now = Date.now();
            const cooldownMs = this.settings.realtimeCooldownMinutes * 60 * 1000;
            if (now - this.lastRealtimeSync >= cooldownMs) {
              this.lastRealtimeSync = now;
              await this.syncNote(file);
            }
          }
        })
      );
    }

    if (this.settings.autoSync && this.settings.syncMode === 'hourly') {
      this.hourlyInterval = window.setInterval(async () => {
        await this.bulkProcessVault();
      }, 60 * 60 * 1000);
    }

    console.log('Didymos PKM plugin loaded');
  }

  onunload() {
    console.log('Didymos PKM plugin unloaded');
    this.app.workspace.detachLeavesOfType(DIDYMOS_CONTEXT_VIEW_TYPE);
    this.app.workspace.detachLeavesOfType(DIDYMOS_GRAPH_VIEW_TYPE);
    this.app.workspace.detachLeavesOfType(DIDYMOS_TASK_VIEW_TYPE);
    this.app.workspace.detachLeavesOfType(DIDYMOS_REVIEW_VIEW_TYPE);
    if (this.hourlyInterval) {
      window.clearInterval(this.hourlyInterval);
      this.hourlyInterval = null;
    }
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async ensureDefaultIdentifiers() {
    let changed = false;
    if (!this.settings.vaultId) {
      this.settings.vaultId = this.app.vault.getName();
      changed = true;
    }
    if (!this.settings.userToken) {
      const slug = this.app.vault.getName().replace(/\s+/g, '-').toLowerCase();
      this.settings.userToken = `local-${slug}`;
      changed = true;
    }
    if (changed) {
      await this.saveSettings();
    }
  }

  async saveSettings() {
    await this.saveData(this.settings);
    this.api = new DidymosAPI(this.settings);
  }

  async syncNote(file: TFile): Promise<void> {
    if (!this.settings.userToken || !this.settings.vaultId) {
      new Notice('Please configure Didymos settings first');
      return;
    }
    this.ensureUsageReset();

    // 제외 폴더 체크
    const isExcluded = this.settings.excludedFolders.some((folder) =>
      folder && file.path.startsWith(folder)
    );
    if (isExcluded) {
      console.log(`Skipped excluded folder: ${file.path}`);
      return;
    }

    try {
      const content = await this.app.vault.read(file);
      const metadata = this.app.metadataCache.getFileCache(file);

      const notePayload: NotePayload = {
        note_id: file.path,
        title: file.basename,
        path: file.path,
        content: content,
        yaml: metadata?.frontmatter || {},
        tags: metadata?.tags?.map(t => t.tag.replace('#', '')) || [],
        links: metadata?.links?.map(l => l.link) || [],
        created_at: new Date(file.stat.ctime).toISOString(),
        updated_at: new Date(file.stat.mtime).toISOString()
      };

      this.incrementUsage();

      const result = await this.api.syncNote(notePayload, this.settings.privacyMode);
      new Notice(`✅ ${result.message ?? 'Synced'}`);
      console.log('Sync result:', result);

      if (this.settings.autoExportOntology) {
        await this.exportOntologySnapshot(file);
      }

      // Context Panel 업데이트
      const leaf = this.app.workspace.getLeavesOfType(DIDYMOS_CONTEXT_VIEW_TYPE)[0];
      if (leaf && leaf.view instanceof DidymosContextView) {
        await (leaf.view as DidymosContextView).updateContext(notePayload.note_id);
      }

    } catch (error) {
      console.error('Sync failed:', error);
      new Notice(`❌ Sync failed: ${error.message}`);
    }
  }

  private async bulkProcessVault() {
    const files = this.app.vault.getMarkdownFiles();
    if (!files.length) {
      new Notice("No markdown files found for bulk processing");
      return;
    }
    new Notice(`Bulk processing ${files.length} notes...`);
    let processed = 0;
    for (const file of files) {
      try {
        await this.syncNote(file);
        processed++;
        // Only show progress at 10-unit increments
        if (processed % 10 === 0) {
          new Notice(`Progress: ${processed}/${files.length} notes processed`);
        }
      } catch (e) {
        console.error(`Bulk sync failed for ${file.path}:`, e);
      }
    }
    new Notice(`Bulk processing complete: ${processed}/${files.length} notes`);
  }

  async exportOntologySnapshot(file: TFile) {
    try {
      if (this.settings.localMode) {
        await this.exportOntologyLocal(file);
        return;
      }

      const context = await this.api.fetchContext(file.path);

      const lines: string[] = [];
      lines.push(`# Ontology Snapshot: ${file.basename}`);
      lines.push(`Source: ${file.path}`);
      lines.push("");
      if (context.topics.length) {
        lines.push("## Topics");
        context.topics.forEach((t) => {
          lines.push(`- ${t.name} (score: ${Math.round(t.importance_score * 100)}%, mentions: ${t.mention_count})`);
        });
        lines.push("");
      }
      if (context.projects.length) {
        lines.push("## Projects");
        context.projects.forEach((p) => {
          lines.push(`- ${p.name} [${p.status}] (updated: ${p.updated_at})`);
        });
        lines.push("");
      }
      if (context.tasks.length) {
        lines.push("## Tasks");
        context.tasks.forEach((t) => {
          lines.push(`- ${t.title} [${t.status}/${t.priority}]`);
        });
        lines.push("");
      }
      if (context.related_notes.length) {
        lines.push("## Related Notes");
        context.related_notes.forEach((r, idx) => {
          lines.push(`- ${idx + 1}. ${r.title} (${r.similarity * 100}%) - ${r.path}`);
        });
        lines.push("");
      }

      const exportFolder = this.settings.exportFolder || "Didymos/Ontology";
      await this.ensureFolder(exportFolder);
      const targetPath = `${exportFolder}/${file.basename}.ontology.md`;

      // 덮어쓰기 방지: 이미 있으면 suffix 추가
      let finalPath = targetPath;
      let counter = 1;
      while (await this.app.vault.adapter.exists(finalPath)) {
        finalPath = `${exportFolder}/${file.basename}.ontology.${counter}.md`;
        counter += 1;
      }

      await this.app.vault.create(finalPath, lines.join("\n"));
      new Notice(`✅ Ontology snapshot saved: ${finalPath}`);
    } catch (error: any) {
      console.error(error);
      new Notice(`❌ Export failed: ${error.message}`);
    }
  }

  async exportOntologyLocal(file: TFile) {
    if (!this.settings.localOpenAIApiKey) {
      new Notice("OpenAI API Key is required for local mode");
      return;
    }
    const content = await this.app.vault.read(file);
    const prompt = [
      "Extract ontology entities from the note.",
      "Return JSON with keys: topics, projects, tasks, persons.",
      "topics/projects/tasks/persons should be arrays of strings.",
    ].join(" ");

    const body = {
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: prompt },
        { role: "user", content: content.slice(0, 4000) },
      ],
      temperature: 0,
      max_tokens: 400,
    };

    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.settings.localOpenAIApiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      new Notice(`❌ Local extraction failed: ${resp.status}`);
      return;
    }

    const data = await resp.json();
    const contentJson = data?.choices?.[0]?.message?.content;
    let parsed: any;
    try {
      parsed = JSON.parse(contentJson);
    } catch (e) {
      new Notice("❌ Failed to parse ontology JSON");
      return;
    }

    const lines: string[] = [];
    lines.push(`# Ontology Snapshot (Local): ${file.basename}`);
    lines.push(`Source: ${file.path}`);
    lines.push("");

    if (parsed.topics?.length) {
      lines.push("## Topics");
      parsed.topics.forEach((t: string) => lines.push(`- ${t}`));
      lines.push("");
    }
    if (parsed.projects?.length) {
      lines.push("## Projects");
      parsed.projects.forEach((p: string) => lines.push(`- ${p}`));
      lines.push("");
    }
    if (parsed.tasks?.length) {
      lines.push("## Tasks");
      parsed.tasks.forEach((t: string) => lines.push(`- ${t}`));
      lines.push("");
    }
    if (parsed.persons?.length) {
      lines.push("## Persons");
      parsed.persons.forEach((p: string) => lines.push(`- ${p}`));
      lines.push("");
    }

    const exportFolder = this.settings.exportFolder || "Didymos/Ontology";
    await this.ensureFolder(exportFolder);
    const targetPath = `${exportFolder}/${file.basename}.ontology.local.md`;

    let finalPath = targetPath;
    let counter = 1;
    while (await this.app.vault.adapter.exists(finalPath)) {
      finalPath = `${exportFolder}/${file.basename}.ontology.local.${counter}.md`;
      counter += 1;
    }

    await this.app.vault.create(finalPath, lines.join("\n"));
    new Notice(`✅ Local ontology saved: ${finalPath}`);
  }

  private async ensureFolder(folder: string) {
    const exists = await this.app.vault.adapter.exists(folder);
    if (!exists) {
      await this.app.vault.createFolder(folder);
    }
  }

  private ensureUsageReset() {
    const today = new Date().toISOString().slice(0, 10);
    if (this.settings.usageResetAt !== today) {
      this.settings.usageResetAt = today;
      this.settings.usageUsedToday = 0;
      this.saveSettings();
    }
  }

  private incrementUsage() {
    this.settings.usageUsedToday += 1;
    const remaining = this.settings.usageBudgetPerDay - this.settings.usageUsedToday;
    if (remaining <= Math.max(5, this.settings.usageBudgetPerDay * 0.1)) {
      new Notice(`⚠️ Usage remaining today: ${remaining}/${this.settings.usageBudgetPerDay}`);
    }
    if (remaining < 0) {
      new Notice(`⚠️ Daily usage budget exceeded (${this.settings.usageUsedToday}/${this.settings.usageBudgetPerDay})`);
    }
    this.saveSettings();
  }

  private async generateDecisionNote(file: TFile) {
    try {
      this.ensureUsageReset();
      this.incrementUsage();
      const decisionFolder = this.settings.decisionFolder || "Didymos/Decisions";
      await this.ensureFolder(decisionFolder);

      // 기본 컨텍스트/리뷰 데이터를 가져온다 (백엔드 의존)
      const [context, review] = await Promise.all([
        this.api.fetchContext(file.path),
        this.api.fetchWeeklyReview(this.settings.vaultId),
      ]);

      const lines: string[] = [];
      lines.push(`# Decision Note: ${file.basename}`);
      lines.push(`Source: ${file.path}`);
      lines.push(`Generated: ${new Date().toISOString()}`);
      lines.push("");

      lines.push("## Key Topics");
      if (context.topics.length) {
        context.topics.slice(0, 5).forEach((t) => lines.push(`- ${t.name} (${Math.round(t.importance_score * 100)}%)`));
      } else {
        lines.push("- (none)");
      }
      lines.push("");

      lines.push("## Projects & Status");
      if (context.projects.length) {
        context.projects.slice(0, 5).forEach((p) => lines.push(`- ${p.name} [${p.status}]`));
      } else {
        lines.push("- (none)");
      }
      lines.push("");

      lines.push("## Open Tasks");
      if (context.tasks.length) {
        context.tasks.slice(0, 10).forEach((t) => lines.push(`- ${t.title} [${t.status}/${t.priority}]`));
      } else {
        lines.push("- (none)");
      }
      lines.push("");

      lines.push("## Related Notes");
      if (context.related_notes.length) {
        context.related_notes.slice(0, 5).forEach((r, idx) => lines.push(`- ${idx + 1}. ${r.title} (${Math.round(r.similarity * 100)}%) - ${r.path}`));
      } else {
        lines.push("- (none)");
      }
      lines.push("");

      lines.push("## Weekly Signals");
      lines.push("### New Topics");
      (review.new_topics || []).slice(0, 5).forEach((t) => lines.push(`- ${t.name} (${t.mention_count})`));
      if (!review.new_topics?.length) lines.push("- (none)");
      lines.push("");

      lines.push("### Forgotten Projects");
      (review.forgotten_projects || []).slice(0, 5).forEach((p) => lines.push(`- ${p.name} (${p.days_inactive}d inactive)`));
      if (!review.forgotten_projects?.length) lines.push("- (none)");
      lines.push("");

      lines.push("### Overdue Tasks");
      (review.overdue_tasks || []).slice(0, 5).forEach((t) => lines.push(`- ${t.title} [${t.priority}] - ${t.note_title}`));
      if (!review.overdue_tasks?.length) lines.push("- (none)");
      lines.push("");

      const payload = this.buildOntologyPayload(context);
      lines.push("## Ontology (json)");
      lines.push("```json");
      lines.push(this.stringifyOntology(payload));
      lines.push("```");

      const targetPath = `${decisionFolder}/${file.basename}.decision.md`;
      let finalPath = targetPath;
      let counter = 1;
      while (await this.app.vault.adapter.exists(finalPath)) {
        finalPath = `${decisionFolder}/${file.basename}.decision.${counter}.md`;
        counter += 1;
      }

      await this.app.vault.create(finalPath, lines.join("\n"));
      new Notice(`✅ Decision note saved: ${finalPath}`);
    } catch (error: any) {
      console.error(error);
      new Notice(`❌ Decision note failed: ${error.message}`);
    }
  }

  private buildOntologyPayload(context: any) {
    return {
      source: context?.note_id || "",
      topics: (context.topics || []).map((t: any) => t.name || t.id),
      projects: (context.projects || []).map((p: any) => p.name || p.id),
      tasks: (context.tasks || []).map((t: any) => t.title || t.id),
      related_notes: (context.related_notes || []).map((r: any) => r.note_id || r.path),
    };
  }

  private buildLocalOntologyPayload(parsed: any, file: TFile) {
    return {
      source: file.path,
      topics: parsed.topics || [],
      projects: parsed.projects || [],
      tasks: parsed.tasks || [],
      persons: parsed.persons || [],
    };
  }

  private stringifyOntology(payload: any): string {
    const fmt = this.settings.ontologyFormat;
    if (fmt === "json") {
      return JSON.stringify(payload, null, 2);
    }
    // naive yaml-ish serialization for readability
    const yamlLines: string[] = [];
    yamlLines.push(`source: ${payload.source || ""}`);
    const pushArray = (key: string, arr: any[]) => {
      yamlLines.push(`${key}:`);
      if (!arr || arr.length === 0) {
        yamlLines.push(`  []`);
        return;
      }
      arr.forEach((item) => {
        yamlLines.push(`  - ${item}`);
      });
    };
    pushArray("topics", payload.topics || []);
    pushArray("projects", payload.projects || []);
    pushArray("tasks", payload.tasks || []);
    if (payload.persons) pushArray("persons", payload.persons || []);
    if (payload.related_notes) pushArray("related_notes", payload.related_notes || []);
    return yamlLines.join("\n");
  }

  private async writeOntologyToNote(file: TFile, payload: any) {
    const markerStart = "<!-- didymos-ontology:start -->";
    const markerEnd = "<!-- didymos-ontology:end -->";
    const fence = "json";
    const block = [
      markerStart,
      "```" + fence,
      this.stringifyOntology(payload),
      "```",
      markerEnd,
      "",
    ].join("\n");

    const content = await this.app.vault.read(file);
    const startIdx = content.indexOf(markerStart);
    const endIdx = content.indexOf(markerEnd);

    if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
      const newContent =
        content.slice(0, startIdx) + block + content.slice(endIdx + markerEnd.length);
      await this.app.vault.modify(file, newContent);
    } else {
      const newContent = content.trimEnd() + "\n\n" + block;
      await this.app.vault.modify(file, newContent);
    }
  }

  async activateUnifiedView() {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(UNIFIED_VIEW_TYPE)[0] ?? null;

    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({
          type: UNIFIED_VIEW_TYPE,
          active: true,
        });
      }
    }
    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  async activateContextView() {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(DIDYMOS_CONTEXT_VIEW_TYPE)[0] ?? null;

    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({
          type: DIDYMOS_CONTEXT_VIEW_TYPE,
          active: true,
        });
      }
    }
    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  async activateGraphView() {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(DIDYMOS_GRAPH_VIEW_TYPE)[0] ?? null;

    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({
          type: DIDYMOS_GRAPH_VIEW_TYPE,
          active: true,
        });
      }
    }
    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  async activateTaskView() {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(DIDYMOS_TASK_VIEW_TYPE)[0] ?? null;

    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({
          type: DIDYMOS_TASK_VIEW_TYPE,
          active: true,
        });
      }
    }
    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  async activateReviewView() {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(DIDYMOS_REVIEW_VIEW_TYPE)[0] ?? null;

    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({
          type: DIDYMOS_REVIEW_VIEW_TYPE,
          active: true,
        });
      }
    }
    if (leaf) {
      workspace.revealLeaf(leaf);
      if (leaf.view instanceof DidymosReviewView) {
        await (leaf.view as DidymosReviewView).renderReview();
      }
    }
  }

  async activateDecisionView() {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(DIDYMOS_DECISION_VIEW_TYPE)[0] ?? null;

    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({
          type: DIDYMOS_DECISION_VIEW_TYPE,
          active: true,
        });
      }
    }
    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  async activateInsightsView() {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(INSIGHTS_VIEW_TYPE)[0] ?? null;

    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({
          type: INSIGHTS_VIEW_TYPE,
          active: true,
        });
      }
    }
    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  /**
   * 온보딩 모달 표시
   */
  async showOnboarding() {
    new OnboardingModal(
      this.app,
      this.templateService,
      async () => {
        this.settings.onboardingCompleted = true;
        await this.saveSettings();
        new Notice('Welcome to Didymos! 🎉');
      }
    ).open();
  }

  /**
   * Control Panel View 활성화
   */
  async activateControlPanelView() {
    const { workspace } = this.app;

    let leaf: WorkspaceLeaf | null = null;
    const leaves = workspace.getLeavesOfType(CONTROL_PANEL_VIEW_TYPE);

    if (leaves.length > 0) {
      // 이미 열려있으면 해당 leaf로 이동
      leaf = leaves[0];
    } else {
      // 새로 열기 - 오른쪽 사이드바에
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({ type: CONTROL_PANEL_VIEW_TYPE, active: true });
      }
    }

    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  /**
   * Control Panel Actions 가져오기
   */
  getControlPanelActions(): ControlPanelAction[] {
    return [
      // Views - MVP 핵심 기능만 (의사결정 지원)
      {
        id: 'open-graph-panel',
        name: 'Knowledge Graph',
        description: '지식 그래프 시각화',
        icon: '🕸️',
        category: 'views',
        viewType: DIDYMOS_GRAPH_VIEW_TYPE,
        callback: async () => await this.activateGraphView(),
      },
      {
        id: 'open-task-panel',
        name: 'Task Panel',
        description: '작업 목록 보기',
        icon: '✅',
        category: 'views',
        viewType: DIDYMOS_TASK_VIEW_TYPE,
        callback: async () => await this.activateTaskView(),
      },
      {
        id: 'open-review-panel',
        name: 'Weekly Review',
        description: '주간 리뷰 보기',
        icon: '📊',
        category: 'views',
        viewType: DIDYMOS_REVIEW_VIEW_TYPE,
        callback: async () => await this.activateReviewView(),
      },
      {
        id: 'open-decision-panel',
        name: 'Decision Dashboard',
        description: '의사결정 대시보드',
        icon: '🎯',
        category: 'views',
        viewType: DIDYMOS_DECISION_VIEW_TYPE,
        callback: async () => await this.activateDecisionView(),
      },
      {
        id: 'open-insights-panel',
        name: 'Knowledge Insights',
        description: '지식 인사이트 패널',
        icon: '💡',
        category: 'views',
        viewType: INSIGHTS_VIEW_TYPE,
        callback: async () => await this.activateInsightsView(),
      },
      // Sync
      {
        id: 'sync-current-note',
        name: 'Sync Current Note',
        description: '현재 노트를 Didymos에 동기화',
        icon: '🔄',
        category: 'sync',
        callback: async () => {
          const file = this.app.workspace.getActiveFile();
          if (file) {
            await this.syncNote(file);
          } else {
            new Notice('No active file to sync');
          }
        },
      },
    ];
  }
}

class DidymosSettingTab extends PluginSettingTab {
  plugin: DidymosPlugin;

  constructor(app: App, plugin: DidymosPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl('h2', { text: 'Didymos PKM Settings' });

    new Setting(containerEl)
      .setName('API Endpoint')
      .setDesc('Backend API endpoint (e.g., http://localhost:8000/api/v1)')
      .addText(text => text
        .setPlaceholder('http://localhost:8000/api/v1')
        .setValue(this.plugin.settings.apiEndpoint)
        .onChange(async (value) => {
          this.plugin.settings.apiEndpoint = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('User Token')
      .setDesc('Your user authentication token')
      .addText(text => text
        .setPlaceholder('user_token')
        .setValue(this.plugin.settings.userToken)
        .onChange(async (value) => {
          this.plugin.settings.userToken = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Vault ID')
      .setDesc('Your vault identifier')
      .addText(text => text
        .setPlaceholder('vault_id')
        .setValue(this.plugin.settings.vaultId)
        .onChange(async (value) => {
          this.plugin.settings.vaultId = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Auto Sync')
      .setDesc('Automatically sync notes when modified')
      .addToggle(toggle => toggle
        .setValue(this.plugin.settings.autoSync)
        .onChange(async (value) => {
          this.plugin.settings.autoSync = value;
          await this.plugin.saveSettings();
          new Notice(`Auto sync ${value ? 'enabled' : 'disabled'}. Please reload the plugin.`);
        }));

    new Setting(containerEl)
      .setName('Privacy Mode')
      .setDesc('full: 전체 내용, summary: 요약만, metadata: 내용 제외')
      .addDropdown(drop => drop
        .addOptions({ full: 'Full', summary: 'Summary', metadata: 'Metadata only' })
        .setValue(this.plugin.settings.privacyMode)
        .onChange(async (value) => {
          this.plugin.settings.privacyMode = value as DidymosSettings['privacyMode'];
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Language')
      .setDesc('Interface language')
      .addDropdown(drop => drop
        .addOptions({ ko: 'Korean', en: 'English' })
        .setValue(this.plugin.settings.language)
        .onChange(async (value) => {
          this.plugin.settings.language = value as 'ko' | 'en';
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Daily usage budget')
      .setDesc('Number of sync/decision operations per day before warning')
      .addText(text => text
        .setValue(String(this.plugin.settings.usageBudgetPerDay))
        .onChange(async (value) => {
          const num = parseInt(value, 10);
          if (!isNaN(num) && num > 0) {
            this.plugin.settings.usageBudgetPerDay = num;
            await this.plugin.saveSettings();
          }
        }));

    new Setting(containerEl)
      .setName('Usage today')
      .setDesc(`${this.plugin.settings.usageUsedToday}/${this.plugin.settings.usageBudgetPerDay} (resets daily)`)
      .addButton(btn => btn.setButtonText('Reset now').onClick(async () => {
        this.plugin.settings.usageUsedToday = 0;
        this.plugin.settings.usageResetAt = new Date().toISOString().slice(0, 10);
        await this.plugin.saveSettings();
        new Notice('Usage reset for today.');
      }));

    new Setting(containerEl)
      .setName('Excluded folders')
      .setDesc('쉼표로 구분해 제외할 폴더 경로 입력 (예: Private/,Archive/)')
      .addText(text => text
        .setValue(this.plugin.settings.excludedFolders.join(','))
        .onChange(async (value) => {
          this.plugin.settings.excludedFolders = value
            .split(',')
            .map(v => v.trim())
            .filter(Boolean);
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Local mode (skip backend)')
      .setDesc('온톨로지를 로컬 파일로만 저장하고 백엔드로 보내지 않습니다.')
      .addToggle(toggle => toggle
        .setValue(this.plugin.settings.localMode)
        .onChange(async (value) => {
          this.plugin.settings.localMode = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Local OpenAI API Key')
      .setDesc('로컬 모드에서 온톨로지 추출 시 사용할 OpenAI 키')
      .addText(text => text
        .setPlaceholder('sk-...')
        .setValue(this.plugin.settings.localOpenAIApiKey)
        .onChange(async (value) => {
          this.plugin.settings.localOpenAIApiKey = value.trim();
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Auto export ontology after sync')
      .setDesc('동기화 후 자동으로 온톨로지 스냅샷을 Export Folder에 저장')
      .addToggle(toggle => toggle
        .setValue(this.plugin.settings.autoExportOntology)
        .onChange(async (value) => {
          this.plugin.settings.autoExportOntology = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Append ontology to note')
      .setDesc('스냅샷을 별도 파일 대신 노트 하단에 삽입합니다.')
      .addToggle(toggle => toggle
        .setValue(this.plugin.settings.appendOntologyToNote)
        .onChange(async (value) => {
          this.plugin.settings.appendOntologyToNote = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Ontology format')
      .setDesc('JSON으로 고정 (자동 처리 안전성)')
      .addDropdown(drop => drop
        .addOptions({ json: 'json' })
        .setValue('json')
        .onChange(async (_) => {
          this.plugin.settings.ontologyFormat = 'json';
          await this.plugin.saveSettings();
        }));
  }
}
