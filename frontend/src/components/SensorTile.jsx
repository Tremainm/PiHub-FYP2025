import { MdSensors, MdLocalFireDepartment, MdCheckCircle, MdAir } from "react-icons/md";

/**
 * SensorTile: shows live temperature and humidity for a sensor node.
 *
 * Props:
 *   device  { node_id, name }   from DeviceDB
 *   reading { temperature_c, humidity_rh, context_class, context_label } | null
 *   onClick  function   navigate to history page
 */

// Colour and icon for each context label used to give the badge
// visual meaning at a glance on the dashboard
const CONTEXT_STYLE = {
  HEATING_ON:  { modifier: "heating", icon: <MdLocalFireDepartment /> },
  NORMAL:      { modifier: "normal",  icon: <MdCheckCircle />         },
  WINDOW_OPEN: { modifier: "window",  icon: <MdAir />                 },
};

export default function SensorTile({ device, reading, onClick }) {
  const temp = reading?.temperature_c;
  const hum = reading?.humidity_rh;
  const label = reading?.context_label;

  // Look up style for the current label, fall back to neutral grey if unknown
  const style = CONTEXT_STYLE[label] ?? { modifier: "", icon: "?" };

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
      {label != null && (
        <div className={`context-badge ${style.modifier}`}>
          <span>{style.icon}</span>
          <span>{label.replace("_", " ")}</span>
        </div>
      )}
    </div>
  );
}