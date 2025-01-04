"use client";

// named as Disease Prediction form but actually this is upload file component

import React, { useState } from "react";
import { FileUpload } from "./ui/file-upload";
import { FlipWordsDemo } from "./ui/flipwordcomponent";

const DiseasePredictionForm = ({ onFileUpload }) => {
  const [files, setFiles] = useState([]);

  const handleFileUpload = (uploadedFiles) => {
    setFiles(uploadedFiles);
    onFileUpload(uploadedFiles[0]); // Pass the first file to the parent
  };

  return (
    <div className="max-w-s mx-auto p-6">
      <FlipWordsDemo />
      <div className="w-full max-w-4xl mx-auto min-h-96 border border-dashed dark:bg-black dark:border-neutral-800 rounded-lg">
        <FileUpload onChange={handleFileUpload} />
      </div>
      {files.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xl font-bold">Uploaded File:</h3>
          <p className="text-gray-700">{files[0].name}</p>
        </div>
      )}
      
    </div>
  );
};

export default DiseasePredictionForm;
