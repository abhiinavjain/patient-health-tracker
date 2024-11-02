import React from "react";
import './NavBar.css';
import { Link } from "react-router-dom";

const Navbar = () => {
    return (
        <navbar fixed="top" className="navbar">
            <div className="navLogo">
                <h1>Patient Health Tracker</h1>
            </div>
            <ul className="navlinks">
                <li>
                    <Link to="/" className="navlink"><h2>Home</h2></Link>
                </li>
                <li>
                    <Link to="/follow-ups" className="navlink"><h2>Book Appointment</h2></Link>
                </li>
                <li>
                    <Link to={"https://abhiinavjain-portfolio.vercel.app/"} target="blank" className="navlink"><h2>About Developer</h2></Link>
                </li>
            </ul>
        </navbar>
    );
};

export default Navbar;
