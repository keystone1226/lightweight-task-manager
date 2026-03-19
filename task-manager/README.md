# Task Manager

Lightweight kanban task manager for teams in isolated networks.
No external dependencies, no cloud — just run it and share the URL.

## Quick Start

```bash
cd task-manager

# Install dependencies
uv sync

# Run the server
uv run python -m app

# Or specify host/port
uv run python -m app --host 0.0.0.0 --port 9000
```

On startup, the server prints:

```
==================================================
  Task Manager
==================================================
  Local:   http://127.0.0.1:8000
  Network: http://192.168.1.100:8000

  Share the Network URL with your team!
==================================================
```

Share the **Network URL** with your team. Everyone opens the URL in their browser, enters a nickname, and starts using the board.

## Features

- **Kanban Board** — Drag-and-drop cards between customizable columns
- **Figma & Confluence Links** — Dedicated URL fields with icon recognition
- **Image Attachments** — Upload screenshots or design mockups as card covers
- **Color Tags** — Categorize tasks with colored labels (UI, Icon, Research, etc.)
- **Due Dates** — Visual indicators for overdue and upcoming deadlines
- **Comments & @Mentions** — Discuss tasks and notify teammates
- **Notifications** — See unread mention/assignment alerts on login
- **No Login Required** — Just enter a nickname to get started
- **Email Notifications** (optional) — Configure SMTP for email alerts
- **Auto Migration** — Database schema updates automatically on server restart
- **Auto Backup** — Database is backed up before every migration

## Email Notifications (Optional)

Set these environment variables to enable email alerts:

```bash
export TASK_SMTP_HOST=mail.company.internal
export TASK_SMTP_PORT=25
export TASK_SMTP_FROM=taskmanager@company.com
export TASK_SMTP_USER=        # leave empty if no auth
export TASK_SMTP_PASSWORD=    # leave empty if no auth
```

## Database

- SQLite file at `tasks.db` (auto-created)
- Migrations managed by Alembic, applied automatically on startup
- Backup created before each migration: `tasks.db.bak.{timestamp}`
- Manual rollback: `uv run alembic downgrade -1`

## Tech Stack

- Python 3.10+ / FastAPI / SQLModel / Alembic
- Pure HTML/CSS/JS frontend (no build step, no CDN)
- SQLite (zero configuration)
