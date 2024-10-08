import sys
import json
import pickle  # Assuming you're using pickle for loading your model

# Load your pre-trained model
with open('model.pkl', 'rb') as file:
    model = pickle.load(file)

def predict(patient_data):
    # Convert patient data to the format your model expects
    features = [
        patient_data['age'], 
        patient_data['symptoms']  # Add other features as necessary
    ]
    
    # Make prediction
    prediction = model.predict([features])  # Adjust as necessary based on your model input
    return prediction[0]

if __name__ == "__main__":
    # Get JSON input from Node.js
    input_data = json.loads(sys.argv[1])
    result = predict(input_data)
    print(json.dumps(result))  # Print the prediction result to standard output
