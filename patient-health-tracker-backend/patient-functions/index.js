const functions = require("firebase-functions");
const express = require("express");
const mongoose = require("mongoose");
require("dotenv").config(); // To load environment variables from .env file

// MongoDB URI from environment variables
const mongoURI = process.env.MONGODB_URI;

// Connect to MongoDB
mongoose.connect(mongoURI, {useNewUrlParser: true, useUnifiedTopology: true})
    .then(() => console.log("Connected to MongoDB"))
    .catch((err) => console.error("MongoDB connection error:", err));

// Define MongoDB Schema and Model
const PatientSchema = new mongoose.Schema({
  name: String,
  age: Number,
  symptoms: String,
});

const Patient = mongoose.model("Patient", PatientSchema);

// Initialize Express app
const app = express();

// Middleware to parse JSON body
app.use(express.json());

// Firebase function to get patient data
app.get("/patients", (req, res) => {
  Patient.find() // Retrieve all patients from MongoDB
      .then((patients) => {
        res.status(200).json(patients); // Send response as JSON
      })
      .catch((err) => {
        res.status(500).send("Error retrieving patients: " + err.message);
      });
});

// Firebase function to add new patient data
app.post("/patients", (req, res) => {
  const {name, age, symptoms} = req.body; // Get data from the request body
  const newPatient = new Patient({name, age, symptoms});

  newPatient.save()
      .then((patient) => {
        res.status(201).json(patient); // Send back the created patient as JSON
      })
      .catch((err) => {
        res.status(500).send("Error saving patient: " + err.message);
      });
});

// Export the app as a Firebase Function
exports.app = functions.https.onRequest(app);
