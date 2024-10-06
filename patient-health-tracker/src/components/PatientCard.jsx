// PatientCard.jsx
import React from "react";

const PatientCard = ({ patient, onEdit, onDelete }) => {
    return (
        <div className="card">
            <h3 className="font-bold">{patient.name}</h3>
            <p>Age: {patient.age}</p>
            <p>Symptoms: {patient.symptoms}</p>
            <p>Previous Conditions: {patient.previousConditions}</p>
            <p>Test Results: {patient.testResults}</p>
            <p>Medications: {patient.medications}</p>
            <p>Health History: {patient.healthHistory}</p>
            <div>
                <button onClick={onEdit} className="bg-yellow-500 text-white p-2 rounded-lg">Edit</button>
                <button onClick={onDelete} className="bg-red-500 text-white p-2 rounded-lg ml-2">Delete</button>
            </div>
        </div>
    );
};

export default PatientCard;

