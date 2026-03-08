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


class RunKind(str, Enum):
    ANALYZE = "analyze"
    REFRESH = "refresh"
    PANEL = "panel"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"

