"""Board column management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import BoardColumn, BoardColumnCreate, BoardColumnRead, BoardColumnUpdate, Task

router = APIRouter(prefix="/api/columns", tags=["columns"])


@router.get("", response_model=list[BoardColumnRead])
def list_columns(session: Session = Depends(get_session)):
    return session.exec(select(BoardColumn).order_by(BoardColumn.sort_order)).all()


@router.post("", response_model=BoardColumnRead, status_code=201)
def create_column(data: BoardColumnCreate, session: Session = Depends(get_session)):
    column = BoardColumn.model_validate(data)
    session.add(column)
    session.commit()
    session.refresh(column)
    return column


@router.patch("/{column_id}", response_model=BoardColumnRead)
def update_column(
    column_id: int, data: BoardColumnUpdate, session: Session = Depends(get_session)
):
    column = session.get(BoardColumn, column_id)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(column, key, value)
    session.add(column)
    session.commit()
    session.refresh(column)
    return column


@router.delete("/{column_id}", status_code=204)
def delete_column(column_id: int, session: Session = Depends(get_session)):
    column = session.get(BoardColumn, column_id)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")
    # Move tasks in this column to the first available column
    other = session.exec(
        select(BoardColumn).where(BoardColumn.id != column_id).order_by(BoardColumn.sort_order)
    ).first()
    if other:
        tasks = session.exec(select(Task).where(Task.status == column.name)).all()
        for task in tasks:
            task.status = other.name
            session.add(task)
    session.delete(column)
    session.commit()
