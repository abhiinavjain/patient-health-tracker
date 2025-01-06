// src/api/mlService.js
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:5000/api/predict?'; // Update as needed

export const predictDisease = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await axios.post(`${API_BASE_URL}/predict`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data; // Assume it returns { prediction: 'Disease Name' }
  } catch (error) {
    console.error('Error predicting disease:', error);
    throw new Error('Prediction failed. Please try again.');
  }
};
