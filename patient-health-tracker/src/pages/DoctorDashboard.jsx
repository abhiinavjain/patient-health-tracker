import React from 'react';
import { Link } from 'react-router-dom';

const DoctorDashboard = () => {
  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h1>Doctor Dashboard</h1>
      <p>This is where doctors can view patient records and update diagnoses.</p>
      <Link to="/">Go to Patient Dashboard</Link>
    </div>
  );
};

export default DoctorDashboard;
