from __future__ import annotations

from enum import Enum


class CompanyType(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class CoverageStatus(str, Enum):
    WATCHLIST = "watchlist"
    PORTFOLIO = "portfolio"


class Cadence(str, Enum):
    WEEKLY = "weekly"
    MANUAL = "manual"


class RoleType(str, Enum):
    SPECIALIST = "specialist"
    SKEPTIC = "skeptic"
    DURABILITY = "durability"
    JUDGE = "judge"
    LEAD = "lead"
    SYNTHESIZER = "synthesizer"
    GATEKEEPER = "gatekeeper"


class RecordStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    DRAFT = "draft"
    COMPLETE = "complete"


class MemoSectionStatus(str, Enum):
    NOT_ADVANCED = "not_advanced"
    PENDING = "pending"
    DRAFT = "draft"
    REFRESHED = "refreshed"
    STALE = "stale"


class GateDecision(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    FAIL = "fail"


class VerdictRecommendation(str, Enum):
    POSITIVE = "positive"
    MIXED = "mixed"
    NEGATIVE = "negative"
    WATCH = "watch"


class ChangeClassification(str, Enum):
    INITIAL = "initial"
    MATERIAL_CHANGE = "material_change"
    MINOR_REFRESH = "minor_refresh"
    NO_CHANGE = "no_change"


class AlertLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RefreshJobTrigger(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    BULK_WATCHLIST = "bulk_watchlist"
    BULK_PORTFOLIO = "bulk_portfolio"
    RETRY = "retry"
    FORCE_RUN = "force_run"


class RefreshJobStatus(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    REVIEW_REQUIRED = "review_required"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class ReviewNextAction(str, Enum):
    CONTINUE_PROVISIONAL = "continue_provisional"
    RETRY_JOB = "retry_job"
    WAIT = "wait"


class NotificationCategory(str, Enum):
    GATEKEEPER_FAILED = "gatekeeper_failed"
    WORKER_FAILED = "worker_failed"
    MATERIAL_CHANGE = "material_change"
    DAILY_DIGEST = "daily_digest"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    DISPATCHED = "dispatched"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"


class MonitoringChangeType(str, Enum):
    SHARED_RISK_OVERLAP = "shared_risk_overlap"
    CONTRADICTION = "contradiction"
    THESIS_DRIFT = "thesis_drift"
    CONCENTRATION = "concentration"
    SECTION_MOVEMENT = "section_movement"


class RunKind(str, Enum):
    ANALYZE = "analyze"
    REFRESH = "refresh"
    PANEL = "panel"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_CONTINUE = "awaiting_continue"
    GATED_OUT = "gated_out"
    STOPPED = "stopped"
    PROVISIONAL = "provisional"
    COMPLETE = "complete"
    FAILED = "failed"


class RunContinueAction(str, Enum):
    STOP = "stop"
    CONTINUE = "continue"
    CONTINUE_PROVISIONAL = "continue_provisional"
