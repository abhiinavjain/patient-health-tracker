import React, { useState, useEffect } from 'react';
import axios from 'axios';

const FollowUpDashboard = () => {
    const [formData, setFormData] = useState({
        patientName: '',
        appointmentDate: '',
        message: '',
        patientEmail: '', // Add this line
    });

    const [appointments, setAppointments] = useState([]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const response = await axios.post('http://localhost:5000/api/appointments', formData);
            setAppointments([...appointments, response.data]);
            setFormData({ patientName: '', appointmentDate: '', message: '', patientEmail: '' }); // Reset form
        } catch (error) {
            console.error('Error scheduling appointment', error);
        }
    };

    useEffect(() => {
        const fetchAppointments = async () => {
            try {
                const response = await axios.get('http://localhost:5000/api/appointments');
                setAppointments(response.data);
            } catch (error) {
                console.error('Error fetching appointments', error);
            }
        };
        fetchAppointments();
    }, []);

    return (
        <div className="min-h-screen p-8">
            <h1 className="text-3xl font-bold mb-6 text-center">Follow-Up Dashboard</h1>

            {/* Appointment Form */}
            <form onSubmit={handleSubmit} className="p-6 rounded-lg ">
                <div className="mb-4">
                    <label className="block mb-2 font-semibold">Patient Name:</label>
                    <input
                        type="text"
                        name="patientName"
                        value={formData.patientName}
                        onChange={handleInputChange}
                        className="border border-gray-300 p-2 rounded-lg w-full"
                        required
                    />
                </div>

                <div className="mb-4">
                    <label className="block mb-2 font-semibold">Appointment Date & Time:</label>
                    <input
                        type="datetime-local"
                        name="appointmentDate"
                        value={formData.appointmentDate}
                        onChange={handleInputChange}
                        className="border border-gray-300 p-2 rounded-lg w-full"
                        required
                    />
                </div>

                <div className="mb-4">
                    <label className="block mb-2 font-semibold">Reminder Message:</label>
                    <textarea
                        name="message"
                        value={formData.message}
                        onChange={handleInputChange}
                        className="border border-gray-300 p-2 rounded-lg w-full"
                        required
                    />
                </div>

                <div className="mb-4">
                    <label className="block mb-2 font-semibold">Patient Email:</label>
                    <input
                        type="email"
                        name="patientEmail"
                        value={formData.patientEmail}
                        onChange={handleInputChange}
                        className="border border-gray-300 p-2 rounded-lg w-full"
                        required
                    />
                </div>

                <button type="submit" className="bg-blue-500 text-white font-semibold py-2 px-4 rounded-lg">Schedule Appointment</button>
            </form>
        </div>
    );
};

export default FollowUpDashboard;
