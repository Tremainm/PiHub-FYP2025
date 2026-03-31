import { NavLink } from "react-router-dom";
import { MdDashboard, MdDevices, MdShowChart, MdSettings } from "react-icons/md";

export default function Navbar() {
  return (
    <nav className="navbar">
      <NavLink to="/" className="nav-logo">PiHub</NavLink>

      <ul className="nav-links">
        <li>
          <NavLink to="/" end className={({ isActive }) => isActive ? "active" : ""}>
            <MdDashboard size={20} /> Dashboard
          </NavLink>
        </li>
        <li>
          <NavLink to="/settings" className={({ isActive }) => isActive ? "active" : ""}>
            <MdSettings size={20} /> Settings
          </NavLink>
        </li>
      </ul>
    </nav>
  );
}