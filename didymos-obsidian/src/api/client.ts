import { DidymosSettings } from "../settings";

export interface ContextData {
  topics: Array<{
    id: string;
    name: string;
    importance_score: number;
    mention_count: number;
  }>;
  projects: Array<{
    id: string;
    name: string;
    status: string;
    updated_at: string;
  }>;
  tasks: Array<{
    id: string;
    title: string;
    status: string;
    priority: string;
  }>;
  related_notes: Array<{
    note_id: string;
    title: string;
    path: string;
    similarity: number;
    reason: string;
  }>;
}

export interface NotePayload {
  note_id: string;
  title: string;
  path: string;
  content: string;
  yaml: Record<string, unknown>;
  tags: string[];
  links: string[];
  created_at: string;
  updated_at: string;
}

export interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    shape: string;
    color: any;
    size: number;
    group: string;
  }>;
  edges: Array<{
    from: string;
    to: string;
    label: string;
    arrows: string;
    color: string;
    dashes?: boolean;
  }>;
}

export interface TaskData {
  id: string;
  title: string;
  status: string;
  priority: string;
  note_id: string;
  note_title: string;
}

export interface NewTopicOut {
  name: string;
  mention_count: number;
  first_seen: string;
}

export interface ForgottenProjectOut {
  name: string;
  status: string;
  last_updated: string;
  days_inactive: number;
}

export interface OverdueTaskOut {
  id: string;
  title: string;
  priority: string;
  note_title: string;
}

export interface ActiveNoteOut {
  title: string;
  path: string;
  update_count: number;
}

export interface WeeklyReviewResponse {
  new_topics: NewTopicOut[];
  forgotten_projects: ForgottenProjectOut[];
  overdue_tasks: OverdueTaskOut[];
  most_active_notes: ActiveNoteOut[];
}

export interface WeeklyReviewRecord {
  id: string;
  vault_id: string;
  created_at: string;
  summary: any;
}

export class DidymosAPI {
  settings: DidymosSettings;

  constructor(settings: DidymosSettings) {
    this.settings = settings;
  }

  private baseUrl(path: string): string {
    const base = this.settings.apiEndpoint.replace(/\/$/, "");
    return `${base}${path}`;
  }

  async syncNote(note: NotePayload, privacyMode: string = "full"): Promise<any> {
    const payload = {
      user_token: this.settings.userToken,
      vault_id: this.settings.vaultId,
      note,
      privacy_mode: privacyMode,
    };

    const response = await fetch(this.baseUrl("/notes/sync"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async fetchContext(noteId: string): Promise<ContextData> {
    const url = new URL(this.baseUrl(`/notes/context/${encodeURIComponent(noteId)}`));
    url.searchParams.set("user_token", this.settings.userToken);

    const response = await fetch(url.toString());

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async fetchGraph(noteId: string, hops: number = 1): Promise<GraphData> {
    const url = new URL(this.baseUrl(`/notes/graph/${encodeURIComponent(noteId)}`));
    url.searchParams.set("user_token", this.settings.userToken);
    url.searchParams.set("hops", String(hops));

    const response = await fetch(url.toString());

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async listTasks(
    vaultId: string,
    status?: string,
    priority?: string
  ): Promise<TaskData[]> {
    const url = new URL(this.baseUrl("/tasks/list"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);
    if (status) url.searchParams.set("status", status);
    if (priority) url.searchParams.set("priority", priority);

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  async updateTask(
    taskId: string,
    updates: { status?: string; priority?: string }
  ): Promise<void> {
    const url = new URL(this.baseUrl(`/tasks/${encodeURIComponent(taskId)}`));
    url.searchParams.set("user_token", this.settings.userToken);

    const response = await fetch(url.toString(), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);
  }

  async fetchWeeklyReview(vaultId: string): Promise<WeeklyReviewResponse> {
    const url = new URL(this.baseUrl("/review/weekly"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  async saveWeeklyReview(vaultId: string): Promise<{ review_id: string; review: WeeklyReviewResponse }> {
    const url = new URL(this.baseUrl("/review/weekly/save"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    const response = await fetch(url.toString(), { method: "POST" });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  async fetchReviewHistory(vaultId: string, limit = 5): Promise<WeeklyReviewRecord[]> {
    const url = new URL(this.baseUrl("/review/history"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);
    url.searchParams.set("limit", String(limit));

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }
}
