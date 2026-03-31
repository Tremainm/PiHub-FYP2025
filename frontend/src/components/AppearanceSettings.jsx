import { MdDarkMode, MdLightMode, MdRestartAlt } from "react-icons/md";
import { useTheme } from "../context/ThemeContext";

/**
 * AppearanceSettings
 *
 * Renders theme controls at the top of Settings:
 *   - Dark / Light mode toggle (large touch-friendly button)
 *   - Sensor tile accent colour picker
 *   - LED tile accent colour picker
 *   - Reset colours button
 *
 * All state lives in ThemeContext. This component only reads and calls setters.
 * No local state needed; the pickers are controlled via the context values.
 */
export default function AppearanceSettings() {
  const {
    isDark,
    toggleDark,
    sensorColor,
    setSensorColor,
    ledColor,
    setLedColor,
    resetColors,
  } = useTheme();

  return (
    <div className="settings-section">
      <div className="settings-section-title">Appearance</div>
      <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20, lineHeight: 1.6 }}>
        Customise the look of PiHub. Changes apply instantly and are saved
        between sessions.
      </p>

      {/* ── Dark / Light toggle ──────────────────────────────────────────── */}
      <div className="appearance-row">
        <div className="appearance-field">
          <div className="appearance-label">Theme</div>
          <div className="appearance-desc">
            Switch between dark and light mode.
          </div>
        </div>

        {/*
          Theme toggle button. Uses a two-part visual: an icon on the left
          and a pill indicator on the right showing the current mode.
          The active state is driven entirely by the isDark value from context.
        */}
        <button
          className={`theme-toggle-btn ${isDark ? "dark" : "light"}`}
          onClick={toggleDark}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          <span className="theme-toggle-icon">
            {isDark ? <MdDarkMode size={18} /> : <MdLightMode size={18} />}
          </span>
          <span className="theme-toggle-label">
            {isDark ? "Dark" : "Light"}
          </span>
          {/* Animated sliding pill */}
          <span className="theme-toggle-track">
            <span className="theme-toggle-thumb" />
          </span>
        </button>
      </div>

      <div className="divider" style={{ margin: "18px 0" }} />

      {/* ── Tile accent colours ──────────────────────────────────────────── */}
      <div className="appearance-colors-grid">

        {/*
          Sensor colour picker.
          The <input type="color"> is a native browser colour wheel — on the
          Pi's Chromium kiosk this renders as a full-screen colour picker,
          which is touch-friendly. onChange fires on every change during drag;
          we pass the hex string directly to setSensorColor which writes to
          localStorage and triggers the accent CSS override in ThemeContext.
        */}
        <div className="appearance-color-item">
          <label className="appearance-color-label" htmlFor="sensor-color-pick">
            Sensor tile
          </label>
          <div className="appearance-color-swatch-row">
            <input
              id="sensor-color-pick"
              type="color"
              className="appearance-color-input"
              value={sensorColor}
              onChange={(e) => setSensorColor(e.target.value)}
              aria-label="Sensor tile accent colour"
            />
            <span className="appearance-color-hex">{sensorColor}</span>
          </div>
        </div>

        {/*
          LED colour picker — same pattern as sensor, targets --led-* tokens.
        */}
        <div className="appearance-color-item">
          <label className="appearance-color-label" htmlFor="led-color-pick">
            LED tile
          </label>
          <div className="appearance-color-swatch-row">
            <input
              id="led-color-pick"
              type="color"
              className="appearance-color-input"
              value={ledColor}
              onChange={(e) => setLedColor(e.target.value)}
              aria-label="LED tile accent colour"
            />
            <span className="appearance-color-hex">{ledColor}</span>
          </div>
        </div>

      </div>

      {/*
        Reset button — calls resetColors() in ThemeContext which clears
        localStorage keys and restores the built-in default accent values.
      */}
      <button
        className="btn btn-ghost"
        style={{ marginTop: 18, gap: 8 }}
        onClick={resetColors}
      >
        <MdRestartAlt size={16} />
        Reset to defaults
      </button>
    </div>
  );
}
