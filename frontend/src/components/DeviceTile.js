import React from "react";

export default function DeviceTile({ name, status, onToggle }) {
  return (
    <div className="tile device-tile">
      <h2>{name}</h2>
      <p>Status: {status}</p>

      <button className={status === "ON" ? "btn-off" : "btn-on"} onClick={onToggle}>
        {status === "ON" ? "Turn Off" : "Turn On"}
      </button>
    </div>
  );
}
