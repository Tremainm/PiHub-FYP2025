import { useState, useEffect, useRef, useCallback } from "react";
import { getLightState, toggleLight, setBrightness, setColorXY } from "../api/matter";
import { hexToXY, xyToHex } from "../components/ColourHelpers";

const POLL_INTERVAL = 4000;
const DEFAULT_COLOR = "#ffaa44";

export function useLedState(nodeId) {
  const [isOn, setIsOn] = useState(false);
  const [brightness, setBri] = useState(128);
  const [colorHex, setColorHex] = useState(DEFAULT_COLOR);

  // Once the user explicitly picks a colour, the poll must never overwrite it.
  // The xyToHex round-trip is lossy, every poll would drift the colour slightly,
  // and changeBrightness re-sends whatever is in colorHex, so any drift
  // compounds into a completely wrong colour over time.
  const userSetColorRef = useRef(false);
  const pendingRef = useRef(false);       // prevents poller from overwriting UI
  const brightnessTimer = useRef(null);
  const colorTimer = useRef(null);

  // -- Sync from Matter cache ---------------------------------
  // Polls on mount and every POLL_INTERVAL ms to stay in sync with external
  // changes (e.g. physical switch). Colour is only synced on the very first
  // poll, after the user sets a colour it becomes the local source of truth.
  const syncFromCache = useCallback(() => {
    if (pendingRef.current) return;
    getLightState(nodeId)
      .then((state) => {
        if (!state || pendingRef.current) return;
        if (state.on !== null && state.on !== undefined) setIsOn(state.on);
        if (state.brightness != null) setBri(state.brightness);
        if (state.color_xy && !userSetColorRef.current) {
          setColorHex(xyToHex(state.color_xy.x, state.color_xy.y));
        }
      })
      .catch(() => {});
  }, [nodeId]); // function reference only changes if nodeId changes

  useEffect(() => {
    syncFromCache();
    const interval = setInterval(syncFromCache, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [syncFromCache]);

  // -- Commands ----------------------------------------------

  async function toggle() {
    const next = !isOn;
    setIsOn(next);
    pendingRef.current = true;
    try {
      await toggleLight(nodeId);
    } catch (err) {
      setIsOn(!next);
      console.error("Toggle failed:", err);
    } finally {
      setTimeout(() => { pendingRef.current = false; }, POLL_INTERVAL + 1000);
    }
  }

  async function changeBrightness(level) {
    setBri(level);
    clearTimeout(brightnessTimer.current);
    pendingRef.current = true;
    brightnessTimer.current = setTimeout(async () => {
      try {
        // Send colour first so current_x/current_y are set on the device
        // before MoveToLevelWithOnOff triggers the hardware update.
        // This eliminates the white flash, the firmware re-applies colour
        // immediately after brightness using the already-updated globals.
        if (userSetColorRef.current) {
          const { x, y } = hexToXY(colorHex);
          await setColorXY(nodeId, x, y);
        }
        await setBrightness(nodeId, level);
      } catch (err) {
        console.error("Brightness failed:", err);
      } finally {
        setTimeout(() => { pendingRef.current = false; }, POLL_INTERVAL + 1000);
      }
    }, 300);
  }

  function changeColor(hex) {
    userSetColorRef.current = true;
    setColorHex(hex);
    clearTimeout(colorTimer.current);
    pendingRef.current = true;
    colorTimer.current = setTimeout(async () => {
      try {
        const { x, y } = hexToXY(hex);
        await setColorXY(nodeId, x, y);
      } catch (err) {
        console.error("Color failed:", err);
      } finally {
        setTimeout(() => { pendingRef.current = false; }, POLL_INTERVAL + 1000);
      }
    }, 300);
  }

  return { isOn, brightness, colorHex, toggle, changeBrightness, changeColor };
}