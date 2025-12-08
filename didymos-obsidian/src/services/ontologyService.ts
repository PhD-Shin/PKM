import { App, Notice, TFile } from 'obsidian';
import { DidymosAPI } from '../api/client';
import { DidymosSettings } from '../settings';

export class OntologyService {
    constructor(
        private app: App,
        private settings: DidymosSettings,
        private api: DidymosAPI
    ) { }

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

            // Prevent overwrite
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

        try {
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
        } catch (error: any) {
            console.error(error);
            new Notice(`❌ Local export failed: ${error.message}`);
        }
    }

    async ensureFolder(folder: string) {
        const exists = await this.app.vault.adapter.exists(folder);
        if (!exists) {
            await this.app.vault.createFolder(folder);
        }
    }

    buildOntologyPayload(context: any) {
        return {
            source: context?.note_id || "",
            topics: (context.topics || []).map((t: any) => t.name || t.id),
            projects: (context.projects || []).map((p: any) => p.name || p.id),
            tasks: (context.tasks || []).map((t: any) => t.title || t.id),
            related_notes: (context.related_notes || []).map((r: any) => r.note_id || r.path),
        };
    }

    stringifyOntology(payload: any): string {
        const fmt = this.settings.ontologyFormat;
        if (fmt === "json") {
            return JSON.stringify(payload, null, 2);
        }
        // naive yaml-ish serialization
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
}
