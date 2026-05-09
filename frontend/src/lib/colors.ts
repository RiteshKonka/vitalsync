import type { AgentName } from '../types/agents'

export const DOMAIN_COLORS: Record<string, string> = {
  sleep:      '#7F77DD',
  activity:   '#D85A30',
  nutrition:  '#BA7517',
  stress:     '#1D9E75',
  weather:    '#378ADD',
  correlator: '#993C1D',
  coach:      '#0F6E56',
  supervisor: '#888780',
}

export const DOMAIN_LABELS: Record<string, string> = {
  sleep:      'Sleep',
  activity:   'Activity',
  nutrition:  'Nutrition',
  stress:     'Stress',
  weather:    'Weather',
  correlator: 'Correlator',
  coach:      'Coach',
  supervisor: 'Supervisor',
}

export const DOMAIN_KEY_METRICS: Record<string, string> = {
  sleep:     'deep_sleep_pct',
  activity:  'training_load',
  nutrition: 'caloric_balance',
  stress:    'resting_hr_bpm',
  weather:   'temperature_c',
}

export const DOMAIN_METRIC_LABELS: Record<string, string> = {
  deep_sleep_pct:   'Deep Sleep %',
  training_load:    'Training Load',
  caloric_balance:  'Caloric Balance',
  resting_hr_bpm:   'Resting HR',
  temperature_c:    'Temperature °C',
  hrv_ms:           'HRV (ms)',
  hrv_morning_ms:   'Morning HRV',
  recovery_score:   'Recovery Score',
}

export function agentColor(agent: AgentName): string {
  return DOMAIN_COLORS[agent] ?? '#888780'
}

export function confidenceColor(conf: number): string {
  if (conf >= 0.8) return '#1D9E75'
  if (conf >= 0.6) return '#BA7517'
  return '#D85A30'
}