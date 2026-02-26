import React from "react";
import { Link } from "react-router-dom";
import { MdDashboard, MdSettings, MdSensors, MdDevices } from "react-icons/md";
import "./Navbar.css"; 

export default function Navbar() {
  return (
    <nav className="navbar">
      <ul className="nav-links">
        <li><Link to="/">PiHub</Link></li>
      </ul>

      <ul className="nav-links">
        <li><Link to="/"><MdDashboard /> </Link></li>
        <li><Link to="/devices"><MdDevices /> </Link></li>
        <li><Link to="/sensors"><MdSensors /> </Link></li>
        <li><Link to="/settings"><MdSettings /> </Link></li>
      </ul>
    </nav>
  );
}
