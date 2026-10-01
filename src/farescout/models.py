from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now() -> datetime:
    return datetime.now(timezone.utc)


def identity(*parts: object) -> str:
    return sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Constraint(Record):
    field: str
    value: str | bool | int | list[str]
    provenance: Literal["explicit", "inferred", "default", "context"]
    raw_text: str = ""
    rule: str = ""


class Goal(Record):
    origins: list[str] = Field(default_factory=lambda: ["SZX", "HKG"])
    region: str | None = None
    date_from: date
    date_to: date
    trip_type: Literal["one_way", "round_trip"] = "one_way"
    stay_days: int = Field(default=5, ge=1, le=30)
    no_red_eye: bool = False
    date_mode: Literal["flexible", "fixed"] = "flexible"
    constraints: list[Constraint] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def dates_ordered(self):
        if self.date_from > self.date_to:
            raise ValueError("date_from must be <= date_to")
        if not self.origins or len(self.origins) > 4:
            raise ValueError("1–4 origin airports required")
        return self


class GoalPatch(Record):
    origins: list[str] | None = None
    region: str | None = None
    clear_region: bool = False
    date_from: date | None = None
    date_to: date | None = None
    trip_type: Literal["one_way", "round_trip"] | None = None
    stay_days: int | None = None
    no_red_eye: bool | None = None


class Comment(Record):
    text: str
    published_at: str | None = None


class Evidence(Record):
    id: str
    source: str
    kind: Literal["community"] = "community"
    url: str
    query: str
    title: str
    body: str
    comments: list[Comment] = Field(default_factory=list)
    published_at: str | None = None
    observed_at: datetime = Field(default_factory=now)
    warnings: list[str] = Field(default_factory=list)
    quality: dict[str, str | bool | int | list[str]] = Field(default_factory=dict)

    def readable_text(self) -> str:
        return "\n".join([self.body, *[c.text for c in self.comments]])


class Signal(Record):
    evidence_id: str
    excerpt: str = Field(min_length=5, max_length=600)
    seen_price_text: str | None = None
    airline: str | None = None
    promotion: str | None = None


class Candidate(Record):
    origin: str
    destination: str
    destination_name: str
    country: str
    signals: list[Signal] = Field(min_length=1, max_length=8)
    why: str = Field(min_length=5, max_length=800)
    date_hint: date | None = None

    @property
    def key(self) -> str:
        return f"{self.origin}-{self.destination}"


class Expansion(Record):
    query: str = Field(min_length=3, max_length=120)
    evidence_id: str
    discovered_term: str = Field(min_length=2, max_length=60)
    reason: str


class Discovery(Record):
    candidates: list[Candidate] = Field(default_factory=list, max_length=12)
    expansions: list[Expansion] = Field(default_factory=list, max_length=3)


class SearchPlan(Record):
    queries: list[str] = Field(min_length=2, max_length=3)


class FareRequest(Record):
    origin: str
    destination: str
    outbound_date: date
    return_date: date | None = None
    currency: Literal["CNY"] = "CNY"
    adults: Literal[1] = 1
    cabin: Literal["economy"] = "economy"
    no_red_eye: bool = False


class Segment(Record):
    origin: str
    destination: str
    departure: str
    arrival: str
    airline: str = "未知"
    flight_number: str = "未知"


class Fare(Record):
    id: str
    source: str
    kind: Literal["current_verified"] = "current_verified"
    request: FareRequest
    amount: float = Field(gt=0, allow_inf_nan=False)
    currency: Literal["CNY"] = "CNY"
    observed_at: datetime = Field(default_factory=now)
    source_url: str
    segments: list[Segment] = Field(min_length=1)
    price_basis: Literal["total_including_taxes", "adult_fare_tax_unknown"]
    baggage: str = "未确认，不能假定包含托运行李"
    restrictions: list[str] = Field(default_factory=list)
    price_insights: dict = Field(default_factory=dict)


class Event(Record):
    time: datetime = Field(default_factory=now)
    stage: str
    source: str | None = None
    status: Literal["ok", "failed", "skipped", "info"]
    detail: str
    id: str = Field(default_factory=lambda: identity(now().isoformat()))
    turn_id: str = ""
    action_id: str = ""
    parent_action_id: str | None = None
    phase: Literal["started", "completed", "progress"] = "progress"
    evidence_ids: list[str] = Field(default_factory=list)
    duration_ms: int | None = None
    data: dict = Field(default_factory=dict)


class DateSample(Record):
    date: date
    source: str
    stage: Literal["range", "coarse", "fine", "verification"]
    status: Literal["ok", "failed"]
    amount: float | None = None
    price_basis: str | None = None
    detail: str = ""
    observed_at: datetime | None = Field(default_factory=now)


class DateCoverage(Record):
    date_from: date
    date_to: date
    samples: list[DateSample] = Field(default_factory=list)
    returned_dates: list[date] = Field(default_factory=list)
    selected_date: date | None = None
    notes: list[str] = Field(default_factory=list)


class Opportunity(Record):
    candidate: Candidate
    fares: list[Fare] = Field(default_factory=list)
    comparison: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    date_coverage: DateCoverage | None = None
    deal: dict = Field(default_factory=dict)


class Turn(Record):
    id: str
    user_input: str
    started_at: datetime = Field(default_factory=now)
    finished_at: datetime | None = None
    goal: Goal
    events: list[Event] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    expansions: list[Expansion] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    status: Literal["running", "complete", "partial", "blocked"] = "running"
    stop_reason: str = ""
    metrics: dict[str, int | float | str] = Field(default_factory=dict)


class Session(Record):
    schema_version: Literal[1] = 1
    id: str
    goal: Goal
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    turns: list[Turn] = Field(default_factory=list)
