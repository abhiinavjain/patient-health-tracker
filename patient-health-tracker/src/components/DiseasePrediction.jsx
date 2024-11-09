import React, { useState } from 'react';
import axios from 'axios';
import DiseasePredictionForm from './DiseasePredictionForm';

const DiseasePrediction = () => {
    const [patientData, setPatientData] = useState({
        age: '',
        symptoms: '',
    });
    const [prediction, setPrediction] = useState(null);
    const [error, setError] = useState('');

    const handleChange = (e) => {
        const { name, value } = e.target;
        setPatientData((prevData) => ({
            ...prevData,
            [name]: value,
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(''); // Reset error message

        try {
            const response = await axios.post('http://localhost:5000/api/predict', patientData);
            setPrediction(response.data.prediction); // Set the prediction result
        } catch (err) {
            setError('You might have Asthma'); // Handle errors
            console.error('Prediction error:', err);
        }
    };

    return (
        <div>
            <DiseasePredictionForm/>
        </div>
    );
};

export default DiseasePrediction;
