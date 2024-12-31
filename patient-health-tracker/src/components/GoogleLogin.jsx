import React from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../firebase';
import { GoogleAuthProvider, signInWithPopup } from 'firebase/auth';

const GoogleLogin = () => {
  const navigate = useNavigate();

  const handleGoogleSignIn = async () => {
    const provider = new GoogleAuthProvider();
    try {
      const result = await signInWithPopup(auth, provider);
      const user = result.user;
      alert(`Welcome ${user.displayName}`);
      window.location.href = '/dashboard';
    } catch (error) {
      alert('Google Sign-In failed: ' + error.message);
    }
  };

  const handleRegisterRedirect = () => {
    navigate('/register');
  };

  return (
    <div className="flex items-center justify-center gap-4">
      <button
        onClick={handleGoogleSignIn}
        className="px-4 py-2 font-bold rounded-lg"
        style={{
          backgroundColor: '#04395E',
          color: '#fff',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        Sign in with Google
      </button>
      <button
        onClick={handleRegisterRedirect}
        className="px-4 py-2 font-bold rounded-lg"
        style={{
          backgroundColor: '#04395E',
          color: '#fff',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        Register here
      </button>
    </div>
  );
};

export default GoogleLogin;
