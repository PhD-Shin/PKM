import { App, Notice, TFile } from 'obsidian';
import { DidymosAPI, NotePayload } from '../api/client';
import { DidymosSettings } from '../settings';
import { DidymosContextView, DIDYMOS_CONTEXT_VIEW_TYPE } from '../views/contextView';

export class SyncService {
    private lastRealtimeSync: number = 0;

    constructor(
        private app: App,
        private settings: DidymosSettings,
        private api: DidymosAPI,
        private saveSettingsCallback: () => Promise<void>
    ) { }

    async syncNote(file: TFile): Promise<void> {
        if (!this.settings.userToken || !this.settings.vaultId) {
            new Notice('Please configure Didymos settings first');
            return;
        }
        this.ensureUsageReset();

        // Check excluded folders
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

            // Trigger Context Panel update if open
            const leaf = this.app.workspace.getLeavesOfType(DIDYMOS_CONTEXT_VIEW_TYPE)[0];
            if (leaf && leaf.view instanceof DidymosContextView) {
                await (leaf.view as DidymosContextView).updateContext(notePayload.note_id);
            }

        } catch (error: any) {
            console.error('Sync failed:', error);
            new Notice(`❌ Sync failed: ${error.message}`);
        }
    }

    async bulkProcessVault(): Promise<void> {
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

    checkRealtimeSyncCooldown(): boolean {
        const now = Date.now();
        const cooldownMs = this.settings.realtimeCooldownMinutes * 60 * 1000;
        if (now - this.lastRealtimeSync >= cooldownMs) {
            this.lastRealtimeSync = now;
            return true;
        }
        return false;
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

    // Helper to save settings back to plugin - simplistic approach
    // Ideally, settings management should be a separate service or passed as a callback
    private async saveSettings() {
        // In a real refactor, we might want to inject a 'SettingsManager'.
        // For now, we assume settings object is shared reference, but we can't easily persist it without the plugin instance.
        // However, `this.settings` is a reference to the settings object held by the plugin.
        // The plugin's `saveSettings` method calls `saveData(this.settings)`.
        // We can't call `plugin.saveData` from here unless we pass the plugin instance.
        // I will modify the constructor to accept a save callback or the plugin instance?
        // Passing the plugin instance causes circular dependency issues sometimes if not careful, but `DidymosPlugin` is the main class.
        // Let's rely on the fact that we modify the object reference, but we need to trigger the save.
        // I'll emit an event or just ignore the persistence for a second? No, usage tracking requires persistence.
        // I will pass a `saveSettings` callback to the constructor.
        // BUT, for now, let's assume we pass the plugin instance as 'any' or an interface to avoid circular deps.
        await this.saveSettingsCallback();
    }
}
