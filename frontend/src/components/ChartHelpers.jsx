import { MdDeleteOutline } from "react-icons/md";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";

// ── Timestamp formatter ───────────────────────────────────────────────────────
// - Same day:       "14:32:05"
// - Yesterday:      "Yesterday 14:32"
// - This week:      "Mon 14:32"
// - Older:          "12 Jan 14:32"
export function formatTimestamp(isoString) {
  const date  = new Date(isoString);
  const now   = new Date();

  const isToday     = date.toDateString() === now.toDateString();
  const yesterday   = new Date(now); yesterday.setDate(now.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();

  const daysDiff = (now - date) / (1000 * 60 * 60 * 24);
  const isThisWeek = daysDiff < 7;

  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const timeShort = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  if (isToday)     return time;
  if (isYesterday) return `Yesterday ${timeShort}`;
  if (isThisWeek)  return `${date.toLocaleDateString([], { weekday: "short" })} ${timeShort}`;
  return `${date.toLocaleDateString([], { day: "numeric", month: "short" })} ${timeShort}`;
}

// ── Shared tooltip ─────────────────────────────────────────────────────────────
export function ChartTooltip({ active, payload, label, unit }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background:   "var(--surface)",
      border:       "1px solid var(--border-strong)",
      borderRadius: 8,
      padding:      "10px 14px",
      fontSize:     13,
      fontFamily:   "var(--font-mono)",
      boxShadow:    "var(--shadow)",
    }}>
      <p style={{ color: "var(--text-secondary)", marginBottom: 4 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color, fontWeight: 600 }}>
          {p.value?.toFixed(2)} {unit}
        </p>
      ))}
    </div>
  );
}

// ── Individual chart card ──────────────────────────────────────────────────────
export function ChartCard({ snapshot, onRemove }) {
  const { label, unit, color, dataKey, data, loadedAt } = snapshot;

  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <div>
          <span className="chart-card-title">{label}</span>
          <span className="chart-card-meta">
            {data.length} readings · {loadedAt}
          </span>
        </div>
        <button
          className="btn btn-ghost chart-card-remove"
          onClick={onRemove}
          title="Remove this chart"
        >
          <MdDeleteOutline size={18} />
        </button>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 11, fill: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={false}
            unit={unit}
            width={52}
          />
          <Tooltip content={<ChartTooltip unit={unit} />} />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3, fill: color, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
