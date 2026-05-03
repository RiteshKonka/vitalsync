"""
schemas/health.py
─────────────────
Pydantic models for every health domain record.

These mirror the dicts returned by mock_data/generator.py and
the MCP tools. Used for:
  - Validating data coming out of the mock generator / real APIs
  - Type-safe access in agents (convert raw dicts → typed models)
  - FastAPI response serialisation on /api/data/{domain} endpoints
  - TypeScript type generation (if you add openapi-ts to the build)

Naming convention: <Domain>Record for raw daily records,
<Domain>Summary for aggregated stats.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────

DayOfWeek = Literal[
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


class WeeklyPattern(BaseModel):
    """Day-of-week averages for a single metric."""
    Monday:    float
    Tuesday:   float
    Wednesday: float
    Thursday:  float
    Friday:    float
    Saturday:  float
    Sunday:    float

    def highest_day(self) -> str:
        return max(self.model_dump(), key=lambda k: self.model_dump()[k])

    def lowest_day(self) -> str:
        return min(self.model_dump(), key=lambda k: self.model_dump()[k])

    def tuesday_vs_avg(self) -> float:
        """How much Tuesday deviates from the 7-day average."""
        vals = list(self.model_dump().values())
        avg  = sum(vals) / len(vals)
        return round(self.Tuesday - avg, 2)


# ── Sleep ─────────────────────────────────────────────────────────

class SleepRecord(BaseModel):
    date:             str
    day_of_week:      DayOfWeek
    total_hours:      float = Field(ge=0, le=14)
    deep_sleep_pct:   float = Field(ge=0, le=100, description="% of total sleep in deep/N3 stage")
    light_sleep_pct:  float = Field(ge=0, le=100)
    rem_sleep_pct:    float = Field(ge=0, le=100)
    hrv_ms:           float = Field(ge=0, description="RMSSD HRV during sleep (ms)")
    sleep_score:      float = Field(ge=0, le=100)
    sleep_start:      str   = Field(description="HH:MM format")
    wake_time:        str   = Field(description="HH:MM format")

    @property
    def is_poor_deep_sleep(self) -> bool:
        return self.deep_sleep_pct < 15.0

    @property
    def is_low_hrv(self) -> bool:
        return self.hrv_ms < 44.0


class SleepSummary(BaseModel):
    avg_total_hours:    float
    avg_deep_sleep_pct: float
    avg_hrv_ms:         float
    avg_sleep_score:    float
    worst_day:          DayOfWeek
    best_day:           DayOfWeek
    tuesday_deep_pct:   float
    deep_pct_deficit_tuesday: float   # how much lower than average


# ── Activity ──────────────────────────────────────────────────────

class ActivityRecord(BaseModel):
    date:             str
    day_of_week:      DayOfWeek
    steps:            int   = Field(ge=0)
    workout_minutes:  int   = Field(ge=0)
    zone1_minutes:    int   = Field(ge=0, description="Light activity zone")
    zone3_minutes:    int   = Field(ge=0, description="Aerobic zone (moderate-hard)")
    zone4_minutes:    int   = Field(ge=0, description="Threshold zone (hard)")
    calories_burned:  int   = Field(ge=0)
    training_load:    float = Field(ge=0, description="Composite training stress score")
    workout_type:     str

    @property
    def high_intensity_minutes(self) -> int:
        return self.zone3_minutes + self.zone4_minutes

    @property
    def is_high_load(self) -> bool:
        return self.training_load > 60.0


class ActivitySummary(BaseModel):
    avg_training_load:       float
    avg_workout_minutes:     float
    avg_steps:               float
    avg_zone34_minutes:      float
    highest_load_day:        DayOfWeek
    tuesday_training_load:   float
    tuesday_zone34_minutes:  float
    load_ratio_tuesday:      float   # tuesday / weekly average


# ── Nutrition ─────────────────────────────────────────────────────

class NutritionRecord(BaseModel):
    date:                str
    day_of_week:         DayOfWeek
    total_kcal:          int   = Field(ge=0)
    protein_g:           float = Field(ge=0)
    carbs_g:             float = Field(ge=0)
    fat_g:               float = Field(ge=0)
    meal_count:          int   = Field(ge=0)
    last_meal_time:      str   = Field(description="HH:MM format")
    last_meal_carbs_g:   float = Field(ge=0)
    caloric_balance:     float = Field(description="kcal vs TDEE (negative = deficit)")
    hydration_ml:        int   = Field(ge=0)

    @property
    def is_late_meal(self) -> bool:
        """True if last meal was after 20:30."""
        try:
            h, m = map(int, self.last_meal_time.split(":"))
            return h > 20 or (h == 20 and m >= 30)
        except ValueError:
            return False

    @property
    def is_deficit_day(self) -> bool:
        return self.caloric_balance < -200


class NutritionSummary(BaseModel):
    avg_caloric_balance:      float
    avg_protein_g:            float
    tuesday_caloric_balance:  float
    tuesday_last_meal_time:   str
    tuesday_late_meal_carbs:  float
    caloric_deficit_delta:    float   # tuesday deficit vs average


# ── Stress / Recovery ─────────────────────────────────────────────

class StressRecord(BaseModel):
    date:               str
    day_of_week:        DayOfWeek
    resting_hr_bpm:     float = Field(ge=30, le=120)
    hrv_morning_ms:     float = Field(ge=0, description="Morning RMSSD HRV (ms)")
    recovery_score:     float = Field(ge=0, le=100)
    stress_level:       float = Field(ge=0, le=10)
    autonomic_balance:  Literal["parasympathetic", "sympathetic"]

    @property
    def is_under_recovered(self) -> bool:
        return self.recovery_score < 50

    @property
    def is_elevated_hr(self) -> bool:
        return self.resting_hr_bpm > 65   # approximate threshold


class StressSummary(BaseModel):
    avg_resting_hr:           float
    avg_hrv_morning:          float
    avg_recovery_score:       float
    wednesday_resting_hr:     float
    wednesday_hrv_morning:    float
    wednesday_recovery_score: float
    hr_elevation_wednesday:   float   # bpm above average


# ── Weather ───────────────────────────────────────────────────────

class WeatherRecord(BaseModel):
    date:             str
    day_of_week:      DayOfWeek
    temperature_c:    float
    humidity_pct:     float = Field(ge=0, le=100)
    precipitation_mm: float = Field(ge=0)
    pressure_hpa:     float
    condition:        Literal["sunny", "cloudy", "rainy"]
    uv_index:         Optional[float] = None
    windspeed_kmh:    Optional[float] = None

    @property
    def is_heat_stress_risk(self) -> bool:
        return self.temperature_c > 32 and self.humidity_pct > 75


class WeatherSummary(BaseModel):
    avg_temperature_c:          float
    tuesday_avg_temperature_c:  float
    tuesday_rain_frequency_pct: float
    avg_humidity_pct:           float
    correlation_strength:       Literal["none", "weak", "moderate", "strong"]


# ── User profile ──────────────────────────────────────────────────

class UserProfile(BaseModel):
    name:           str
    age:            int  = Field(ge=10, le=100)
    weight_kg:      float
    height_cm:      float
    tdee_kcal:      int
    resting_hr:     int
    hrv_baseline:   float
    goals:          list[str]
    training_days:  list[DayOfWeek]

    @property
    def bmi(self) -> float:
        h_m = self.height_cm / 100
        return round(self.weight_kg / (h_m ** 2), 1)