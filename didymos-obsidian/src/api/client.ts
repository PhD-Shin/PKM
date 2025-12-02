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
    [key: string]: any;  // 추가 속성 허용
  }>;
  edges: Array<{
    from: string;
    to: string;
    label: string;
    arrows: any;  // string 또는 object 허용
    color: any;   // string 또는 object 허용
    dashes?: boolean;
    width?: number;
    font?: any;
    smooth?: any;
    [key: string]: any;  // 추가 속성 허용
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

export interface HubEntity {
  id: string;
  name: string;
  centrality: number;  // 0~1, 그래프 중심성 점수
}

export interface StaleKnowledge {
  uuid: string;
  name: string;
  summary: string | null;
  created_at: string;
  last_accessed: string | null;
  days_since_access: number;
  priority: "high" | "medium";
}

export interface StaleKnowledgeResponse {
  status: string;
  criteria: {
    min_days_old: number;
    cutoff_date: string;
  };
  stale_knowledge: StaleKnowledge[];
  total_count: number;
  message: string;
}

// ============================================
// GraphRAG Search Types (Phase 12-14)
// ============================================

export type SearchMode = "vector" | "hybrid" | "text2cypher" | "agentic";

export interface SearchResult {
  note_id: string;
  title: string;
  path: string;
  content: string;
  updated_at: string;
  score?: number;
  mentioned_entities?: Array<{
    id: string;
    name: string;
    type: string;
  }>;
  hierarchy?: {
    broader: Array<{ id: string; name: string }>;
    narrower: Array<{ id: string; name: string }>;
  };
  related_entities?: Array<{ id: string; name: string }>;
}

export interface SearchResponse {
  status: string;
  mode: string;
  query: string;
  count: number;
  results: SearchResult[];
  generated_cypher?: string;  // text2cypher 모드
  selected_retriever?: string;  // agentic 모드
  reasoning?: string;  // agentic 모드
  fallback?: boolean;  // agentic fallback 여부
}

export interface SearchStatusResponse {
  status: string;
  message: string;
  available_modes: SearchMode[];
  features?: Record<string, string>;
  tools_retriever_available?: boolean;
}

export interface ClusterNode {
  id: string;
  name: string;
  level: number;
  node_count: number;
  summary?: string;
  key_insights: string[];
  sample_entities?: string[];
  sample_notes?: string[];
  note_ids?: string[];
  recent_updates?: number;
  importance_score: number;
  last_updated: string;
  last_computed: string;
  clustering_method: string;
  is_manual: boolean;
  contains_types: Record<string, number>;
  hub_entities?: HubEntity[];  // 그래프 중심성 기반 허브 엔티티
}

export interface ClusteredGraphData {
  status: string;
  level: number;
  cluster_count: number;
  total_nodes: number;
  clusters: ClusterNode[];
  edges: Array<{
    from: string;
    to: string;
    relation_type: string;
    weight: number;
  }>;
  last_computed: string;
  computation_method: string;
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

  async fetchClusteredGraph(
    vaultId: string,
    options?: {
      forceRecompute?: boolean;
      targetClusters?: number;
      includeLLM?: boolean;
      method?: "semantic" | "type_based" | "auto";
      folderPrefix?: string;  // 폴더 필터 추가
    }
  ): Promise<ClusteredGraphData> {
    const url = new URL(this.baseUrl("/graph/vault/clustered"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    if (options?.forceRecompute) {
      url.searchParams.set("force_recompute", "true");
    }
    if (options?.targetClusters) {
      url.searchParams.set("target_clusters", String(options.targetClusters));
    }
    if (options?.includeLLM) {
      url.searchParams.set("include_llm", "true");
    }
    if (options?.method) {
      url.searchParams.set("method", options.method);
    }
    if (options?.folderPrefix) {
      url.searchParams.set("folder_prefix", options.folderPrefix);
    }

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  async fetchVaultFolders(vaultId: string): Promise<{
    status: string;
    vault_id: string;
    total_folders: number;
    folders: Array<{ folder: string; note_count: number }>;
  }> {
    const url = new URL(this.baseUrl("/graph/vault/folders"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  async invalidateClusterCache(vaultId: string): Promise<void> {
    const url = new URL(this.baseUrl("/graph/vault/clustered/invalidate"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    const response = await fetch(url.toString(), { method: "POST" });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
  }

  async resetVaultEntities(vaultId: string): Promise<{
    status: string;
    message: string;
    deleted_entities: number;
    orphans_deleted: number;
    relations_deleted: number;
  }> {
    const url = new URL(this.baseUrl("/graph/vault/reset-entities"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    const response = await fetch(url.toString(), { method: "POST" });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  // ============================================
  // Temporal Knowledge Graph APIs
  // ============================================

  async fetchStaleKnowledge(days: number = 30, limit: number = 20): Promise<StaleKnowledgeResponse> {
    const url = new URL(this.baseUrl("/temporal/insights/stale"));
    url.searchParams.set("days", String(days));
    url.searchParams.set("limit", String(limit));

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  async markKnowledgeReviewed(uuid: string): Promise<{
    status: string;
    message: string;
    entity: { uuid: string; name: string; last_accessed: string };
  }> {
    const response = await fetch(this.baseUrl("/temporal/insights/mark-reviewed"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uuid }),
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  async markKnowledgeReviewedBatch(uuids: string[]): Promise<{
    status: string;
    message: string;
    updated_count: number;
    requested_count: number;
  }> {
    const response = await fetch(this.baseUrl("/temporal/insights/mark-reviewed-batch"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(uuids),
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  // ============================================
  // GraphRAG Search APIs (Phase 12-14)
  // ============================================

  /**
   * 통합 검색 API
   * @param query 검색 쿼리
   * @param mode 검색 모드 (vector, hybrid, text2cypher, agentic)
   * @param topK 반환할 결과 수
   */
  async search(
    query: string,
    mode: SearchMode = "hybrid",
    topK: number = 10
  ): Promise<SearchResponse> {
    const response = await fetch(this.baseUrl("/search"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        mode,
        top_k: topK,
        vault_id: this.settings.vaultId,
      }),
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  /**
   * 벡터 유사도 검색
   * 노트 임베딩 기반 시맨틱 검색
   */
  async searchVector(query: string, topK: number = 10): Promise<SearchResponse> {
    const url = new URL(this.baseUrl("/search/vector"));
    url.searchParams.set("query", query);
    url.searchParams.set("top_k", String(topK));
    url.searchParams.set("vault_id", this.settings.vaultId);

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  /**
   * 하이브리드 검색 (벡터 + 그래프 컨텍스트)
   * 권장 검색 모드: 벡터 검색 + SKOS 계층 관계 확장
   */
  async searchHybrid(query: string, topK: number = 10): Promise<SearchResponse> {
    const url = new URL(this.baseUrl("/search/hybrid"));
    url.searchParams.set("query", query);
    url.searchParams.set("top_k", String(topK));
    url.searchParams.set("vault_id", this.settings.vaultId);

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  /**
   * 자연어 → Cypher 검색
   * 자연어 질문을 Cypher 쿼리로 자동 변환
   */
  async searchText2Cypher(query: string): Promise<SearchResponse> {
    const url = new URL(this.baseUrl("/search/text2cypher"));
    url.searchParams.set("query", query);
    url.searchParams.set("vault_id", this.settings.vaultId);

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  /**
   * Agentic RAG 검색 (Phase 14)
   * LLM이 질문을 분석하고 최적의 retriever를 자동 선택
   */
  async searchAgentic(query: string): Promise<SearchResponse> {
    const url = new URL(this.baseUrl("/search/agentic"));
    url.searchParams.set("query", query);
    url.searchParams.set("vault_id", this.settings.vaultId);

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  /**
   * 검색 서비스 상태 확인
   */
  async getSearchStatus(): Promise<SearchStatusResponse> {
    const url = new URL(this.baseUrl("/search/status"));

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }
}
