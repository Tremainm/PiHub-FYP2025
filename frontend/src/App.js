import "./styles.css";
import Dashboard from "./pages/Dashboard";
import Navbar from "./components/Navbar";
import { BrowserRouter as Router } from "react-router-dom";

export default function App() {
  return (
    <Router>
      <Navbar />
      <Dashboard />
    </Router>
  );
}
