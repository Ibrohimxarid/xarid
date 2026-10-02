"""Application settings loaded from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


def _int_set(raw: str) -> frozenset[int]:
    return frozenset(int(x) for x in raw.replace(";", ",").split(",") if x.strip())


def _bool(raw: str | None, default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "да"}


@dataclass(frozen=True)
class Settings:
    bot_token: str = ""
    # Telegram user ids of managers (руководители). Everyone else registers as an employee.
    manager_ids: frozenset[int] = frozenset()
    database_url: str = "sqlite+aiosqlite:///taskbot.db"
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Tashkent"))

    # AI (Claude). When disabled or unavailable, a transparent formula is used instead.
    ai_enabled: bool = True
    ai_model: str = "claude-opus-5-5"
    ai_effort: str = "medium"
    ai_timeout: float = 90.0

    # Deadline control
    remind_before_hours: tuple[int, ...] = (24, 3)
    check_interval_sec: int = 300
    overdue_reminder_days: int = 7
    default_deadline_hour: int = 18

    # Scoring
    max_score: int = 150
    late_penalty_per_day: int = 5
    max_late_penalty: int = 50
    # Overdue tasks without a submitted result count as 0% in the efficiency coefficient.
    overdue_counts_as_zero: bool = True


def load_settings() -> Settings:
    load_dotenv()
    env = os.environ
    hours = tuple(
        sorted({int(x) for x in env.get("REMIND_BEFORE_HOURS", "24,3").split(",") if x.strip()}, reverse=True)
    )
    has_credentials = bool(env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"))
    return Settings(
        bot_token=env.get("BOT_TOKEN", ""),
        manager_ids=_int_set(env.get("MANAGER_IDS", "")),
        database_url=env.get("DATABASE_URL", Settings.database_url),
        timezone=ZoneInfo(env.get("TIMEZONE", "Asia/Tashkent")),
        ai_enabled=_bool(env.get("AI_ENABLED"), has_credentials),
        ai_model=env.get("AI_MODEL", Settings.ai_model),
        ai_effort=env.get("AI_EFFORT", Settings.ai_effort),
        ai_timeout=float(env.get("AI_TIMEOUT", Settings.ai_timeout)),
        remind_before_hours=hours,
        check_interval_sec=int(env.get("CHECK_INTERVAL_SEC", Settings.check_interval_sec)),
        overdue_reminder_days=int(env.get("OVERDUE_REMINDER_DAYS", Settings.overdue_reminder_days)),
        default_deadline_hour=int(env.get("DEFAULT_DEADLINE_HOUR", Settings.default_deadline_hour)),
        max_score=int(env.get("MAX_SCORE", Settings.max_score)),
        late_penalty_per_day=int(env.get("LATE_PENALTY_PER_DAY", Settings.late_penalty_per_day)),
        max_late_penalty=int(env.get("MAX_LATE_PENALTY", Settings.max_late_penalty)),
        overdue_counts_as_zero=_bool(env.get("OVERDUE_COUNTS_AS_ZERO"), True),
    )
