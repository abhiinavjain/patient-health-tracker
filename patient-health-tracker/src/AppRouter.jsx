import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PatientDashboard from './pages/PatientDashboard';
import DoctorDashboard from './pages/DoctorDashboard';
import FollowUpDashboard from './pages/FollowUpDashboard';

const AppRouter = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<PatientDashboard />} />
        <Route path="/doctor" element={<DoctorDashboard />} />
        <Route path="/follow-ups" element={<FollowUpDashboard />} />

      </Routes>
    </Router>
  );
};

export default AppRouter;
