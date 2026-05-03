"""
mock_data/patterns.py
─────────────────────
Documents and exports every seeded pattern in the mock dataset.

This file serves two purposes:
  1. Single source of truth for what patterns the agents should find
     (use this to write tests, check agent output quality)
  2. Pattern injection helpers used by generator.py to apply each
     pattern to the raw time-series data

Patterns are designed to be:
  - Real (based on actual sports science / sleep research)
  - Discoverable (strong enough signal for the agents to find)
  - Cross-domain (require the correlator to surface, not a single agent)
  - Noisy (realistic variance so they're not trivially obvious)

PRIMARY PATTERN — Tuesday Fatigue Loop
───────────────────────────────────────
Causal chain:
  Tuesday: high training load (69 vs 22 avg)
    → Tuesday: caloric deficit (-420 kcal vs -20 avg)
    → Tuesday: late heavy carb meal (21:15 vs 19:30 avg, 120g carbs)
    → Tuesday night: deep sleep suppressed (11% vs 22% avg)
    → Tuesday night: HRV suppressed (44ms vs 62ms avg)
    → Wednesday morning: elevated resting HR (66 vs 58 avg)
    → Wednesday: subjective fatigue / brain fog

SECONDARY PATTERN — Rainy Tuesday amplification
─────────────────────────────────────────────────
Weak weather correlation:
  Rainy/cold Tuesdays → perceived exertion +15%
    → same workout feels harder → greater physiological stress
    → slightly worse recovery scores

These patterns are detectable at the following thresholds:
  - Sleep deep%:   Tuesday delta ≥ 8pp below avg
  - Training load: Tuesday / avg ≥ 2.5×
  - Resting HR:    Wednesday ≥ 6bpm above avg
  - Cal balance:   Tuesday ≤ -300 kcal
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


# ── Pattern definitions ────────────────────────────────────────────

@dataclass
class PatternSpec:
    """Describes a single seeded pattern for documentation and testing."""
    name:          str
    domains:       list[str]
    trigger_day:   str   # day the root cause occurs
    effect_day:    str   # day the symptom manifests
    description:   str
    expected_deltas: dict[str, Any]   # metric → expected deviation from baseline
    min_confidence: float             # minimum confidence an agent should report


TUESDAY_FATIGUE_LOOP = PatternSpec(
    name="Tuesday Fatigue Loop",
    domains=["activity", "nutrition", "sleep", "stress"],
    trigger_day="Tuesday",
    effect_day="Wednesday",
    description=(
        "High Tuesday training load combined with caloric underfueling and "
        "a late high-carb meal suppresses deep sleep and HRV, resulting in "
        "incomplete recovery and Wednesday fatigue."
    ),
    expected_deltas={
        "sleep.deep_sleep_pct":       {"direction": "down", "magnitude_pp": 10},
        "sleep.hrv_ms":               {"direction": "down", "magnitude_ms": 18},
        "activity.training_load":     {"direction": "up",   "ratio": 3.0},
        "activity.zone34_minutes":    {"direction": "up",   "magnitude_min": 30},
        "nutrition.caloric_balance":  {"direction": "down", "magnitude_kcal": 400},
        "nutrition.last_meal_carbs_g":{"direction": "up",   "magnitude_g": 60},
        "stress.resting_hr_bpm":      {"direction": "up",   "magnitude_bpm": 7, "day": "Wednesday"},
        "stress.hrv_morning_ms":      {"direction": "down", "magnitude_ms": 12, "day": "Wednesday"},
        "stress.recovery_score":      {"direction": "down", "magnitude_pts": 15,"day": "Wednesday"},
    },
    min_confidence=0.70,
)

RAINY_TUESDAY_AMPLIFICATION = PatternSpec(
    name="Rainy Tuesday Amplification",
    domains=["weather", "activity", "stress"],
    trigger_day="Tuesday",
    effect_day="Tuesday",
    description=(
        "On rainy/cool Tuesdays, perceived exertion during the high-intensity "
        "session is elevated, leading to marginally greater training stress."
    ),
    expected_deltas={
        "weather.precipitation_mm":   {"direction": "up",   "magnitude_mm": 2},
        "stress.recovery_score":       {"direction": "down", "magnitude_pts": 5},
    },
    min_confidence=0.35,   # weak signal by design
)

ALL_PATTERNS: list[PatternSpec] = [
    TUESDAY_FATIGUE_LOOP,
    RAINY_TUESDAY_AMPLIFICATION,
]


# ── Test helpers (used in unit tests to validate agent output) ────

def validate_agent_found_pattern(
    insight_messages: list,
    pattern: PatternSpec,
) -> dict[str, Any]:
    """
    Checks whether the domain agent InsightMessages collectively
    contain enough evidence to confirm the given pattern was found.

    Returns a report dict:
    {
        "pattern": pattern.name,
        "domains_with_evidence": [...],
        "domains_missing": [...],
        "overall_pass": bool
    }
    """
    domains_with_evidence = []
    domains_missing = []

    insight_by_domain = {msg.domain: msg for msg in insight_messages}

    for domain in pattern.domains:
        msg = insight_by_domain.get(domain)
        if msg and msg.confidence >= pattern.min_confidence * 0.8:
            domains_with_evidence.append(domain)
        else:
            domains_missing.append(domain)

    overall_pass = len(domains_with_evidence) >= max(2, len(pattern.domains) - 1)

    return {
        "pattern":               pattern.name,
        "domains_with_evidence": domains_with_evidence,
        "domains_missing":       domains_missing,
        "overall_pass":          overall_pass,
        "coverage":              f"{len(domains_with_evidence)}/{len(pattern.domains)}",
    }


# ── Pattern injection parameters (used by generator.py) ──────────
# These constants are what the generator.py uses to apply the patterns.
# Documented here as the authoritative source.

PATTERN_PARAMS = {
    "tuesday_deep_sleep_suppression_pp": 10,    # percentage points below baseline
    "tuesday_hrv_suppression_ms":        18,    # ms below baseline (sleep HRV)
    "tuesday_training_load_multiplier":  2.0,   # × Monday's load
    "tuesday_caloric_deficit_kcal":      400,   # extra deficit vs other days
    "tuesday_late_meal_hour":            21,    # last meal at 21:xx
    "tuesday_late_meal_carbs_g":         120,   # late carb load
    "wednesday_resting_hr_elevation_bpm": 8,   # above personal baseline
    "wednesday_hrv_suppression_ms":       12,  # morning HRV below baseline
    "rainy_tuesday_frequency":            0.40, # 40% of Tuesdays have rain
    "noise_scale":                        1.0,  # global noise multiplier (1.0 = realistic)
}