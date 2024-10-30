import React, { useState } from 'react';
import axios from 'axios';

const PatientForm = () => {
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [previousConditions, setPreviousConditions] = useState('');
  const [testResults, setTestResults] = useState('');
  const [medications, setMedications] = useState('');
  const [healthHistory, setHealthHistory] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newPatient = { name, age, symptoms, previousConditions, testResults, medications, healthHistory };
    try {
      await axios.post('http://localhost:5000/api/patients', newPatient);
      // Clear form after submission
      setName('');
      setAge('');
      setSymptoms('');
      setPreviousConditions('');
      setTestResults('');
      setMedications('');
      setHealthHistory('');
    } catch (error) {
      console.error('Error adding patient', error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mb-6">
     
      <h2 className="text-2xl font-bold mb-4">Add Patient</h2>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <input
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="border  p-2 rounded"
          required
        />
        <input
          type="number"
          placeholder="Age"
          value={age}
          onChange={(e) => setAge(e.target.value)}
          className="border  p-2 rounded"
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <input
          placeholder="Symptoms (comma-separated)"
          value={symptoms}
          onChange={(e) => setSymptoms(e.target.value)}
          className="border p-2 rounded"
          required
        />
        <input
          placeholder="Previous Conditions (comma-separated)"
          value={previousConditions}
          onChange={(e) => setPreviousConditions(e.target.value)}
          className="border  p-2 rounded"
          
        />
      </div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <input
          placeholder="Test Results (comma-separated)"
          value={testResults}
          onChange={(e) => setTestResults(e.target.value)}
          className="border p-2 rounded"
        />
        <input
          placeholder="Medications (comma-separated)"
          value={medications}
          onChange={(e) => setMedications(e.target.value)}
          className="border  p-2 rounded"
        />
      </div>
      <input
        placeholder="Health History"
        value={healthHistory}
        onChange={(e) => setHealthHistory(e.target.value)}
        className="border p-2 rounded mb-4"
      />
      <div class="button-container">
      <button type="submit" className="  bg-04395E text-white p-2 rounded" >Add Patient</button>
      </div>
    </form>
  );
};

export default PatientForm;
