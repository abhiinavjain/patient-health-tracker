import React, { useEffect } from 'react';
import { sendEmailVerification } from 'firebase/auth';
import { auth } from './firebase';
import { useNavigate } from 'react-router-dom';

const VerifyEmail = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Auto-refresh the page after some time to check email verification status
    const interval = setInterval(() => {
      window.location.reload();
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  const handleResend = async () => {
    try {
      await sendEmailVerification(auth.currentUser);
      alert('Verification email sent!');
    } catch (error) {
      alert('Failed to resend verification email: ' + error.message);
    }
  };

  const handleLoginRedirect = () => {
    navigate('/login');
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-[#04395E] mb-4">Verify Your Email</h1>
        <p className="text-lg text-[#04395E] mb-6">
          A verification link has been sent to your email address. Please check your inbox and click on the link to activate your account.
        </p>
        <p className="text-lg text-[#04395E] mb-6">
          Please login after verification.
        </p>
        <button
          onClick={handleLoginRedirect}
          className="px-4 py-2 font-bold rounded-lg"
          style={{
            backgroundColor: '#04395E',
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          Login
        </button>
      </div>
    </div>
  );
};

export default VerifyEmail;
