const express = require('express');
const router = express.Router(); // Initialize the router
const Patient = require('../models/Patient'); // Correct path to your model
const { PythonShell } = require('python-shell');
// Get all patients
router.get('/patients', async (req, res) => {
  try {
    const patients = await Patient.find();
    res.json(patients);
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// Add a new patient
router.post('/patients', async (req, res) => {
  const newPatient = new Patient(req.body);
  try {
    const savedPatient = await newPatient.save();
    res.status(201).json(savedPatient);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

// Update patient by ID
router.put('/patients/:id', async (req, res) => {
  try {
    const updatedPatient = await Patient.findByIdAndUpdate(req.params.id, req.body, { new: true });
    if (!updatedPatient) return res.status(404).json({ message: 'Patient not found' });
    res.json(updatedPatient);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

// Delete patient by ID
router.delete('/patients/:id', async (req, res) => {
  try {
    const deletedPatient = await Patient.findByIdAndDelete(req.params.id);
    if (!deletedPatient) return res.status(404).json({ message: 'Patient not found' });
    res.json({ message: 'Patient deleted successfully' });
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});
router.post('/predict', async (req, res) => {
  const inputData = req.body; // Expect input data from the request body

  // Set up options for PythonShell
  let options = {
    mode: 'text',
    pythonOptions: ['-u'], // get print results in real-time
    scriptPath: 'scripts', // Path to the directory containing the script
    args: [JSON.stringify(inputData)], // Send input data as argument
  };

  PythonShell.run('disease_prediction.py', options, (err, result) => {
    if (err) {
      return res.status(500).send({ error: 'Error while running prediction' });
    }
    res.json({ prediction: result[0] }); // Return the prediction result
  });
});

module.exports = router; // Export the router
