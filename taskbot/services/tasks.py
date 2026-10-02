"""Task lifecycle: ПОРУЧЕНИЕ → ПЛАН → СРОК → ФАКТ → ПРОВЕРКА → ОЦЕНКА.

All state changes go through this module so that every change is written to the audit log.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskbot.models import (
    IN_WORK,
    Priority,
    Reminder,
    Role,
    Task,
    TaskEvent,
    TaskFile,
    TaskSource,
    TaskStatus,
    User,
    UserStatus,
    utcnow,
)


class InvalidTransition(Exception):
    pass


def _check(task: Task, *allowed: TaskStatus) -> None:
    if task.status not in allowed:
        raise InvalidTransition(f"Задача #{task.id} в статусе «{task.status}», действие недоступно")


def log_event(session: AsyncSession, task: Task, actor: User | None, action: str, **details) -> None:
    session.add(
        TaskEvent(
            task_id=task.id,
            actor_id=actor.id if actor else None,
            action=action,
            details=json.dumps(details, ensure_ascii=False, default=str) if details else None,
        )
    )


# ---------------------------------------------------------------- users


async def get_user_by_tg(session: AsyncSession, tg_id: int) -> User | None:
    return await session.scalar(select(User).where(User.tg_id == tg_id))


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def active_employees(session: AsyncSession) -> Sequence[User]:
    rows = await session.scalars(
        select(User)
        .where(User.role == Role.EMPLOYEE, User.status == UserStatus.ACTIVE)
        .order_by(User.full_name)
    )
    return rows.all()


async def active_managers(session: AsyncSession) -> Sequence[User]:
    rows = await session.scalars(
        select(User).where(User.role == Role.MANAGER, User.status == UserStatus.ACTIVE)
    )
    return rows.all()


# ---------------------------------------------------------------- creation


async def create_task(
    session: AsyncSession,
    *,
    title: str,
    expected_result: str,
    plan_value: float | None,
    plan_unit: str | None,
    deadline: datetime,
    employee: User,
    created_by: User,
    priority: str = Priority.MEDIUM,
    weight: int = 0,
) -> Task:
    """Manager creates an active task, or an employee proposes one (status PROPOSED)."""
    by_manager = created_by.is_manager
    task = Task(
        title=title,
        expected_result=expected_result,
        plan_value=plan_value,
        plan_unit=plan_unit or None,
        deadline=deadline,
        priority=priority,
        weight=weight,
        status=TaskStatus.ACTIVE if by_manager else TaskStatus.PROPOSED,
        source=TaskSource.MANAGER if by_manager else TaskSource.EMPLOYEE,
        employee_id=employee.id,
        manager_id=created_by.id if by_manager else None,
        created_by_id=created_by.id,
        confirmed_at=utcnow() if by_manager else None,
    )
    session.add(task)
    await session.flush()
    log_event(
        session,
        task,
        created_by,
        "created" if by_manager else "proposed",
        title=title,
        expected_result=expected_result,
        plan_value=plan_value,
        plan_unit=plan_unit,
        deadline=deadline.isoformat(),
        priority=priority,
        weight=weight,
    )
    await session.commit()
    await session.refresh(task)
    return task


async def confirm_proposal(session: AsyncSession, task: Task, manager: User, weight: int, priority: str) -> Task:
    _check(task, TaskStatus.PROPOSED)
    task.status = TaskStatus.ACTIVE
    task.weight = weight
    task.priority = priority
    task.manager_id = manager.id
    task.confirmed_at = utcnow()
    log_event(session, task, manager, "confirmed", weight=weight, priority=priority)
    await session.commit()
    return task


async def reject_proposal(session: AsyncSession, task: Task, manager: User, reason: str) -> Task:
    _check(task, TaskStatus.PROPOSED)
    task.status = TaskStatus.REJECTED
    task.manager_id = manager.id
    task.review_comment = reason
    log_event(session, task, manager, "rejected", reason=reason)
    await session.commit()
    return task


async def cancel_task(session: AsyncSession, task: Task, manager: User) -> Task:
    _check(task, TaskStatus.ACTIVE, TaskStatus.REWORK, TaskStatus.SUBMITTED, TaskStatus.PROPOSED)
    task.status = TaskStatus.CANCELLED
    log_event(session, task, manager, "cancelled")
    await session.commit()
    return task


EDITABLE_FIELDS = {"title", "expected_result", "plan", "deadline", "priority", "weight"}


async def update_task(session: AsyncSession, task: Task, actor: User, **changes) -> Task:
    _check(task, TaskStatus.PROPOSED, TaskStatus.ACTIVE, TaskStatus.REWORK, TaskStatus.SUBMITTED)
    diff = {}
    for name, value in changes.items():
        old = getattr(task, name)
        if old != value:
            diff[name] = {"было": old, "стало": value}
            setattr(task, name, value)
    if "deadline" in diff:
        # A new deadline restarts reminders.
        await session.execute(delete(Reminder).where(Reminder.task_id == task.id))
    if diff:
        log_event(session, task, actor, "edited", **diff)
    await session.commit()
    return task


# ---------------------------------------------------------------- result and review


async def submit_result(
    session: AsyncSession,
    task: Task,
    employee: User,
    *,
    fact_text: str,
    fact_value: float | None,
    fact_extra: str | None,
    files: list[dict],
    now: datetime | None = None,
) -> Task:
    _check(task, *IN_WORK)
    now = now or utcnow()
    task.status = TaskStatus.SUBMITTED
    task.submitted_at = now
    task.fact_text = fact_text
    task.fact_value = fact_value
    task.fact_extra = fact_extra or None
    task.ai_score = task.ai_comment = task.ai_source = None
    if now > task.deadline:
        task.missed_deadline = True
    for f in files:
        task.files.append(
            TaskFile(file_id=f["file_id"], file_name=f["file_name"], kind=f["kind"], round=task.rework_count)
        )
    log_event(
        session,
        task,
        employee,
        "submitted",
        fact_text=fact_text,
        fact_value=fact_value,
        fact_extra=fact_extra,
        files=[f["file_name"] for f in files],
        late=now > task.deadline,
    )
    await session.commit()
    return task


async def save_ai_evaluation(session: AsyncSession, task: Task, score: int, comment: str, source: str) -> Task:
    task.ai_score = score
    task.ai_comment = comment
    task.ai_source = source
    log_event(session, task, None, "ai_evaluated", score=score, comment=comment, source=source)
    await session.commit()
    return task


async def approve(session: AsyncSession, task: Task, manager: User, score: int, comment: str | None = None) -> Task:
    _check(task, TaskStatus.SUBMITTED)
    task.status = TaskStatus.DONE
    task.final_score = score
    task.review_comment = comment or None
    task.reviewed_at = utcnow()
    task.reviewed_by_id = manager.id
    action = "approved" if task.ai_score is None or score == task.ai_score else "score_changed"
    log_event(session, task, manager, action, score=score, ai_score=task.ai_score, comment=comment)
    await session.commit()
    return task


async def return_for_rework(
    session: AsyncSession, task: Task, manager: User, comment: str, new_deadline: datetime | None
) -> Task:
    _check(task, TaskStatus.SUBMITTED)
    task.status = TaskStatus.REWORK
    task.rework_count += 1
    task.review_comment = comment
    task.submitted_at = None
    details = {"comment": comment}
    if new_deadline is not None and new_deadline != task.deadline:
        details["deadline"] = {"было": task.deadline.isoformat(), "стало": new_deadline.isoformat()}
        task.deadline = new_deadline
        await session.execute(delete(Reminder).where(Reminder.task_id == task.id))
    log_event(session, task, manager, "returned", **details)
    await session.commit()
    return task


# ---------------------------------------------------------------- queries


async def get_task(session: AsyncSession, task_id: int) -> Task | None:
    return await session.get(Task, task_id)


async def tasks_of_employee(
    session: AsyncSession, employee_id: int, statuses: Sequence[str] | None = None
) -> Sequence[Task]:
    q = select(Task).where(Task.employee_id == employee_id)
    if statuses:
        q = q.where(Task.status.in_(statuses))
    rows = await session.scalars(q.order_by(Task.deadline))
    return rows.unique().all()


async def tasks_by_status(session: AsyncSession, statuses: Sequence[str]) -> Sequence[Task]:
    rows = await session.scalars(select(Task).where(Task.status.in_(statuses)).order_by(Task.deadline))
    return rows.unique().all()


async def tasks_in_range(
    session: AsyncSession, start: datetime, end: datetime, employee_id: int | None = None
) -> Sequence[Task]:
    q = select(Task).where(Task.deadline >= start, Task.deadline < end)
    if employee_id is not None:
        q = q.where(Task.employee_id == employee_id)
    rows = await session.scalars(q.order_by(Task.deadline))
    return rows.unique().all()


async def recent_evaluations(session: AsyncSession, employee_id: int, limit: int = 10) -> Sequence[Task]:
    rows = await session.scalars(
        select(Task)
        .where(Task.employee_id == employee_id, Task.status == TaskStatus.DONE)
        .order_by(Task.reviewed_at.desc())
        .limit(limit)
    )
    return rows.unique().all()


async def recent_results(session: AsyncSession, limit: int = 5) -> Sequence[Task]:
    rows = await session.scalars(
        select(Task)
        .where(Task.status.in_((TaskStatus.SUBMITTED, TaskStatus.DONE)), Task.fact_text.is_not(None))
        .order_by(Task.updated_at.desc())
        .limit(limit)
    )
    return rows.unique().all()


async def task_events(session: AsyncSession, task_id: int) -> Sequence[TaskEvent]:
    rows = await session.scalars(select(TaskEvent).where(TaskEvent.task_id == task_id).order_by(TaskEvent.id))
    return rows.unique().all()
