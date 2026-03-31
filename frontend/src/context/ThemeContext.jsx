/**
 * ThemeContext.jsx
 *
 * Provides app-wide theme state: dark/light mode and custom tile accent colours
 * (sensor and LED). Preferences are persisted to localStorage so they survive
 * page refreshes and kiosk restarts.
 *
 * Usage
 * -----
 *   // Wrap the app once (in App.jsx):
 *   <ThemeProvider>...</ThemeProvider>
 *
 *   // Consume anywhere:
 *   const { isDark, toggleDark, sensorColor, ledColor, setSensorColor, setLedColor } = useTheme();
 *
 * How it works
 * ------------
 * CSS custom properties on :root drive every colour in styles.css.
 *
 * Dark mode: a `data-theme="dark"` attribute is set on <html>. styles.css
 *            defines a [data-theme="dark"] block that overrides all surface,
 *            border, and text tokens.
 *
 * Accent colours: a dynamically-managed <style id="pihub-theme-vars"> tag in
 *                 <head> overrides --sensor-* and --led-* token families whenever
 *                 the user picks a custom colour. All derived tokens (pale, border,
 *                 glow) are recomputed from the single chosen base colour, so every
 *                 component that uses them stays visually consistent.
 */

import { createContext, useContext, useState, useEffect, useCallback } from "react";

// -- Storage keys --------------------------------------------------------------
const STORAGE_DARK = "pihub_dark_mode";
const STORAGE_SENSOR_CLR = "pihub_sensor_color";
const STORAGE_LED_CLR = "pihub_led_color";

// -- Defaults (mirror :root values in styles.css) ------------------------------
export const DEFAULT_SENSOR_COLOR = "#2563eb";
export const DEFAULT_LED_COLOR = "#ea580c";

// -- Context -------------------------------------------------------------------
const ThemeContext = createContext(null);

// -- Helpers -------------------------------------------------------------------

/**
 * hexToRgb: parse #rrggbb -> { r, g, b } integers.
 */
function hexToRgb(hex) {
  const n = parseInt(hex.replace("#", ""), 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

/**
 * buildAccentVars: returns inline CSS text overriding all tokens for one role.
 *
 * Token family built from a single hex base:
 *   --{role}          base colour
 *   --{role}-light    slightly lighter shade (hover highlights)
 *   --{role}-pale     very low-alpha tint (tile wash, badge bg)
 *   --{role}-border   medium-alpha tint (tile border)
 *   --{role}-glow     low-alpha (box-shadow glow)
 */
function buildAccentVars(role, hex, isDark) {
  const { r, g, b } = hexToRgb(hex);

  // Blend base toward white by 12% for the light variant
  const lr = Math.min(255, Math.round(r + (255 - r) * 0.12));
  const lg = Math.min(255, Math.round(g + (255 - g) * 0.12));
  const lb = Math.min(255, Math.round(b + (255 - b) * 0.12));
  const light = `#${lr.toString(16).padStart(2, "0")}${lg.toString(16).padStart(2, "0")}${lb.toString(16).padStart(2, "0")}`;

  // Dark mode uses a more subtle tint to avoid washed-out pastels on dark surfaces
  const pale = isDark ? `rgba(${r},${g},${b},0.08)` : `rgba(${r},${g},${b},0.09)`;
  const border = isDark ? `rgba(${r},${g},${b},0.30)` : `rgba(${r},${g},${b},0.28)`;
  const glow = `rgba(${r},${g},${b},0.12)`;

  return `
    --${role}: ${hex};
    --${role}-light: ${light};
    --${role}-pale: ${pale};
    --${role}-border: ${border};
    --${role}-glow: ${glow};
  `;
}

/**
 * applyTheme: writes the data-theme attribute and injects the accent
 * overrides into a dedicated <style> tag. Called on every state change.
 */
function applyTheme(isDark, sensorColor, ledColor) {
  // 1. Dark mode toggle: styles.css [data-theme="dark"] takes over
  document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");

  // 2. Accent overrides: separate <style> so they cascade over :root defaults
  let tag = document.getElementById("pihub-theme-vars");
  if (!tag) {
    tag = document.createElement("style");
    tag.id = "pihub-theme-vars";
    document.head.appendChild(tag);
  }
  tag.textContent = `:root {
    ${buildAccentVars("sensor", sensorColor, isDark)}
    ${buildAccentVars("led", ledColor, isDark)}
  }`;
}

// -- Provider ---------------------------------------------------------------
export function ThemeProvider({ children }) {
  // Default to dark mode if no preference has been stored yet
  const [isDark, setIsDark] = useState(() => {
    const stored = localStorage.getItem(STORAGE_DARK);
    return stored === null ? true : stored === "true";
  });

  const [sensorColor, setSensorColorState] = useState(
    () => localStorage.getItem(STORAGE_SENSOR_CLR) || DEFAULT_SENSOR_COLOR
  );

  const [ledColor, setLedColorState] = useState(
    () => localStorage.getItem(STORAGE_LED_CLR) || DEFAULT_LED_COLOR
  );

  // Re-apply to DOM whenever anything changes
  useEffect(() => {
    applyTheme(isDark, sensorColor, ledColor);
  }, [isDark, sensorColor, ledColor]);

  // -- Exposed actions ------------------------------------------------------

  const toggleDark = useCallback(() => {
    setIsDark((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_DARK, String(next));
      return next;
    });
  }, []);

  const setSensorColor = useCallback((hex) => {
    localStorage.setItem(STORAGE_SENSOR_CLR, hex);
    setSensorColorState(hex);
  }, []);

  const setLedColor = useCallback((hex) => {
    localStorage.setItem(STORAGE_LED_CLR, hex);
    setLedColorState(hex);
  }, []);

  // Reset accent colours to the built-in defaults
  const resetColors = useCallback(() => {
    localStorage.removeItem(STORAGE_SENSOR_CLR);
    localStorage.removeItem(STORAGE_LED_CLR);
    setSensorColorState(DEFAULT_SENSOR_COLOR);
    setLedColorState(DEFAULT_LED_COLOR);
  }, []);

  const value = {
    isDark,
    toggleDark,
    sensorColor,
    setSensorColor,
    ledColor,
    setLedColor,
    resetColors,
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

// -- Consumer hook -------------------------------------------------------
export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}