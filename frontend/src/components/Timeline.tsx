import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { useHealthStore } from "../store/healthStore";
import {
  DOMAIN_COLORS,
  DOMAIN_METRIC_LABELS,
  DOMAIN_KEY_METRICS,
} from "../lib/colors";

const DOMAINS = ["sleep", "activity", "nutrition", "stress"];

interface ChartPoint {
  date: string;
  day: string;
  sleep: number;
  activity: number;
  nutrition: number;
  stress: number;
}

function buildChartData(
  data: Record<string, unknown[]>,
  weekly: Record<string, Record<string, number>>,
): ChartPoint[] {
  const sleepRows = (data.sleep ?? []) as Record<string, unknown>[];
  const activityRows = (data.activity ?? []) as Record<string, unknown>[];
  const nutritionRows = (data.nutrition ?? []) as Record<string, unknown>[];
  const stressRows = (data.stress ?? []) as Record<string, unknown>[];

  const len = Math.min(
    sleepRows.length,
    activityRows.length,
    nutritionRows.length,
    stressRows.length,
    14,
  );
  const points: ChartPoint[] = [];

  for (let i = 0; i < len; i++) {
    const s = sleepRows[i];
    const a = activityRows[i];
    const n = nutritionRows[i];
    const st = stressRows[i];
    const dateStr = ((s.date as string) ?? "").slice(5); // MM-DD
    const day = ((s.day_of_week as string) ?? "").slice(0, 3);

    points.push({
      date: dateStr,
      day: day,
      sleep: +((s.deep_sleep_pct as number) ?? 0).toFixed(1),
      activity: +((a.training_load as number) ?? 0).toFixed(1),
      nutrition: Math.abs(+((n.caloric_balance as number) ?? 0)) / 10, // scale to 0-100
      stress: +((st.resting_hr_bpm as number) ?? 0) - 40, // normalise around 0
    });
  }

  return points;
}

const LINES = [
  { key: "sleep", color: DOMAIN_COLORS.sleep, label: "Deep Sleep %" },
  { key: "activity", color: DOMAIN_COLORS.activity, label: "Training Load" },
  {
    key: "nutrition",
    color: DOMAIN_COLORS.nutrition,
    label: "Cal Deficit /10",
  },
  { key: "stress", color: DOMAIN_COLORS.stress, label: "Resting HR −40" },
];

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "#1a1d2b",
        border: "0.5px solid #2a2d3a",
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 12,
      }}
    >
      <div style={{ color: "#8a8d9e", marginBottom: 6 }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color, marginBottom: 2 }}>
          {p.name}: <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  );
}

export default function Timeline() {
  const { data, weekly, loading, loadWeekly } = useHealthStore();
  const [view, setView] = useState<"timeline" | "weekly">("timeline");

  useEffect(() => {
    if (view === "weekly") {
      loadWeekly("sleep", "deep_sleep_pct");
      loadWeekly("activity", "training_load");
      loadWeekly("stress", "resting_hr_bpm");
      loadWeekly("nutrition", "caloric_balance");
    }
  }, [view]);

  const chartData = buildChartData(data, weekly);

  // Weekly view data
  const DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];
  const weeklyData = DAYS.map((day) => ({
    day: day.slice(0, 3),
    sleep: weekly["sleep.deep_sleep_pct"]?.[day] ?? 0,
    activity: weekly["activity.training_load"]?.[day] ?? 0,
    stress: weekly["stress.resting_hr_bpm"]?.[day] ?? 0,
  }));

  return (
    <div
      style={{
        background: "#13151f",
        border: "0.5px solid #1e2030",
        borderRadius: 14,
        padding: "16px",
        height: "100%",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 16,
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 500, color: "#e8eaf0" }}>
          Health Timeline
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          {(["timeline", "weekly"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                fontSize: 11,
                padding: "3px 10px",
                borderRadius: 99,
                cursor: "pointer",
                background: view === v ? "#7F77DD" : "transparent",
                color: view === v ? "#fff" : "#555",
                border: `0.5px solid ${view === v ? "#7F77DD" : "#2a2d3a"}`,
              }}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div
          style={{
            height: 200,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#555",
            fontSize: 13,
          }}
        >
          Loading health data…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart
            data={view === "timeline" ? chartData : weeklyData}
            margin={{ top: 4, right: 8, left: -20, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" />
            <XAxis
              dataKey={view === "timeline" ? "day" : "day"}
              tick={{ fontSize: 10, fill: "#555" }}
              axisLine={{ stroke: "#1e2030" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#555" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              formatter={(v) => <span style={{ color: "#8a8d9e" }}>{v}</span>}
            />
            {LINES.map((l) => (
              <Line
                key={l.key}
                type="monotone"
                dataKey={l.key}
                name={l.label}
                stroke={l.color}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 4, fill: l.color }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}

      <div
        style={{
          marginTop: 12,
          padding: "8px 12px",
          background: "#BA751710",
          borderRadius: 8,
          border: "0.5px solid #BA751730",
        }}
      >
        <span style={{ fontSize: 11, color: "#BA7517" }}>
          Tip: Switch to <strong>weekly</strong> view to see the Tuesday pattern
          — deep sleep drops to ~12% vs 22% every other day.
        </span>
      </div>
    </div>
  );
}
