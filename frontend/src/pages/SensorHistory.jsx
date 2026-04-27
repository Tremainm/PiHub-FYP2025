import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MdArrowBack } from "react-icons/md";
import { getSensorHistory } from "../api/sensors";
import { formatTimestamp, ChartCard } from "../components/ChartHelpers";

const LIMIT_OPTIONS = [20, 50, 100, 200, 500];

const SENSOR_TYPES = [
  { value: "temperature_c", label: "Temperature", unit: "°C",  color: "var(--sensor)" },
  { value: "humidity_rh", label: "Humidity", unit: "%", color: "var(--led)" },
];

export default function SensorHistory() {
  const { node_id } = useParams();
  const nodeId = node_id ? parseInt(node_id, 10) : 2;
  const navigate = useNavigate();

  const [sensorType, setSensorType] = useState("temperature_c");
  const [limit, setLimit] = useState(50);
  const [charts, setCharts] = useState([]);  // accumulated snapshots
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleLoadChart() {
    setLoading(true);
    setError(null);
    try {
      const raw = await getSensorHistory(nodeId, { sensor_type: sensorType, limit });

      if (!raw.length) {
        setError("No readings found for this selection.");
        return;
      }

      // API returns newest-first - reverse to chronological order
      const points = [...raw].reverse().map(({ value, timestamp }) => ({
        time: formatTimestamp(timestamp), [sensorType]: parseFloat(value.toFixed(2)),
      }));

      const meta = SENSOR_TYPES.find((t) => t.value === sensorType);

      // Prepend so the newest chart appears at the top of the stack
      setCharts((prev) => [
        {
          id: Date.now(),
          dataKey: sensorType,
          label: meta.label,
          unit: meta.unit,
          color: meta.color,
          data: points,
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
        <p className="page-subtitle">Node {nodeId} - readings from the database</p>
      </div>

      {/* Controls: only affect the NEXT chart loaded, not existing ones */}
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
          <div className="empty-state-icon">...</div>
          <div className="empty-state-text">
            Choose a sensor and reading count, then press Load Chart.<br />
            Each load adds a new chart below.
          </div>
        </div>
      )}

      {/* Stacked charts: each press of Load Chart adds one here */}
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