import { MdLightbulb } from "react-icons/md";
import Toggle from "./Toggle";
import { toggleLight } from "../api/matter";

/**
 * LedTile — shows on/off state with an inline toggle. Tapping the tile body
 * (not the toggle) navigates to the full LED control page.
 *
 * Props:
 *   device   { node_id, name }
 *   state    { on, brightness, color_xy } | null   from live cache
 *   onToggle function   called after a successful toggle so parent can refresh
 *   onClick  function   navigate to LED control page
 */
export default function LedTile({ device, state, onToggle, onClick }) {
  const isOn = state?.on ?? false;

  async function handleToggle() {
    try {
      await toggleLight(device.node_id);
      // Small delay to let the subscription cache update before parent refreshes
      setTimeout(onToggle, 10);
    } catch (err) {
      console.error("Toggle failed:", err);
    }
  }

  return (
    <div className="tile led-tile" onClick={onClick}>
      <div className="tile-icon"><MdLightbulb /></div>
      <span className="tile-type-badge">LED Bulb</span>
      <div className="tile-name">{device.name}</div>

      <div className="led-status-row">
        <span className={`led-state-label ${isOn ? "on" : "off"}`}>
          {isOn ? "On" : "Off"}
        </span>
        <Toggle on={isOn} onChange={handleToggle} />
      </div>
    </div>
  );
}