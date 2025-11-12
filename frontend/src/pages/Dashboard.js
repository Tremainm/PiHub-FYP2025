import React, { useEffect, useState } from "react";
import { getDevices, toggleDevice } from "../api/devices";
import { getSensors } from "../api/sensors";
import DeviceTile from "../components/DeviceTile";
import SensorTile from "../components/SensorTile";
import "./../styles.css";

export default function Dashboard() {
  // Mock device + sensor state
  const [ledOn, setLedOn] = useState(false);
  // const [temp, setTemp] = useState(22.4);

  const [devices, setDevices] = useState([]);
  const [sensors, setSensors] = useState([]);

  const toggleLED = () => {
    setLedOn(!ledOn);
  };

    useEffect(() => {
      console.log("useEffect triggered");
      load();
  }, []);
  
  async function load() {
    try {
      const [devRes, sensRes] = await Promise.all([
        getDevices(),
        getSensors(),
      ]);

      console.log("Devices:", devRes);

      setDevices(devRes);
      setSensors(sensRes);
    } catch (err) {
      console.error("Failed to fetch:", err);
    }
  }

  async function handleToggle(id) {
    try {
      await toggleDevice(id);
      await load();
    } catch (err) {
      console.error(err);
    }
  }

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

        {devices.map((d) => (
          <DeviceTile
            key={d.id}
            name={d.name}
            status={d.status}
            onToggle={() => handleToggle(d.id)}
          />
        ))}

        {/* Sensor Tiles */}
        {/* <SensorTile label="Temperature" value={`${temp} C`} /> */}

        {/* {sensors.map((s) => (
          <SensorTile
            key={s.id}
            label={s.sensor_type}
            value={s.value}
          />
        ))} */}

      </div>
    </div>
  );
}
