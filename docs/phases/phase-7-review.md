# Phase 7: Weekly Review

> 주간 리뷰 자동 생성

**예상 시간**: 3~4시간  
**난이도**: ⭐⭐⭐☆☆

---

## 목표

- `/review/weekly` API 구현
- 새 Topics 탐지 (최근 7일)
- 잊힌 Projects 탐지 (14일 이상 업데이트 없음)
- 미완료 Tasks 목록
- Weekly Review Panel UI

---

## Part 1: 백엔드 Review API 구현

### Step 7-1: Review 스키마 정의

파일 생성: `didymos-backend/app/schemas/review.py`

```python
"""
Review 관련 Pydantic 스키마
"""
from typing import List
from pydantic import BaseModel


class NewTopicOut(BaseModel):
    name: str
    mention_count: int
    first_seen: str


class ForgottenProjectOut(BaseModel):
    name: str
    status: str
    last_updated: str
    days_inactive: int


class OverdueTaskOut(BaseModel):
    id: str
    title: str
    priority: str
    note_title: str


class ActiveNoteOut(BaseModel):
    title: str
    path: str
    update_count: int


class WeeklyReviewResponse(BaseModel):
    new_topics: List[NewTopicOut]
    forgotten_projects: List[ForgottenProjectOut]
    overdue_tasks: List[OverdueTaskOut]
    most_active_notes: List[ActiveNoteOut]
```

---

### Step 7-2: Review 서비스 작성

파일 생성: `didymos-backend/app/services/review_service.py`

```python
"""
Weekly Review 서비스
"""
from neo4j import Driver
from typing import List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_weekly_review(driver: Driver, vault_id: str) -> Dict:
    """
    주간 리뷰 데이터 생성
    """
    return {
        "new_topics": get_new_topics(driver, vault_id, days=7),
        "forgotten_projects": get_forgotten_projects(driver, vault_id, days=14),
        "overdue_tasks": get_overdue_tasks(driver, vault_id),
        "most_active_notes": get_most_active_notes(driver, vault_id, days=7)
    }


def get_new_topics(driver: Driver, vault_id: str, days: int) -> List[Dict]:
    """
    최근 N일 내 새로 등장한 Topics
    """
    try:
        with driver.session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            result = session.run(
                """
                MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
                -[:MENTIONS]->(t:Topic)
                WHERE t.first_seen >= datetime($cutoff_date)
                WITH t, COUNT(n) AS mention_count
                RETURN 
                    t.name AS name,
                    mention_count,
                    toString(t.first_seen) AS first_seen
                ORDER BY mention_count DESC
                LIMIT 10
                """,
                vault_id=vault_id,
                cutoff_date=cutoff_date.isoformat()
            )
            
            topics = []
            for record in result:
                topics.append({
                    "name": record["name"],
                    "mention_count": record["mention_count"],
                    "first_seen": record.get("first_seen", "")
                })
            
            logger.info(f"Found {len(topics)} new topics")
            return topics
            
    except Exception as e:
        logger.error(f"Error getting new topics: {e}")
        return []


def get_forgotten_projects(driver: Driver, vault_id: str, days: int) -> List[Dict]:
    """
    N일 이상 업데이트 없는 active Projects
    """
    try:
        with driver.session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            result = session.run(
                """
                MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
                -[:RELATES_TO_PROJECT]->(p:Project)
                WHERE p.status = 'active'
                WITH p, MAX(n.updated_at) AS last_note_update
                WHERE last_note_update < datetime($cutoff_date)
                RETURN 
                    p.name AS name,
                    p.status AS status,
                    toString(last_note_update) AS last_updated,
                    duration.inDays(last_note_update, datetime()).days AS days_inactive
                ORDER BY days_inactive DESC
                LIMIT 5
                """,
                vault_id=vault_id,
                cutoff_date=cutoff_date.isoformat()
            )
            
            projects = []
            for record in result:
                projects.append({
                    "name": record["name"],
                    "status": record["status"],
                    "last_updated": record.get("last_updated", ""),
                    "days_inactive": record.get("days_inactive", 0)
                })
            
            logger.info(f"Found {len(projects)} forgotten projects")
            return projects
            
    except Exception as e:
        logger.error(f"Error getting forgotten projects: {e}")
        return []


def get_overdue_tasks(driver: Driver, vault_id: str) -> List[Dict]:
    """
    미완료 Tasks (todo 또는 in_progress)
    """
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
                -[:CONTAINS_TASK]->(t:Task)
                WHERE t.status IN ['todo', 'in_progress']
                RETURN 
                    t.id AS id,
                    t.title AS title,
                    t.priority AS priority,
                    n.title AS note_title
                ORDER BY 
                    CASE t.priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END,
                    t.created_at ASC
                LIMIT 10
                """,
                vault_id=vault_id
            )
            
            tasks = []
            for record in result:
                tasks.append({
                    "id": record["id"],
                    "title": record["title"],
                    "priority": record.get("priority", "medium"),
                    "note_title": record["note_title"]
                })
            
            logger.info(f"Found {len(tasks)} overdue tasks")
            return tasks
            
    except Exception as e:
        logger.error(f"Error getting overdue tasks: {e}")
        return []


def get_most_active_notes(driver: Driver, vault_id: str, days: int) -> List[Dict]:
    """
    최근 N일 내 가장 많이 업데이트된 노트
    """
    try:
        with driver.session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            result = session.run(
                """
                MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
                WHERE n.updated_at >= datetime($cutoff_date)
                WITH n, COUNT(*) AS update_count
                RETURN 
                    n.title AS title,
                    n.path AS path,
                    update_count
                ORDER BY update_count DESC
                LIMIT 5
                """,
                vault_id=vault_id,
                cutoff_date=cutoff_date.isoformat()
            )
            
            notes = []
            for record in result:
                notes.append({
                    "title": record["title"],
                    "path": record["path"],
                    "update_count": record.get("update_count", 1)
                })
            
            logger.info(f"Found {len(notes)} active notes")
            return notes
            
    except Exception as e:
        logger.error(f"Error getting active notes: {e}")
        return []
```

---

### Step 7-3: Review API 라우터

파일 생성: `didymos-backend/app/api/routes_review.py`

```python
"""
Review API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status
import logging

from app.schemas.review import WeeklyReviewResponse
from app.db.neo4j import get_neo4j_driver
from app.services.review_service import get_weekly_review

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])


def get_user_id_from_token(token: str) -> str:
    return token


@router.get("/weekly", response_model=WeeklyReviewResponse)
async def weekly_review_endpoint(vault_id: str, user_token: str):
    """
    주간 리뷰 조회
    """
    try:
        driver = get_neo4j_driver()
        user_id = get_user_id_from_token(user_token)
        
        logger.info(f"Getting weekly review for vault: {vault_id}")
        
        review = get_weekly_review(driver, vault_id)
        
        return WeeklyReviewResponse(**review)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

파일 수정: `didymos-backend/app/main.py`

```python
from app.api import routes_notes, routes_tasks, routes_review

app.include_router(routes_review.router, prefix=settings.api_prefix)
```

---

### Step 7-4: API 테스트

Swagger UI에서 테스트:

1. `/api/v1/review/weekly` 펼치기
2. `vault_id`: `test_vault`
3. `user_token`: `test_user_001`
4. "Execute" 클릭

---

## Part 2: Obsidian 플러그인 Review Panel

### Step 7-5: API 클라이언트 확장

파일 수정: `didymos-obsidian/src/api/client.ts`

```typescript
export interface WeeklyReviewData {
  new_topics: Array<{
    name: string;
    mention_count: number;
    first_seen: string;
  }>;
  forgotten_projects: Array<{
    name: string;
    status: string;
    last_updated: string;
    days_inactive: number;
  }>;
  overdue_tasks: Array<{
    id: string;
    title: string;
    priority: string;
    note_title: string;
  }>;
  most_active_notes: Array<{
    title: string;
    path: string;
    update_count: number;
  }>;
}
```

메소드 추가:

```typescript
async fetchWeeklyReview(vaultId: string): Promise<WeeklyReviewData> {
  const url = new URL(`${this.settings.apiBaseUrl}/review/weekly`);
  url.searchParams.set("vault_id", vaultId);
  url.searchParams.set("user_token", this.settings.userToken);

  try {
    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch weekly review:", error);
    throw error;
  }
}
```

---

### Step 7-6: Review View 구현

파일 생성: `didymos-obsidian/src/views/reviewView.ts`

```typescript
import { ItemView, WorkspaceLeaf } from "obsidian";
import { DidymosSettings } from "../settings";
import { DidymosAPI, WeeklyReviewData } from "../api/client";

export const CAIRN_REVIEW_VIEW_TYPE = "didymos-review-view";

export class DidymosReviewView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return CAIRN_REVIEW_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Review";
  }

  getIcon(): string {
    return "calendar-check";
  }

  async onOpen() {
    await this.renderReview();
  }

  async renderReview() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("didymos-review-container");

    // Header
    const header = container.createEl("div", { cls: "didymos-review-header" });
    header.createEl("h2", { text: "📅 Weekly Review" });

    const dateStr = new Date().toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
    header.createEl("p", {
      text: dateStr,
      cls: "didymos-review-date",
    });

    // Refresh button
    const refreshBtn = header.createEl("button", {
      text: "🔄 Refresh",
      cls: "didymos-review-refresh",
    });
    refreshBtn.addEventListener("click", async () => {
      await this.renderReview();
    });

    try {
      // Loading
      const loading = container.createEl("div", {
        text: "Loading review...",
        cls: "didymos-review-loading",
      });

      // Fetch review data
      const review = await this.api.fetchWeeklyReview(this.settings.vaultId);

      loading.remove();

      // New Topics
      this.renderNewTopics(container, review.new_topics);

      // Forgotten Projects
      this.renderForgottenProjects(container, review.forgotten_projects);

      // Overdue Tasks
      this.renderOverdueTasks(container, review.overdue_tasks);

      // Most Active Notes
      this.renderActiveNotes(container, review.most_active_notes);
    } catch (error) {
      container.createEl("div", {
        text: `❌ Failed to load review: ${error.message}`,
        cls: "didymos-review-error",
      });
    }
  }

  renderNewTopics(container: HTMLElement, topics: WeeklyReviewData["new_topics"]) {
    if (topics.length === 0) return;

    const section = container.createEl("div", { cls: "didymos-review-section" });
    section.createEl("h3", { text: `✨ New Topics (${topics.length})` });

    const list = section.createEl("ul");
    topics.forEach((topic) => {
      const li = list.createEl("li");
      li.createEl("span", {
        text: topic.name,
        cls: "didymos-review-topic-name",
      });
      li.createEl("span", {
        text: `(${topic.mention_count}x)`,
        cls: "didymos-review-count",
      });
    });
  }

  renderForgottenProjects(
    container: HTMLElement,
    projects: WeeklyReviewData["forgotten_projects"]
  ) {
    if (projects.length === 0) return;

    const section = container.createEl("div", { cls: "didymos-review-section" });
    section.createEl("h3", { text: `😴 Forgotten Projects (${projects.length})` });

    const list = section.createEl("ul");
    projects.forEach((project) => {
      const li = list.createEl("li");
      li.createEl("span", {
        text: project.name,
        cls: "didymos-review-project-name",
      });
      li.createEl("span", {
        text: `${project.days_inactive} days ago`,
        cls: "didymos-review-days",
      });
    });
  }

  renderOverdueTasks(container: HTMLElement, tasks: WeeklyReviewData["overdue_tasks"]) {
    if (tasks.length === 0) return;

    const section = container.createEl("div", { cls: "didymos-review-section" });
    section.createEl("h3", { text: `⚠️ Pending Tasks (${tasks.length})` });

    const list = section.createEl("ul");
    tasks.forEach((task) => {
      const li = list.createEl("li");
      li.createEl("span", {
        text: task.title,
        cls: "didymos-review-task-title",
      });

      const priorityClass =
        task.priority === "high"
          ? "priority-high"
          : task.priority === "medium"
          ? "priority-medium"
          : "priority-low";

      li.createEl("span", {
        text: `[${task.priority[0].toUpperCase()}]`,
        cls: `didymos-review-priority ${priorityClass}`,
      });
    });
  }

  renderActiveNotes(container: HTMLElement, notes: WeeklyReviewData["most_active_notes"]) {
    if (notes.length === 0) return;

    const section = container.createEl("div", { cls: "didymos-review-section" });
    section.createEl("h3", { text: `🔥 Most Active Notes (${notes.length})` });

    const list = section.createEl("ul");
    notes.forEach((note, index) => {
      const li = list.createEl("li");
      li.createEl("span", {
        text: `${index + 1}.`,
        cls: "didymos-review-number",
      });

      const link = li.createEl("a", {
        text: note.title,
        cls: "didymos-review-note-link",
      });
      link.addEventListener("click", (e) => {
        e.preventDefault();
        this.app.workspace.openLinkText(note.path, "", false);
      });

      li.createEl("span", {
        text: `(${note.update_count} updates)`,
        cls: "didymos-review-count",
      });
    });
  }
}
```

---

### Step 7-7: CSS 스타일링

파일 수정: `didymos-obsidian/styles.css`

추가:

```css
/* Review Panel */
.didymos-review-container {
  padding: 16px;
}

.didymos-review-header {
  margin-bottom: 24px;
}

.didymos-review-header h2 {
  margin: 0;
}

.didymos-review-date {
  color: var(--text-muted);
  font-size: 0.9em;
  margin: 4px 0 0 0;
}

.didymos-review-refresh {
  margin-top: 12px;
  padding: 6px 12px;
  border: 1px solid var(--background-modifier-border);
  border-radius: 4px;
  background-color: var(--interactive-normal);
  color: var(--text-normal);
  cursor: pointer;
}

.didymos-review-refresh:hover {
  background-color: var(--interactive-hover);
}

.didymos-review-loading {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}

.didymos-review-error {
  color: var(--text-error);
  background-color: var(--background-modifier-error);
  padding: 16px;
  border-radius: 8px;
}

.didymos-review-section {
  margin-bottom: 32px;
}

.didymos-review-section h3 {
  margin: 0 0 16px 0;
  font-size: 1.2em;
  border-bottom: 2px solid var(--background-modifier-border);
  padding-bottom: 8px;
}

.didymos-review-section ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.didymos-review-section li {
  padding: 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.didymos-review-count,
.didymos-review-days {
  color: var(--text-muted);
  font-size: 0.9em;
}

.didymos-review-note-link {
  color: var(--link-color);
  text-decoration: none;
  cursor: pointer;
}

.didymos-review-note-link:hover {
  text-decoration: underline;
}

.didymos-review-number {
  font-weight: bold;
  color: var(--text-muted);
  min-width: 20px;
}
```

---

### Step 7-8: 메인 플러그인에 Review View 등록

파일 수정: `didymos-obsidian/main.ts`

import 추가:

```typescript
import { DidymosReviewView, CAIRN_REVIEW_VIEW_TYPE } from "./src/views/reviewView";
```

등록:

```typescript
// Review View 등록
this.registerView(
  CAIRN_REVIEW_VIEW_TYPE,
  (leaf) => new DidymosReviewView(leaf, this.settings)
);

// 명령 추가
this.addCommand({
  id: "didymos-open-review",
  name: "Open Weekly Review",
  callback: () => {
    this.activateReviewView();
  },
});
```

메소드 추가:

```typescript
async activateReviewView() {
  const { workspace } = this.app;
  let leaf = workspace.getLeavesOfType(CAIRN_REVIEW_VIEW_TYPE)[0];

  if (!leaf) {
    leaf = workspace.getRightLeaf(false);
    await leaf.setViewState({
      type: CAIRN_REVIEW_VIEW_TYPE,
      active: true,
    });
  }

  workspace.revealLeaf(leaf);
}
```

---

### Step 7-9: 빌드 및 테스트

```bash
cd didymos-obsidian
npm run dev
cp main.js manifest.json styles.css "../didymos-test-vault/.obsidian/plugins/didymos/"
```

테스트:

1. Cmd+P → "Open Weekly Review"
2. Weekly Review Panel 확인
3. 각 섹션 정상 표시 확인

---

## ✅ 완료 체크리스트

### 백엔드
- [ ] `app/schemas/review.py` 작성
- [ ] `app/services/review_service.py` 작성
- [ ] `app/api/routes_review.py` 작성
- [ ] Swagger UI에서 테스트

### 프론트엔드
- [ ] `src/views/reviewView.ts` 작성
- [ ] CSS 스타일링
- [ ] Review View 등록

### 통합 테스트
- [ ] Weekly Review Panel 열기 성공
- [ ] 새 Topics 표시
- [ ] 잊힌 Projects 표시
- [ ] 미완료 Tasks 표시
- [ ] 활발한 노트 표시

---

## 🎯 다음 단계

Weekly Review가 완성되었습니다!

**다음**: [Phase 8 - 프라이버시 & 배포](./phase-8-deploy.md)

프라이버시 모드와 배포를 준비합니다.
