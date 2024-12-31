import React from "react";
import './NavBar.css';
import { Link } from "react-router-dom";

const Navbar = () => {
    return (
        <nav fixed="top" className="navbar">
            <div className="navLogo">
                <h1>
                <Link to="/" className="navlink"><h1>Well Path</h1></Link>
                </h1>
            </div>
            <ul className="navlinks">
                <li>
                    <Link to="/" className="navlink"><h2>Home</h2></Link>
                </li>
                <li>
                    <Link to="/follow-ups" className="navlink"><h2>Book Appointment</h2></Link>
                </li>
                <li>
                    <Link to={"/add-patient"} className="navlink"><h2>Add Patient</h2></Link>
                </li>
                <li>
                    <Link to={"/records"} className="navlink"><h2>Patient Records</h2></Link>
                </li>
                <li>
                    <Link to={"/predict"} className="navlink"><h2>Disease Prediction</h2></Link>
                </li>
                <li>
                    <Link to={"/login"} className="navlink"><h2>Login</h2></Link>
                </li>
                <li>
                    <Link to={"/dashboard"} className="navlink"><h2>Profile</h2></Link>
                </li>
               
            </ul>
        </nav>
    );
};

export default Navbar;
