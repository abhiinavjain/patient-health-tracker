import React, { useState } from "react";
import DiseasePredictionForm from "./DiseasePredictionForm";
import { predictDisease } from "./api/mlService";

const DiseasePrediction = () => {
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState("");
  const handleFileUpload = async (file) => {
    try {
      const result = await predictDisease(file);
      setPrediction(result.prediction); // Expect { prediction: "Disease Name" }
      // Open a new pop-up window and display the prediction
      
    } catch (err) {
      setError("Prediction failed. Please try again.");
      // Open a new pop-up window and display the error
      
      console.error(err);
    }
  };

  return (
    <div className="p-6">
      <DiseasePredictionForm onFileUpload={handleFileUpload} />
      {prediction && (
        <p className="mt-1 text-center text-green-500">
          <strong>Your CT Scan shows you might have :{prediction}</strong> 
        </p>
      )}
      {error && <p className="text-center mt-6 text-red-500">{error}</p>}
      <div>
      <footer className="text-center mt-6">
        <p className="text-sm text-gray-500">
          This prediction model is under development
        </p>
      </footer>
      </div>
    </div>
  );
};

export default DiseasePrediction;
