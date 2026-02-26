import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MdArrowBack } from "react-icons/md";
import { getDevices } from "../api/devices";
import { getLightState, turnOn, turnOff, setBrightness, setColorXY, hexToXY, xyToHex } from "../api/matter";
import Toggle from "../components/Toggle";

// Colour presets — hex values are converted to CIE XY when sent to the bulb
const PRESETS = [
  { label: "Warm White", hex: "#ffaa44" },
  { label: "Cool White", hex: "#e8f0ff" },
  { label: "Red",        hex: "#ff2200" },
  { label: "Green",      hex: "#00cc44" },
  { label: "Blue",       hex: "#0055ff" },
  { label: "Purple",     hex: "#8833ff" },
];

export default function LedControl() {
  const { node_id } = useParams();
  const nodeId      = parseInt(node_id, 10);
  const navigate    = useNavigate();

  const [deviceName,  setDeviceName]  = useState(`Node ${nodeId}`);
  const [isOn,        setIsOn]        = useState(false);
  const [brightness,  setBrightnessV] = useState(128);
  const [colorHex,    setColorHex]    = useState("#ffaa44");
  const [activePreset, setActivePreset] = useState(null);

  // Debounce refs — avoid flooding the device with slider events
  const brightnessTimer = useRef(null);
  const colorTimer      = useRef(null);

  // Keep a ref of the latest colorHex so the debounced brightness handler
  // can always re-assert the current colour. Some bulbs reset their colour
  // mode to colour-temperature when they receive a MoveToLevel command.
  const colorHexRef = useRef(colorHex);

  // Load device name and initial state
  useEffect(() => {
    getDevices().then((devs) => {
      const d = devs.find((d) => d.node_id === nodeId);
      if (d) setDeviceName(d.name);
    });

    getLightState(nodeId).then((state) => {
      if (!state) return;
      setIsOn(state.on ?? false);
      if (state.brightness != null) setBrightnessV(state.brightness);
      if (state.color_xy)           setColorHex(xyToHex(state.color_xy.x, state.color_xy.y));
    }).catch(() => {});
  }, [nodeId]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function handleToggle() {
    try {
      if (isOn) { await turnOff(nodeId); setIsOn(false); }
      else      { await turnOn(nodeId);  setIsOn(true);  }
    } catch (err) { console.error(err); }
  }

  function handleBrightnessChange(e) {
    const level = parseInt(e.target.value, 10);
    setBrightnessV(level);
    // Debounce: only send command 300ms after user stops dragging.
    // After setting brightness we also re-assert the current colour because
    // some bulbs reset their colour mode to colour-temperature when they
    // receive a MoveToLevel command, which makes the colour appear to revert.
    clearTimeout(brightnessTimer.current);
    brightnessTimer.current = setTimeout(async () => {
      try {
        await setBrightness(nodeId, level);
        const { x, y } = hexToXY(colorHexRef.current);
        await setColorXY(nodeId, x, y);
      } catch (err) {
        console.error(err);
      }
    }, 300);
  }

  function handleColorChange(hex) {
    setColorHex(hex);
    colorHexRef.current = hex;
    setActivePreset(null);
    clearTimeout(colorTimer.current);
    colorTimer.current = setTimeout(() => {
      const { x, y } = hexToXY(hex);
      setColorXY(nodeId, x, y).catch(console.error);
    }, 300);
  }

  function handlePreset(preset) {
    setActivePreset(preset.hex);
    setColorHex(preset.hex);
    colorHexRef.current = preset.hex;
    const { x, y } = hexToXY(preset.hex);
    setColorXY(nodeId, x, y).catch(console.error);
  }

  const brightnessPercent = Math.round((brightness / 254) * 100);

  return (
    <div className="page">
      <button className="back-btn" onClick={() => navigate("/")}>
        <MdArrowBack /> Back
      </button>

      <div className="page-header">
        <h1 className="page-title">{deviceName}</h1>
        <p className="page-subtitle">LED Bulb Control</p>
      </div>

      <div className="led-control-panel">

        {/* On / Off */}
        <div className="control-section">
          <div className="control-label">Power</div>
          <div className="led-status-row">
            <span className={`led-state-label ${isOn ? "on" : "off"}`} style={{ fontSize: 16 }}>
              {isOn ? "On" : "Off"}
            </span>
            <Toggle on={isOn} onChange={handleToggle} />
          </div>
        </div>

        {/* Brightness */}
        <div className="control-section">
          <div className="control-label">Brightness</div>
          <input
            type="range"
            className="brightness-slider"
            min={1}
            max={254}
            value={brightness}
            onChange={handleBrightnessChange}
          />
          <div className="brightness-value">{brightnessPercent}%</div>
        </div>

        {/* Colour picker + presets */}
        <div className="control-section">
          <div className="control-label">Colour</div>
          <div className="color-picker-wrap">
            <input
              type="color"
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