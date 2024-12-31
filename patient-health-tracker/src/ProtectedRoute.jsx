import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const ProtectedRoute = ({ children }) => {
  const { currentUser } = useAuth();

  // Redirect to login page if not logged in
  return currentUser ? children : <Navigate to="/login" />;
};

export default ProtectedRoute;
