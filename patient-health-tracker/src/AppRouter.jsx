import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PatientDashboard from './pages/PatientDashboard';
import FollowUpDashboard from './pages/FollowUpDashboard';
import PatientRecords from './pages/PatientRecords';
import Navbar from './pages/NavBar';

const AppRouter = () => {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<PatientDashboard />} />
        <Route path="/follow-ups" element={<FollowUpDashboard />} />
        <Route path="/records" element={<PatientRecords />} /> {/* New Route */}
      </Routes>
    </Router>
  );
};

export default AppRouter;
