import React from "react";

export default function SensorTile({ label, value }) {
  return (
    <div className="tile sensor-tile">
      <h2>{label}</h2>
      <p className="sensor-value">{value}</p>
    </div>
  );
}
