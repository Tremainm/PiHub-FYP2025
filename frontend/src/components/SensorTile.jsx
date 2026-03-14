import { MdSensors } from "react-icons/md";

/**
 * SensorTile: shows live temperature and humidity for a sensor node.
 *
 * Props:
 *   device  { node_id, name }   from DeviceDB
 *   reading { temperature_c, humidity_rh } | null   from live cache
 *   onClick  function   navigate to history page
 */
export default function SensorTile({ device, reading, onClick }) {
  const temp = reading?.temperature_c;
  const hum  = reading?.humidity_rh;

  return (
    <div className="tile sensor-tile" onClick={onClick}>
      <div className="tile-icon"><MdSensors /></div>
      <span className="tile-type-badge">Sensor</span>
      <div className="tile-name">{device.name}</div>

      <div className="sensor-readings">
        <div className="reading-block">
          <div className="reading-label">Temp</div>
          <div className="reading-value">
            {temp != null ? temp.toFixed(1) : "—"}
            <span className="reading-unit"> °C</span>
          </div>
        </div>
        <div className="reading-block">
          <div className="reading-label">Humidity</div>
          <div className="reading-value">
            {hum != null ? hum.toFixed(1) : "—"}
            <span className="reading-unit"> %</span>
          </div>
        </div>
      </div>
    </div>
  );
}