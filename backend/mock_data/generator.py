"""
mock_data/generator.py
──────────────────────
Generates 90 days of realistic health data with intentional patterns
baked in — most importantly the "Tuesday fatigue loop" that VitalSync
is designed to detect.

Seeded patterns (all discoverable by the agents):
  1. Tuesday training load is 2.3× higher than Monday
  2. Tuesday caloric intake is ~400 kcal below TDEE on training days
  3. Tuesday meals are timed poorly — large carb meal at ~21:00
  4. Tuesday night deep sleep drops to ~12% (vs 22% baseline)
  5. Tuesday night HRV is 18ms below average
  6. Wednesday morning resting HR is 8bpm above baseline
  7. Cold/rainy weather weakly correlates with worse Tuesday performance

All values include realistic noise so the pattern isn't trivially obvious.
"""

from __future__ import annotations

import random
import math
from datetime import date, timedelta
from typing import Any

# Fixed seed for reproducibility across sessions
RNG = random.Random(42)

# ─────────────────────────────────────────────
# User baseline profile
# ─────────────────────────────────────────────

BASELINE = {
    "age":           28,
    "weight_kg":     72,
    "height_cm":     175,
    "tdee_kcal":     2400,      # total daily energy expenditure
    "resting_hr":    58,        # bpm
    "hrv_baseline":  62,        # ms (RMSSD)
    "vo2max":        48,
    "deep_sleep_pct": 22,       # % of total sleep
    "sleep_hours":   7.4,
}

START_DATE = date.today() - timedelta(days=89)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _noise(scale: float = 1.0) -> float:
    """Gaussian noise, zero-centred."""
    return RNG.gauss(0, scale)


def _is_tuesday(d: date) -> bool:
    return d.weekday() == 1   # Monday=0


def _is_wednesday(d: date) -> bool:
    return d.weekday() == 2


def _seasonal_temp(d: date) -> float:
    """Rough Mumbai temperature curve (°C) — warmer in summer."""
    day_of_year = d.timetuple().tm_yday
    base_temp = 28 + 6 * math.sin(2 * math.pi * (day_of_year - 90) / 365)
    return round(base_temp + _noise(1.5), 1)


def _date_range() -> list[date]:
    return [START_DATE + timedelta(days=i) for i in range(90)]


# ─────────────────────────────────────────────
# Sleep data
# ─────────────────────────────────────────────

def generate_sleep_data() -> list[dict[str, Any]]:
    records = []
    for d in _date_range():
        is_tue = _is_tuesday(d)

        total_hours = BASELINE["sleep_hours"] + _noise(0.4)
        total_hours = max(5.0, min(9.5, total_hours))

        # Tuesday night: deep sleep suppressed due to late heavy meal + high load
        deep_pct = (
            BASELINE["deep_sleep_pct"] - 10 + _noise(2)
            if is_tue else
            BASELINE["deep_sleep_pct"] + _noise(3)
        )
        deep_pct = max(8, min(35, deep_pct))

        # HRV: lower on Tuesday nights (high training load + poor nutrition)
        hrv = (
            BASELINE["hrv_baseline"] - 18 + _noise(5)
            if is_tue else
            BASELINE["hrv_baseline"] + _noise(8)
        )
        hrv = max(25, min(95, hrv))

        light_pct = 50 + _noise(4)
        rem_pct   = max(5, 100 - deep_pct - light_pct)

        records.append({
            "date":           d.isoformat(),
            "day_of_week":    d.strftime("%A"),
            "total_hours":    round(total_hours, 1),
            "deep_sleep_pct": round(deep_pct, 1),
            "light_sleep_pct": round(light_pct, 1),
            "rem_sleep_pct":  round(rem_pct, 1),
            "hrv_ms":         round(hrv, 1),
            "sleep_score":    round(60 + (deep_pct - 12) * 1.2 + _noise(5), 0),
            "sleep_start":    "23:30" if is_tue else "22:45",
            "wake_time":      "07:00",
        })
    return records


# ─────────────────────────────────────────────
# Activity data
# ─────────────────────────────────────────────

def generate_activity_data() -> list[dict[str, Any]]:
    records = []
    for d in _date_range():
        is_tue = _is_tuesday(d)
        is_rest = d.weekday() in (5, 6)  # Sat/Sun lighter

        if is_rest:
            workout_mins = 0
            zone3_mins, zone4_mins = 0, 0
            steps = int(6000 + _noise(1000))
            training_load = 0
        elif is_tue:
            # Tuesday: high-intensity long session (the problem day)
            workout_mins  = int(65 + _noise(8))
            zone3_mins    = int(30 + _noise(5))
            zone4_mins    = int(25 + _noise(5))
            steps         = int(12000 + _noise(1500))
            training_load = round(70 + _noise(6), 1)
        else:
            workout_mins  = int(40 + _noise(10))
            zone3_mins    = int(15 + _noise(5))
            zone4_mins    = int(8 + _noise(4))
            steps         = int(9500 + _noise(1500))
            training_load = round(35 + _noise(8), 1)

        records.append({
            "date":              d.isoformat(),
            "day_of_week":       d.strftime("%A"),
            "steps":             max(0, steps),
            "workout_minutes":   max(0, workout_mins),
            "zone1_minutes":     max(0, workout_mins - zone3_mins - zone4_mins),
            "zone3_minutes":     max(0, zone3_mins),
            "zone4_minutes":     max(0, zone4_mins),
            "calories_burned":   max(0, int(training_load * 10 + 1800 + _noise(100))),
            "training_load":     max(0, training_load),
            "workout_type":      "HIIT cardio" if is_tue else ("rest" if is_rest else "moderate"),
        })
    return records


# ─────────────────────────────────────────────
# Nutrition data
# ─────────────────────────────────────────────

def generate_nutrition_data() -> list[dict[str, Any]]:
    records = []
    for d in _date_range():
        is_tue = _is_tuesday(d)

        # Tuesday: undereating + late large carb meal
        if is_tue:
            total_kcal    = int(BASELINE["tdee_kcal"] - 400 + _noise(80))
            dinner_time   = "21:15"
            dinner_carbs  = int(120 + _noise(15))   # large late carb load
            protein_g     = int(110 + _noise(15))
            carbs_g       = int(220 + _noise(20))
            fat_g         = int(65 + _noise(10))
        else:
            total_kcal    = int(BASELINE["tdee_kcal"] + _noise(200))
            dinner_time   = "19:30"
            dinner_carbs  = int(60 + _noise(15))
            protein_g     = int(140 + _noise(15))
            carbs_g       = int(260 + _noise(25))
            fat_g         = int(75 + _noise(10))

        records.append({
            "date":           d.isoformat(),
            "day_of_week":    d.strftime("%A"),
            "total_kcal":     max(1200, total_kcal),
            "protein_g":      max(60, protein_g),
            "carbs_g":        max(80, carbs_g),
            "fat_g":          max(30, fat_g),
            "meal_count":     3,
            "last_meal_time": dinner_time,
            "last_meal_carbs_g": max(20, dinner_carbs),
            "caloric_balance": total_kcal - BASELINE["tdee_kcal"],
            "hydration_ml":   int(2200 + _noise(300)),
        })
    return records


# ─────────────────────────────────────────────
# Stress / recovery data
# ─────────────────────────────────────────────

def generate_stress_data() -> list[dict[str, Any]]:
    records = []
    for d in _date_range():
        is_wed = _is_wednesday(d)
        is_tue = _is_tuesday(d)

        # Wednesday morning: elevated resting HR (incomplete recovery)
        resting_hr = (
            BASELINE["resting_hr"] + 8 + _noise(2)
            if is_wed else
            BASELINE["resting_hr"] + _noise(3)
        )

        # HRV: lower on Tuesday mornings (pre-loaded fatigue)
        hrv_morning = (
            BASELINE["hrv_baseline"] - 12 + _noise(5)
            if is_tue or is_wed else
            BASELINE["hrv_baseline"] + _noise(7)
        )

        recovery_score = round(
            70 - (resting_hr - BASELINE["resting_hr"]) * 2
            + (hrv_morning - BASELINE["hrv_baseline"]) * 0.5
            + _noise(5),
            0
        )

        records.append({
            "date":                  d.isoformat(),
            "day_of_week":           d.strftime("%A"),
            "resting_hr_bpm":        round(max(45, resting_hr), 0),
            "hrv_morning_ms":        round(max(20, hrv_morning), 1),
            "recovery_score":        max(20, min(100, recovery_score)),
            "stress_level":          round(5 + (resting_hr - BASELINE["resting_hr"]) * 0.4 + _noise(1), 1),
            "autonomic_balance":     "parasympathetic" if hrv_morning > 55 else "sympathetic",
        })
    return records


# ─────────────────────────────────────────────
# Weather data (mock — mirrors Open-Meteo schema)
# ─────────────────────────────────────────────

def generate_weather_data() -> list[dict[str, Any]]:
    records = []
    for d in _date_range():
        temp   = _seasonal_temp(d)
        is_tue = _is_tuesday(d)

        # Slight bias: Tuesdays are marginally cooler/rainier in this dataset
        # (weak environmental correlation with fatigue pattern)
        rain_mm = max(0, _noise(3) + (2 if is_tue and RNG.random() > 0.65 else 0))

        records.append({
            "date":             d.isoformat(),
            "day_of_week":      d.strftime("%A"),
            "temperature_c":    temp,
            "humidity_pct":     round(65 + _noise(10), 1),
            "precipitation_mm": round(rain_mm, 1),
            "pressure_hpa":     round(1013 + _noise(4), 1),
            "uv_index":         round(max(0, 6 + _noise(2)), 1),
            "condition":        "rainy" if rain_mm > 3 else ("cloudy" if rain_mm > 0.5 else "sunny"),
        })
    return records


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

# Cache generated data at module level so all MCP tool calls within
# a session see the same consistent dataset.
_cache: dict[str, list] = {}

def get_data(domain: str) -> list[dict[str, Any]]:
    """
    Returns the 90-day dataset for a domain.
    Valid domains: 'sleep', 'activity', 'nutrition', 'stress', 'weather'
    """
    if domain not in _cache:
        generators = {
            "sleep":     generate_sleep_data,
            "activity":  generate_activity_data,
            "nutrition": generate_nutrition_data,
            "stress":    generate_stress_data,
            "weather":   generate_weather_data,
        }
        if domain not in generators:
            raise ValueError(f"Unknown domain: {domain}")
        _cache[domain] = generators[domain]()
    return _cache[domain]


def get_domain_summary(domain: str) -> dict[str, Any]:
    """
    Returns aggregate statistics for a domain — used by agents
    to get a quick overview before deciding which dates to inspect.
    """
    data = get_data(domain)
    if not data:
        return {}

    # Day-of-week averages for key metrics
    from collections import defaultdict
    day_buckets: dict[str, list] = defaultdict(list)

    numeric_keys = [k for k, v in data[0].items() if isinstance(v, (int, float))]

    for row in data:
        day = row["day_of_week"]
        for key in numeric_keys:
            day_buckets[f"{day}_{key}"].append(row[key])

    averages = {
        k: round(sum(v) / len(v), 2)
        for k, v in day_buckets.items()
    }

    return {
        "domain":       domain,
        "record_count": len(data),
        "date_range":   f"{data[0]['date']} to {data[-1]['date']}",
        "day_averages": averages,
    }


def get_weekly_pattern(domain: str, metric: str) -> dict[str, float]:
    """
    Returns the average value of `metric` for each day of the week.
    Useful for agents to quickly spot day-of-week patterns.
    """
    data = get_data(domain)
    from collections import defaultdict

    buckets: dict[str, list] = defaultdict(list)
    for row in data:
        if metric in row and isinstance(row[metric], (int, float)):
            buckets[row["day_of_week"]].append(row[metric])

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return {
        day: round(sum(buckets[day]) / len(buckets[day]), 2)
        for day in days_order
        if buckets[day]
    }