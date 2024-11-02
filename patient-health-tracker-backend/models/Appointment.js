const mongoose = require('mongoose');

const appointmentSchema = new mongoose.Schema({
    patientName: {
        type: String,
        required: true,
    },
    appointmentDate: {
        type: Date,
        required: true,
    },
    message: {
        type: String,
        required: true,
    },
    patientEmail: {
        type: String,
        required: true,
    },
});

module.exports = mongoose.model('Appointment', appointmentSchema);
