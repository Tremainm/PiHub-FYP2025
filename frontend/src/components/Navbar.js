import React from "react";
import { Link } from "react-router-dom";
import "./Navbar.css"; 

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="nav-logo">PiHub</div>

      <ul className="nav-links">
        <li><Link to="/">Dashboard</Link></li>
        <li><Link to="/devices">Devices</Link></li>
        <li><Link to="/sensors">Sensors</Link></li>
        <li><Link to="/settings">Settings</Link></li>
      </ul>
    </nav>
  );
}
