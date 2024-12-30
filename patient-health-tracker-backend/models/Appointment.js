const mongoose = require('mongoose');

// Define the schema for appointments
const appointmentSchema = new mongoose.Schema({
  patientName: { type: String, required: true },
  patientEmail: { type: String, required: true },
  doctorName: { type: String, required: true },
  appointmentDate: { type: Date, required: true },
  reason: { type: String },
});

// Create the model
const Appointment = mongoose.model('Appointment', appointmentSchema);

// Export the model
module.exports = Appointment;
