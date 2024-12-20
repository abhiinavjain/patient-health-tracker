const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const cron = require('node-cron');
const dotenv = require('dotenv');

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

// Predict Route with Error Handling


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

// Start Server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
    
});
