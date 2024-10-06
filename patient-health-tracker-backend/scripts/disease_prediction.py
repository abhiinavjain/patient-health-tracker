# scripts/disease_prediction.py
import pandas as pd
import pickle

# Function to make a prediction
def predict_disease(input_data):
    # Load the trained model (model.pkl should be in the same folder)
    model = pickle.load(open('model.pkl', 'rb'))
    
    # Convert the input JSON string to a DataFrame
    data = pd.DataFrame([input_data])
    
    # Make a prediction
    prediction = model.predict(data)
    
    return prediction[0]

if __name__ == "__main__":
    import sys, json
    # Accept the input from command-line arguments as JSON
    input_data = json.loads(sys.argv[1])
    
    # Call the prediction function and print the result
    result = predict_disease(input_data)
    print(result)
