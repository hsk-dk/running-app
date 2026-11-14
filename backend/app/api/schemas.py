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
    # Google-encoded polyline of the route, or None (treadmill, manual entry)
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


class RouteOut(BaseModel):
    id: int
    date: str | None
    name: str | None = None
    distance_km: float
    duration_min: float = 0
    route: str


class IndoorOut(BaseModel):
    id: int
    date: str | None
    name: str | None = None
    distance_km: float
    duration_min: float = 0


class OtherOut(BaseModel):
    id: int
    date: str | None
    kind: str  # Walk, Ride, Row, Paddle, Swim, Strength or Other
    name: str | None = None
    distance_km: float = 0
    duration_min: float = 0


class SplitOut(BaseModel):
    km: int
    distance_m: float
    time_s: int
    pace_s_per_km: float
    elevation_m: float | None
    partial: bool
    avg_hr: float | None = None


class ProfileSeriesOut(BaseModel):
    t: list[float]
    d: list[float]
    hr: list[float | None] | None = None
    v: list[float | None] | None = None
    cad: list[float | None] | None = None
    alt: list[float | None] | None = None


class RunProfileOut(BaseModel):
    id: int
    date: str | None
    name: str | None = None
    distance_km: float
    duration_min: float
    avg_hr: float | None = None
    profile: ProfileSeriesOut


class ReadDetailsOut(BaseModel):
    read: int
    failed: int
    remaining: int


class LapOut(BaseModel):
    start_s: float | None = None
    duration_s: float
    distance_m: float | None = None
    avg_hr: float | None = None
    pace_s_per_km: float | None = None
    intensity: str | None = None


class ProfileOut(BaseModel):
    # available=False: Garmin could not be asked right now. source=False: this run does not come from Garmin.
    available: bool
    source: bool
    profile: ProfileSeriesOut | None = None
    laps: list[LapOut] = []


class SplitsOut(BaseModel):
    # available=False: the source could not be asked right now (not connected, or an error). Try again later.
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




class SmashrunStatusOut(BaseModel):
    connected: bool
    configured: bool
    mode: Literal["oauth", "token"] | None = None
    expires_at: str | None = None  # only for a personal token
    expired: bool = False


class SmashrunTokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class GarminStatusOut(BaseModel):
    connected: bool
    last_sync_at: str | None = None
    last_error: str | None = None


class GarminKeyIn(BaseModel):
    key: str = Field(min_length=1, max_length=700)


class RunnaStatusOut(BaseModel):
    connected: bool
    last_sync_at: str | None = None
    last_error: str | None = None


class RunnaLinkIn(BaseModel):
    url: str = Field(min_length=1, max_length=300)


class MeOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    sharing_level: str
    is_child: bool = False
    family_sharing_enabled: bool
    smashrun: SmashrunStatusOut
    runna: RunnaStatusOut
    garmin: GarminStatusOut


class PersonOut(BaseModel):
    id: int
    name: str
    username: str
    role: str
    is_child: bool


class ChildUpdate(BaseModel):
    is_child: bool


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


class FirstOut(BaseModel):
    key: str
    label: str
    date: str
    is_new: bool = False


class NextUpOut(BaseModel):
    key: str
    label: str
    current: float
    target: float
    unit: str


class FirstsOut(BaseModel):
    achieved: list[FirstOut]
    next: list[NextUpOut]


class FamilyMilestoneOut(BaseModel):
    key: str
    label: str
    date: str


Weekday = Literal[0, 1, 2, 3, 4, 5, 6]


class ChallengePlan(BaseModel):
    """What a daily challenge is: a name, a unit, a start that grows a little every so many days, and the days off."""

    name: str = Field(min_length=1, max_length=40)
    unit: Literal["stk", "sek", "min"] = "stk"
    start_value: int = Field(ge=1, le=10000)
    step: int = Field(default=1, ge=0, le=1000)
    step_every_days: int = Field(default=7, ge=1, le=60)
    cap: int | None = Field(default=None, ge=1, le=100000)
    rest_weekdays: list[Weekday] = Field(default_factory=list, max_length=6)


class ChallengeCreate(ChallengePlan):
    start_date: date | None = None


class ChallengeShare(BaseModel):
    day: date | None = None


class ChallengeLog(BaseModel):
    count: int = Field(ge=0, le=100000)
    day: date | None = None  # today when left out


class ChallengeDayOut(BaseModel):
    date: str
    target: int | None
    count: int | None
    status: str


class ChallengePlanOut(BaseModel):
    start_value: int
    step: int
    step_every_days: int
    cap: int | None
    rest_weekdays: list[int]
    start_date: str


class ChallengeHistoryDay(BaseModel):
    date: str
    target: int | None
    count: int | None


class ChallengeProgress(BaseModel):
    first_count: int
    recent_best: int | None
    weeks: int


class ChallengeOut(BaseModel):
    id: int
    name: str
    unit: str
    today_target: int | None
    today_count: int | None
    today_done: bool
    rest_today: bool
    not_started: bool
    streak_days: int
    done_week: int
    planned_week: int
    best_day: int
    new_best_today: bool = False
    shared_today: bool = False
    progress: ChallengeProgress | None = None
    history: list[ChallengeHistoryDay] = Field(default_factory=list)
    total: int
    week: list[ChallengeDayOut]
    plan: ChallengePlanOut


class GuardianChallengeOut(BaseModel):
    name: str
    unit: str = "stk"
    done_week: int
    planned_week: int
    streak_days: int
    first_count: int | None = None
    recent_best: int | None = None
    weeks: int | None = None


class GuardianOut(BaseModel):
    """What a parent sees about a child: how often and for how long, not how far or how fast."""

    runs_week: int
    active_days_week: int
    minutes_week: int
    runs_month: int
    minutes_month: int
    last_run_date: str | None
    streak_weeks: int
    challenges: list[GuardianChallengeOut] = Field(default_factory=list)


class GoalOut(BaseModel):
    target_km: float | None
    km: float
    month: str


class GoalUpdate(BaseModel):
    target_km: float | None = Field(default=None, ge=1, le=5000)


class FamilyMemberOut(BaseModel):
    user_id: int
    name: str
    is_me: bool
    level: Literal["private", "overview", "all", "milestones", "guardian"]
    shared: bool
    week: FamilyWeekOut | None
    month_km: float | None
    month_runs: int | None
    streak_weeks: int | None
    recent_runs: list[FamilyRunOut] | None
    new_milestones: list[FamilyMilestoneOut] | None = None
    is_child: bool = False
    guardian: GuardianOut | None = None


class BragOut(BaseModel):
    """Something a person chose to show the family, with the number."""

    user_id: int
    name: str
    is_me: bool
    challenge: str
    unit: str
    count: int
    date: str


class FamilyOut(BaseModel):
    members: list[FamilyMemberOut]
    total_km_this_month: float
    sharing_enabled: bool
    goal: GoalOut
    brags: list[BragOut] = Field(default_factory=list)
