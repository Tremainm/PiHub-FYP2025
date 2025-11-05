import React, { useState } from "react";
import DeviceTile from "../components/DeviceTile";
import SensorTile from "../components/SensorTile";
import "./../styles.css";

export default function Dashboard() {
  // Mock device + sensor state
  const [ledOn, setLedOn] = useState(false);
  const [temp, setTemp] = useState(22.4);

  const toggleLED = () => {
    setLedOn(!ledOn);
  };

  return (
    <div className="dashboard-container">
      <h1>PiHub Dashboard</h1>

      <div className="tile-grid">

        {/* LED Device Tile */}
        <DeviceTile
          name="Living Room LED"
          status={ledOn ? "ON" : "OFF"}
          onToggle={toggleLED}
        />

        {/* Sensor Tiles */}
        <SensorTile label="Temperature" value={`${temp} C`} />

      </div>
    </div>
  );
}
