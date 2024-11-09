import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Form from './form';

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
        <div >
            <Form/>
           
            <footer className="mt-16 text-center">
                <p className="text-sm text-gray-500">&copy; 2024 Well Path. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default FollowUpDashboard;
