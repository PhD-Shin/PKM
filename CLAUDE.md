# Claude Code Instructions for Didymos Project

## OpenAI Model Configuration

### IMPORTANT: gpt-5-mini Model

**`gpt-5-mini` is a valid OpenAI model.** Do NOT change it to `gpt-4o-mini` or any other model.

However, `gpt-5-mini` has specific limitations:
- **Does NOT support `temperature` parameter** - only default value (1) is allowed
- If you see error: `"Unsupported value: 'temperature' does not support 0.0 with this model"`
  - Solution: Remove `temperature=0` parameter, do NOT change the model name

### Correct Configuration

```python
# CORRECT - gpt-5-mini without temperature
llm = ChatOpenAI(
    model="gpt-5-mini",
    api_key=settings.openai_api_key
)

# WRONG - do not use temperature with gpt-5-mini
llm = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0,  # THIS WILL CAUSE ERROR
    api_key=settings.openai_api_key
)
```

### Location
- File: `didymos-backend/app/services/ontology_service.py`
- The LLM is used for entity extraction via LangChain's `LLMGraphTransformer`

## Graphiti Temporal Knowledge Graph

### Overview
Didymos uses [Graphiti](https://github.com/getzep/graphiti) (by Zep AI) for temporal knowledge graph capabilities.

### Bi-Temporal Model
All edges have 4 time fields:
- `valid_at`: When the relationship actually started (user perspective)
- `invalid_at`: When the relationship ended (NULL = currently valid)
- `created_at`: When recorded in the system
- `expired_at`: When expired in the system

### Enabling Graphiti
Set `USE_GRAPHITI=true` in environment variables to enable Graphiti.
Default is `false` (uses legacy LLMGraphTransformer).

### Key Features
- **Episode-based Processing**: Notes become Episodes with automatic entity extraction
- **Entity Resolution**: Automatic deduplication and summarization
- **Hybrid Search**: Semantic + BM25 + Graph traversal
- **Temporal Queries**: "What was I interested in during January 2024?"

### API Endpoints
- `GET /api/v1/temporal/status` - Check Graphiti status
- `POST /api/v1/temporal/search` - Temporal-aware search
- `GET /api/v1/temporal/evolution/{entity_name}` - Track entity changes over time
- `GET /api/v1/temporal/insights/recent` - Recent knowledge changes

## Project Structure

- `didymos-backend/` - FastAPI backend (Python)
- `didymos-obsidian/` - Obsidian plugin (TypeScript)
- `docs/` - Documentation

## Deployment

- Backend: Railway (`railway up`)
- Frontend: Build with `npm run build`, output in `dist/`

## Key Services
- `graphiti_service.py` - Temporal knowledge graph (Graphiti)
- `ontology_service.py` - Legacy entity extraction (LLMGraphTransformer)
- `cluster_service.py` - Semantic clustering (UMAP + HDBSCAN)
