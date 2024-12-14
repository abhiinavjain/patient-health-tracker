// src/components/DiseasePredictionForm.jsx
"use client";

import React, { useState } from "react";
import axios from "axios";
import { FlipWordsDemo } from "./ui/flipwordcomponent";
import { FileUpload } from "./ui/file-upload";

const DiseasePredictionForm = () => {
  const [files, setFiles] = useState([]);

  // Handle file upload
  const handleFileUpload = (uploadedFiles) => {
    setFiles(uploadedFiles);
    console.log(uploadedFiles);
  };

  return (
    <div className="max-w-s mx-auto p-6">
      <br />
      <FlipWordsDemo />
      <br />
      <br />

      {/* File Upload Section */}
      <div
        className="w-full max-w-4xl mx-auto min-h-96 border border-dashed  dark:bg-black  dark:border-neutral-800 rounded-lg"
      >
        <FileUpload onChange={handleFileUpload} />
      </div>

      {/* Display uploaded files */}
      {files.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xl font-bold">Uploaded Files:</h3>
          <ul className="mt-2 list-disc list-inside">
            {files.map((file, index) => (
              <li key={index} className="text-gray-700">
                {file.name}
              </li>
            ))}
          </ul>
        </div>
      )}

      <br />
      <br />
      <footer className="text-center">
        <p className="text-sm text-gray-500">
          This prediction model is under development
        </p>
      </footer>
    </div>
  );
};

export default DiseasePredictionForm;
