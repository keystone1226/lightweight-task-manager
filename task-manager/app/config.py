"""Application configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "tasks.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"

# SMTP settings (optional - email notifications only work when configured)
SMTP_HOST = os.getenv("TASK_SMTP_HOST", "")
SMTP_PORT = int(os.getenv("TASK_SMTP_PORT", "25"))
SMTP_FROM = os.getenv("TASK_SMTP_FROM", "taskmanager@local")
SMTP_USER = os.getenv("TASK_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("TASK_SMTP_PASSWORD", "")

# LLM settings (for weekly report generation)
LLM_API_URL = os.getenv("TASK_LLM_URL", "")          # e.g. https://llm.company.internal/v1/chat/completions
LLM_API_TOKEN = os.getenv("TASK_LLM_TOKEN", "")      # Bearer token
LLM_MODEL = os.getenv("TASK_LLM_MODEL", "gpt-4o")    # model name

# Server settings
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
