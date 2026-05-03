import { agentColor, DOMAIN_LABELS } from "../lib/colors";
import type { AgentName } from "../types/agents";

interface Props {
  agent: AgentName;
  size?: "sm" | "md";
}

export default function DomainBadge({ agent, size = "sm" }: Props) {
  const color = agentColor(agent);
  const label = DOMAIN_LABELS[agent] ?? agent;
  const px = size === "sm" ? "6px 10px" : "4px 12px";
  const fs = size === "sm" ? 11 : 12;
  return (
    <span
      style={{
        display: "inline-block",
        padding: px,
        fontSize: fs,
        fontWeight: 500,
        borderRadius: 99,
        background: color + "22",
        color,
        border: `0.5px solid ${color}55`,
      }}
    >
      {label}
    </span>
  );
}
