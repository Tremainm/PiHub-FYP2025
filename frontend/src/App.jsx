import "./styles.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import LedControl from "./pages/LedControl";
import SensorHistory from "./pages/SensorHistory";
import Settings from "./pages/Settings";

/**
 * App: root component.
 *
 * ThemeProvider wraps everything so that any component in the tree can call
 * useTheme() to read or mutate the current theme. The provider applies
 * data-theme="dark|light" to <html> and injects accent colour overrides via
 * a <style> tag. No prop-drilling required.
 */
export default function App() {
  return (
    <ThemeProvider>
      <Router>
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/led/:node_id" element={<LedControl />} />
          <Route path="/sensors/:node_id" element={<SensorHistory />} />
          <Route path="/sensors" element={<SensorHistory />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}