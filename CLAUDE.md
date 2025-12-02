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

## Project Structure

- `didymos-backend/` - FastAPI backend (Python)
- `didymos-obsidian/` - Obsidian plugin (TypeScript)
- `docs/` - Documentation

## Deployment

- Backend: Railway (`railway up`)
- Frontend: Build with `npm run build`, output in `dist/`
