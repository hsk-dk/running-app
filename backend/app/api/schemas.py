from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TargetType = Literal["time", "distance"]


def _validate_planned_date(value: str) -> str:
    value = value.strip()
    try:
        datetime.fromisoformat(value) if "T" in value or " " in value else date.fromisoformat(value)
    except ValueError:
        raise ValueError("must be an ISO date, e.g. 2026-11-12")
    return value


class _PlanInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    planned_date: str
    session_type: str = Field(min_length=1, max_length=50)
    optional: bool = False
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("planned_date")
    @classmethod
    def _date(cls, v: str) -> str:
        return _validate_planned_date(v)

    @field_validator("session_type")
    @classmethod
    def _session_type(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class PlannedRunCreate(_PlanInput):
    target_type: TargetType = "time"
    target_value: float | None = Field(default=None, ge=0)
    target_minutes: int | None = Field(default=None, ge=0)


class PlannedRunUpdate(_PlanInput):
    target_type: TargetType
    target_value: float | None = Field(ge=0)


class MatchActivityRequest(BaseModel):
    activity_id: int = Field(gt=0)


class PlannedRunOut(BaseModel):
    id: int
    planned_date: str
    session_type: str
    target_type: str
    target_value: float | None
    mandatory: bool
    optional: bool
    notes: str | None
    status: str
    manual_override: bool
    override_reason: str | None
    matched_activity_id: int | None
    matched_activity_date: str | None
    matched_activity_name: str | None
    actual_value: float | None
    display_target: str
    display_actual: str
    evaluated_at: str | None
    match_score: float | None
    match_reason: str | None


class ActivityOut(BaseModel):
    id: int
    date: str | None
    name: str | None
    distance_km: float
    duration_min: float
    avg_hr: float | None
    is_extra: bool
    matched_planned_run_id: int | None


class ActivityDetailOut(ActivityOut):
    start_time_local: str | None
    elevation_gain_m: float | None
    avg_pace_s_per_km: float | None
    max_hr: float | None
    # Google-encoded polyline of a simplified route from Strava, or None (treadmill, manual entry)
    route: str | None


class FamilyActivityOut(BaseModel):
    """A run as other family members see it: no heart rate and no plan details."""

    id: int
    date: str | None
    name: str | None
    distance_km: float
    duration_min: float


class FamilyActivityDetailOut(FamilyActivityOut):
    start_time_local: str | None
    elevation_gain_m: float | None
    avg_pace_s_per_km: float | None
    route: str | None


class SplitOut(BaseModel):
    km: int
    distance_m: float
    time_s: int
    pace_s_per_km: float
    elevation_m: float | None
    partial: bool


class SplitsOut(BaseModel):
    # available=False: Strava could not be asked right now (not connected, or an error). Try again later.
    available: bool
    splits: list[SplitOut]


class MonthlyVolumeOut(BaseModel):
    month: str
    km: float


class WeeklyConsistencyOut(BaseModel):
    week: str
    mandatory_runs: int
    relevant_runs: int
    completed: int
    shortened: int
    score: str


class DeletedOut(BaseModel):
    deleted: int


class HealthOut(BaseModel):
    ok: bool
    mismatch_count: int


class StravaWebhookEvent(BaseModel):
    """Strava push event. Everything is optional: unknown/partial events are
    stored and ignored by the service rather than rejected."""

    model_config = ConfigDict(extra="allow")

    object_type: str | None = None
    object_id: int | None = None
    aspect_type: str | None = None
    owner_id: int | str | None = None
    subscription_id: int | str | None = None
    event_time: int | None = None
    updates: dict | None = None


class StravaStatusOut(BaseModel):
    connected: bool
    configured: bool
    athlete_id: str | None


class SmashrunStatusOut(BaseModel):
    connected: bool
    configured: bool
    mode: Literal["oauth", "token"] | None = None
    expires_at: str | None = None  # only for a personal token
    expired: bool = False


class SmashrunTokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class MeOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    sharing_level: str
    family_sharing_enabled: bool
    strava: StravaStatusOut
    smashrun: SmashrunStatusOut


class MeUpdate(BaseModel):
    sharing_level: Literal["private", "overview", "all"] | None = None
    display_name: str | None = Field(default=None, max_length=60)


class ConnectOut(BaseModel):
    url: str


class FamilyRunOut(BaseModel):
    id: int
    date: str | None
    name: str | None
    distance_km: float
    duration_min: float


class FamilyWeekOut(BaseModel):
    done: int
    total: int
    open: int


class FamilyMemberOut(BaseModel):
    user_id: int
    name: str
    is_me: bool
    level: Literal["private", "overview", "all"]
    shared: bool
    strava_connected: bool
    week: FamilyWeekOut | None
    month_km: float | None
    month_runs: int | None
    streak_weeks: int | None
    recent_runs: list[FamilyRunOut] | None


class FamilyOut(BaseModel):
    members: list[FamilyMemberOut]
    total_km_this_month: float
    sharing_enabled: bool
