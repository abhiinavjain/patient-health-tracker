import React from "react";
import './NavBar.css';
import { Link } from "react-router-dom";

const Navbar = () => {
    return (
        <nav className="navbar">
            <div className="navLogo">
                <h1>Patient Health Tracker</h1>
            </div>
            <ul className="navlinks">
                <li>
                    <Link to="/" className="navlink"><h2>Home</h2></Link>
                </li>
                <li>
                    <Link to="/doctor" className="navlink"><h2>Doctor Dashboard</h2></Link>
                </li>
                <li>
                    <Link to="/follow-ups" className="navlink"><h2>Book Appointment</h2></Link>
                </li>
            </ul>
        </nav>
    );
};

export default Navbar;
