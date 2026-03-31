import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { getDevices } from "../api/devices";
import { getSensorLive } from "../api/sensors";
import { SENSOR_NODE_IDS, LED_NODE_IDS } from "../config/nodeId.config"
import SensorTile from "../components/SensorTile";
import LedTile from "../components/LedTile";

export default function Dashboard() {
  // navigate() is used as a callback prop on tiles. 
  // Link can't be passed as a function
  const navigate = useNavigate();

  const POLL_INTERVAL = 4000;

  const [devices, setDevices] = useState([]);
  const [sensorData, setSensorData] = useState({});
  const [loading, setLoading] = useState(true);

  // Load device name registry once on mount
  useEffect(() => {
    getDevices()
      .then(setDevices)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Poll sensor live cache
  const refreshSensors = useCallback(() => {
    SENSOR_NODE_IDS.forEach((id) => {
      getSensorLive(id)
        .then((data) => setSensorData((prev) => ({ ...prev, [id]: data })))
        .catch(() => {});
    });
  }, []);

  useEffect(() => {
    refreshSensors();
    const interval = setInterval(refreshSensors, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refreshSensors]);

  const sensorDevices = devices.filter((d) => SENSOR_NODE_IDS.includes(d.node_id));
  const ledDevices = devices.filter((d) => LED_NODE_IDS.includes(d.node_id));

  if (loading) return <div className="spinner" />;

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">
          {devices.length} device{devices.length !== 1 ? "s" : ""} on fabric
        </p>
      </div>

      {devices.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">📡</div>
          <div className="empty-state-text">
            No devices registered yet. Go to Settings to commission one.
          </div>
        </div>
      )}

      <div className="tile-grid">
        {sensorDevices.map((device) => (
          <SensorTile
            key={device.node_id}
            device={device}
            reading={sensorData[device.node_id] ?? null}
            onClick={() => navigate(`/sensors/${device.node_id}`)}
          />
        ))}

        {ledDevices.map((device) => (
          <LedTile
            key={device.node_id}
            device={device}
            onClick={() => navigate(`/led/${device.node_id}`)}
          />
        ))}
      </div>
    </div>
  );
}