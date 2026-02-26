/**
 * Toggle — a large touch-friendly on/off switch.
 *
 * Props:
 *   on       {boolean}  current state
 *   onChange {function} called with no args when tapped — caller decides what to do
 *   disabled {boolean}  greys out and prevents interaction
 */
export default function Toggle({ on, onChange, disabled = false }) {
  function handleClick(e) {
    // Stop the click bubbling up to a parent tile's onClick
    e.stopPropagation();
    if (!disabled) onChange();
  }

  return (
    <button
      className={`toggle-btn ${on ? "on" : ""}`}
      onClick={handleClick}
      disabled={disabled}
      aria-label={on ? "Turn off" : "Turn on"}
      aria-pressed={on}
    />
  );
}