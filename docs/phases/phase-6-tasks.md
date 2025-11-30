# Phase 6: Task 관리

> Task 추출, 표시, 상태 관리

**예상 시간**: 3~4시간  
**난이도**: ⭐⭐⭐☆☆

---

## 목표

- `/tasks/update` API 구현
- `/tasks/list` API 구현
- Task Panel UI 구현
- 우선순위별 필터링
- 체크박스로 상태 변경

---

## Part 1: 백엔드 Task API 구현

### Step 6-1: Task 스키마 정의

파일 생성: `didymos-backend/app/schemas/task.py`

```python
"""
Task 관련 Pydantic 스키마
"""
from typing import Optional
from pydantic import BaseModel


class TaskUpdate(BaseModel):
    status: Optional[str] = None  # todo/in_progress/done
    priority: Optional[str] = None  # low/medium/high


class TaskListQuery(BaseModel):
    vault_id: str
    status: Optional[str] = None  # 필터링
    priority: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    note_id: str
    note_title: str
```

파일 수정: `didymos-backend/app/schemas/__init__.py`

```python
from .task import TaskUpdate, TaskListQuery, TaskOut

__all__ = [..., "TaskUpdate", "TaskListQuery", "TaskOut"]
```

---

### Step 6-2: Task 서비스 작성

파일 생성: `didymos-backend/app/services/task_service.py`

```python
"""
Task 관리 서비스
"""
from neo4j import Driver
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def update_task(driver: Driver, task_id: str, updates: Dict[str, Any]) -> bool:
    """
    Task 상태 업데이트
    """
    try:
        with driver.session() as session:
            # SET 절 동적 생성
            set_clauses = []
            if "status" in updates:
                set_clauses.append("t.status = $status")
            if "priority" in updates:
                set_clauses.append("t.priority = $priority")
            
            if not set_clauses:
                return True  # 업데이트할 것 없음
            
            set_clause = ", ".join(set_clauses)
            
            result = session.run(
                f"""
                MATCH (t:Task {{id: $task_id}})
                SET {set_clause}, t.updated_at = datetime()
                RETURN t.id AS id
                """,
                task_id=task_id,
                **updates
            )
            
            record = result.single()
            success = record is not None
            
            if success:
                logger.info(f"✅ Task updated: {task_id}")
            
            return success
            
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return False


def list_tasks(
    driver: Driver,
    vault_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None
) -> List[Dict]:
    """
    Vault의 Task 목록 조회
    """
    try:
        with driver.session() as session:
            # 동적 WHERE 절 생성
            where_clauses = []
            params = {"vault_id": vault_id}
            
            if status:
                where_clauses.append("t.status = $status")
                params["status"] = status
            
            if priority:
                where_clauses.append("t.priority = $priority")
                params["priority"] = priority
            
            where_clause = ""
            if where_clauses:
                where_clause = "AND " + " AND ".join(where_clauses)
            
            result = session.run(
                f"""
                MATCH (v:Vault {{id: $vault_id}})-[:HAS_NOTE]->(n:Note)
                -[:CONTAINS_TASK]->(t:Task)
                WHERE 1=1 {where_clause}
                RETURN 
                    t.id AS id,
                    t.title AS title,
                    t.status AS status,
                    t.priority AS priority,
                    n.note_id AS note_id,
                    n.title AS note_title
                ORDER BY 
                    CASE t.priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END,
                    t.created_at DESC
                """,
                **params
            )
            
            tasks = []
            for record in result:
                tasks.append({
                    "id": record["id"],
                    "title": record["title"],
                    "status": record["status"],
                    "priority": record["priority"],
                    "note_id": record["note_id"],
                    "note_title": record["note_title"]
                })
            
            logger.info(f"Found {len(tasks)} tasks for vault {vault_id}")
            return tasks
            
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return []
```

---

### Step 6-3: Task API 라우터

파일 생성: `didymos-backend/app/api/routes_tasks.py`

```python
"""
Task API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional
import logging

from app.schemas.task import TaskUpdate, TaskOut
from app.db.neo4j import get_neo4j_driver
from app.services.task_service import update_task, list_tasks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_user_id_from_token(token: str) -> str:
    return token


@router.put("/{task_id}")
async def update_task_endpoint(task_id: str, updates: TaskUpdate, user_token: str):
    """
    Task 업데이트
    """
    try:
        driver = get_neo4j_driver()
        
        logger.info(f"Updating task: {task_id}")
        
        success = update_task(driver, task_id, updates.dict(exclude_none=True))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return {"status": "ok", "task_id": task_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/list", response_model=list[TaskOut])
async def list_tasks_endpoint(
    vault_id: str,
    user_token: str,
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    """
    Task 목록 조회
    """
    try:
        driver = get_neo4j_driver()
        
        logger.info(f"Listing tasks for vault: {vault_id}")
        
        tasks = list_tasks(driver, vault_id, status, priority)
        
        return tasks
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

파일 수정: `didymos-backend/app/main.py`

```python
from app.api import routes_notes, routes_tasks

app.include_router(routes_tasks.router, prefix=settings.api_prefix)
```

---

### Step 6-4: API 테스트

Swagger UI에서 테스트:

1. `/api/v1/tasks/list` 테스트
   - `vault_id`: `test_vault`
   - `user_token`: `test_user_001`

2. `/api/v1/tasks/{task_id}` 테스트
   - `task_id`: 조회된 Task ID
   - `updates`: `{"status": "done"}`

---

## Part 2: Obsidian 플러그인 Task Panel

### Step 6-5: API 클라이언트 확장

파일 수정: `didymos-obsidian/src/api/client.ts`

interface 추가:

```typescript
export interface TaskData {
  id: string;
  title: string;
  status: string;
  priority: string;
  note_id: string;
  note_title: string;
}
```

메소드 추가:

```typescript
async listTasks(
  vaultId: string,
  status?: string,
  priority?: string
): Promise<TaskData[]> {
  const url = new URL(`${this.settings.apiBaseUrl}/tasks/list`);
  url.searchParams.set("vault_id", vaultId);
  url.searchParams.set("user_token", this.settings.userToken);
  if (status) url.searchParams.set("status", status);
  if (priority) url.searchParams.set("priority", priority);

  try {
    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to list tasks:", error);
    throw error;
  }
}

async updateTask(taskId: string, updates: { status?: string; priority?: string }): Promise<void> {
  const url = new URL(`${this.settings.apiBaseUrl}/tasks/${taskId}`);
  url.searchParams.set("user_token", this.settings.userToken);

  try {
    const response = await fetch(url.toString(), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);
  } catch (error) {
    console.error("Failed to update task:", error);
    throw error;
  }
}
```

---

### Step 6-6: Task View 구현

파일 생성: `didymos-obsidian/src/views/taskView.ts`

```typescript
import { ItemView, WorkspaceLeaf, Notice } from "obsidian";
import { DidymosSettings } from "../settings";
import { DidymosAPI, TaskData } from "../api/client";

export const CAIRN_TASK_VIEW_TYPE = "didymos-task-view";

export class DidymosTaskView extends ItemView {
  settings: DidymosSettings;
  api: DidymosAPI;
  tasks: TaskData[] = [];
  currentFilter: { status?: string; priority?: string } = {};

  constructor(leaf: WorkspaceLeaf, settings: DidymosSettings) {
    super(leaf);
    this.settings = settings;
    this.api = new DidymosAPI(settings);
  }

  getViewType(): string {
    return CAIRN_TASK_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Didymos Tasks";
  }

  getIcon(): string {
    return "check-square";
  }

  async onOpen() {
    await this.renderTasks();
  }

  async renderTasks() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("didymos-task-container");

    // Header
    const header = container.createEl("div", { cls: "didymos-task-header" });
    header.createEl("h2", { text: "✅ Tasks" });

    // Controls
    const controls = container.createEl("div", { cls: "didymos-task-controls" });

    // Status filter
    const statusLabel = controls.createEl("label", { text: "Status: " });
    const statusSelect = controls.createEl("select");
    ["All", "Todo", "In Progress", "Done"].forEach((label) => {
      statusSelect.createEl("option", {
        text: label,
        value: label === "All" ? "" : label.toLowerCase().replace(" ", "_"),
      });
    });

    // Priority filter
    const priorityLabel = controls.createEl("label", { text: "Priority: " });
    const prioritySelect = controls.createEl("select");
    ["All", "High", "Medium", "Low"].forEach((label) => {
      prioritySelect.createEl("option", {
        text: label,
        value: label === "All" ? "" : label.toLowerCase(),
      });
    });

    // Refresh button
    const refreshBtn = controls.createEl("button", { text: "🔄 Refresh" });

    // Event listeners
    statusSelect.addEventListener("change", async () => {
      this.currentFilter.status = statusSelect.value || undefined;
      await this.loadTasks();
    });

    prioritySelect.addEventListener("change", async () => {
      this.currentFilter.priority = prioritySelect.value || undefined;
      await this.loadTasks();
    });

    refreshBtn.addEventListener("click", async () => {
      await this.loadTasks();
    });

    // Task list container
    const listContainer = container.createEl("div", { cls: "didymos-task-list" });

    // Load tasks
    await this.loadTasks(listContainer);
  }

  async loadTasks(listContainer?: HTMLElement) {
    if (!listContainer) {
      listContainer = this.containerEl.querySelector(
        ".didymos-task-list"
      ) as HTMLElement;
    }

    if (!listContainer) return;

    listContainer.empty();

    try {
      // Loading
      listContainer.createEl("div", {
        text: "Loading tasks...",
        cls: "didymos-task-loading",
      });

      // Fetch tasks
      this.tasks = await this.api.listTasks(
        this.settings.vaultId,
        this.currentFilter.status,
        this.currentFilter.priority
      );

      listContainer.empty();

      if (this.tasks.length === 0) {
        listContainer.createEl("div", {
          text: "No tasks found.",
          cls: "didymos-task-empty",
        });
        return;
      }

      // Group by status
      const grouped: { [key: string]: TaskData[] } = {};
      this.tasks.forEach((task) => {
        if (!grouped[task.status]) grouped[task.status] = [];
        grouped[task.status].push(task);
      });

      // Render groups
      ["todo", "in_progress", "done"].forEach((status) => {
        if (!grouped[status] || grouped[status].length === 0) return;

        const groupDiv = listContainer.createEl("div", { cls: "didymos-task-group" });

        const statusLabel = {
          todo: "📋 To Do",
          in_progress: "⏳ In Progress",
          done: "✅ Done",
        }[status] || status;

        groupDiv.createEl("h3", {
          text: `${statusLabel} (${grouped[status].length})`,
        });

        const ul = groupDiv.createEl("ul");

        grouped[status].forEach((task) => {
          const li = ul.createEl("li", { cls: "didymos-task-item" });

          // Checkbox
          const checkbox = li.createEl("input", {
            type: "checkbox",
            cls: "didymos-task-checkbox",
          });
          checkbox.checked = task.status === "done";

          checkbox.addEventListener("change", async () => {
            await this.handleTaskStatusChange(task.id, checkbox.checked);
          });

          // Title
          const titleSpan = li.createEl("span", {
            text: task.title,
            cls: "didymos-task-title",
          });

          // Priority badge
          const priorityClass =
            task.priority === "high"
              ? "priority-high"
              : task.priority === "medium"
              ? "priority-medium"
              : "priority-low";

          li.createEl("span", {
            text: `[${task.priority[0].toUpperCase()}]`,
            cls: `didymos-task-priority ${priorityClass}`,
          });

          // Note link
          const noteLink = li.createEl("a", {
            text: `📄 ${task.note_title}`,
            cls: "didymos-task-note-link",
          });

          noteLink.addEventListener("click", (e) => {
            e.preventDefault();
            this.app.workspace.openLinkText(task.note_id, "", false);
          });
        });
      });
    } catch (error) {
      listContainer.empty();
      listContainer.createEl("div", {
        text: `❌ Failed to load tasks: ${error.message}`,
        cls: "didymos-task-error",
      });
    }
  }

  async handleTaskStatusChange(taskId: string, checked: boolean) {
    try {
      const newStatus = checked ? "done" : "todo";

      await this.api.updateTask(taskId, { status: newStatus });

      new Notice(`✅ Task updated`);

      // Reload tasks
      await this.loadTasks();
    } catch (error) {
      new Notice(`❌ Failed to update task`);
      console.error(error);
    }
  }
}
```

---

### Step 6-7: CSS 스타일링

파일 수정: `didymos-obsidian/styles.css`

추가:

```css
/* Task Panel */
.didymos-task-container {
  padding: 16px;
}

.didymos-task-header h2 {
  margin: 0 0 16px 0;
}

.didymos-task-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.didymos-task-controls label {
  font-weight: 500;
}

.didymos-task-controls select,
.didymos-task-controls button {
  padding: 4px 8px;
  border: 1px solid var(--background-modifier-border);
  border-radius: 4px;
  background-color: var(--background-primary);
  color: var(--text-normal);
  cursor: pointer;
}

.didymos-task-list {
  min-height: 200px;
}

.didymos-task-loading,
.didymos-task-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}

.didymos-task-error {
  color: var(--text-error);
  background-color: var(--background-modifier-error);
  padding: 16px;
  border-radius: 8px;
}

.didymos-task-group {
  margin-bottom: 24px;
}

.didymos-task-group h3 {
  margin: 0 0 12px 0;
  font-size: 1.1em;
  border-bottom: 1px solid var(--background-modifier-border);
  padding-bottom: 8px;
}

.didymos-task-group ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.didymos-task-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
}

.didymos-task-item:hover {
  background-color: var(--background-modifier-hover);
}

.didymos-task-checkbox {
  margin: 0;
  cursor: pointer;
}

.didymos-task-title {
  flex: 1;
}

.didymos-task-note-link {
  font-size: 0.85em;
  color: var(--text-muted);
  text-decoration: none;
}

.didymos-task-note-link:hover {
  color: var(--link-color);
}
```

---

### Step 6-8: 메인 플러그인에 Task View 등록

파일 수정: `didymos-obsidian/main.ts`

import 추가:

```typescript
import { DidymosTaskView, CAIRN_TASK_VIEW_TYPE } from "./src/views/taskView";
```

등록:

```typescript
// Task View 등록
this.registerView(
  CAIRN_TASK_VIEW_TYPE,
  (leaf) => new DidymosTaskView(leaf, this.settings)
);

// 명령 추가
this.addCommand({
  id: "didymos-open-tasks",
  name: "Open Task Panel",
  callback: () => {
    this.activateTaskView();
  },
});
```

메소드 추가:

```typescript
async activateTaskView() {
  const { workspace } = this.app;
  let leaf = workspace.getLeavesOfType(CAIRN_TASK_VIEW_TYPE)[0];

  if (!leaf) {
    leaf = workspace.getRightLeaf(false);
    await leaf.setViewState({
      type: CAIRN_TASK_VIEW_TYPE,
      active: true,
    });
  }

  workspace.revealLeaf(leaf);
}
```

---

### Step 6-9: 빌드 및 테스트

```bash
cd didymos-obsidian
npm run dev
cp main.js manifest.json styles.css "../didymos-test-vault/.obsidian/plugins/didymos/"
```

테스트:

1. Cmd+P → "Open Task Panel"
2. Task 목록 확인
3. 체크박스 클릭하여 상태 변경
4. 필터링 테스트

---

## ✅ 완료 체크리스트

### 백엔드
- [ ] `app/schemas/task.py` 작성
- [ ] `app/services/task_service.py` 작성
- [ ] `app/api/routes_tasks.py` 작성
- [ ] Swagger UI에서 테스트

### 프론트엔드
- [ ] `src/views/taskView.ts` 작성
- [ ] CSS 스타일링
- [ ] Task View 등록

### 통합 테스트
- [ ] Task Panel 열기 성공
- [ ] Task 목록 정상 표시
- [ ] 체크박스로 상태 변경
- [ ] 필터링 동작 확인

---

## 🎯 다음 단계

Task 관리가 완성되었습니다!

**다음**: [Phase 7 - Weekly Review](./phase-7-review.md)

주간 리뷰 기능을 추가합니다.
