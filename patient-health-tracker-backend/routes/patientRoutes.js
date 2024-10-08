// patientRoutes.js
const express = require('express');
const router = express.Router(); // Initialize the router
const Patient = require('../models/Patient'); // Correct path to your model
const { PythonShell } = require('python-shell');
const { predictDisease } = require('../scripts/disease_prediction');

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
      console.error('Error during Python script execution:', err);
      return res.status(500).json({ error: 'Error while running prediction', details: err.message });
    }
    res.status(200).json({ prediction: result[0] }); // Return the prediction result
  });
});

router.get('/predict',async(req,res)=>{
    try {
        const predict = await predictDisease.find(); // Fetch all patients from the database
        res.status(200).json(predict); // Return the patients in JSON format
      } catch (error) {
        res.status(500).json({ message: 'Error fetching patients', error: error.message });
      }
    
})


module.exports = router; // Export the router
