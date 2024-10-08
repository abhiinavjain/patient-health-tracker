const { PythonShell } = require('python-shell');

// Function to predict disease based on patient data
const predictDisease = (patientData) => {
    return new Promise((resolve, reject) => {
        const inputData = {
            age: age,
            symptoms: symptoms.split(',').map(symptom => symptom.trim())
        };

        const options = {
            mode: 'text',
            pythonOptions: ['-u'], // get print results in real-time
            scriptPath: './scripts', // path to your Python script
            args: [JSON.stringify(patientData)] // send the patient data to the Python script
        };

        // Run the Python script
        PythonShell.run('predict.py', options, (err, results) => {
            if (err) {
                console.error('Error executing Python script:', err);
                return reject(err);
            }
            try {
                const prediction = JSON.parse(results[0]); // Parse the result from the Python script
                resolve(prediction); // Resolve the promise with the prediction
            } catch (parseError) {
                console.error('Error parsing results:', parseError);
                reject(parseError);
            }
        });
    });
};

module.exports = { predictDisease };
