import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MdArrowBack, MdDeleteOutline } from "react-icons/md";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { getSensorHistory } from "../api/sensors";

const LIMIT_OPTIONS = [20, 50, 100, 200, 500];

const SENSOR_TYPES = [
  { value: "temperature_c", label: "Temperature", unit: "°C",  color: "var(--sensor)" },
  { value: "humidity_rh",   label: "Humidity",    unit: "%",   color: "var(--led)"    },
];

// ── Timestamp formatter ───────────────────────────────────────────────────────
// - Same day:       "14:32:05"
// - Yesterday:      "Yesterday 14:32"
// - This week:      "Mon 14:32"
// - Older:          "12 Jan 14:32"
function formatTimestamp(isoString) {
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
function ChartTooltip({ active, payload, label, unit }) {
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
function ChartCard({ snapshot, onRemove }) {
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

// ── Page ───────────────────────────────────────────────────────────────────────
export default function SensorHistory() {
  const { node_id } = useParams();
  const nodeId      = node_id ? parseInt(node_id, 10) : 2;
  const navigate    = useNavigate();

  const [sensorType, setSensorType] = useState("temperature_c");
  const [limit,      setLimit]      = useState(50);
  const [charts,     setCharts]     = useState([]);  // accumulated snapshots
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState(null);

  async function handleLoadChart() {
    setLoading(true);
    setError(null);
    try {
      const raw = await getSensorHistory(nodeId, { sensor_type: sensorType, limit });

      if (!raw.length) {
        setError("No readings found for this selection.");
        return;
      }

      // API returns newest-first — reverse to chronological order
      const points = [...raw].reverse().map(({ value, timestamp }) => ({
        time:         formatTimestamp(timestamp),
        [sensorType]: parseFloat(value.toFixed(2)),
      }));

      const meta = SENSOR_TYPES.find((t) => t.value === sensorType);

      // Prepend so the newest chart appears at the top of the stack
      setCharts((prev) => [
        {
          id:       Date.now(),
          dataKey:  sensorType,
          label:    meta.label,
          unit:     meta.unit,
          color:    meta.color,
          data:     points,
          loadedAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
        ...prev,
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <button className="back-btn" onClick={() => navigate("/")}>
        <MdArrowBack /> Back
      </button>

      <div className="page-header">
        <h1 className="page-title">Sensor History</h1>
        <p className="page-subtitle">Node {nodeId} — readings from the database</p>
      </div>

      {/* Controls — only affect the NEXT chart loaded, not existing ones */}
      <div className="history-controls">
        <div className="form-group">
          <label className="form-label">Sensor</label>
          <select
            className="form-select"
            value={sensorType}
            onChange={(e) => setSensorType(e.target.value)}
          >
            {SENSOR_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Readings</label>
          <select
            className="form-select"
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value))}
          >
            {LIMIT_OPTIONS.map((n) => (
              <option key={n} value={n}>{n} readings</option>
            ))}
          </select>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleLoadChart}
          disabled={loading}
        >
          {loading ? "Loading…" : "Load Chart"}
        </button>

        {charts.length > 0 && (
          <button
            className="btn btn-ghost"
            onClick={() => setCharts([])}
          >
            Clear All
          </button>
        )}
      </div>

      {error && <div className="status-msg error" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Empty prompt */}
      {charts.length === 0 && !error && (
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <div className="empty-state-text">
            Choose a sensor and reading count, then press Load Chart.<br />
            Each load adds a new chart below.
          </div>
        </div>
      )}

      {/* Stacked charts — each press of Load Chart adds one here */}
      <div className="chart-stack">
        {charts.map((snapshot) => (
          <ChartCard
            key={snapshot.id}
            snapshot={snapshot}
            onRemove={() => setCharts((prev) => prev.filter((c) => c.id !== snapshot.id))}
          />
        ))}
      </div>
    </div>
  );
}