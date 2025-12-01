# 📊 Palantir Ontology Migration Plan

> Didymos를 Palantir Foundry 스타일의 온톨로지로 전환하는 마이그레이션 계획

**작성일**: 2025-12-01
**목표**: 의사결정과 액션 중심의 강력한 온톨로지 시스템 구축

---

## 1. 개요

### 1.1 왜 Palantir 온톨로지인가?

Palantir Foundry의 온톨로지는 **의사결정과 액션**에 최적화되어 있습니다:

- ✅ **Object Types**: 명시적 타입 정의로 일관성 보장
- ✅ **Properties**: 강타입 시스템으로 데이터 품질 향상
- ✅ **Links**: 양방향 관계로 탐색 성능 개선
- ✅ **Actions**: 워크플로우 자동화 가능
- ✅ **Versioning**: 전체 변경 이력 추적

### 1.2 현재 vs Palantir 비교

| 측면 | Didymos (현재) | Palantir Foundry | 마이그레이션 필요성 |
|------|----------------|------------------|-------------------|
| **타입 시스템** | LLM 자동 추출 (느슨함) | 명시적 스키마 (엄격함) | 🔴 높음 |
| **속성 검증** | 없음 | 타입별 검증 강제 | 🟡 중간 |
| **관계 방향** | 단방향 | 양방향 자동 생성 | 🔴 높음 |
| **액션 시스템** | 없음 | 워크플로우 자동화 | 🟢 낮음 (MVP 이후) |
| **버전 관리** | 단순 timestamp | 전체 이력 추적 | 🟢 낮음 (MVP 이후) |

---

## 2. Phase 1: Object Type 시스템 (우선순위 1)

### 2.1 목표
현재 느슨한 타입 시스템을 명시적 스키마 기반으로 전환

### 2.2 Object Type 정의

```python
# didymos-backend/app/ontology/object_types.py

from typing import List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class PropertyType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    EMAIL = "email"
    URL = "url"
    ENUM = "enum"

class PropertyDefinition(BaseModel):
    """속성 정의"""
    name: str
    type: PropertyType
    required: bool = False
    default: Optional[Any] = None
    enum_values: Optional[List[str]] = None  # ENUM 타입일 때
    validation_regex: Optional[str] = None   # STRING 타입 검증
    min_value: Optional[float] = None        # NUMBER 타입 최소값
    max_value: Optional[float] = None        # NUMBER 타입 최대값

class LinkDefinition(BaseModel):
    """관계 정의"""
    name: str
    target_type: str
    bidirectional: bool = True
    reverse_name: Optional[str] = None  # 양방향일 때 역방향 이름
    cardinality: str = "many"  # one, many
    required: bool = False

class ActionDefinition(BaseModel):
    """액션 정의"""
    name: str
    description: str
    parameters: List[PropertyDefinition] = []

class ObjectType(BaseModel):
    """Object Type 스키마"""
    name: str
    display_name: str
    description: str
    properties: List[PropertyDefinition]
    allowed_links: List[LinkDefinition]
    actions: List[ActionDefinition] = []
    icon: str = "📄"
    color: str = "#888888"


# === 기본 Object Types 정의 ===

NOTE_TYPE = ObjectType(
    name="Note",
    display_name="노트",
    description="개인 지식 노트",
    icon="📝",
    color="#4A90E2",
    properties=[
        PropertyDefinition(name="note_id", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="path", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="content", type=PropertyType.STRING),
        PropertyDefinition(name="folder", type=PropertyType.STRING),
        PropertyDefinition(name="tags", type=PropertyType.STRING),  # JSON array
        PropertyDefinition(name="created_at", type=PropertyType.DATE, required=True),
        PropertyDefinition(name="updated_at", type=PropertyType.DATE, required=True),
    ],
    allowed_links=[
        LinkDefinition(
            name="mentions",
            target_type="Topic",
            bidirectional=True,
            reverse_name="mentioned_in"
        ),
        LinkDefinition(
            name="relates_to",
            target_type="Note",
            bidirectional=True,
            reverse_name="relates_to"
        ),
        LinkDefinition(
            name="has_task",
            target_type="Task",
            bidirectional=True,
            reverse_name="belongs_to_note"
        ),
    ],
    actions=[
        ActionDefinition(
            name="archive",
            description="노트를 아카이브",
            parameters=[]
        ),
        ActionDefinition(
            name="merge_with",
            description="다른 노트와 병합",
            parameters=[
                PropertyDefinition(name="target_note_id", type=PropertyType.STRING, required=True)
            ]
        ),
    ]
)

TOPIC_TYPE = ObjectType(
    name="Topic",
    display_name="주제",
    description="지식 개념/주제",
    icon="🏷️",
    color="#50C878",
    properties=[
        PropertyDefinition(name="name", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="description", type=PropertyType.STRING),
        PropertyDefinition(name="category", type=PropertyType.ENUM, enum_values=[
            "concept", "technology", "methodology", "domain"
        ]),
    ],
    allowed_links=[
        LinkDefinition(
            name="mentioned_in",
            target_type="Note",
            bidirectional=True,
            reverse_name="mentions"
        ),
        LinkDefinition(
            name="broader_than",
            target_type="Topic",
            bidirectional=True,
            reverse_name="narrower_than"
        ),
        LinkDefinition(
            name="related_to",
            target_type="Topic",
            bidirectional=True,
            reverse_name="related_to"
        ),
    ],
    actions=[
        ActionDefinition(
            name="merge_topics",
            description="중복 토픽 병합",
            parameters=[
                PropertyDefinition(name="target_topic", type=PropertyType.STRING, required=True)
            ]
        ),
    ]
)

PROJECT_TYPE = ObjectType(
    name="Project",
    display_name="프로젝트",
    description="진행 중인 프로젝트",
    icon="📁",
    color="#FF6B6B",
    properties=[
        PropertyDefinition(name="name", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="status", type=PropertyType.ENUM, required=True, enum_values=[
            "active", "paused", "completed", "archived"
        ]),
        PropertyDefinition(name="start_date", type=PropertyType.DATE),
        PropertyDefinition(name="end_date", type=PropertyType.DATE),
        PropertyDefinition(name="priority", type=PropertyType.ENUM, enum_values=[
            "high", "medium", "low"
        ]),
    ],
    allowed_links=[
        LinkDefinition(
            name="has_task",
            target_type="Task",
            bidirectional=True,
            reverse_name="belongs_to_project"
        ),
        LinkDefinition(
            name="documented_in",
            target_type="Note",
            bidirectional=True,
            reverse_name="documents_project"
        ),
        LinkDefinition(
            name="involves_person",
            target_type="Person",
            bidirectional=True,
            reverse_name="works_on"
        ),
    ],
    actions=[
        ActionDefinition(
            name="complete_project",
            description="프로젝트 완료 처리",
            parameters=[]
        ),
        ActionDefinition(
            name="archive_project",
            description="프로젝트 아카이브",
            parameters=[]
        ),
    ]
)

TASK_TYPE = ObjectType(
    name="Task",
    display_name="태스크",
    description="실행 가능한 작업",
    icon="✓",
    color="#FFD700",
    properties=[
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="status", type=PropertyType.ENUM, required=True, enum_values=[
            "todo", "in_progress", "done", "cancelled"
        ]),
        PropertyDefinition(name="priority", type=PropertyType.ENUM, enum_values=[
            "high", "medium", "low"
        ]),
        PropertyDefinition(name="due_date", type=PropertyType.DATE),
        PropertyDefinition(name="completed_date", type=PropertyType.DATE),
    ],
    allowed_links=[
        LinkDefinition(
            name="belongs_to_note",
            target_type="Note",
            bidirectional=True,
            reverse_name="has_task"
        ),
        LinkDefinition(
            name="belongs_to_project",
            target_type="Project",
            bidirectional=True,
            reverse_name="has_task"
        ),
        LinkDefinition(
            name="assigned_to",
            target_type="Person",
            bidirectional=True,
            reverse_name="responsible_for"
        ),
        LinkDefinition(
            name="depends_on",
            target_type="Task",
            bidirectional=True,
            reverse_name="blocks"
        ),
    ],
    actions=[
        ActionDefinition(
            name="complete_task",
            description="태스크 완료",
            parameters=[]
        ),
        ActionDefinition(
            name="reschedule",
            description="마감일 연기",
            parameters=[
                PropertyDefinition(name="new_due_date", type=PropertyType.DATE, required=True)
            ]
        ),
    ]
)

PERSON_TYPE = ObjectType(
    name="Person",
    display_name="인물",
    description="관련된 사람",
    icon="👤",
    color="#9B59B6",
    properties=[
        PropertyDefinition(name="name", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="email", type=PropertyType.EMAIL),
        PropertyDefinition(name="affiliation", type=PropertyType.STRING),
        PropertyDefinition(name="role", type=PropertyType.STRING),
    ],
    allowed_links=[
        LinkDefinition(
            name="works_on",
            target_type="Project",
            bidirectional=True,
            reverse_name="involves_person"
        ),
        LinkDefinition(
            name="responsible_for",
            target_type="Task",
            bidirectional=True,
            reverse_name="assigned_to"
        ),
        LinkDefinition(
            name="collaborates_with",
            target_type="Person",
            bidirectional=True,
            reverse_name="collaborates_with"
        ),
    ],
    actions=[]
)

# 모든 타입 등록
OBJECT_TYPES = {
    "Note": NOTE_TYPE,
    "Topic": TOPIC_TYPE,
    "Project": PROJECT_TYPE,
    "Task": TASK_TYPE,
    "Person": PERSON_TYPE,
}
```

### 2.3 속성 검증 로직

```python
# didymos-backend/app/ontology/validators.py

import re
from datetime import datetime
from typing import Any, Optional
from app.ontology.object_types import PropertyDefinition, PropertyType

class ValidationError(Exception):
    pass

def validate_property(
    prop_def: PropertyDefinition,
    value: Any
) -> Any:
    """
    속성 값 검증

    Returns:
        검증 및 변환된 값

    Raises:
        ValidationError: 검증 실패 시
    """
    # Required 체크
    if prop_def.required and value is None:
        raise ValidationError(f"Property '{prop_def.name}' is required")

    if value is None:
        return prop_def.default

    # 타입별 검증
    if prop_def.type == PropertyType.STRING:
        if not isinstance(value, str):
            raise ValidationError(f"Property '{prop_def.name}' must be a string")

        if prop_def.validation_regex:
            if not re.match(prop_def.validation_regex, value):
                raise ValidationError(
                    f"Property '{prop_def.name}' does not match pattern {prop_def.validation_regex}"
                )

        return value

    elif prop_def.type == PropertyType.NUMBER:
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Property '{prop_def.name}' must be a number")

        if prop_def.min_value is not None and num_value < prop_def.min_value:
            raise ValidationError(
                f"Property '{prop_def.name}' must be >= {prop_def.min_value}"
            )

        if prop_def.max_value is not None and num_value > prop_def.max_value:
            raise ValidationError(
                f"Property '{prop_def.name}' must be <= {prop_def.max_value}"
            )

        return num_value

    elif prop_def.type == PropertyType.DATE:
        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, str):
            try:
                datetime.fromisoformat(value)
                return value
            except ValueError:
                raise ValidationError(
                    f"Property '{prop_def.name}' must be a valid ISO date"
                )

        raise ValidationError(f"Property '{prop_def.name}' must be a date")

    elif prop_def.type == PropertyType.BOOLEAN:
        if not isinstance(value, bool):
            raise ValidationError(f"Property '{prop_def.name}' must be a boolean")
        return value

    elif prop_def.type == PropertyType.EMAIL:
        if not isinstance(value, str):
            raise ValidationError(f"Property '{prop_def.name}' must be a string")

        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise ValidationError(f"Property '{prop_def.name}' must be a valid email")

        return value

    elif prop_def.type == PropertyType.URL:
        if not isinstance(value, str):
            raise ValidationError(f"Property '{prop_def.name}' must be a string")

        url_regex = r'^https?://.+'
        if not re.match(url_regex, value):
            raise ValidationError(f"Property '{prop_def.name}' must be a valid URL")

        return value

    elif prop_def.type == PropertyType.ENUM:
        if value not in prop_def.enum_values:
            raise ValidationError(
                f"Property '{prop_def.name}' must be one of {prop_def.enum_values}"
            )
        return value

    return value


def validate_object(object_type: str, properties: dict) -> dict:
    """
    Object 전체 검증

    Args:
        object_type: Object Type 이름
        properties: 검증할 속성들

    Returns:
        검증된 속성 dict
    """
    from app.ontology.object_types import OBJECT_TYPES

    if object_type not in OBJECT_TYPES:
        raise ValidationError(f"Unknown object type: {object_type}")

    obj_type = OBJECT_TYPES[object_type]
    validated = {}

    for prop_def in obj_type.properties:
        value = properties.get(prop_def.name)
        validated[prop_def.name] = validate_property(prop_def, value)

    return validated
```

### 2.4 마이그레이션 전략

**Step 1**: 기존 데이터 스키마 분석
```cypher
// 현재 Note 노드 속성 확인
MATCH (n:Note)
RETURN keys(n) LIMIT 1

// 현재 관계 타입 확인
MATCH ()-[r]->()
RETURN DISTINCT type(r), count(*)
```

**Step 2**: 타입별 순차 마이그레이션
```python
# 마이그레이션 스크립트
async def migrate_to_typed_system():
    client = get_neo4j_client()

    # 1. Note 노드 마이그레이션
    notes = client.query("MATCH (n:Note) RETURN n")
    for note in notes:
        validated = validate_object("Note", note)
        # 검증된 속성으로 업데이트

    # 2. Topic 노드 마이그레이션
    # 3. Project 노드 마이그레이션
    # ...
```

---

## 3. Phase 2: 양방향 Link 시스템 (우선순위 2)

### 3.1 목표
모든 관계를 양방향으로 자동 생성하여 탐색 성능 향상

### 3.2 Link Manager 구현

```python
# didymos-backend/app/ontology/link_manager.py

from typing import Optional
from app.db.neo4j import get_neo4j_client
from app.ontology.object_types import OBJECT_TYPES

class LinkManager:
    """양방향 링크 자동 관리"""

    def create_link(
        self,
        from_type: str,
        from_id: str,
        link_name: str,
        to_type: str,
        to_id: str,
        properties: dict = None
    ):
        """
        링크 생성 (양방향 자동 생성)

        Args:
            from_type: 시작 노드 타입
            from_id: 시작 노드 ID
            link_name: 링크 이름
            to_type: 대상 노드 타입
            to_id: 대상 노드 ID
            properties: 링크 속성
        """
        # 타입 검증
        if from_type not in OBJECT_TYPES:
            raise ValueError(f"Unknown type: {from_type}")

        obj_type = OBJECT_TYPES[from_type]

        # 허용된 링크인지 확인
        link_def = None
        for allowed_link in obj_type.allowed_links:
            if allowed_link.name == link_name and allowed_link.target_type == to_type:
                link_def = allowed_link
                break

        if not link_def:
            raise ValueError(
                f"Link '{link_name}' from {from_type} to {to_type} is not allowed"
            )

        client = get_neo4j_client()

        # Forward link 생성
        cypher = f"""
        MATCH (from:{from_type} {{id: $from_id}})
        MATCH (to:{to_type} {{id: $to_id}})
        MERGE (from)-[r:{link_name.upper()}]->(to)
        SET r += $properties
        SET r.created_at = datetime()
        RETURN r
        """

        client.query(cypher, {
            "from_id": from_id,
            "to_id": to_id,
            "properties": properties or {}
        })

        # Reverse link 생성 (bidirectional일 때)
        if link_def.bidirectional and link_def.reverse_name:
            reverse_cypher = f"""
            MATCH (from:{to_type} {{id: $to_id}})
            MATCH (to:{from_type} {{id: $from_id}})
            MERGE (from)-[r:{link_def.reverse_name.upper()}]->(to)
            SET r += $properties
            SET r.created_at = datetime()
            RETURN r
            """

            client.query(reverse_cypher, {
                "from_id": from_id,
                "to_id": to_id,
                "properties": properties or {}
            })

    def delete_link(
        self,
        from_type: str,
        from_id: str,
        link_name: str,
        to_id: str
    ):
        """링크 삭제 (양방향 모두 삭제)"""
        # Forward + Reverse 모두 삭제
        pass
```

### 3.3 Link 메타데이터

```python
# 링크에 추가 정보 저장
class LinkMetadata:
    strength: float  # 0.0 ~ 1.0 (연결 강도)
    context: str     # 링크가 발생한 맥락
    auto_generated: bool  # LLM 자동 생성 여부
    verified: bool   # 사용자가 검증했는지
    created_at: datetime
    updated_at: datetime
```

---

## 4. Phase 3: Action 시스템 (우선순위 3)

### 4.1 목표
노트 워크플로우 자동화 및 사용자 정의 액션 지원

### 4.2 Action Executor

```python
# didymos-backend/app/ontology/actions.py

from typing import Dict, Any
from app.db.neo4j import get_neo4j_client

class ActionExecutor:
    """Object Action 실행기"""

    async def execute_action(
        self,
        object_type: str,
        object_id: str,
        action_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        액션 실행

        Args:
            object_type: 대상 Object Type
            object_id: 대상 Object ID
            action_name: 액션 이름
            parameters: 액션 파라미터

        Returns:
            실행 결과
        """
        # 액션 정의 찾기
        from app.ontology.object_types import OBJECT_TYPES

        if object_type not in OBJECT_TYPES:
            raise ValueError(f"Unknown type: {object_type}")

        obj_type = OBJECT_TYPES[object_type]
        action_def = None

        for action in obj_type.actions:
            if action.name == action_name:
                action_def = action
                break

        if not action_def:
            raise ValueError(f"Action '{action_name}' not found for {object_type}")

        # 액션별 로직
        if action_name == "archive":
            return await self._archive_note(object_id)

        elif action_name == "merge_with":
            target_id = parameters.get("target_note_id")
            return await self._merge_notes(object_id, target_id)

        elif action_name == "complete_project":
            return await self._complete_project(object_id)

        elif action_name == "complete_task":
            return await self._complete_task(object_id)

        elif action_name == "merge_topics":
            target = parameters.get("target_topic")
            return await self._merge_topics(object_id, target)

        raise NotImplementedError(f"Action '{action_name}' not implemented")

    async def _archive_note(self, note_id: str):
        """노트 아카이브"""
        client = get_neo4j_client()

        cypher = """
        MATCH (n:Note {note_id: $note_id})
        SET n.status = 'archived'
        SET n.archived_at = datetime()

        // 관련 Task들도 아카이브
        OPTIONAL MATCH (n)-[:HAS_TASK]->(t:Task)
        WHERE t.status IN ['todo', 'in_progress']
        SET t.status = 'cancelled'
        SET t.cancelled_reason = 'Note archived'

        RETURN n, collect(t) as tasks
        """

        result = client.query(cypher, {"note_id": note_id})

        return {
            "status": "success",
            "archived_note": note_id,
            "cancelled_tasks": len(result[0]["tasks"]) if result else 0
        }

    async def _merge_notes(self, source_id: str, target_id: str):
        """두 노트 병합"""
        client = get_neo4j_client()

        cypher = """
        MATCH (source:Note {note_id: $source_id})
        MATCH (target:Note {note_id: $target_id})

        // source의 모든 관계를 target으로 이동
        OPTIONAL MATCH (source)-[r]->(other)
        WHERE other.note_id <> $target_id
        WITH source, target, type(r) as rel_type, other

        CALL apoc.create.relationship(target, rel_type, {}, other) YIELD rel

        // source 삭제
        DETACH DELETE source

        RETURN target
        """

        # Note: APOC 플러그인 필요
        result = client.query(cypher, {
            "source_id": source_id,
            "target_id": target_id
        })

        return {
            "status": "success",
            "merged_into": target_id
        }

    async def _complete_project(self, project_id: str):
        """프로젝트 완료"""
        client = get_neo4j_client()

        cypher = """
        MATCH (p:Project {id: $project_id})
        SET p.status = 'completed'
        SET p.end_date = datetime()

        // 완료되지 않은 Task 확인
        OPTIONAL MATCH (p)-[:HAS_TASK]->(t:Task)
        WHERE t.status IN ['todo', 'in_progress']

        RETURN p, collect(t.title) as incomplete_tasks
        """

        result = client.query(cypher, {"project_id": project_id})

        incomplete = result[0]["incomplete_tasks"] if result else []

        return {
            "status": "success",
            "project_id": project_id,
            "warning": f"{len(incomplete)} tasks still incomplete" if incomplete else None,
            "incomplete_tasks": incomplete
        }

    async def _complete_task(self, task_id: str):
        """Task 완료"""
        client = get_neo4j_client()

        cypher = """
        MATCH (t:Task {id: $task_id})
        SET t.status = 'done'
        SET t.completed_date = datetime()

        RETURN t
        """

        client.query(cypher, {"task_id": task_id})

        return {
            "status": "success",
            "task_id": task_id
        }

    async def _merge_topics(self, source: str, target: str):
        """중복 Topic 병합"""
        client = get_neo4j_client()

        cypher = """
        MATCH (source:Topic {name: $source})
        MATCH (target:Topic {name: $target})

        // source의 모든 MENTIONED_IN 관계를 target으로 이동
        OPTIONAL MATCH (source)<-[r:MENTIONS]-(note:Note)
        MERGE (note)-[:MENTIONS]->(target)
        DELETE r

        // source 삭제
        DELETE source

        RETURN target, count(note) as merged_mentions
        """

        result = client.query(cypher, {"source": source, "target": target})

        return {
            "status": "success",
            "merged_mentions": result[0]["merged_mentions"] if result else 0
        }
```

### 4.3 Obsidian UI에서 Action 실행

```typescript
// didymos-obsidian/src/api/actions.ts

export class ActionAPI {
  constructor(private settings: DidymosSettings) {}

  async executeAction(
    objectType: string,
    objectId: string,
    actionName: string,
    parameters: Record<string, any> = {}
  ) {
    const response = await fetch(
      `${this.settings.apiEndpoint}/ontology/actions/execute`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_token: this.settings.userToken,
          vault_id: this.settings.vaultId,
          object_type: objectType,
          object_id: objectId,
          action_name: actionName,
          parameters: parameters
        })
      }
    );

    return await response.json();
  }
}
```

---

## 5. Phase 4: Versioning (우선순위 4)

### 5.1 목표
모든 변경 이력을 추적하여 시간 여행 쿼리 지원

### 5.2 변경 이력 노드

```cypher
// ChangeLog 노드
(:ChangeLog {
  id: "change_123",
  object_type: "Note",
  object_id: "note_456",
  change_type: "update",  // create, update, delete
  changed_properties: ["title", "content"],
  old_values: {...},
  new_values: {...},
  changed_by: "user_789",
  timestamp: datetime()
})

// Object와 연결
(:Note {note_id: "note_456"})-[:HAS_CHANGE]->(:ChangeLog)
```

### 5.3 시간 여행 쿼리

```cypher
// 특정 시점의 Note 상태 조회
MATCH (n:Note {note_id: $note_id})-[:HAS_CHANGE]->(c:ChangeLog)
WHERE c.timestamp <= $target_datetime
RETURN n, collect(c) as changes
ORDER BY c.timestamp DESC
LIMIT 1
```

---

## 6. 마이그레이션 로드맵

### 6.1 Phase 순서

| Phase | 작업 | 예상 기간 | 우선순위 |
|-------|------|----------|---------|
| **Phase 1** | Object Type 시스템 | 2주 | 🔴 높음 |
| **Phase 2** | 양방향 Link 시스템 | 1주 | 🔴 높음 |
| **Phase 3** | Action 시스템 | 2주 | 🟡 중간 |
| **Phase 4** | Versioning | 1주 | 🟢 낮음 |

### 6.2 단계별 체크리스트

#### Phase 1: Object Type 시스템
- [ ] Object Type 스키마 정의 (`object_types.py`)
- [ ] 속성 검증 로직 구현 (`validators.py`)
- [ ] 기존 데이터 마이그레이션 스크립트
- [ ] API 엔드포인트 수정 (타입 검증 추가)
- [ ] 테스트 케이스 작성
- [ ] Obsidian UI 업데이트 (타입별 아이콘, 색상)

#### Phase 2: 양방향 Link 시스템
- [ ] LinkManager 구현
- [ ] 기존 단방향 링크 마이그레이션
- [ ] Link 메타데이터 추가
- [ ] API 업데이트 (링크 생성/삭제)
- [ ] Graph View 업데이트 (양방향 표시)

#### Phase 3: Action 시스템
- [ ] ActionExecutor 구현
- [ ] 기본 액션 구현 (archive, merge, complete)
- [ ] API 엔드포인트 추가
- [ ] Obsidian UI: 액션 버튼 추가
- [ ] 액션 이력 추적

#### Phase 4: Versioning
- [ ] ChangeLog 스키마 정의
- [ ] 자동 변경 추적 미들웨어
- [ ] 시간 여행 쿼리 API
- [ ] Obsidian UI: 변경 이력 뷰

---

## 7. 이점 요약

### 7.1 사용자 관점
- ✅ **데이터 품질 향상**: 타입 검증으로 일관성 보장
- ✅ **더 나은 탐색**: 양방향 링크로 빠른 탐색
- ✅ **워크플로우 자동화**: 반복 작업을 액션으로 자동화
- ✅ **변경 추적**: 언제든 이전 상태 복원 가능

### 7.2 개발자 관점
- ✅ **명확한 스키마**: 타입 기반 개발로 버그 감소
- ✅ **확장성**: 새로운 Object Type 쉽게 추가
- ✅ **유지보수성**: 액션 로직 중앙화

### 7.3 의사결정 지원
- ✅ **신뢰할 수 있는 데이터**: 검증된 속성만 사용
- ✅ **명확한 관계**: 양방향 링크로 맥락 파악
- ✅ **실행 가능한 인사이트**: 액션으로 즉시 실행

---

## 8. 참고 자료

- [Palantir Foundry Ontology Docs](https://www.palantir.com/docs/foundry/ontology/)
- [Neo4j APOC Procedures](https://neo4j.com/labs/apoc/)
- [Pydantic Data Validation](https://docs.pydantic.dev/)

---

**작성자**: Claude Code
**마지막 업데이트**: 2025-12-01
