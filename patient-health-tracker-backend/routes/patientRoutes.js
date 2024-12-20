// patientRoutes.js
const express = require('express');
const router = express.Router(); // Initialize the router
const Patient = require('../models/Patient'); // Correct path to your model
const { PythonShell } = require('python-shell');

// Get all patients
router.get('/patients', async (req, res) => {
  try {
    const patients = await Patient.find(); // Fetch all patients from the database
    res.status(200).json(patients); // Return the patients in JSON format
  } catch (error) {
    res.status(500).json({ message: 'Error fetching patients', error: error.message });
  }
});
// Add a new patient
router.post('/patients', async (req, res) => {
  try {
    const newPatient = new Patient(req.body); // Create a new Patient instance with request body data
    const savedPatient = await newPatient.save(); // Save the patient to the database
    res.status(201).json(savedPatient); // Return the saved patient in JSON format
  } catch (error) {
    res.status(400).json({ message: 'Error adding patient', error: error.message });
  }
});
// Update patient by ID
router.put('/patients/:id', async (req, res) => {
  try {
    const updatedPatient = await Patient.findByIdAndUpdate(req.params.id, req.body, { new: true });
    if (!updatedPatient) {
      return res.status(404).json({ message: 'Patient not found' });
    }
    res.status(200).json(updatedPatient); // Return the updated patient in JSON format
  } catch (error) {
    res.status(400).json({ message: 'Error updating patient', error: error.message });
  }
});
// Delete patient by ID
router.delete('/patients/:id', async (req, res) => {
  try {
    const deletedPatient = await Patient.findByIdAndDelete(req.params.id);
    if (!deletedPatient) {
      return res.status(404).json({ message: 'Patient not found' });
    }
    res.status(200).json({ message: 'Patient deleted successfully' });
  } catch (error) {
    res.status(400).json({ message: 'Error deleting patient', error: error.message });
  }
});
// Disease prediction route


module.exports = router; // Export the router