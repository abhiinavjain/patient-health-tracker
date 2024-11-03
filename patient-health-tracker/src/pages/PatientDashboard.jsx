// PatientDashboard.jsx
import React from "react";
import PatientForm from "../components/PatientForm";

const PatientDashboard = () => {
  return (
    <div className="min-h-screen p-6">
      <h1 className="text-3xl font-bold text-center mb-6">Patient Dashboard</h1>
      <PatientForm />
    </div>
  );
};

export default PatientDashboard;
