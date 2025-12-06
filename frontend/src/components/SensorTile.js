import React, { useEffect, useState } from "react";

export default function SensorTile({ sensor }) {
  const [liveValue, setLiveValue] = useState(null);
  const [error, setError] = useState(null);

  const isMatterTempSensor =
    sensor.sensor_type === "temperature" && sensor.is_matter === true;

  useEffect(() => {
    if (!isMatterTempSensor) return;

    async function fetchTemp() {
      try {
        const res = await fetch("http://localhost:8000/matter/temperature");
        const data = await res.json();

        if (data.temperature_celsius !== undefined) {
          setLiveValue(data.temperature_celsius);
          setError(null);
        } else {
          setError("Failed to load");
        }
      } catch (err) {
        setError("Backend offline");
      }
    }

    fetchTemp();

    const interval = setInterval(fetchTemp, 5000); // refresh every 5s
    return () => clearInterval(interval);
  }, [isMatterTempSensor]);

  return (
    <div className="sensor-tile">
      <h3>{sensor.sensor_type.toUpperCase()}</h3>

      {isMatterTempSensor ? (
        <>
          {error && <p style={{ color: "red" }}>{error}</p>}
          {liveValue === null && !error && <p>Loading...</p>}
          {liveValue !== null && (
            <p className="sensor-value">{liveValue.toFixed(2)} °C</p>
          )}
        </>
      ) : (
        <p className="sensor-value">{sensor.value}</p>
      )}
    </div>
  );
}
