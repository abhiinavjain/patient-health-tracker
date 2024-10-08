// server.js
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const cron = require('node-cron');
const dotenv = require('dotenv');
const { sendEmail } = require('./mail'); // Import the sendEmail function
const Appointment = require('./models/Appointment'); // Import the Appointment model
const patientRoutes = require('./routes/patientRoutes'); // Import patient routes

dotenv.config(); // Load environment variables from .env file

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// MongoDB Connection
mongoose.connect(process.env.MONGODB_URI, { useNewUrlParser: true, useUnifiedTopology: true })
    .then(() => console.log('MongoDB connected'))
    .catch(err => console.error('MongoDB connection error:', err));

// Routes
app.get('/', (req, res) => {
    res.send('API is running');
});

// Use patient routes
app.use('/api', patientRoutes);

// Schedule a task to run every minute (adjust as necessary)
cron.schedule('* * * * *', async () => {
    const appointments = await Appointment.find(); // Fetch all appointments
    const now = new Date();

    appointments.forEach(async (appointment) => {
        const appointmentDate = new Date(appointment.appointmentDate);
        // Check if the appointment is within the next hour
        if (appointmentDate - now <= 60 * 60 * 1000 && appointmentDate - now > 0) {
            const emailSent = await sendEmail(
                appointment.patientEmail, // Ensure you have the patient's email in your model
                'Appointment Reminder',
                `Dear ${appointment.patientName},\n\nThis is a reminder for your appointment on ${appointmentDate}.\n\nBest,\nYour Health Tracking System`
            );
            console.log(`Reminder email sent to ${appointment.patientEmail}`);
        }
    });
});

// Start Server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});