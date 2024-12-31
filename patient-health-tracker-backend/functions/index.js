const functions = require("firebase-functions");
const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const cron = require("node-cron");
require("dotenv").config(); // To load environment variables from .env file

const Appointment = require("./models/Appointment"); // Import the Appointment model
const patientRoutes = require("./routes/patientRoutes"); // Import patient routes

// MongoDB URI from environment variables
const mongoURI = process.env.MONGODB_URI;

// Initialize Express app
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// MongoDB Connection
mongoose.connect(mongoURI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.error('MongoDB connection error:', err));

// Routes
app.get('/', (req, res) => {
  res.send('API is running');
});

// Use patient routes
app.use('/api', patientRoutes);

// Appointment Reminder Scheduling
cron.schedule('* * * * *', async () => {
    try {
        const appointments = await Appointment.find(); // Fetch all appointments
        const now = new Date();

        const emailPromises = appointments.map(async (appointment) => {
            const appointmentDate = new Date(appointment.appointmentDate);
            if (appointmentDate - now <= 60 * 60 * 1000 && appointmentDate - now > 0) {
                try {
                    await sendEmail(
                        appointment.patientEmail,
                        'Appointment Reminder',
                        `Dear ${appointment.patientName},\n\nThis is a reminder for your appointment on ${appointmentDate}.\n\nBest,\nYour Health Tracking System`
                    );
                    console.log(`Reminder email sent to ${appointment.patientEmail}`);
                } catch (error) {
                    console.error(`Failed to send email to ${appointment.patientEmail}:`, error);
                }
            }
        });

        await Promise.all(emailPromises); // Wait for all email promises to complete
    } catch (error) {
        console.error('Error fetching appointments:', error);
    }
});

// Export the app as a Firebase Function
exports.app = functions.https.onRequest(app);
