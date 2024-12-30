import React, { useState } from 'react';
import { createUserWithEmailAndPassword } from 'firebase/auth';
import { auth } from './firebase';
import './Register.css';

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
      await createUserWithEmailAndPassword(auth, email, password);

      // Optionally save the additional user data (name, age, phone) in your database
      console.log({ name, age, phone });

      alert('Registration successful');
      window.location.href = '/login';
    } catch (error) {
      alert('Registration failed: ' + error.message);
    }
  };

  return (
    <div className="register-container">
      <form className="register-form" onSubmit={handleRegister}>
        <h2 className="form-title">Register</h2>
        <input
          type="text"
          placeholder="Name"
          className="form-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          type="number"
          placeholder="Age"
          className="form-input"
          value={age}
          onChange={(e) => setAge(e.target.value)}
        />
        <input
          type="tel"
          placeholder="Phone Number"
          className="form-input"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <input
          type="email"
          placeholder="Email"
          className="form-input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          className="form-input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" >
          Register
        </button>
      </form>
    </div>
  );
};

export default Register;
