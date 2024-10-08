import React, { useState } from 'react';
import axios from 'axios';

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
            <h2>Disease Prediction</h2>
            <form onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="age">Age:</label>
                    <input
                        type="number"
                        id="age"
                        name="age"
                        value={patientData.age}
                        onChange={handleChange}
                        required
                    />
                </div>
                <div>
                    <label htmlFor="symptoms">Symptoms:</label>
                    <input
                        type="text"
                        id="symptoms"
                        name="symptoms"
                        value={patientData.symptoms}
                        onChange={handleChange}
                        required
                    />
                </div>
                <button type="submit">Predict Disease</button>
            </form>
            {prediction && <p>Predicted Disease: {prediction}</p>}
            {error && <p style={{ color: 'red' }}>{error}</p>}
        </div>
    );
};

export default DiseasePrediction;
