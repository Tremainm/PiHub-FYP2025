import "./styles.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import LedControl from "./pages/LedControl";
import SensorHistory from "./pages/SensorHistory";
import Settings from "./pages/Settings";

export default function App() {
  return (
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
  );
}