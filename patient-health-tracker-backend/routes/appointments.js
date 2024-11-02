// routes/appointments.js
const express = require('express');
const router = express.Router();
const Appointment = require('../models/Appointment'); // Adjust the path if necessary

// GET all appointments
router.get('/appointments', async (req, res) => {
    try {
        const appointments = await Appointment.find();
        res.status(200).json(appointments);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// POST to create an appointment
router.post('/appointments', async (req, res) => {
    const { patientName, appointmentDate, message, patientEmail } = req.body; // Make sure to include patientEmail

    const appointment = new Appointment({
        patientName,
        appointmentDate,
        message,
        patientEmail, // Include this line to save the email
    });

    try {
        const savedAppointment = await appointment.save();
        res.status(201).json(savedAppointment);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// Export the router
module.exports = router;
