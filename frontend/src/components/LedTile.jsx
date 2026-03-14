import { MdLightbulb } from "react-icons/md";
import Toggle from "./Toggle";
import { useLedState } from "../hooks/useLedState";

/**
 * LedTile: dashboard tile for an LED bulb.
 * State is owned by useLedState, no local state here.
 */
export default function LedTile({ device, onClick }) {
  const { isOn, toggle } = useLedState(device.node_id);

  return (
    <div className="tile led-tile" onClick={onClick}>
      <div className="tile-icon"><MdLightbulb /></div>
      <span className="tile-type-badge">LED Bulb</span>
      <div className="tile-name">{device.name}</div>

      <div className="led-status-row">
        <span className={`led-state-label ${isOn ? "on" : "off"}`}>
          {isOn ? "On" : "Off"}
        </span>
        <Toggle on={isOn} onChange={toggle} />
      </div>
    </div>
  );
}