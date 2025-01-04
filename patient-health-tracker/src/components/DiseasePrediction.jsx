import React, { useState } from "react";
import DiseasePredictionForm from "./DiseasePredictionForm";
import { predictDisease } from "./api/mlService";

const DiseasePrediction = () => {
  const handleFileUpload = async (file) => {
    try {
      const result = await predictDisease(file);
      // Open a new pop-up window and display the prediction
      const newWindow = window.open("", "_blank", "width=400,height=200");
      newWindow.document.write(
        `<html>
          <head>
            <title>Prediction Result</title>
            <style>
              body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 20px;
              }
              p {
                font-size: 18px;
                color: green;
              }
            </style>
          </head>
          <body>
            <h2>Prediction Result</h2>
            <p><strong>${result.prediction}</strong></p>
          </body>
        </html>`
      );
    } catch (err) {
      // Open a new pop-up window and display the error
      const newWindow = window.open("", "_blank", "width=400,height=200");
      newWindow.document.write(
        `<html>
          <head>
            <title>Error</title>
            <style>
              body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 20px;
              }
              p {
                font-size: 18px;
                color: red;
              }
            </style>
          </head>
          <body>
            <h2>Prediction Error</h2>
            <p>Prediction failed. Please try again.</p>
          </body>
        </html>`
      );
      console.error(err);
    }
  };

  return (
    <div className="p-6">
      <DiseasePredictionForm onFileUpload={handleFileUpload} />
      <footer className="text-center mt-6">
        <p className="text-sm text-gray-500">
          This prediction model is under development
        </p>
      </footer>
    </div>
  );
};

export default DiseasePrediction;
