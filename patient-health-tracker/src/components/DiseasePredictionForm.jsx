// src/components/DiseasePredictionForm.jsx
import React, { useState } from "react";
import axios from "axios";

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
      setError("Visit Doctor its very serious");
      console.error("Prediction error:", err);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 rounded-lg ">
      <h2 className="text-2xl font-bold mb-4">Disease Prediction</h2>
      <p className="mb-6 text-gray-600">
        Discover potential health insights based on your age and symptoms. Our AI-powered prediction system helps identify possible health conditions, providing guidance on the next steps in your wellness journey. Just fill in your information and get a prediction instantly!
      </p>

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
        <button
          type="submit"
          className="bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 transition duration-200"
        >
          Get Prediction
        </button>
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
