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

Date: 2026-09-05

Today's completed work:

- added the first external Telegram prompt template:
  - `prompts/telegram/default.txt`
- updated `TelegramContentGenerator` so it loads the Telegram draft template from that file
- replaced hardcoded placeholder string assembly in Python with simple template rendering
- added the first LLM service contract:
  - `src/ai_content_maker/services/llm/base.py`
- added the first OpenAI LLM service implementation:
  - `src/ai_content_maker/services/llm/openai.py`
- updated `TelegramContentGenerator` so it depends on an injected `LLMService`
- updated `/telegram/generate` so it creates `OpenAILLMService` and passes it into `TelegramContentGenerator`
- updated the Telegram prompt template so it now instructs the LLM to write a Telegram post
- made the OpenAI model configurable through `OPENAI_MODEL`
- added `OPENAI_MODEL=gpt-5.4-mini` to `.env.example`
- added provider-neutral LLM error handling through `LLMServiceError`
- updated `OpenAILLMService` to catch OpenAI SDK errors and raise `LLMServiceError`
- updated `/telegram/generate` to return `502` when text generation fails
- verified that the generator renders `project_id` and `topic`
- verified that `POST /telegram/generate` still returns `200` and saves a draft
- verified the route with a fake LLM service to avoid making a real OpenAI API call during smoke testing
- verified that `settings.openai_model` falls back to `gpt-5.4-mini`
- verified that a fake LLM failure returns `502`
- manually tested `POST /telegram/generate` with a real `OPENAI_API_KEY`
- confirmed that real OpenAI-generated content is saved as `Content(status="draft")`
- added the first basic tests:
  - prompt rendering through `TelegramContentGenerator` with a fake LLM service
  - `/telegram/generate` happy path with a fake LLM service and isolated in-memory SQLite database
  - `/telegram/generate` LLM failure path returning `502`
- verified that `python -m unittest discover -s tests` passes
- added the first Telegram publisher service:
  - `src/ai_content_maker/services/publishing/telegram.py`
- added `TELEGRAM_CHAT_ID` configuration
- added `POST /telegram/{content_id}/publish`
- updated `ContentRepository` with methods for loading content and marking it `published` or `failed`
- added publish response schema with `content_id`, `status`, and `telegram_message_id`
- added tests for successful draft publishing and failed Telegram publishing
- verified that `python -m unittest discover -s tests` passes with 5 tests
- selected the first MVP channel direction:
  - AI tools, practical AI workflows, and occasional interesting AI facts
- added an idempotent seed script for the first AI Tools Telegram channel:
  - `src/ai_content_maker/db/seed.py`
- seeded the local SQLite database with:
  - Project `AI Tools Daily` (`project_id=1`)
  - Channel `AI Tools Daily Telegram` (`channel_id=1`)
- updated the default Telegram prompt so generated posts are written in Ukrainian for the AI Tools channel positioning
- generated a real OpenAI draft for the AI Tools channel and saved it as `content_id=6`
- manually published `content_id=6` to the real Telegram channel
- confirmed Telegram returned `telegram_message_id=2`
- confirmed `content_id=6` is now `status="published"`
- collected feedback from the first real post:
  - the post was too long for Telegram
  - the output used too much Markdown formatting with `**`
  - the tone needed a few emoji
  - the post should not end with an offer such as "I can generate more"
- updated the Telegram prompt to generate shorter Ukrainian posts:
  - 700-900 characters
  - plain Telegram-friendly text
  - no Markdown bold/italics/headings/asterisks
  - 1-2 relevant emoji
  - max 3 short bullet or numbered points
  - practical takeaway at the end
- clarified the desired future operating model:
  - once per week, the system prepares a weekly content plan
  - the user reviews and approves/rejects posts
  - approved posts are scheduled across the week
  - the system publishes approved posts automatically according to schedule
- added `GET /telegram/drafts`
- added `TelegramDraftResponse`
- added `ContentRepository.list_telegram_drafts`
- added a test that verifies the drafts endpoint returns only Telegram drafts
- verified that `GET /telegram/drafts?project_id=1` returns local draft metadata from SQLite
- added review endpoints:
  - `POST /telegram/{content_id}/approve`
  - `POST /telegram/{content_id}/reject`
- added `TelegramReviewResponse`
- added repository methods:
  - `mark_approved`
  - `mark_rejected`
- changed publishing so only `approved` content can be published
- added tests for approve, reject, and publish requiring approval
- verified that `python -m unittest discover -s tests` passes with 9 tests
- locally approved `content_id=5` as a smoke test
- added scheduling endpoint:
  - `POST /telegram/{content_id}/schedule`
- added schedule request/response schemas
- added `ContentRepository.mark_scheduled`
- scheduling requires content to be `approved`
- `scheduled_at` must include a timezone
- schedule endpoint normalizes input datetime to UTC for storage/response
- updated publishing so it allows `approved` or `scheduled` content
- added tests for scheduling, timezone validation, and publishing scheduled content
- verified that `python -m unittest discover -s tests` passes with 13 tests
- locally scheduled `content_id=5` for `2026-09-07T10:00:00Z`
- added a manual due-publishing endpoint:
  - `POST /telegram/scheduled/publish-due`
- added `ScheduledTelegramPublisher` service for reusable scheduled publishing logic
- added `ContentRepository.list_due_telegram_posts`
- added scheduled publish response schemas
- due publishing finds Telegram content with `status="scheduled"` and `scheduled_at <= now`
- due publishing marks successful posts as `published`
- due publishing marks failed Telegram sends as `failed`
- added tests for publishing only due scheduled content and failure handling
- verified that `python -m unittest discover -s tests` passes with 15 tests
- locally verified that `POST /telegram/scheduled/publish-due` returns zero results when no posts are due
- updated the target publishing cadence:
  - publish 1 post every 2 days
  - this means roughly 3-4 posts per week, not 7 posts per week
- added `GET /telegram/content` for listing Telegram content by optional `project_id` and `status`
- added a reusable `TelegramContentResponse`
- added a local CLI job entry point:
  - `src/ai_content_maker/jobs/publish_due.py`
  - command: `uv run python -m ai_content_maker.jobs.publish_due`
- added console script entry point:
  - `ai-content-maker-publish-due`
- added README instructions for setup, generation, review, scheduling, publishing, due publishing, and tests
- verified that `python -m unittest discover -s tests` passes with 16 tests
- verified that the publish-due CLI returns zero results when no posts are due
- added content plan prompt:
  - `prompts/telegram/content_plan.txt`
- added `TelegramContentPlanGenerator`
- added `POST /telegram/content-plan/generate`
- content plan generation creates 3-4 draft posts for the AI channel by default using the cadence of 1 post every 2 days
- added tests for content plan topic parsing and generating multiple drafts from a content plan
- verified that `python -m unittest discover -s tests` passes with 18 tests
- generated a real content plan with `post_count=4` for project `AI Tools Daily`
- created draft content:
  - `content_id=7`
  - `content_id=8`
  - `content_id=9`
  - `content_id=10`
- observed that `content_id=8` was 995 characters, above the desired 700-900 character range
- next prompt refinement should make the upper length limit stricter
- pivoted the first MVP channel from AI tools to interesting facts
- the same Telegram channel will be reused; the user will change its public name and description manually
- updated the local seeded project/channel:
  - Project `Curious Facts Daily` (`project_id=1`)
  - Channel `Curious Facts Telegram` (`channel_id=1`)
- updated the default Telegram post prompt for facts content:
  - history
  - money and finance
  - business
  - technology
  - science
  - everyday systems
- updated the content plan prompt to generate surprising, specific facts topics instead of AI tools topics
- updated README to describe the facts-channel direction
- generated a real facts content plan with `post_count=4`
- created draft content:
  - `content_id=11`
  - `content_id=12`
  - `content_id=13`
  - `content_id=14`
- quick manual/source spot-check:
  - `content_id=12` about US ZIP codes looks grounded
  - `content_id=14` about Japanese 5/50 yen coin holes looks grounded
  - `content_id=11` about Neste and `content_id=13` about McDonald's POS failure look suspicious and should be manually verified or rejected
- next prompt refinement should prefer facts that can be checked against well-known public sources and avoid obscure claims without confidence
- added semi-automatic image workflow:
  - image metadata fields on `Content`
  - `POST /telegram/{content_id}/suggest-images`
  - `POST /telegram/{content_id}/image`
  - `WikimediaImageSearchService`
- publishing now uses Telegram `sendPhoto` when `image_url` is present and `sendMessage` otherwise
- scheduled publishing also passes `image_url` when present
- added SQLite compatibility helper to add image columns to the existing local SQLite database before real migrations exist
- verified Wikimedia image search for `content_id=12` using query override `ZIP Code 1963 United States Post Office`
- observed that Ukrainian long-topic search can return no candidates, so the endpoint supports a shorter `query` override
- image suggestions filter out non-image files such as PDFs
- added tests for image attachment, image suggestions, query override, and publishing with an image URL
- verified that `python -m unittest discover -s tests` passes with 22 tests
- started the phone-first Telegram admin workflow:
  - added `TELEGRAM_ADMIN_CHAT_ID`
  - added `TelegramAdminNotifier`
  - added `POST /telegram/review/send-digest`
  - added `POST /telegram/review/{content_id}/send-images`
  - the endpoint sends latest drafts to the user's private Telegram chat for review
  - the digest includes content IDs, topics, text previews, image status, and command examples
  - image review sends Wikimedia image candidates to the user's private Telegram chat as photo messages

Current endpoint behavior remains:

```text
POST /telegram/generate
-> validates request
-> loads the default Telegram prompt template
-> renders a Telegram prompt from the template
-> sends the prompt to OpenAI through OpenAILLMService
-> creates a Topic row
-> creates a Content row with platform="telegram" and status="draft"
-> returns content_id, project_id, topic, content, status
```

Current publish endpoint behavior:

```text
POST /telegram/{content_id}/publish
-> loads existing Content by id
-> returns 404 if content does not exist
-> returns 400 if content is not platform="telegram"
-> returns 400 if content is not status="approved" or status="scheduled"
-> sends content text to Telegram through TelegramPublisher
-> marks content as published and sets published_at on success
-> marks content as failed when Telegram publishing fails
-> returns content_id, status, telegram_message_id
```

Current review endpoint behavior:

```text
POST /telegram/{content_id}/approve
-> loads existing Content by id
-> returns 404 if content does not exist
-> returns 400 if content is not platform="telegram"
-> returns 400 if content is not status="draft"
-> marks content as approved
-> returns content_id and status

POST /telegram/{content_id}/reject
-> same validation as approve
-> marks content as rejected
-> returns content_id and status
```

Current schedule endpoint behavior:

```text
POST /telegram/{content_id}/schedule
-> loads existing Content by id
-> returns 404 if content does not exist
-> returns 400 if content is not platform="telegram"
-> returns 400 if content is not status="approved"
-> requires scheduled_at to include a timezone
-> normalizes scheduled_at to UTC
-> marks content as scheduled
-> returns content_id, status, scheduled_at
```

Current due publishing endpoint behavior:

```text
POST /telegram/scheduled/publish-due
-> finds scheduled Telegram posts whose scheduled_at is in the past or now
-> publishes each due post through TelegramPublisher
-> marks successful posts as published
-> marks Telegram failures as failed
-> returns published_count, failed_count, and per-post results
```

Current content listing endpoint behavior:

```text
GET /telegram/content
GET /telegram/content?project_id=1
GET /telegram/content?project_id=1&status=scheduled
-> lists Telegram content with optional project/status filters
-> returns content_id, project_id, topic, content, status, scheduled_at, published_at
```

Current content plan endpoint behavior:

```text
POST /telegram/content-plan/generate
-> asks the LLM for a JSON array of post topics
-> default post_count is 4
-> generates one Telegram draft for each topic
-> saves each generated post as Content(status="draft")
-> returns project_id, post_count, and created drafts
```

Current image workflow behavior:

```text
POST /telegram/{content_id}/suggest-images
-> searches Wikimedia Commons using the content topic
-> optional query parameter can override the search phrase
-> returns image candidates with image_url, source_url, author, and license

POST /telegram/{content_id}/image
-> attaches the selected image metadata to draft/approved/scheduled content
-> publishing uses sendPhoto when image_url is present
```

Current admin review behavior:

```text
POST /telegram/review/send-digest
-> finds latest Telegram drafts
-> formats a private review digest with content IDs, topics, text previews, and image status
-> sends it to TELEGRAM_ADMIN_CHAT_ID through the Telegram bot

POST /telegram/review/{content_id}/send-images
-> searches Wikimedia Commons for image candidates
-> sends candidate images to TELEGRAM_ADMIN_CHAT_ID as private Telegram photo messages
-> each caption includes the source/license details and the future `/set_image` command format
```

Recommended next step:

- add a Telegram bot webhook or polling command handler for private admin chat commands:
  - `/drafts`
  - `/approve CONTENT_ID`
  - `/reject CONTENT_ID`
  - `/images CONTENT_ID`
  - `/set_image CONTENT_ID IMAGE_URL_OR_TELEGRAM_FILE_ID`
  - `/schedule CONTENT_ID ISO_DATETIME`
- after that, add inline buttons so the user can control weekly review from the phone without typing commands

Previous session:

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
