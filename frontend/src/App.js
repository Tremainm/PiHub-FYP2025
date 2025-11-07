import "./styles.css";
import Dashboard from "./pages/Dashboard";
import Devices from "./pages/Devices";
import Sensors from "./pages/Sensors";
import Settings from "./pages/Settings";
import Navbar from "./components/Navbar";

import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

export default function App() {
  return (
    <Router>
      <Navbar />

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/devices" element={<Devices />} />
        <Route path="/sensors" element={<Sensors />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Router>
  );
}
