from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ai_investing.config.models import CadencePoliciesRegistry, CadencePolicyConfig
from ai_investing.domain.models import CoverageEntry

DEFAULT_PREFERRED_RUN_TIME = time(hour=9, minute=0)
WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(frozen=True)
class ScheduleContext:
    timezone: ZoneInfo
    policy: CadencePolicyConfig | None
    schedule_enabled: bool
    preferred_run_time: time


def resolve_schedule_context(
    registry: CadencePoliciesRegistry,
    coverage: CoverageEntry,
    *,
    fallback_time: datetime | None = None,
) -> ScheduleContext:
    try:
        timezone = ZoneInfo(registry.workspace_timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Unsupported workspace timezone: {registry.workspace_timezone}"
        ) from exc

    preferred_run_time = _resolve_preferred_run_time(coverage, timezone, fallback_time=fallback_time)
    if not coverage.schedule_enabled:
        return ScheduleContext(
            timezone=timezone,
            policy=None,
            schedule_enabled=False,
            preferred_run_time=preferred_run_time,
        )

    policy_id = coverage.schedule_policy_id or registry.default_policy_id
    policy = next((item for item in registry.cadence_policies if item.id == policy_id), None)
    if policy is None:
        raise ValueError(f"Unknown cadence policy: {policy_id}")
    return ScheduleContext(
        timezone=timezone,
        policy=policy,
        schedule_enabled=True,
        preferred_run_time=preferred_run_time,
    )


def compute_initial_next_run_at(
    registry: CadencePoliciesRegistry,
    coverage: CoverageEntry,
    *,
    now: datetime,
    preserve_legacy_weekly_due_now: bool = False,
) -> datetime | None:
    schedule = resolve_schedule_context(registry, coverage, fallback_time=now)
    if not schedule.schedule_enabled:
        return None
    if preserve_legacy_weekly_due_now and coverage.preferred_run_time is None:
        return now
    assert schedule.policy is not None
    return _compute_policy_slot(
        coverage=coverage,
        policy=schedule.policy,
        timezone=schedule.timezone,
        preferred_run_time=schedule.preferred_run_time,
        reference=now,
        inclusive=True,
    )


def compute_next_run_at(
    registry: CadencePoliciesRegistry,
    coverage: CoverageEntry,
    *,
    completed_at: datetime,
) -> datetime | None:
    schedule = resolve_schedule_context(registry, coverage, fallback_time=completed_at)
    if not schedule.schedule_enabled:
        return None
    assert schedule.policy is not None
    return _compute_policy_slot(
        coverage=coverage,
        policy=schedule.policy,
        timezone=schedule.timezone,
        preferred_run_time=schedule.preferred_run_time,
        reference=completed_at,
        inclusive=False,
    )


def _resolve_preferred_run_time(
    coverage: CoverageEntry,
    timezone: ZoneInfo,
    *,
    fallback_time: datetime | None,
) -> time:
    if coverage.preferred_run_time:
        hour, minute = (int(piece) for piece in coverage.preferred_run_time.split(":"))
        return time(hour=hour, minute=minute)
    for candidate in (coverage.next_run_at, coverage.last_run_at, fallback_time):
        if candidate is not None:
            return candidate.astimezone(timezone).timetz().replace(tzinfo=None)
    return DEFAULT_PREFERRED_RUN_TIME


def _compute_policy_slot(
    *,
    coverage: CoverageEntry,
    policy: CadencePolicyConfig,
    timezone: ZoneInfo,
    preferred_run_time: time,
    reference: datetime,
    inclusive: bool,
) -> datetime:
    reference_local = reference.astimezone(timezone)
    if policy.kind == "weekly":
        return _next_weekly_slot(
            weekday=WEEKDAY_INDEX[policy.weekday or "monday"],
            reference_local=reference_local,
            preferred_run_time=preferred_run_time,
            inclusive=inclusive,
        )
    if policy.kind == "biweekly":
        return _next_biweekly_slot(
            coverage=coverage,
            weekday=WEEKDAY_INDEX[policy.weekday or "monday"],
            reference_local=reference_local,
            preferred_run_time=preferred_run_time,
            timezone=timezone,
            inclusive=inclusive,
        )
    if policy.kind == "weekdays":
        return _next_weekday_set_slot(
            weekdays={0, 1, 2, 3, 4},
            reference_local=reference_local,
            preferred_run_time=preferred_run_time,
            inclusive=inclusive,
        )
    if policy.kind == "custom_weekdays":
        return _next_weekday_set_slot(
            weekdays={WEEKDAY_INDEX[value] for value in policy.weekdays},
            reference_local=reference_local,
            preferred_run_time=preferred_run_time,
            inclusive=inclusive,
        )
    if policy.kind == "monthly":
        return _next_monthly_slot(
            day_of_month=policy.day_of_month or 1,
            reference_local=reference_local,
            preferred_run_time=preferred_run_time,
            inclusive=inclusive,
        )
    raise ValueError(f"Unsupported cadence policy kind: {policy.kind}")


def _next_weekly_slot(
    *,
    weekday: int,
    reference_local: datetime,
    preferred_run_time: time,
    inclusive: bool,
    step_days: int = 7,
) -> datetime:
    days_ahead = (weekday - reference_local.weekday()) % 7
    candidate_date = reference_local.date() + timedelta(days=days_ahead)
    candidate = _combine_local(candidate_date, preferred_run_time, reference_local.tzinfo)
    if not _is_candidate_valid(candidate, reference_local, inclusive=inclusive):
        candidate_date += timedelta(days=step_days)
        candidate = _combine_local(candidate_date, preferred_run_time, reference_local.tzinfo)
    return candidate.astimezone(UTC)


def _next_biweekly_slot(
    *,
    coverage: CoverageEntry,
    weekday: int,
    reference_local: datetime,
    preferred_run_time: time,
    timezone: ZoneInfo,
    inclusive: bool,
) -> datetime:
    anchor = coverage.next_run_at or coverage.last_run_at
    if anchor is None:
        first_slot = _next_weekly_slot(
            weekday=weekday,
            reference_local=reference_local,
            preferred_run_time=preferred_run_time,
            inclusive=inclusive,
        )
        return first_slot

    anchor_local = anchor.astimezone(timezone)
    candidate = _combine_local(anchor_local.date(), preferred_run_time, timezone)
    while candidate.weekday() != weekday:
        candidate += timedelta(days=1)
    while not _is_candidate_valid(candidate, reference_local, inclusive=inclusive):
        candidate += timedelta(days=14)
    return candidate.astimezone(UTC)


def _next_weekday_set_slot(
    *,
    weekdays: set[int],
    reference_local: datetime,
    preferred_run_time: time,
    inclusive: bool,
) -> datetime:
    for offset in range(0, 14):
        candidate_date = reference_local.date() + timedelta(days=offset)
        if candidate_date.weekday() not in weekdays:
            continue
        candidate = _combine_local(candidate_date, preferred_run_time, reference_local.tzinfo)
        if _is_candidate_valid(candidate, reference_local, inclusive=inclusive):
            return candidate.astimezone(UTC)
    raise ValueError("Unable to compute next weekday slot")


def _next_monthly_slot(
    *,
    day_of_month: int,
    reference_local: datetime,
    preferred_run_time: time,
    inclusive: bool,
) -> datetime:
    year = reference_local.year
    month = reference_local.month
    for _ in range(0, 24):
        candidate_date = date(year, month, day_of_month)
        candidate = _combine_local(candidate_date, preferred_run_time, reference_local.tzinfo)
        if _is_candidate_valid(candidate, reference_local, inclusive=inclusive):
            return candidate.astimezone(UTC)
        year, month = _next_month(year, month)
    raise ValueError("Unable to compute next monthly slot")


def _combine_local(candidate_date: date, preferred_run_time: time, timezone: ZoneInfo | None) -> datetime:
    assert timezone is not None
    return datetime.combine(candidate_date, preferred_run_time, tzinfo=timezone)


def _is_candidate_valid(candidate: datetime, reference_local: datetime, *, inclusive: bool) -> bool:
    return candidate >= reference_local if inclusive else candidate > reference_local


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1
