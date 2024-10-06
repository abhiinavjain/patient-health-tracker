import React, { useState } from "react";

const UpdatePatientForm = ({ patient, onUpdate, onCancel }) => {
  const [updatedPatient, setUpdatedPatient] = useState({ ...patient });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setUpdatedPatient((prevPatient) => ({
      ...prevPatient,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onUpdate(updatedPatient);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 shadow-lg rounded-lg max-w-md mx-auto">
      <h2 className="text-2xl font-bold mb-4">Update Patient Information</h2>

      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">Name:</label>
        <input
          type="text"
          name="name"
          value={updatedPatient.name}
          onChange={handleChange}
          className="border border-gray-300 p-2 w-full rounded"
        />
      </div>

      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">Age:</label>
        <input
          type="number"
          name="age"
          value={updatedPatient.age}
          onChange={handleChange}
          className="border border-gray-300 p-2 w-full rounded"
        />
      </div>

      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">Symptoms:</label>
        <input
          type="text"
          name="symptoms"
          value={updatedPatient.symptoms}
          onChange={handleChange}
          className="border border-gray-300 p-2 w-full rounded"
        />
      </div>

      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">Previous Conditions:</label>
        <input
          type="text"
          name="previousConditions"
          value={updatedPatient.previousConditions}
          onChange={handleChange}
          className="border border-gray-300 p-2 w-full rounded"
        />
      </div>

      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">Test Results:</label>
        <input
          type="text"
          name="testResults"
          value={updatedPatient.testResults}
          onChange={handleChange}
          className="border border-gray-300 p-2 w-full rounded"
        />
      </div>

      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">Medications:</label>
        <input
          type="text"
          name="medications"
          value={updatedPatient.medications}
          onChange={handleChange}
          className="border border-gray-300 p-2 w-full rounded"
        />
      </div>

      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">Health History:</label>
        <textarea
          name="healthHistory"
          value={updatedPatient.healthHistory}
          onChange={handleChange}
          className="border border-gray-300 p-2 w-full rounded"
        />
      </div>

      <div className="flex justify-between">
        <button
          type="submit"
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition duration-300"
        >
          Update
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 transition duration-300"
        >
          Cancel
        </button>
      </div>
    </form>
  );
};

export default UpdatePatientForm;
