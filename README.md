# AI Content Maker

Minimal FastAPI MVP for generating, reviewing, scheduling, and publishing Telegram posts.

Current first channel:

```text
Цікаво за хвилину
```

Positioning:

```text
Short, non-obvious facts about history, money, business, technology, science, and everyday systems.
```

Target cadence:

```text
1 post every 2 days
```

## Setup

Create `.env` from `.env.example` and fill in:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=@your_channel_username
TELEGRAM_ADMIN_CHAT_ID=your_private_chat_id
DATABASE_URL=sqlite:///./ai_content_maker.db
```

For Telegram publishing, add the bot to the channel as an administrator with permission to post messages.
For Telegram admin review, start a private chat with the bot and use your private Telegram chat id as `TELEGRAM_ADMIN_CHAT_ID`.

## Seed Local Data

Create the first local project and Telegram channel:

```bash
uv run python -m ai_content_maker.db.seed
```

Expected local seed:

```text
Project: Curious Facts Daily
Channel: Curious Facts Telegram
```

## Run API

```bash
uv run uvicorn ai_content_maker.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Workflow

Generate a draft:

```bash
curl -X POST http://127.0.0.1:8000/telegram/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":1,\"topic\":\"Чому Nokia починала не з телефонів, а з паперової фабрики\"}"
```

Generate a content plan with multiple drafts:

```bash
curl -X POST http://127.0.0.1:8000/telegram/content-plan/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":1,\"post_count\":4}"
```

For the current channel cadence, use `post_count=4`. That gives roughly one week of content when posting every 2 days.

List drafts:

```bash
curl "http://127.0.0.1:8000/telegram/drafts?project_id=1"
```

List content by status:

```bash
curl "http://127.0.0.1:8000/telegram/content?project_id=1&status=approved"
curl "http://127.0.0.1:8000/telegram/content?project_id=1&status=scheduled"
curl "http://127.0.0.1:8000/telegram/content?project_id=1&status=published"
curl "http://127.0.0.1:8000/telegram/content?project_id=1&status=failed"
```

Send the latest drafts to your private Telegram chat for phone review:

```bash
curl -X POST "http://127.0.0.1:8000/telegram/review/send-digest?project_id=1&limit=4"
```

This sends a private digest with post IDs, topics, text previews, image status, and the command format that the bot workflow will support next.

Send image candidates for one draft to your private Telegram chat:

```bash
curl -X POST "http://127.0.0.1:8000/telegram/review/CONTENT_ID/send-images?limit=3"
```

If the topic needs a better search phrase, pass a shorter English query:

```bash
curl -X POST "http://127.0.0.1:8000/telegram/review/CONTENT_ID/send-images?query=ZIP%20Code%201963%20United%20States%20Post%20Office&limit=3"
```

Suggest real image candidates from Wikimedia Commons:

```bash
curl -X POST "http://127.0.0.1:8000/telegram/CONTENT_ID/suggest-images?limit=5"
```

If the Ukrainian topic is too hard to search, pass a shorter English query:

```bash
curl -X POST "http://127.0.0.1:8000/telegram/CONTENT_ID/suggest-images?query=ZIP%20Code%201963%20United%20States%20Post%20Office&limit=5"
```

Attach the selected image to a draft:

```bash
curl -X POST http://127.0.0.1:8000/telegram/CONTENT_ID/image ^
  -H "Content-Type: application/json" ^
  -d "{\"image_url\":\"https://example.com/image.jpg\",\"image_source_url\":\"https://commons.wikimedia.org/wiki/File:Example.jpg\",\"image_author\":\"Author\",\"image_license\":\"Public domain\"}"
```

When a post has `image_url`, publishing uses Telegram `sendPhoto` with the post text as the caption. Without `image_url`, publishing uses `sendMessage`.

Approve a draft:

```bash
curl -X POST http://127.0.0.1:8000/telegram/CONTENT_ID/approve
```

Reject a draft:

```bash
curl -X POST http://127.0.0.1:8000/telegram/CONTENT_ID/reject
```

Schedule an approved post:

```bash
curl -X POST http://127.0.0.1:8000/telegram/CONTENT_ID/schedule ^
  -H "Content-Type: application/json" ^
  -d "{\"scheduled_at\":\"2026-09-07T10:00:00Z\"}"
```

Publish due scheduled posts manually:

```bash
curl -X POST http://127.0.0.1:8000/telegram/scheduled/publish-due
```

Or run the local job command:

```bash
uv run python -m ai_content_maker.jobs.publish_due
```

Later this command can be run automatically every few minutes through Windows Task Scheduler or cron.

## Tests

```bash
uv run python -m unittest discover -s tests
```

## Current Status Flow

```text
draft
-> approved
-> scheduled
-> published
```

Rejected flow:

```text
draft
-> rejected
```

Failure flow:

```text
scheduled
-> failed
```
