import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MdArrowBack } from "react-icons/md";
import { getDevices } from "../api/devices";
import Toggle from "../components/Toggle";
import { useLedState } from "../hooks/useLedState";

const PRESETS = [
  { label: "Warm White", hex: "#ffaa44" },
  { label: "Cool White", hex: "#e8f0ff" },
  { label: "Red", hex: "#ff2200" },
  { label: "Green", hex: "#00cc44" },
  { label: "Blue", hex: "#0055ff" },
  { label: "Purple", hex: "#8833ff" },
];

export default function LedControl() {
  const { node_id } = useParams();
  const nodeId  = parseInt(node_id, 10);  // 10 represents the base of the number (node_id base 10)
  const navigate = useNavigate();

  const [deviceName, setDeviceName] = useState(`Node ${nodeId}`);
  const [activePreset, setActivePreset] = useState(null);

  // All LED state and commands come from useLedState
  const { isOn, brightness, colorHex, toggle, changeBrightness, changeColor } = useLedState(nodeId);

  useEffect(() => {
    getDevices().then((devs) => {
      const d = devs.find((d) => d.node_id === nodeId);
      if (d) setDeviceName(d.name);
    });
  }, [nodeId]);

  function handlePreset(preset) {
    setActivePreset(preset.hex);
    changeColor(preset.hex);
  }

  function handleColorChange(hex) {
    setActivePreset(null);
    changeColor(hex);
  }

  const brightnessPercent = Math.round((brightness / 254) * 100);

  return (
    <div className="page">
      <button className="back-btn" onClick={() => navigate("/")}>
        <MdArrowBack /> Back
      </button>

      <div className="page-header">
        <h1 className="page-title">{deviceName}</h1>
        <p className="page-subtitle">{deviceName} Control</p>
      </div>

      <div className="led-control-panel">

        <div className="control-section">
          <div className="control-label">Power</div>
          <div className="led-status-row">
            <span className={`led-state-label ${isOn ? "on" : "off"}`} style={{ fontSize: 16 }}>
              {isOn ? "On" : "Off"}
            </span>
            <Toggle on={isOn} onChange={toggle} />
          </div>
        </div>

        <div className="control-section">
          <div className="control-label">Brightness</div>
          <input
            type="range"
            className="brightness-slider"
            min={1}
            max={254}
            value={brightness}
            onChange={(e) => changeBrightness(parseInt(e.target.value, 10))}
          />
          <div className="brightness-value">{brightnessPercent}%</div>
        </div>

        <div className="control-section">
          <div className="control-label">Colour</div>
          <div className="color-picker-wrap">
            <input
              type="color"  // built-in HTML input type - native browser colour picker
              className="color-input"
              value={colorHex}
              onChange={(e) => handleColorChange(e.target.value)}
            />
            <div className="color-presets">
              {PRESETS.map((p) => (
                <button
                  key={p.hex}
                  className={`color-preset ${activePreset === p.hex ? "active" : ""}`}
                  style={{ background: p.hex }}
                  onClick={() => handlePreset(p)}
                  title={p.label}
                />
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}