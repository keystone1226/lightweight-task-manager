"""Weekly report routes."""

from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import LLM_API_TOKEN, LLM_API_URL, LLM_MODEL
from app.database import get_session
from app.models import Task, TaskHistory, User

router = APIRouter(prefix="/api/report", tags=["report"])


# ── Helpers ────────────────────────────────────────────────────────────────

def _week_range(year: int, week: int) -> tuple[datetime, datetime]:
    jan4 = date(year, 1, 4)
    monday = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week - 1)
    start = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
    end = start + timedelta(days=7)
    return start, end


def _current_week() -> tuple[int, int]:
    today = date.today()
    return today.year, today.isocalendar()[1]


# ── Schemas ────────────────────────────────────────────────────────────────

class TaskSummary(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    assignee: Optional[str]
    tags: Optional[str]
    changes: list[dict]   # [{field, old_value, new_value, changed_at}]


class WeeklyTasksResponse(BaseModel):
    year: int
    week: int
    period: str
    tasks: list[TaskSummary]


class GenerateRequest(BaseModel):
    year: int
    week: int
    task_ids: list[int]       # 사용자가 선택한 태스크 ID
    example_report: str       # 과거 보고서 예시


class GenerateResponse(BaseModel):
    report: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/weekly-tasks", response_model=WeeklyTasksResponse)
def get_weekly_tasks(
    year: Optional[int] = None,
    week: Optional[int] = None,
    session: Session = Depends(get_session),
) -> WeeklyTasksResponse:
    if year is None or week is None:
        year, week = _current_week()

    start, end = _week_range(year, week)
    period = f"{start.month}/{start.day} ~ {(end - timedelta(days=1)).month}/{(end - timedelta(days=1)).day}"

    # 해당 주에 updated_at이 있는 태스크 전체
    tasks = session.exec(
        select(Task).where(Task.updated_at >= start, Task.updated_at < end)
    ).all()

    # 각 태스크의 해당 주 변경 이력
    history_rows = session.exec(
        select(TaskHistory).where(
            TaskHistory.task_id.in_([t.id for t in tasks]),
            TaskHistory.changed_at >= start,
            TaskHistory.changed_at < end,
        )
    ).all()
    history_by_task: dict[int, list] = {}
    for h in history_rows:
        history_by_task.setdefault(h.task_id, []).append({
            "field": h.field,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "changed_at": h.changed_at.isoformat(),
        })

    # 담당자 이름 조회
    user_ids = {t.assignee_id for t in tasks if t.assignee_id}
    users = {u.id: u.nickname for u in session.exec(select(User).where(User.id.in_(user_ids))).all()}

    summaries = [
        TaskSummary(
            id=t.id,
            title=t.title,
            status=t.status,
            priority=t.priority,
            assignee=users.get(t.assignee_id),
            tags=t.tags,
            changes=history_by_task.get(t.id, []),
        )
        for t in sorted(tasks, key=lambda t: t.updated_at, reverse=True)
    ]

    return WeeklyTasksResponse(year=year, week=week, period=period, tasks=summaries)


@router.post("/generate", response_model=GenerateResponse)
async def generate_report(req: GenerateRequest, session: Session = Depends(get_session)) -> GenerateResponse:
    if not LLM_API_URL:
        raise HTTPException(status_code=503, detail="LLM API가 설정되지 않았습니다. TASK_LLM_URL 환경변수를 설정하세요.")

    # 선택된 태스크 조회
    tasks = session.exec(select(Task).where(Task.id.in_(req.task_ids))).all()
    user_ids = {t.assignee_id for t in tasks if t.assignee_id}
    users = {u.id: u.nickname for u in session.exec(select(User).where(User.id.in_(user_ids))).all()}

    start, end = _week_range(req.year, req.week)
    history_rows = session.exec(
        select(TaskHistory).where(
            TaskHistory.task_id.in_(req.task_ids),
            TaskHistory.changed_at >= start,
            TaskHistory.changed_at < end,
        )
    ).all()
    history_by_task: dict[int, list] = {}
    for h in history_rows:
        history_by_task.setdefault(h.task_id, []).append(
            f"{h.field}: {h.old_value} → {h.new_value}"
        )

    task_lines = []
    for t in tasks:
        assignee = users.get(t.assignee_id, "미배정")
        changes = ", ".join(history_by_task.get(t.id, [])) or "내용 수정"
        task_lines.append(f"- [{t.status}] {t.title} (담당: {assignee}) | 변경: {changes}")

    task_text = "\n".join(task_lines)
    _, week = _current_week()
    period_label = f"{req.year}년 {req.week}주차"

    prompt = f"""아래는 팀의 주간보고 예시입니다. 이 형식과 문체를 그대로 따라서 이번 주 업무 내용으로 주간보고를 작성해주세요.

---
[주간보고 예시]
{req.example_report}
---

[{period_label} 업무 내역]
{task_text}
---

위 업무 내역을 바탕으로 예시와 동일한 형식의 주간보고를 작성해주세요."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                LLM_API_URL,
                headers={"Authorization": f"Bearer {LLM_API_TOKEN}", "Content-Type": "application/json"},
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            report_text = data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"LLM API 오류: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 연결 실패: {str(e)}")

    return GenerateResponse(report=report_text)
