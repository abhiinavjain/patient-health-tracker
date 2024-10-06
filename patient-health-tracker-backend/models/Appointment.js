// models/Appointment.js
const mongoose = require('mongoose');

// Define the schema for appointments
const appointmentSchema = new mongoose.Schema({
    patientName: { type: String, required: true },
    appointmentDate: { type: Date, required: true },
    message: { type: String, required: true },
    patientEmail: { type: String, required: true }, // Add this line for the patient's email
});

// Create the Appointment model
const Appointment = mongoose.model('Appointment', appointmentSchema);

// Export the model
module.exports = Appointment;
