import React, { useEffect, useState } from "react";
import { getDevices, toggleDevice } from "../api/devices";
import { getSensors } from "../api/sensors";
import DeviceTile from "../components/DeviceTile";
import SensorTile from "../components/SensorTile";
import "./../styles.css";

export default function Dashboard() {
  // Mock device + sensor state
  // const [ledOn, setLedOn] = useState(false);
  // const [temp, setTemp] = useState(22.4);

  const [devices, setDevices] = useState([]);
  const [sensors, setSensors] = useState([]);

    useEffect(() => {
      loadDevices();
      
      loadSensors();
      const interval = setInterval(loadSensors, 5000); // refresh every 5 seconds
      return () => clearInterval(interval);
  }, []);

  async function loadDevices() {
    const devRes = await getDevices();
    setDevices(devRes);
  }

  async function loadSensors() {
    const sensRes = await getSensors();
    setSensors([sensRes]);
  }

  async function handleToggle(id) {
    try {
      await toggleDevice(id);
      await loadDevices();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="dashboard-container">
      <h1>PiHub Dashboard</h1>

      <div className="tile-grid">
        {devices.map((d) => (
          <DeviceTile
            key={d.id}
            name={d.name}
            status={d.status}
            onToggle={() => handleToggle(d.id)}
          />
        ))}

        {sensors.map((s) => (
          <SensorTile
            key={s.id}
            sensor={s}
          />
        ))}

      </div>
    </div>
  );
}
