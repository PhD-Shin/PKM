import { App, Notice, TFile } from 'obsidian';
import { DidymosAPI } from '../api/client';
import { DidymosSettings } from '../settings';
import { OntologyService } from './ontologyService';

export class DecisionService {
    constructor(
        private app: App,
        private settings: DidymosSettings,
        private api: DidymosAPI,
        private ontologyService: OntologyService,
        private usageCallback: () => { ensureReset: () => void; increment: () => void }
    ) { }

    async generateDecisionNote(file: TFile) {
        try {
            const usage = this.usageCallback();
            usage.ensureReset();
            usage.increment();

            const decisionFolder = this.settings.decisionFolder || "Didymos/Decisions";
            await this.ontologyService.ensureFolder(decisionFolder);

            // Fetch data
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

            // Ontology block
            const payload = this.ontologyService.buildOntologyPayload(context);
            lines.push("## Ontology (json)");
            lines.push("```json");
            lines.push(this.ontologyService.stringifyOntology(payload));
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
}
