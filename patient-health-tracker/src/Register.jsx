import React, { useState } from 'react';
import { createUserWithEmailAndPassword, sendEmailVerification, signOut } from 'firebase/auth';
import { auth } from './firebase';

const Register = () => {
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!name || !age || !phone || !email || !password) {
      alert('All fields are required.');
      return;
    }

    try {
      // Register the user in Firebase
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;

      // Send email verification
      await sendEmailVerification(user);

      // Sign out the user immediately after registration
      await signOut(auth);

      alert('Registration successful. Please check your email to verify your account.');
      window.location.href = '/verify-email'; // Redirect to verification page
    } catch (error) {
      alert('Registration failed: ' + error.message);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="container mx-auto">
        <div className="max-w-md mx-auto my-10 p-6 rounded-lg shadow-md">
          <h1 className="text-4xl font-bold text-center mb-6 text-[#04395E]">Register</h1>
          <p className="text-xl text-center mb-7 text-[#04395E]">
            Create your account to explore amazing features! 🌟
          </p>
          <form onSubmit={handleRegister} className="space-y-4">
            <input
              type="text"
              placeholder="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg text-lg text-[#04395E]"
            />
            <input
              type="number"
              placeholder="Age"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg text-lg text-[#04395E]"
            />
            <input
              type="tel"
              placeholder="Phone Number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg text-lg text-[#04395E]"
            />
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg text-lg text-[#04395E]"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg text-lg text-[#04395E]"
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
              Register
            </button>
          </form>
          <p className="text-center text-lg my-4 text-[#04395E]">
            Already have an account? <a href="/login" className="underline text-blue-600">Login</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
