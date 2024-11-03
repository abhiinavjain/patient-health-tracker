import React from "react";
import PatientForm from "../components/PatientForm";

const AddPatient = () => {
    return (
 
      
      <div className="min-h-screen p-6">
        <h1 className="text-3xl font-bold text-center mb-6">Patient Dashboard</h1>
        <PatientForm />
        <footer className="mt-16 text-center">
        <p className="text-sm text-gray-500">&copy; 2024 Well Path. All rights reserved.</p>
      </footer>
      </div>

    );
  };
  
  export default AddPatient;
  