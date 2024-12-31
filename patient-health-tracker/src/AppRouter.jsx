import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PatientDashboard from './pages/PatientDashboard';
import FollowUpDashboard from './pages/FollowUpDashboard';
import PatientRecords from './pages/PatientRecords';
import Navbar from './pages/NavBar';
import AddPatient from './pages/AddPatient';
import DiseasePrediction from './components/DiseasePrediction';
import Register from './Register';
import Dashboard from './Dashboard';
import LoginPage from './LoginPage';
import VerifyEmail from './VerifyEmail'; 
import { AuthProvider } from './AuthContext';
import ProtectedRoute from './ProtectedRoute';

const AppRouter = () => {
  return (
    <AuthProvider>
      <Router>
        <Navbar />
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail/>}/>

          {/* Protected Routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <PatientDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/follow-ups"
            element={
              <ProtectedRoute>
                <FollowUpDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/records"
            element={
              <ProtectedRoute>
                <PatientRecords />
              </ProtectedRoute>
            }
          />
          <Route
            path="/add-patient"
            element={
              <ProtectedRoute>
                <AddPatient />
              </ProtectedRoute>
            }
          />
          <Route
            path="/predict"
            element={
              <ProtectedRoute>
                <DiseasePrediction />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default AppRouter;
