import React, { useState } from 'react';
import { signInWithEmailAndPassword } from 'firebase/auth';
import { auth } from './firebase';
import GoogleLogin from './components/GoogleLogin';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      await signInWithEmailAndPassword(auth, email, password);
      alert('Login successful');
      window.location.href = '/dashboard';
    } catch (error) {
      alert('Login failed: ' + error.message);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen ">
      <div className="container mx-auto">
        <div className="max-w-md mx-auto my-10 p-6 rounded-lg shadow-md ">
          <h1 className="text-4xl font-bold text-center mb-6 text-[#04395E]">Login</h1>
          <p className="text-xl text-center mb-7 text-[#04395E]">
            Unlock All Features! 🚀<br /> Sign in with your Google account and get started with amazing features at your fingertips!
          </p>
          <form onSubmit={handleLogin} className="space-y-4">
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3 border border-gray-500 rounded-lg text-lg text-[#04395E]"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3 border border-gray-500 rounded-lg text-lg text-[#04395E]"
            />
            <button
              type="submit"
              className="w-full p-3"
              style={{
                backgroundColor: '#04395E',
                color: 'white',
                fontWeight: '600',
                borderRadius: '0.375rem',
                transition: 'background-color 0.2s',
              }}
              onMouseOver={(e) => (e.target.style.backgroundColor = '#04395E')}
              onMouseOut={(e) => (e.target.style.backgroundColor = '#04395E')}
            >
              Login
            </button>
          </form>
          <p className="text-center text-lg my-4 text-[#04395E]">Or</p>
          <div className="flex justify-center">
            <GoogleLogin />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
