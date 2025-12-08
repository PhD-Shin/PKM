import { Plugin, Notice, TFile, PluginSettingTab, App, Setting, WorkspaceLeaf } from 'obsidian';
import { DidymosAPI } from './api/client';
import { DidymosContextView, DIDYMOS_CONTEXT_VIEW_TYPE } from './views/contextView';
import { DidymosGraphView, DIDYMOS_GRAPH_VIEW_TYPE } from './views/graphView';
import { DidymosTaskView, DIDYMOS_TASK_VIEW_TYPE } from './views/taskView';
import { DidymosReviewView, DIDYMOS_REVIEW_VIEW_TYPE } from './views/reviewView';
import { DidymosDecisionView, DIDYMOS_DECISION_VIEW_TYPE } from './views/decisionView';
import { DidymosInsightsView, INSIGHTS_VIEW_TYPE } from './views/insightsView';
import { DidymosUnifiedView, UNIFIED_VIEW_TYPE } from './views/unifiedView';
import { DidymosSettings, DEFAULT_SETTINGS } from './settings';
import { TemplateService } from './services/templateService';
import { SyncService } from './services/syncService';
import { OntologyService } from './services/ontologyService';
import { DecisionService } from './services/decisionService';
import { OnboardingModal } from './modals/onboardingModal';
import { DidymosControlPanelView, CONTROL_PANEL_VIEW_TYPE, ControlPanelAction } from './views/controlPanelView';

export default class DidymosPlugin extends Plugin {
  settings: DidymosSettings;
  api: DidymosAPI;
  templateService: TemplateService;
  syncService: SyncService;
  ontologyService: OntologyService;
  decisionService: DecisionService;
  hourlyInterval: number | null = null;

  async onload() {
    await this.loadSettings();
    await this.ensureDefaultIdentifiers();
    this.ensureUsageReset();
    this.api = new DidymosAPI(this.settings);
    this.templateService = new TemplateService(this.app);

    // Initialize Services
    this.syncService = new SyncService(
      this.app,
      this.settings,
      this.api,
      async () => await this.saveSettings()
    );

    this.ontologyService = new OntologyService(
      this.app,
      this.settings,
      this.api
    );

    this.decisionService = new DecisionService(
      this.app,
      this.settings,
      this.api,
      this.ontologyService,
      () => ({
        ensureReset: () => this.ensureUsageReset(),
        increment: () => this.incrementUsage()
      })
    );

    // Settings tab
    this.addSettingTab(new DidymosSettingTab(this.app, this));

    // Register Views
    this.registerView(DIDYMOS_CONTEXT_VIEW_TYPE, (leaf) => new DidymosContextView(leaf, this.settings));
    this.registerView(DIDYMOS_GRAPH_VIEW_TYPE, (leaf) => new DidymosGraphView(leaf, this.settings, this));
    this.registerView(DIDYMOS_TASK_VIEW_TYPE, (leaf) => new DidymosTaskView(leaf, this.settings));
    this.registerView(DIDYMOS_REVIEW_VIEW_TYPE, (leaf) => new DidymosReviewView(leaf, this.settings));
    this.registerView(DIDYMOS_DECISION_VIEW_TYPE, (leaf) => new DidymosDecisionView(leaf, this.settings));
    this.registerView(INSIGHTS_VIEW_TYPE, (leaf) => new DidymosInsightsView(leaf, this.settings));
    this.registerView(UNIFIED_VIEW_TYPE, (leaf) => new DidymosUnifiedView(leaf, this.settings));
    this.registerView(
      CONTROL_PANEL_VIEW_TYPE,
      (leaf) => {
        const actions = this.getControlPanelActions();
        return new DidymosControlPanelView(leaf, actions, this, this.settings);
      }
    );

    // Ribbon Icon
    this.addRibbonIcon('layout-dashboard', 'Open Didymos Control Panel', async () => {
      await this.activateControlPanelView();
    });

    // Commands
    this.addCommand({
      id: 'open-control-panel',
      name: 'Open Didymos Control Panel',
      callback: async () => {
        await this.activateControlPanelView();
      }
    });

    // Bulk Process on Start
    if (this.settings.bulkProcessOnStart) {
      await this.syncService.bulkProcessVault();
    }

    // Auto-sync
    if (this.settings.autoSync && this.settings.syncMode === 'realtime' && this.settings.premiumRealtime) {
      this.registerEvent(
        this.app.vault.on('modify', async (file) => {
          if (file instanceof TFile && file.extension === 'md') {
            if (this.syncService.checkRealtimeSyncCooldown()) {
              await this.syncService.syncNote(file);
            }
          }
        })
      );
    }

    // Auto-delete
    this.registerEvent(
      this.app.vault.on('delete', async (file) => {
        if (file instanceof TFile && file.extension === 'md') {
          try {
            console.log(`🗑️ File deleted in Obsidian: ${file.path}`);
            await this.api.deleteNote(file.path);
            console.log(`✅ Note deleted from Neo4j: ${file.path}`);
          } catch (error) {
            console.error(`❌ Failed to delete note from Neo4j: ${file.path}`, error);
          }
        }
      })
    );

    // Hourly Sync
    if (this.settings.autoSync && this.settings.syncMode === 'hourly') {
      this.hourlyInterval = window.setInterval(async () => {
        await this.syncService.bulkProcessVault();
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

  // Views Activation (Delegation)
  async activateUnifiedView() { this.activateView(UNIFIED_VIEW_TYPE); }
  async activateContextView() { this.activateView(DIDYMOS_CONTEXT_VIEW_TYPE); }
  async activateGraphView() { this.activateView(DIDYMOS_GRAPH_VIEW_TYPE); }
  async activateTaskView() { this.activateView(DIDYMOS_TASK_VIEW_TYPE); }
  async activateReviewView() {
    await this.activateView(DIDYMOS_REVIEW_VIEW_TYPE);
    const leaf = this.app.workspace.getLeavesOfType(DIDYMOS_REVIEW_VIEW_TYPE)[0];
    if (leaf && leaf.view instanceof DidymosReviewView) {
      await (leaf.view as DidymosReviewView).renderReview();
    }
  }
  async activateDecisionView() { this.activateView(DIDYMOS_DECISION_VIEW_TYPE); }
  async activateInsightsView() { this.activateView(INSIGHTS_VIEW_TYPE); }

  async activateControlPanelView() {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = null;
    const leaves = workspace.getLeavesOfType(CONTROL_PANEL_VIEW_TYPE);
    if (leaves.length > 0) {
      leaf = leaves[0];
    } else {
      leaf = workspace.getRightLeaf(false);
      if (leaf) await leaf.setViewState({ type: CONTROL_PANEL_VIEW_TYPE, active: true });
    }
    if (leaf) workspace.revealLeaf(leaf);
  }

  private async activateView(type: string) {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(type)[0] ?? null;
    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (leaf) await leaf.setViewState({ type: type, active: true });
    }
    if (leaf) workspace.revealLeaf(leaf);
  }

  showOnboarding() {
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

  getControlPanelActions(): ControlPanelAction[] {
    return [
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
        id: 'decision-note',
        name: 'Decision Note',
        description: '현재 컨텍스트로 의사결정 노트 생성',
        icon: '📝',
        category: 'actions',
        callback: async () => {
          const file = this.app.workspace.getActiveFile();
          if (file) await this.decisionService.generateDecisionNote(file);
          else new Notice("No active file");
        }
      },
      {
        id: 'export-ontology',
        name: 'Export Ontology',
        description: '온톨로지 스냅샷 추출 (Markdown)',
        icon: '📤',
        category: 'actions',
        callback: async () => {
          const file = this.app.workspace.getActiveFile();
          if (file) await this.ontologyService.exportOntologySnapshot(file);
          else new Notice("No active file");
        }
      }
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
    containerEl.createEl('h2', { text: 'Didymos Settings' });

    new Setting(containerEl)
      .setName('Vault ID')
      .setDesc('Unique identifier for this vault')
      .addText(text => text
        .setPlaceholder('Enter vault ID')
        .setValue(this.plugin.settings.vaultId)
        .onChange(async (value) => {
          this.plugin.settings.vaultId = value;
          await this.plugin.saveSettings();
        }));

    // ... (Other settings can be added here as needed)
  }
}
