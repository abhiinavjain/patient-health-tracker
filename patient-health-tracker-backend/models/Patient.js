const mongoose = require('mongoose');

const PatientSchema = new mongoose.Schema({
  name: { type: String, required: true },
  age: { type: Number, required: true },
  symptoms: { type: String, required: true },
  previousConditions: { type: String },
  testResults: [{ type: String }], // New field
  medications: [{ type: String }], // New field
  healthHistory: [{ type: String }] // New field
}, { timestamps: true });

module.exports = mongoose.model('Patient', PatientSchema);
