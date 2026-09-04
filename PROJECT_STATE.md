# Project State: AI Content Maker

This file is the short operational state of the project.
Every new Codex chat should read this file first before deciding what to build next.

For the full product vision and long-term architecture, read `PROJECT_CONTEXT.md`.

## Current Phase

We are in **Phase 1: Telegram MVP**.

The goal of this phase is to build the simplest reliable version of:

```text
Topic
-> FastAPI
-> Telegram content generation
-> Database draft storage
-> Telegram publishing
```

We are intentionally avoiding overengineering:

- no multi-agent framework yet
- no LangGraph yet
- no Kubernetes
- no complex event-driven architecture
- no vector database until there is a real need

## Last Session Summary

Date: 2026-09-04

Today's completed work:

- created this `PROJECT_STATE.md` file as the short operational memory for the project
- added the collaboration rule: the user wants to write the project themselves, and Codex should not modify files unless explicitly asked
- added the first database foundation
- added first SQLModel models:
  - `Project`
  - `Channel`
  - `Topic`
  - `Content`
- added a `ContentRepository`
- updated `/telegram/generate` so it now saves a generated Telegram draft to the database
- updated the response from `/telegram/generate` to include:
  - `content_id`
  - `status`
- added local SQLite fallback when `DATABASE_URL` is not configured
- added `*.db` to `.gitignore`

Verified:

- `uv run python -m compileall src` passes
- FastAPI app imports successfully
- `POST /telegram/generate` returns `200`
- generated placeholder Telegram content is saved as `Content(status="draft")`
- the endpoint returns a real `content_id`

Current endpoint behavior:

```text
POST /telegram/generate
-> validates request
-> generates placeholder Telegram text
-> creates a Topic row
-> creates a Content row with platform="telegram" and status="draft"
-> returns content_id, project_id, topic, content, status
```

Example verified response:

```json
{
  "content_id": 1,
  "project_id": 1,
  "topic": "Why airplane lights are dimmed before landing",
  "content": "Draft Telegram post for project #1\n\nTopic: Why airplane lights are dimmed before landing\n\nThis is a placeholder. Later, this service will call the LLM.",
  "status": "draft"
}
```

## Collaboration Rule

The user wants to build this project themselves and learn to write code like a senior developer.

Future Codex chats must work in mentor/copilot mode by default:

- explain architecture and code clearly
- help the user think through implementation choices
- suggest next steps and tradeoffs
- review user-written code when asked
- do **not** create or modify files unless the user explicitly asks to implement, change, create, or edit something

When explaining code, be practical and detailed enough for learning:

- explain what each module is responsible for
- explain why a design choice fits the current MVP
- point out risks and simpler alternatives
- avoid overengineering

If the user asks "what should we do next?", answer with guidance and a suggested plan only.
Do not start editing files until the user clearly asks to write the code.

## What Exists Now

The repository already contains a minimal FastAPI backend.

Existing files:

```text
src/ai_content_maker/main.py
src/ai_content_maker/config.py
src/ai_content_maker/api/health.py
src/ai_content_maker/api/telegram.py
src/ai_content_maker/schemas/telegram.py
src/ai_content_maker/services/content/telegram_generator.py
```

Current implemented behavior:

- FastAPI app is created in `main.py`
- database tables are created on FastAPI startup through the app lifespan
- `/health` endpoint returns `{"status": "ok"}`
- `/telegram/generate` endpoint exists
- `TelegramGenerateRequest` validates:
  - `project_id`
  - `topic`
- `TelegramContentGenerator` currently returns a placeholder draft
- `/telegram/generate` saves the generated placeholder draft to the database
- `/telegram/generate` response includes:
  - `content_id`
  - `project_id`
  - `topic`
  - `content`
  - `status`
- environment variables are loaded through `.env`
- `.env.example` contains:
  - `OPENAI_API_KEY`
  - `TELEGRAM_BOT_TOKEN`
  - `DATABASE_URL`
- repository structure already follows `src/ai_content_maker/...`

New files added in this phase:

```text
src/ai_content_maker/db/__init__.py
src/ai_content_maker/db/session.py
src/ai_content_maker/models/__init__.py
src/ai_content_maker/models/project.py
src/ai_content_maker/models/channel.py
src/ai_content_maker/models/topic.py
src/ai_content_maker/models/content.py
src/ai_content_maker/repositories/__init__.py
src/ai_content_maker/repositories/content_repository.py
```

Current dependencies in `pyproject.toml` include:

- `fastapi`
- `uvicorn`
- `pydantic`
- `python-dotenv`
- `openai`
- `sqlmodel`

## Current Limitations

The project does **not** yet have:

- database migrations
- project/channel management endpoints
- topic duplicate detection
- real OpenAI/LLM integration
- prompt templates stored outside Python code
- Content Manager orchestration service
- Telegram Bot API publishing
- tests
- Docker setup
- README instructions

The current `/telegram/generate` endpoint saves placeholder content only.
It does not call a real LLM yet.

Important current limitations:

- `project_id` is accepted but not checked against a real `Project` row yet
- `channel_id` is optional and currently not selected from a real channel
- every request creates a new `Topic`; duplicate detection does not exist yet
- `status` is currently a string; later it can become an Enum
- tables are auto-created on startup; later production should use migrations
- local SQLite is used as a fallback; PostgreSQL is still the target database for the real deployment
- Telegram generation is still placeholder text, not real OpenAI generation

## Completed In The Current MVP Layer

The first database foundation is now in place.

Implemented:

```text
src/ai_content_maker/db/
src/ai_content_maker/models/
src/ai_content_maker/repositories/
```

Added first versions of:

```text
src/ai_content_maker/db/session.py
src/ai_content_maker/models/project.py
src/ai_content_maker/models/channel.py
src/ai_content_maker/models/topic.py
src/ai_content_maker/models/content.py
src/ai_content_maker/repositories/content_repository.py
```

`POST /telegram/generate` now:

1. receives `project_id` and `topic`
2. generates a placeholder Telegram draft
3. saves a `Topic`
4. saves a `Content` row with status `draft`
5. returns `content_id`, `project_id`, `topic`, `content`, and `status`

## Recommended Next Step

Tomorrow's recommended next step:

First, read and understand the code that was added today before writing more code.

Suggested learning path:

1. Read `src/ai_content_maker/api/telegram.py`
2. Follow the flow into `TelegramContentGenerator`
3. Follow the flow into `ContentRepository`
4. Read the `Topic` and `Content` models
5. Read `db/session.py`
6. Confirm how FastAPI `Depends(get_session)` gives the route a database session

After the code is understood, add prompt templates outside Python code.

Implement:

```text
prompts/telegram/default.txt
```

Then update `TelegramContentGenerator` so the prompt text can be loaded from that file instead of being hardcoded in Python.

This prepares the project for real LLM integration without coupling prompts to service code.

After that, add:

```text
src/ai_content_maker/services/llm/base.py
src/ai_content_maker/services/llm/openai.py
```

The next practical goal is to replace placeholder generation with real LLM generation while keeping OpenAI-specific code outside the Telegram generator.

## Suggested MVP Entities

### Project

Represents a content brand.

Fields for MVP:

```text
id
name
description
niche
language
status
created_at
```

### Channel

Represents a platform channel for a project.

Fields for MVP:

```text
id
project_id
platform
name
external_id
settings
is_active
created_at
```

### Topic

Represents a content idea.

Fields for MVP:

```text
id
project_id
title
description
source
source_url
status
created_at
```

### Content

Represents generated content.

Fields for MVP:

```text
id
project_id
channel_id
topic_id
platform
content
status
created_at
scheduled_at
published_at
```

Initial statuses:

```text
draft
approved
scheduled
published
failed
```

## After Database Persistence

After draft persistence works, continue in this order:

1. Add prompt templates outside Python code
   - start with `prompts/telegram/default.txt`
   - keep prompts easy to replace later per niche/project

2. Add `LLMService` abstraction
   - `services/llm/base.py`
   - `services/llm/openai.py`
   - keep OpenAI-specific code out of content generators

3. Replace placeholder Telegram generator with real LLM generation
   - use `OPENAI_API_KEY`
   - handle missing API key clearly
   - avoid hardcoded secrets
   - load the Telegram prompt template instead of hardcoding the whole prompt inside Python

4. Add Telegram publisher
   - `services/publishing/telegram.py`
   - use `TELEGRAM_BOT_TOKEN`
   - publish existing draft content

5. Add endpoint:

```http
POST /telegram/{content_id}/publish
```

6. Update content status after publish:
   - `published` on success
   - `failed` on Telegram/API error

7. Add basic tests for:
   - schema validation
   - draft generation
   - content repository
   - publish status updates

8. Add README run instructions.

9. Add Docker/Docker Compose only after the basic local MVP works.

## Content Manager Timing

`PROJECT_CONTEXT.md` describes a future central `ContentManager`.

Do **not** build a large Content Manager yet.

For the current Telegram-only MVP, the API route may orchestrate a small flow:

```text
request
-> TelegramContentGenerator
-> ContentRepository
-> response
```

Add `services/content/manager.py` only when it clearly simplifies shared flow, for example when the same topic needs to produce content for multiple platforms or when duplicate-topic checks and scheduling become real requirements.

## Architecture Rules

Keep modules separated by responsibility.

Good boundaries:

- `TelegramContentGenerator` generates Telegram text
- `LLMService` calls model providers
- `TelegramPublisher` calls Telegram Bot API
- `ContentRepository` talks to the database
- API routes orchestrate request/response flow only

Avoid putting database logic, LLM calls, and Telegram publishing all inside one route or one "agent" file.

## Important Notes For Future Codex Chats

- Start by reading this file.
- Then read only the files related to the next task.
- Do not rebuild the project structure from scratch.
- Do not duplicate existing services.
- Keep the MVP simple and working.
- Add abstractions only when they support the next real feature.
- Do not hardcode secrets.
- Do not commit `.env`.
- Prefer production-like but understandable code.
