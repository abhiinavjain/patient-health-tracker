// src/components/DiseasePredictionForm.jsx
import React, { useState } from "react";
import axios from "axios";

const DiseasePredictionForm = () => {
  const [formData, setFormData] = useState({
    age: "",
    symptoms: "",
    testResults: "",
    medications: "",
    healthHistory: "",
  });

  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);

  // Handle input changes
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await axios.post(
        "http://localhost:5000/api/predict",
        formData
      );
      setPrediction(response.data.prediction);
      setError(null); // Clear any previous errors
    } catch (err) {
      setError("Error while predicting disease. Please try again.");
      console.error("Prediction error:", err);
     
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Age:</label>
          <input
            type="number"
            name="age"
            value={formData.age}
            onChange={handleChange}
            className="border p-2"
            required
          />
        </div>
        <div>
          <label>Symptoms (comma-separated):</label>
          <input
            type="text"
            name="symptoms"
            value={formData.symptoms}
            onChange={handleChange}
            className="border p-2 w-full"
            required
          />
        </div>
        <div>
          <label>Test Results (comma-separated):</label>
          <input
            type="text"
            name="testResults"
            value={formData.testResults}
            onChange={handleChange}
            className="border p-2 w-full"
            required
          />
        </div>
        <div>
          <label>Medications (comma-separated):</label>
          <input
            type="text"
            name="medications"
            value={formData.medications}
            onChange={handleChange}
            className="border p-2 w-full"
            required
          />
        </div>
        <div>
          <label>Health History (comma-separated):</label>
          <input
            type="text"
            name="healthHistory"
            value={formData.healthHistory}
            onChange={handleChange}
            className="border p-2 w-full"
            required
          />
        </div>
        <button
          type="submit"
          className="bg-blue-500 text-white p-2 rounded-md"
        >
          Predict Disease
        </button>
      </form>

      {/* Display the prediction result */}
      {prediction && (
        <div className="mt-4">
          <h3 className="text-xl font-bold">Prediction Result:</h3>
          <p>{prediction}</p>
        </div>
      )}

      {/* Display any errors */}
      {error && <p className="text-red-500 mt-4">{error}</p>}
    </div>
  );
};

export default DiseasePredictionForm;
