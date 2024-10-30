// PatientCard.jsx
import React from "react";
import { HoverEffect } from "./ui/card-hover-effect";
import { BackgroundGradient } from "./ui/BackgroundGradient";

export function CardHoverEffectDemo() {
    return (
      <div className="max-w-5xl mx-auto px-8">
        <HoverEffect items={patients} />
      </div>
    );
  }

export const patients = ({ patient, onEdit, onDelete }) => {
    return (
        <BackgroundGradient className="card rounded-[22px] max-w-m sm:p-4 bg-white">
        <div className=" card ">
            <h3 className="font-bold">{patient.name}</h3>
            <p>Age: {patient.age}</p>
            <p>Symptoms: {patient.symptoms}</p>
            <p>Previous Conditions: {patient.previousConditions}</p>
            <p>Test Results: {patient.testResults}</p>
            <p>Medications: {patient.medications}</p>
            <p>Health History: {patient.healthHistory}</p>
            <div>
                <button onClick={onEdit} className=" text-white p-2 rounded-lg">Edit</button>
                <button onClick={onDelete} className=" text-white p-2 rounded-lg ml-2">Delete</button>
            </div>
        </div>
        </BackgroundGradient>
    );
};


export default patients;

