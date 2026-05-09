export interface SleepRecord {
  date:             string
  day_of_week:      string
  total_hours:      number
  deep_sleep_pct:   number
  light_sleep_pct:  number
  rem_sleep_pct:    number
  hrv_ms:           number
  sleep_score:      number
  sleep_start:      string
  wake_time:        string
}

export interface ActivityRecord {
  date:            string
  day_of_week:     string
  steps:           number
  workout_minutes: number
  zone3_minutes:   number
  zone4_minutes:   number
  calories_burned: number
  training_load:   number
  workout_type:    string
}

export interface NutritionRecord {
  date:               string
  day_of_week:        string
  total_kcal:         number
  protein_g:          number
  carbs_g:            number
  fat_g:              number
  caloric_balance:    number
  last_meal_time:     string
  last_meal_carbs_g:  number
}

export interface StressRecord {
  date:              string
  day_of_week:       string
  resting_hr_bpm:    number
  hrv_morning_ms:    number
  recovery_score:    number
  stress_level:      number
  autonomic_balance: string
}

export interface WeatherRecord {
  date:             string
  day_of_week:      string
  temperature_c:    number
  humidity_pct:     number
  precipitation_mm: number
  pressure_hpa:     number
  condition:        string
}

export type DomainRecord =
  | SleepRecord | ActivityRecord | NutritionRecord
  | StressRecord | WeatherRecord

export interface DomainMeta {
  id:         string
  label:      string
  color:      string
  key_metric: string
}

export interface WeeklyPattern {
  Monday:    number
  Tuesday:   number
  Wednesday: number
  Thursday:  number
  Friday:    number
  Saturday:  number
  Sunday:    number
}