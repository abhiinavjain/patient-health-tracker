import React, { useEffect, useState } from "react";
import axios from "axios";
import PatientCard from "../components/PatientCard";
import UpdatePatientForm from "../components/UpdatePatientForm";

const PatientRecords = () => {
  const [patients, setPatients] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [ageFilter, setAgeFilter] = useState('');
  const [previousConditionsFilter, setPreviousConditionsFilter] = useState('');
  const [editingPatient, setEditingPatient] = useState(null); // Track the patient being edited

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

  const handleUpdate = async (updatedPatient) => {
    try {
      await axios.put(`http://localhost:5000/api/patients/${updatedPatient._id}`, updatedPatient);
      setPatients((prevPatients) =>
        prevPatients.map((patient) =>
          patient._id === updatedPatient._id ? updatedPatient : patient
        )
      );
      setEditingPatient(null); // Exit editing mode
    } catch (error) {
      console.error("Error updating patient:", error);
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`http://localhost:5000/api/patients/${id}`);
      setPatients(patients.filter(patient => patient._id !== id));
    } catch (error) {
      console.error('Error deleting patient', error);
    }
  };

  const filteredPatients = patients.filter(patient =>
    (patient.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    patient.symptoms.toLowerCase().includes(searchQuery.toLowerCase())) &&
    (ageFilter ? patient.age.toString() === ageFilter : true) &&
    (previousConditionsFilter ? patient.previousConditions.toLowerCase().includes(previousConditionsFilter.toLowerCase()) : true)
  );

  return (
    <div className="min-h-screen p-6">
      <h1 className="text-3xl font-bold text-center mb-6">Patient Records</h1>

      {editingPatient ? (
        <UpdatePatientForm
          patient={editingPatient}
          onUpdate={handleUpdate}
          onCancel={() => setEditingPatient(null)} // Cancel editing
        />
      ) : (
        <>
          <div className="flex justify-center mt-4">
            <div className="w-full max-w-sm min-w-[200px]">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search by name"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-transparent placeholder:text-slate-400 text-slate-700 text-sm border border-rgb(180, 210, 237) rounded-md pl-3 pr-28 py-2 transition duration-300 ease focus:outline-none focus:border-slate-400 hover:border-slate-300 shadow-sm focus:shadow"
                />
                <button
                  className="absolute top-1 right-1 flex items-center rounded bg-slate-800 py-1 px-2.5 border border-transparent text-center text-sm text-white transition-all shadow-sm hover:shadow focus:bg-slate-700 focus:shadow-none active:bg-slate-700 hover:bg-slate-700 active:shadow-none disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none"
                  type="button"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 mr-2">
                    <path fillRule="evenodd" d="M10.5 3.75a6.75 6.75 0 1 0 0 13.5 6.75 6.75 0 0 0 0-13.5ZM2.25 10.5a8.25 8.25 0 1 1 14.59 5.28l4.69 4.69a.75.75 0 1 1-1.06 1.06l-4.69-4.69A8.25 8.25 0 0 1 2.25 10.5Z" clipRule="evenodd" />
                  </svg>
                  Search
                </button>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap justify-center mt-8">
            {filteredPatients.map(patient => (
              <PatientCard
                key={patient._id}
                patient={patient}
                onDelete={() => handleDelete(patient._id)}
                onEdit={() => setEditingPatient(patient)} // Set the selected patient for editing
              />
            ))}
          </div>
        </>
      )}

            <footer className="mt-16 text-center">
                <p className="text-sm text-gray-500">&copy; 2024 Well Path. All rights reserved.</p>
            </footer>
    </div>
  );
};

export default PatientRecords;

