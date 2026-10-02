"""Efficiency coefficient (KPI) calculation.

The coefficient for a period is the weighted average of task scores:

    K = Σ(weight_i × score_i) / Σ(weight_i)

A task belongs to the period in which its deadline falls. Evaluated tasks use the
score confirmed by the manager. Overdue tasks without a result count as 0% (can be
switched off with ``overdue_as_zero=False``). Tasks waiting for review are not counted
until the manager confirms their score.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Protocol
from zoneinfo import ZoneInfo

from taskbot.models import IN_WORK, TaskSource, TaskStatus
from taskbot.services.dates import MONTHS_NOM


class Period(StrEnum):
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


PERIOD_TITLES = {
    Period.WEEK: "Неделя",
    Period.MONTH: "Месяц",
    Period.QUARTER: "Квартал",
    Period.YEAR: "Год",
}


class TaskLike(Protocol):
    status: str
    weight: int
    final_score: int | None
    missed_deadline: bool
    deadline: datetime
    source: str


def weighted_coefficient(items: Iterable[tuple[float, float]]) -> float | None:
    """Weighted average of (weight, score) pairs; None when there is nothing to average."""
    total_weight = 0.0
    total = 0.0
    for weight, score in items:
        if weight <= 0:
            continue
        total_weight += weight
        total += weight * score
    if total_weight == 0:
        return None
    return total / total_weight


def period_bounds(period: Period, ref: date) -> tuple[date, date]:
    """Return [start, end) dates of the period containing ``ref``."""
    if period == Period.WEEK:
        start = ref - timedelta(days=ref.weekday())
        return start, start + timedelta(days=7)
    if period == Period.MONTH:
        start = ref.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)
        return start, end
    if period == Period.QUARTER:
        q_month = 3 * ((ref.month - 1) // 3) + 1
        start = date(ref.year, q_month, 1)
        end = date(ref.year + 1, 1, 1) if q_month == 10 else date(ref.year, q_month + 3, 1)
        return start, end
    return date(ref.year, 1, 1), date(ref.year + 1, 1, 1)


def period_range_utc(period: Period, ref: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start, end = period_bounds(period, ref)
    return (
        datetime.combine(start, time.min, tzinfo=tz),
        datetime.combine(end, time.min, tzinfo=tz),
    )


def period_label(period: Period, ref: date) -> str:
    start, end = period_bounds(period, ref)
    if period == Period.WEEK:
        last = end - timedelta(days=1)
        return f"неделя {start:%d.%m}–{last:%d.%m.%Y}"
    if period == Period.MONTH:
        return f"{MONTHS_NOM[start.month]} {start.year}"
    if period == Period.QUARTER:
        roman = ["I", "II", "III", "IV"][(start.month - 1) // 3]
        return f"{roman} квартал {start.year}"
    return f"{start.year} год"


@dataclass
class EmployeeStats:
    coefficient: float | None = None
    total: int = 0
    done: int = 0
    in_work: int = 0
    on_review: int = 0
    overdue: int = 0
    done_on_time: int = 0
    over_plan: int = 0
    self_added: int = 0

    @property
    def on_time_pct(self) -> float | None:
        if self.done == 0:
            return None
        return 100.0 * self.done_on_time / self.done

    @property
    def completion_pct(self) -> float | None:
        if self.total == 0:
            return None
        return 100.0 * self.done / self.total


def compute_stats(tasks: Iterable[TaskLike], now: datetime, overdue_as_zero: bool = True) -> EmployeeStats:
    """Aggregate statistics for tasks whose deadline is inside the chosen period."""
    stats = EmployeeStats()
    scored: list[tuple[float, float]] = []
    for t in tasks:
        if t.status not in (TaskStatus.ACTIVE, TaskStatus.REWORK, TaskStatus.SUBMITTED, TaskStatus.DONE):
            continue
        stats.total += 1
        if t.source == TaskSource.EMPLOYEE:
            stats.self_added += 1
        currently_overdue = t.status in IN_WORK and t.deadline < now
        if t.missed_deadline or currently_overdue:
            stats.overdue += 1
        if t.status in IN_WORK:
            stats.in_work += 1
            if currently_overdue and overdue_as_zero:
                scored.append((t.weight, 0.0))
        elif t.status == TaskStatus.SUBMITTED:
            stats.on_review += 1
        elif t.status == TaskStatus.DONE:
            stats.done += 1
            if not t.missed_deadline:
                stats.done_on_time += 1
            score = t.final_score or 0
            if score > 100:
                stats.over_plan += 1
            scored.append((t.weight, float(score)))
    stats.coefficient = weighted_coefficient(scored)
    return stats


def fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{round(value)}%"
