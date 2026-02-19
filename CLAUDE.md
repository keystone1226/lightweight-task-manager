# CLAUDE.md — AI Assistant Guide for langflow-test

This file provides context, conventions, and workflows for AI assistants (Claude and others) working on this repository.

---

## Project Overview

This is a **Langflow**-based project. Langflow is a low-code, visual framework for building multi-agent and RAG (Retrieval-Augmented Generation) applications powered by large language models. It provides a drag-and-drop UI for composing flows, along with a Python API for custom component development.

- **Upstream project**: https://github.com/langflow-ai/langflow
- **Tech stack**: Python (backend/components), TypeScript/React (frontend), FastAPI, SQLModel, PostgreSQL or SQLite

---

## Repository Status

This repository is newly initialized. As source files are added, this CLAUDE.md should be updated to reflect the actual structure. The sections below document Langflow conventions that apply to this project.

---

## Directory Structure (Typical Langflow Project)

```
.
├── src/
│   ├── backend/            # Python FastAPI backend
│   │   ├── base/           # Core Langflow framework code
│   │   │   └── langflow/
│   │   │       ├── api/            # REST API routes
│   │   │       ├── components/     # Built-in flow components
│   │   │       ├── graph/          # Flow graph execution engine
│   │   │       ├── services/       # Business logic services
│   │   │       ├── schema/         # Pydantic/SQLModel schemas
│   │   │       └── main.py         # FastAPI application entry point
│   │   └── tests/          # Backend tests (pytest)
│   └── frontend/           # React + TypeScript frontend
│       ├── src/
│       │   ├── components/ # Reusable UI components
│       │   ├── pages/      # Page-level components
│       │   ├── hooks/      # Custom React hooks
│       │   ├── stores/     # Zustand state stores
│       │   ├── types/      # TypeScript type definitions
│       │   └── utils/      # Utility functions
│       ├── package.json
│       └── vite.config.ts
├── docker/                 # Docker configuration
├── docs/                   # Project documentation
├── scripts/                # Utility and automation scripts
├── pyproject.toml          # Python project configuration (uv/poetry)
├── docker-compose.yml      # Local development stack
└── CLAUDE.md               # This file
```

---

## Technology Stack

### Backend
| Tool | Purpose |
|------|---------|
| Python 3.10+ | Primary backend language |
| FastAPI | REST API framework |
| SQLModel | ORM (built on SQLAlchemy + Pydantic) |
| Alembic | Database migrations |
| uv | Python package manager (preferred over pip/poetry) |
| pytest | Testing framework |
| ruff | Linting and formatting |
| mypy | Static type checking |

### Frontend
| Tool | Purpose |
|------|---------|
| TypeScript | Primary frontend language |
| React 18 | UI framework |
| Vite | Build tool |
| Tailwind CSS | Styling |
| shadcn/ui | Component library |
| Zustand | State management |
| React Query | Server state and data fetching |
| pnpm | Package manager |

### Infrastructure
| Tool | Purpose |
|------|---------|
| PostgreSQL | Production database |
| SQLite | Default local development database |
| Redis | Optional caching and queuing |
| Docker / Docker Compose | Containerization |

---

## Development Setup

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ and pnpm
- uv (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker and Docker Compose (optional, for full stack)

### Backend Setup
```bash
# Install Python dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows

# Run database migrations
uv run alembic upgrade head

# Start backend dev server
uv run python -m langflow run --dev
# OR
make backend
```

### Frontend Setup
```bash
cd src/frontend

# Install dependencies
pnpm install

# Start dev server (proxies API to backend)
pnpm dev
# OR from root
make frontend
```

### Full Stack via Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f langflow
```

---

## Common Development Commands

### Backend
```bash
# Run all tests
uv run pytest src/backend/tests/

# Run a specific test file
uv run pytest src/backend/tests/unit/test_components.py -v

# Run tests with coverage
uv run pytest --cov=langflow --cov-report=html

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/backend/base/langflow

# Generate new migration
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

### Frontend
```bash
cd src/frontend

# Run tests
pnpm test

# Type check
pnpm typecheck

# Lint
pnpm lint

# Build for production
pnpm build

# Preview production build
pnpm preview
```

---

## Custom Component Development

Langflow components are Python classes that inherit from `Component` (or a specialized subclass). Each component defines typed inputs and outputs that appear in the visual editor.

### Component Structure
```python
from langflow.custom import Component
from langflow.inputs import StrInput, IntInput, HandleInput
from langflow.outputs import MessageOutput
from langflow.schema import Message


class MyCustomComponent(Component):
    display_name = "My Custom Component"
    description = "A short description shown in the UI."
    icon = "custom-icon"  # maps to a Lucide icon name
    name = "MyCustomComponent"

    inputs = [
        StrInput(
            name="system_prompt",
            display_name="System Prompt",
            info="The system prompt for the LLM.",
        ),
        HandleInput(
            name="llm",
            display_name="Language Model",
            input_types=["LanguageModel"],
        ),
    ]

    outputs = [
        MessageOutput(name="response", display_name="Response"),
    ]

    def build_response(self) -> Message:
        # Access inputs via self.<input_name>
        prompt = self.system_prompt
        llm = self.llm
        # ... build and return output
        return Message(text="response text")
```

### Component Conventions
- Each component lives in its own file under `src/backend/base/langflow/components/<category>/`
- `display_name` must be human-readable (shown in UI)
- `name` must be a valid Python identifier, unique across components
- Input/output names must be valid Python identifiers (snake_case)
- Build methods are named `build_<output_name>` matching the output's `name` field
- Use `self.log()` for debug output visible in the UI's log panel
- Raise `ValueError` or `ComponentBuildError` for user-facing errors
- Use `self.update_build_config()` for dynamic input configuration

---

## API Conventions

### REST Endpoints
- All API routes are prefixed with `/api/v1/`
- Route files live in `src/backend/base/langflow/api/v1/`
- Use FastAPI dependency injection for auth, database sessions, and services
- Return Pydantic models, not raw dicts
- Use `HTTPException` for error responses with appropriate status codes

### Example Route Pattern
```python
from fastapi import APIRouter, Depends, HTTPException
from langflow.services.deps import get_session, get_current_active_user

router = APIRouter(prefix="/flows", tags=["Flows"])

@router.get("/{flow_id}", response_model=FlowRead)
async def get_flow(
    flow_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    flow = await session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow
```

---

## Testing Conventions

### Backend Tests
- Test files are in `src/backend/tests/`
- Unit tests: `tests/unit/` — test individual functions/classes in isolation
- Integration tests: `tests/integration/` — test API endpoints with a real DB
- Use `pytest` fixtures for shared setup (database, client, mock services)
- Use `pytest-asyncio` for async test functions
- Mock external LLM calls in unit tests (never make real API calls in tests)
- Test file naming: `test_<module_name>.py`
- Test function naming: `test_<behaviour_description>`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_flow_returns_201(client: AsyncClient, logged_in_headers):
    payload = {"name": "Test Flow", "data": {}}
    response = await client.post("/api/v1/flows/", json=payload, headers=logged_in_headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Test Flow"
```

### Frontend Tests
- Use Vitest for unit and component tests
- Use React Testing Library for component tests
- Test files colocated with source: `ComponentName.test.tsx`
- Avoid testing implementation details; test user-visible behaviour

---

## Code Style and Formatting

### Python
- Follow PEP 8; enforced by `ruff`
- Line length: 88 characters (Black-compatible)
- Use type annotations on all function signatures
- Prefer `async`/`await` throughout the backend (FastAPI is async)
- Use f-strings for string formatting
- Imports: stdlib → third-party → local (ruff organizes automatically)

Run before every commit:
```bash
uv run ruff check --fix .
uv run ruff format .
```

### TypeScript / React
- Use functional components with hooks; no class components
- Use TypeScript strict mode (`"strict": true` in tsconfig)
- Props interfaces should be named `<ComponentName>Props`
- Use named exports; avoid default exports except for page components
- Keep components small and focused; extract logic into hooks
- Use `const` for all variable declarations unless reassignment is required

Run before every commit:
```bash
pnpm lint
pnpm typecheck
```

---

## Git Workflow

### Branch Naming
- Feature branches: `feature/<short-description>`
- Bug fixes: `fix/<short-description>`
- Claude Code branches: `claude/<session-id>` (auto-created by Claude)
- Hotfixes: `hotfix/<short-description>`

### Commit Messages
Follow the Conventional Commits specification:
```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

Examples:
```
feat(components): add OpenAI embedding component
fix(api): return 404 when flow not found instead of 500
test(graph): add unit tests for cycle detection
docs(claude): update CLAUDE.md with testing conventions
```

### Pull Request Process
1. Create a branch from `main` (or `dev` if it exists)
2. Make changes with clear, atomic commits
3. Ensure all tests pass locally
4. Open a PR with a descriptive title and body explaining the change
5. Address review comments before merging

---

## Environment Variables

Key environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGFLOW_DATABASE_URL` | `sqlite:///./langflow.db` | Database connection string |
| `LANGFLOW_SECRET_KEY` | (required in prod) | Secret key for JWT signing |
| `LANGFLOW_SUPERUSER` | `langflow` | Default admin username |
| `LANGFLOW_SUPERUSER_PASSWORD` | (required) | Default admin password |
| `LANGFLOW_HOST` | `0.0.0.0` | Host to bind the server |
| `LANGFLOW_PORT` | `7860` | Port to bind the server |
| `LANGFLOW_WORKERS` | `1` | Number of Uvicorn workers |
| `LANGFLOW_LOG_LEVEL` | `info` | Logging level |
| `LANGFLOW_CACHE_TYPE` | `InMemoryCache` | Cache backend |
| `OPENAI_API_KEY` | — | OpenAI API key (for built-in components) |

Store secrets in a `.env` file (never commit this file):
```bash
cp .env.example .env
# Edit .env with your values
```

---

## AI Assistant Guidelines

### When reading this codebase
- Start with `src/backend/base/langflow/` for backend logic
- Start with `src/frontend/src/` for frontend logic
- Flow execution logic lives in `langflow/graph/`
- Component definitions live in `langflow/components/`
- API route definitions live in `langflow/api/v1/`

### When adding a new component
1. Create file in the appropriate category subfolder under `langflow/components/`
2. Inherit from the correct base class (`Component`, `LLMComponent`, etc.)
3. Define all inputs and outputs with correct types
4. Implement `build_<output_name>()` method(s)
5. Add the component to the category's `__init__.py`
6. Write unit tests in `tests/unit/components/`
7. Test in the UI by running the dev stack

### When modifying the database schema
1. Change the SQLModel model in `langflow/schema/` or `langflow/services/database/models/`
2. Generate a migration: `uv run alembic revision --autogenerate -m "description"`
3. Review the generated migration file before applying
4. Apply: `uv run alembic upgrade head`
5. Never modify existing migration files that have been committed

### When adding API endpoints
1. Add route to the appropriate router in `langflow/api/v1/`
2. Define request/response Pydantic models
3. Add proper auth dependency (`get_current_active_user`)
4. Write integration tests
5. Update OpenAPI docs if needed

### Common Pitfalls
- Do not import heavy ML libraries at module level inside components — import inside the build method to keep startup fast
- Always handle missing optional API keys gracefully with a clear error message
- The frontend proxies API requests to the backend — do not hardcode ports in frontend code
- Flow data is stored as JSON in the database; schema changes require careful migration
- Async database sessions must be properly closed; always use dependency injection

---

## Useful Resources

- Langflow documentation: https://docs.langflow.org
- Langflow GitHub: https://github.com/langflow-ai/langflow
- FastAPI docs: https://fastapi.tiangolo.com
- SQLModel docs: https://sqlmodel.tiangolo.com
- Pydantic docs: https://docs.pydantic.dev
- Ruff docs: https://docs.astral.sh/ruff
- uv docs: https://docs.astral.sh/uv

---

*Last updated: 2026-02-19. Update this file whenever significant architectural changes are made.*
