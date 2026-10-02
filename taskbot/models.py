"""Database models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Stores datetimes as naive UTC and always returns timezone-aware UTC values."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime is not allowed")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Role(StrEnum):
    MANAGER = "manager"
    EMPLOYEE = "employee"


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"


class TaskStatus(StrEnum):
    PROPOSED = "proposed"  # added by an employee, waits for the manager's confirmation
    ACTIVE = "active"
    REWORK = "rework"  # returned by the manager for rework
    SUBMITTED = "submitted"  # result submitted, waits for the manager's review
    DONE = "done"  # evaluated
    REJECTED = "rejected"
    CANCELLED = "cancelled"


IN_WORK = (TaskStatus.ACTIVE, TaskStatus.REWORK)
OPEN = (TaskStatus.PROPOSED, TaskStatus.ACTIVE, TaskStatus.REWORK, TaskStatus.SUBMITTED)
COUNTED = (TaskStatus.ACTIVE, TaskStatus.REWORK, TaskStatus.SUBMITTED, TaskStatus.DONE)


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskSource(StrEnum):
    MANAGER = "manager"
    EMPLOYEE = "employee"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16), default=Role.EMPLOYEE)
    status: Mapped[str] = mapped_column(String(16), default=UserStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    @property
    def is_manager(self) -> bool:
        return self.role == Role.MANAGER

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str] = mapped_column(Text)
    plan_value: Mapped[float | None] = mapped_column(Float)
    plan_unit: Mapped[str | None] = mapped_column(String(100))
    deadline: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    priority: Mapped[str] = mapped_column(String(16), default=Priority.MEDIUM)
    weight: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(16), default=TaskSource.MANAGER)

    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    fact_text: Mapped[str | None] = mapped_column(Text)
    fact_value: Mapped[float | None] = mapped_column(Float)
    fact_extra: Mapped[str | None] = mapped_column(Text)

    ai_score: Mapped[int | None] = mapped_column(Integer)
    ai_comment: Mapped[str | None] = mapped_column(Text)
    ai_source: Mapped[str | None] = mapped_column(String(16))  # "ai" or "formula"

    final_score: Mapped[int | None] = mapped_column(Integer)
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    missed_deadline: Mapped[bool] = mapped_column(Boolean, default=False)
    rework_count: Mapped[int] = mapped_column(Integer, default=0)

    employee: Mapped[User] = relationship(foreign_keys=[employee_id], lazy="joined")
    manager: Mapped[User | None] = relationship(foreign_keys=[manager_id], lazy="joined")
    files: Mapped[list[TaskFile]] = relationship(
        back_populates="task", lazy="selectin", order_by="TaskFile.id", cascade="all, delete-orphan"
    )

    def is_overdue(self, now: datetime) -> bool:
        return self.status in IN_WORK and self.deadline < now

    def current_files(self) -> list[TaskFile]:
        return [f for f in self.files if f.round == self.rework_count]


class TaskFile(Base):
    __tablename__ = "task_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    file_id: Mapped[str] = mapped_column(String(256))
    file_name: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(16))  # document | photo
    round: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    task: Mapped[Task] = relationship(back_populates="files")


class TaskEvent(Base):
    """Audit log: every change of a task is recorded here."""

    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(32))
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    actor: Mapped[User | None] = relationship(lazy="joined")


class Reminder(Base):
    """Marks reminders already sent for a task so each one goes out only once."""

    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("task_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    sent_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
