import { useState, KeyboardEvent } from "react";

const SUGGESTIONS = [
  "Why do I feel exhausted on Wednesdays?",
  "Why is my sleep quality poor on Tuesday nights?",
  "What causes my low recovery scores on Wednesday mornings?",
  "Does the weather affect my performance?",
  "Analyse my overall health patterns this week",
];

interface Props {
  onSend: (query: string) => void;
  isRunning: boolean;
}

export default function ChatBar({ onSend, isRunning }: Props) {
  const [query, setQuery] = useState("");
  const [showHints, setShowHints] = useState(false);

  function submit(q: string) {
    const trimmed = q.trim();
    if (!trimmed || isRunning) return;
    setQuery("");
    setShowHints(false);
    onSend(trimmed);
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") submit(query);
    if (e.key === "Escape") setShowHints(false);
  }

  return (
    <div style={{ position: "relative" }}>
      {showHints && (
        <div
          style={{
            position: "absolute",
            bottom: "100%",
            left: 0,
            right: 0,
            marginBottom: 8,
            background: "#1a1d2b",
            border: "0.5px solid #2a2d3a",
            borderRadius: 12,
            overflow: "hidden",
            zIndex: 10,
          }}
        >
          {SUGGESTIONS.map((s) => (
            <div
              key={s}
              onClick={() => submit(s)}
              style={{
                padding: "10px 16px",
                fontSize: 13,
                color: "#b0b3c0",
                cursor: "pointer",
                borderBottom: "0.5px solid #2a2d3a",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "#22253a")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              {s}
            </div>
          ))}
        </div>
      )}

      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          background: "#1a1d2b",
          border: "0.5px solid #2a2d3a",
          borderRadius: 12,
          padding: "8px 12px",
        }}
      >
        <button
          onClick={() => setShowHints((v) => !v)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 16,
            color: "#555",
            padding: "0 4px",
          }}
          title="Sample queries"
        >
          ✦
        </button>

        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKey}
          onFocus={() => setShowHints(false)}
          placeholder="Ask a health question — e.g. Why do I feel exhausted on Wednesdays?"
          disabled={isRunning}
          style={{
            flex: 1,
            background: "none",
            border: "none",
            outline: "none",
            fontSize: 14,
            color: "#e8eaf0",
            caretColor: "#7F77DD",
          }}
        />

        <button
          onClick={() => submit(query)}
          disabled={isRunning || !query.trim()}
          style={{
            background: isRunning ? "#2a2d3a" : "#7F77DD",
            border: "none",
            borderRadius: 8,
            padding: "6px 16px",
            color: isRunning ? "#555" : "#fff",
            fontSize: 13,
            fontWeight: 500,
            cursor: isRunning ? "not-allowed" : "pointer",
            transition: "background .15s",
          }}
        >
          {isRunning ? "Running…" : "Ask →"}
        </button>
      </div>
    </div>
  );
}
