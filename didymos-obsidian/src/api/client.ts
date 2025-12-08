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
// Entity Graph Types (Knowledge Graph View)
// ============================================

export interface EntityNode {
  id: string;
  label: string;
  type: "Topic" | "Project" | "Person" | "Task";
  color: string;
  size: number;
  summary?: string;
  connections: number;
  connected_notes?: string[];
}

export interface EntityEdge {
  source: string;
  target: string;
  type: string;
  label?: string;
}

export interface EntityGraphData {
  status: string;
  node_count: number;
  edge_count: number;
  nodes: EntityNode[];
  edges: EntityEdge[];
  stats: {
    by_type: Record<string, number>;
  };
}

// ============================================
// Entity Cluster Types (2nd Brain View)
// ============================================

export interface EntityCluster {
  id: string;
  name: string;
  representative_uuid: string;
  entity_count: number;
  entity_uuids: string[];
  sample_entities: string[];
  type_distribution: Record<string, number>;
  internal_edges: number;
  cohesion_score: number;
  computed_at: string;
}

export interface EntityClusterEdge {
  from: string;
  to: string;
  weight: number;
  relation_type: string;
  label?: string;
}

export interface EntityClusterData {
  status: string;
  cluster_count: number;
  total_entities: number;
  clustered_entities: number;
  clusters: EntityCluster[];
  edges: EntityClusterEdge[];
  method: string;
  computed_at: string;
}

export interface EntityClusterDetail {
  id: string;
  name: string;
  representative_uuid: string;
  entity_count: number;
  entity_uuids: string[];
  sample_entities: string[];
  type_distribution: Record<string, number>;
  cohesion_score: number;
  computed_at: string;
  entities: Array<{
    uuid: string;
    name: string;
    summary: string;
    pkm_type: string;
    connections: number;
  }>;
  internal_edges: Array<{
    from: string;
    to: string;
    type?: string;  // RELATES_TO, BROADER, NARROWER
    fact: string;
    weight: number;
  }>;
  related_notes?: Array<{
    note_id: string;
    title: string;
    path: string;
    entity_uuids: string[];
    entity_names: string[];
    entity_count: number;
  }>;
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

  async deleteNote(noteId: string): Promise<{
    status: string;
    message: string;
    note_id: string;
    deleted_notes: number;
    orphans_cleaned: number;
  }> {
    const url = new URL(this.baseUrl(`/notes/delete/${encodeURIComponent(noteId)}`));
    url.searchParams.set("user_token", this.settings.userToken);
    url.searchParams.set("vault_id", this.settings.vaultId);

    const response = await fetch(url.toString(), { method: "DELETE" });

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

  /**
   * Entity Graph - Entity 노드와 RELATES_TO 관계를 직접 반환
   * 클러스터 대신 진정한 Knowledge Graph 시각화
   */
  async fetchEntityGraph(
    vaultId: string,
    options?: {
      limit?: number;
      minConnections?: number;
      includeNotes?: boolean;
    }
  ): Promise<EntityGraphData> {
    const url = new URL(this.baseUrl("/graph/vault/entities"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    if (options?.limit) {
      url.searchParams.set("limit", String(options.limit));
    }
    if (options?.minConnections !== undefined) {
      url.searchParams.set("min_connections", String(options.minConnections));
    }
    if (options?.includeNotes) {
      url.searchParams.set("include_notes", "true");
    }

    const response = await fetch(url.toString());
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

  // ============================================
  // Entity Cluster APIs (2nd Brain View)
  // ============================================

  /**
   * Entity 클러스터 조회 - 하이브리드 클러스터링
   * RELATES_TO 그래프 구조 + name_embedding 벡터 유사도 결합
   */
  async fetchEntityClusters(
    vaultId: string,
    options?: {
      minClusterSize?: number;
      resolution?: number;
      folderPrefix?: string;  // 폴더 필터 추가
    }
  ): Promise<EntityClusterData> {
    const url = new URL(this.baseUrl("/graph/vault/entity-clusters"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    if (options?.minClusterSize) {
      url.searchParams.set("min_cluster_size", String(options.minClusterSize));
    }
    if (options?.resolution) {
      url.searchParams.set("resolution", String(options.resolution));
    }
    if (options?.folderPrefix) {
      url.searchParams.set("folder_prefix", options.folderPrefix);
    }

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  /**
   * 특정 클러스터의 상세 정보 조회
   * entity_uuids를 직접 전달하여 정확한 클러스터 상세 정보를 가져옴
   */
  async fetchEntityClusterDetail(
    vaultId: string,
    clusterName: string,
    entityUuids: string[]
  ): Promise<{ status: string; cluster: EntityClusterDetail }> {
    const url = new URL(this.baseUrl("/graph/vault/entity-clusters/detail"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        cluster_name: clusterName,
        entity_uuids: entityUuids
      })
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  // ============================================
  // Entity-Note Graph API (2nd Brain 노트 연결 시각화)
  // ============================================

  /**
   * Entity-Note 연결 그래프
   * Entity를 통해 Note 간 연결을 보여줌
   */
  async fetchEntityNoteGraph(
    vaultId: string,
    options?: {
      folderPrefix?: string;
      limit?: number;
      minNoteConnections?: number;
    }
  ): Promise<EntityNoteGraphData> {
    const url = new URL(this.baseUrl("/graph/vault/entity-note-graph"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);



    if (options?.folderPrefix) {
      url.searchParams.set("folder_prefix", options.folderPrefix);
    }
    if (options?.limit) {
      url.searchParams.set("limit", String(options.limit));
    }
    if (options?.minNoteConnections) {
      url.searchParams.set("min_note_connections", String(options.minNoteConnections));
    }

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  // ============================================
  // Thinking Insights API (Palantir Foundry 스타일)
  // ============================================

  /**
   * 사고 패턴 인사이트
   * - 집중 영역, 브릿지 개념, 고립 영역, 탐구 제안
   */
  async fetchThinkingInsights(
    vaultId: string,
    options?: {
      folderPrefix?: string;
    }
  ): Promise<ThinkingInsightsData> {
    const url = new URL(this.baseUrl("/graph/vault/thinking-insights"));
    url.searchParams.set("vault_id", vaultId);
    url.searchParams.set("user_token", this.settings.userToken);

    if (options?.folderPrefix) {
      url.searchParams.set("folder_prefix", options.folderPrefix);
    }

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }
}

// ============================================
// Entity-Note Graph Types
// ============================================

export interface EntityNoteGraphEntity {
  id: string;
  name: string;
  summary: string;
  type: "Topic" | "Project" | "Person" | "Task";
  color: string;
  connected_notes: string[];
  note_count: number;
}

export interface EntityNoteGraphNote {
  id: string;
  title: string;
  path: string;
}

export interface NoteNoteEdge {
  from: string;
  to: string;
  shared_entities: string[];
  strength: number;
}

export interface EntityNoteGraphData {
  status: string;
  entity_count: number;
  note_count: number;
  edge_count: number;
  entities: EntityNoteGraphEntity[];
  notes: EntityNoteGraphNote[];
  entity_note_edges: Array<{ entity_id: string; note_id: string }>;
  note_note_edges: NoteNoteEdge[];
}

// ============================================
// Thinking Insights Types (Palantir Foundry Style)
// ============================================

export interface FocusArea {
  uuid: string;
  name: string;
  type: "Topic" | "Project" | "Person" | "Task";
  strength: number;
  notes: string[];
}

export interface BridgeConcept {
  uuid: string;
  name: string;
  connected_count: number;
  connects: string[];
  importance: number;
}

export interface IsolatedArea {
  uuid: string;
  name: string;
  note_count: number;
  relation_count: number;
  suggestion: string;
}

export interface ExplorationSuggestion {
  area1: string;
  area2: string;
  potential: string;
  reason: string;
}

// Time-based Trends Types
export interface TopicTrend {
  name: string;
  uuid: string;
  recent_count: number;
  older_count: number;
  total: number;
}

export interface TimeTrends {
  recent_topics: TopicTrend[];
  emerging_topics: TopicTrend[];
  declining_topics: TopicTrend[];
  stable_topics: TopicTrend[];
  trend_period: string;
}

// Knowledge Health Score Types
export interface HealthScore {
  overall: number;
  connection_density: number;
  isolation_ratio: number;
  completeness_score: number;
  metrics: {
    total_notes: number;
    connected_notes: number;
    avg_connections: number;
    max_connections: number;
  };
  recommendations: string[];
}


export interface PriorityTask {
  uuid: string;
  name: string;
  context: string;
  importance: number;
}

export interface ThinkingInsightsData {
  status: string;
  summary: {
    total_entities: number;
    total_notes: number;
    focus_count: number;
    bridge_count: number;
    isolated_count: number;
    health_score?: number;
  };
  type_distribution: Record<string, { entity_count: number; note_count: number }>;
  focus_areas: FocusArea[];
  bridge_concepts: BridgeConcept[];
  isolated_areas: IsolatedArea[];
  exploration_suggestions: ExplorationSuggestion[];
  time_trends?: TimeTrends;
  health_score?: HealthScore;
  priority_tasks?: PriorityTask[];
}
