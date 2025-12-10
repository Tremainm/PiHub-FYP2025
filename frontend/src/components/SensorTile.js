export default function SensorTile({ sensor }) {
  return (
    <div className="tile sensor-tile">
      <h3>{sensor.sensor_type.toUpperCase()}</h3>
      <p className="sensor-value">{sensor.value.toFixed(2)} °C</p>
      <p>{new Date(sensor.timestamp).toLocaleString()}</p>
    </div>
  );
}
