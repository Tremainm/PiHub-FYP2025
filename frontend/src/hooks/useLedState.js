import { useState, useEffect, useRef, useCallback } from "react";
import {
  getLightState,
  turnOn, turnOff, toggleLight,
  setBrightness, setColorXY,
  hexToXY, xyToHex,
} from "../api/matter";

const POLL_INTERVAL = 4000;
const DEFAULT_COLOR = "#ffaa44";

/**
 * useLedState — shared hook for all LED state and commands.
 *
 * Owns isOn, brightness, and colorHex for a given node. Polls the Matter
 * cache every 4 seconds to stay in sync with external changes (e.g. a
 * physical switch), but suppresses poll updates while a command is in-flight
 * so optimistic UI updates are never overwritten before the device confirms.
 *
 * Usage:
 *   const { isOn, brightness, colorHex, toggle, changeBrightness, changeColor } = useLedState(nodeId);
 */
export function useLedState(nodeId) {
  const [isOn,       setIsOn]      = useState(false);
  const [brightness, setBri]       = useState(128);
  const [colorHex,   setColorHex]  = useState(DEFAULT_COLOR);

  // Ref mirrors for use inside debounce/async closures where stale state
  // would otherwise be captured. Always updated alongside their state counterparts.
  const isOnRef      = useRef(false);
  const brightnessRef = useRef(128);
  const colorHexRef  = useRef(DEFAULT_COLOR);

  // When true, incoming poll results are ignored so they don't overwrite
  // an optimistic update before the device has caught up.
  const pendingRef = useRef(false);

  // Debounce timers for slider/picker — prevents flooding the device
  const brightnessTimer = useRef(null);
  const colorTimer      = useRef(null);

  // Helper: update a state value AND its ref together, keeping them in sync
  function setIsOnBoth(val)      { setIsOn(val);      isOnRef.current      = val; }
  function setBriBoth(val)       { setBri(val);        brightnessRef.current = val; }
  function setColorHexBoth(val)  { setColorHex(val);   colorHexRef.current  = val; }

  // ── Sync from Matter cache ──────────────────────────────────────────────
  // Fetches fresh state and applies it, unless a command is pending.
  const syncFromCache = useCallback(() => {
    if (pendingRef.current) return;
    getLightState(nodeId)
      .then((state) => {
        if (!state || pendingRef.current) return;
        if (state.on !== null && state.on !== undefined) setIsOnBoth(state.on);
        if (state.brightness != null) setBriBoth(state.brightness);
        if (state.color_xy)           setColorHexBoth(xyToHex(state.color_xy.x, state.color_xy.y));
      })
      .catch(() => {});
  }, [nodeId]);

  // Seed on mount, then poll every 4 seconds
  useEffect(() => {
    syncFromCache();
    const interval = setInterval(syncFromCache, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [syncFromCache]);

  // ── Commands ────────────────────────────────────────────────────────────
  // Each command:
  //   1. Updates local state immediately (optimistic UI — instant feedback)
  //   2. Sets pendingRef to block poll syncs from overwriting the update
  //   3. Fires the Matter command in the background
  //   4. Reverts on failure
  //   5. Clears pendingRef after enough time for the cache to update

  async function toggle() {
    const next = !isOnRef.current;
    setIsOnBoth(next);
    pendingRef.current = true;
    try {
      await toggleLight(nodeId);
    } catch (err) {
      setIsOnBoth(!next);   // revert on failure
      console.error("Toggle failed:", err);
    } finally {
      // Hold lock for one full poll cycle + buffer so the cache has time
      // to reflect the new state before we allow syncing again
      setTimeout(() => { pendingRef.current = false; }, POLL_INTERVAL + 1000);
    }
  }

  function changeBrightness(level) {
    setBriBoth(level);
    clearTimeout(brightnessTimer.current);
    pendingRef.current = true;
    brightnessTimer.current = setTimeout(async () => {
      try {
        await setBrightness(nodeId, brightnessRef.current);
        // Re-assert colour after brightness — some bulbs reset colour mode
        // to colour-temperature on a MoveToLevel command
        const { x, y } = hexToXY(colorHexRef.current);
        await setColorXY(nodeId, x, y);
      } catch (err) {
        console.error("Brightness failed:", err);
      } finally {
        setTimeout(() => { pendingRef.current = false; }, POLL_INTERVAL + 1000);
      }
    }, 300);
  }

  function changeColor(hex) {
    setColorHexBoth(hex);
    clearTimeout(colorTimer.current);
    pendingRef.current = true;
    colorTimer.current = setTimeout(async () => {
      try {
        const { x, y } = hexToXY(colorHexRef.current);
        await setColorXY(nodeId, x, y);
      } catch (err) {
        console.error("Color failed:", err);
      } finally {
        setTimeout(() => { pendingRef.current = false; }, POLL_INTERVAL + 1000);
      }
    }, 300);
  }

  return {
    isOn,
    brightness,
    colorHex,
    toggle,
    changeBrightness,
    changeColor,
  };
}