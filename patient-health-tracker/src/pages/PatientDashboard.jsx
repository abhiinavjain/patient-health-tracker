// PatientDashboard.jsx
import React, { useEffect, useState } from "react";
import axios from "axios";
import PatientForm from "../components/PatientForm";
import UpdatePatientForm from "../components/UpdatePatientForm";
import PatientCard from "../components/PatientCard";
import { Link } from 'react-router-dom';

const PatientDashboard = () => {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [ageFilter, setAgeFilter] = useState('');
  const [previousConditionsFilter, setPreviousConditionsFilter] = useState('');

  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/patients');
        setPatients(response.data);
      } catch (error) {
        console.error('Error fetching patients', error);
      }
    };
    fetchPatients();
  }, []);

  const handleDelete = async (id) => {
    try {
      await axios.delete(`http://localhost:5000/api/patients/${id}`);
      setPatients(patients.filter(patient => patient._id !== id));
    } catch (error) {
      console.error('Error deleting patient', error);
    }
  };

  const handleUpdate = (updatedPatient) => {
    setPatients(patients.map(patient => (patient._id === updatedPatient._id ? updatedPatient : patient)));
    setIsUpdating(false);
    setSelectedPatient(null);
  };

  const openUpdateForm = (patient) => {
    setSelectedPatient(patient);
    setIsUpdating(true);
  };

  const filteredPatients = patients.filter(patient =>
    (patient.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    patient.symptoms.toLowerCase().includes(searchQuery.toLowerCase())) &&
    (ageFilter ? patient.age.toString() === ageFilter : true) &&
    (previousConditionsFilter ? patient.previousConditions.toLowerCase().includes(previousConditionsFilter.toLowerCase()) : true)
  );

  return (
    <div className="bg-gray-100 min-h-screen p-6">
      <h1 className="text-3xl font-bold text-center mb-6">Patient Dashboard</h1>
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search by name"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="border border-gray-300 p-2 rounded w-1/3 mr-2"
        />
        <input
          type="text"
          placeholder="Filter by age"
          value={ageFilter}
          onChange={(e) => setAgeFilter(e.target.value)}
          className="border border-gray-300 p-2 rounded w-1/3 mr-2"
        />
        <input
          type="text"
          placeholder="Filter by previous conditions"
          value={previousConditionsFilter}
          onChange={(e) => setPreviousConditionsFilter(e.target.value)}
          className="border border-gray-300 p-2 rounded w-1/3"
        />
      </div>
      <PatientForm />
     
      {isUpdating && selectedPatient && (
        <UpdatePatientForm
          patient={selectedPatient}
          onUpdate={handleUpdate}
          onCancel={() => setIsUpdating(false)}
        />
      )}
      <h2 className="text-2xl mt-8">Patient Records</h2>
      <div className="flex flex-wrap justify-center">
        {filteredPatients.map(patient => (
          <PatientCard
            key={patient._id}
            patient={patient}
            onEdit={() => openUpdateForm(patient)}
            onDelete={() => handleDelete(patient._id)}
          />
        ))}
      </div>
      
    </div>

    
  );
};

export default PatientDashboard;