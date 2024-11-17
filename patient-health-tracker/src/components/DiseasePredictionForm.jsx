// src/components/DiseasePredictionForm.jsx
import React, { useState } from "react";
import axios from "axios";
import { FlipWordsDemo } from "./ui/flipwordcomponent";

const DiseasePredictionForm = () => {
  const [formData, setFormData] = useState({
    age: "",
    symptoms: "",
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
      setError("Please Visit Doctor its very serious");
      console.error("Prediction error:", err);
    }
  };

  return (
    <div className="max-w-s mx-auto p-6 ">
  <br />
      <FlipWordsDemo/>
  <br /><br />

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block font-semibold mb-1">Age:</label>
          <input
            type="number"
            name="age"
            value={formData.age}
            onChange={handleChange}
            className="border p-2 w-full rounded-md"
            required
          />
        </div>
        <div className="mb-4">
          <label className="block font-semibold mb-1">Symptoms (comma-separated):</label>
          <input
            type="text"
            name="symptoms"
            value={formData.symptoms}
            onChange={handleChange}
            className="border p-2 w-full rounded-md"
            placeholder="e.g., cough, fever, headache"
            required
          />
        </div>
        <div class="button-container">
            <button type="submit" className="  bg-04395E text-white p-2 rounded" >Get Prediction</button>
        </div>
      </form>

      {/* Display the prediction result */}
      {prediction && (
        <div className="mt-6">
          <h3 className="text-xl font-bold">Prediction Result:</h3>
          <p className="mt-2 text-gray-700">{prediction}</p>
        </div>
      )}

      {/* Display any errors */}
      {error && <p className="text-red-500 mt-4">{error}</p>}
      <br /> <br />
      <footer className="text-center">
                <p className="text-sm text-gray-500" >This prediction model is under development</p>
            </footer>
    </div>
  );
};

export default DiseasePredictionForm;
