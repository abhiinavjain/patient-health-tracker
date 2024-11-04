import React from "react";
import PatientForm from "../components/PatientForm";

const AddPatient = () => {
    return (
 
      
      <div className="min-h-screen p-6">
        <h1 className="text-3xl font-bold text-center mb-5">Patient Dashboard</h1>
        <h2 className="text-xl font-semibold text-center text-gray-700">Add your health details, 
          and let Well Path handle the rest. 
          We’ll keep your records updated <br />with every new consultation,
           ensuring you always have the most accurate information at hand.<br/>
            Your wellness journey is in safe hands!
        </h2>
        <br /> 
        <PatientForm />
        <footer className="mt-16 text-center">
        <p className="text-sm text-gray-500">&copy; 2024 Well Path. All rights reserved.</p>
      </footer>
      </div>

    );
  };
  
  export default AddPatient;
  