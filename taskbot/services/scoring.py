"""Formula-based scoring: used as guidance for the AI and as a fallback when it is unavailable."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime

_NUMBER_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:[  ]\d{3})+|\d+(?:[.,]\d+)?)\s*(%|[a-zа-яё]+)?", re.IGNORECASE)
_SKIP_UNITS = {"октября", "ноября", "декабря", "января", "февраля", "марта", "апреля", "мая",
               "июня", "июля", "августа", "сентября", "числа", "г", "года", "год", "час", "часов",
               "ч", "дня", "дней", "день", "до"}


@dataclass
class PlanMetric:
    value: float
    unit: str


def parse_number(text: str) -> float | None:
    cleaned = text.strip().replace(" ", "").replace(" ", "").replace(",", ".").rstrip("%")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if math.isnan(value) or math.isinf(value) or value < 0:
        return None
    return value


def extract_plan(text: str) -> PlanMetric | None:
    """Find the first measurable quantity in a result description: 'проверить 100 договоров' → 100 договоров."""
    for m in _NUMBER_RE.finditer(text):
        unit = (m.group(2) or "").lower()
        if unit in _SKIP_UNITS:
            continue
        value = parse_number(m.group(1))
        if value is None or value == 0:
            continue
        return PlanMetric(value=value, unit=unit)
    return None


def late_days(deadline: datetime, submitted_at: datetime) -> int:
    """Number of started days of delay (0 when submitted on time)."""
    delta = (submitted_at - deadline).total_seconds()
    if delta <= 0:
        return 0
    return math.ceil(delta / 86400)


@dataclass
class Score:
    score: int
    comment: str


def formula_score(
    *,
    plan_value: float | None,
    fact_value: float | None,
    deadline: datetime,
    submitted_at: datetime,
    max_score: int,
    penalty_per_day: int,
    max_penalty: int,
) -> Score:
    parts = []
    if plan_value and fact_value is not None:
        base = 100.0 * fact_value / plan_value
        parts.append(f"факт/план = {fmt_num(fact_value)}/{fmt_num(plan_value)} → {round(base)}%")
    else:
        base = 100.0
        parts.append("числового плана нет — базовая оценка 100%, требуется проверка руководителем")
    days = late_days(deadline, submitted_at)
    penalty = min(days * penalty_per_day, max_penalty)
    if penalty:
        parts.append(f"задержка {days} дн. → −{penalty} п.п.")
    score = max(0, min(max_score, round(base - penalty)))
    if base - penalty > max_score:
        parts.append(f"ограничено максимумом {max_score}%")
    return Score(score=score, comment="; ".join(parts))


def fmt_num(value: float | None) -> str:
    if value is None:
        return "—"
    if float(value).is_integer():
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
