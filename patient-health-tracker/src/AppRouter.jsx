import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PatientDashboard from './pages/PatientDashboard';
import FollowUpDashboard from './pages/FollowUpDashboard';
import PatientRecords from './pages/PatientRecords';
import Navbar from './pages/NavBar';
import AddPatient from './pages/AddPatient';
import DiseasePrediction from './components/DiseasePrediction';
import Login from './Login';
import Register from './Register';
import Dashboard from './Dashboard';

const AppRouter = () => {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<PatientDashboard />} />
        <Route path="/follow-ups" element={<FollowUpDashboard />} />
        <Route path="/records" element={<PatientRecords />} /> 
        <Route path="/add-patient" element={<AddPatient/>}/>
        <Route path='/predict' element={<DiseasePrediction/>}/>
        <Route path='/login' element={<Login/>}/>
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Router>
  );
};

export default AppRouter;
