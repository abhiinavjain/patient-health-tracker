import React, { useState, useEffect } from 'react';
import axios from 'axios';

const FollowUpDashboard = () => {
    const [formData, setFormData] = useState({
        patientName: '',
        appointmentDate: '',
        message: '',
    });

    const [appointments, setAppointments] = useState([]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // Send form data to the backend to schedule the appointment
            const response = await axios.post('http://localhost:5000/api/appointments', formData);
            setAppointments([...appointments, response.data]);
            setFormData({ patientName: '', appointmentDate: '', message: '' });
        } catch (error) {
            console.error('Error scheduling appointment', error);
        }
    };

    // Fetch appointments when the component mounts
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
        <div className="min-h-screen bg-gray-100 p-8">
            <h1 className="text-3xl font-bold mb-6 text-center">Follow-Up Dashboard</h1>

            {/* Appointment Form */}
            <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-lg">
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

                <button
                    type="submit"
                    className="bg-blue-500 text-white p-2 rounded-lg hover:bg-blue-600 transition duration-300"
                >
                    Schedule Appointment
                </button>
            </form>

            {/* List of Scheduled Appointments */}
            <div className="mt-8">
                <h2 className="text-2xl mb-4">Upcoming Follow-Ups</h2>
                {appointments.length > 0 ? (
                    appointments.map((appointment, index) => (
                        <div key={index} className="bg-white p-4 mb-4 rounded-lg shadow-lg">
                            <p><strong>Patient:</strong> {appointment.patientName}</p>
                            <p><strong>Appointment Date:</strong> {new Date(appointment.appointmentDate).toLocaleString()}</p>
                            <p><strong>Reminder Message:</strong> {appointment.message}</p>
                        </div>
                    ))
                ) : (
                    <p>No follow-ups scheduled yet.</p>
                )}
            </div>
        </div>
    );
};

export default FollowUpDashboard;
