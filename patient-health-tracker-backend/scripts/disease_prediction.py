import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

# Load the dataset (replace 'your_dataset.csv' with your actual file path)
df = pd.read_csv('D:\patient-health-tracker\patient-health-tracker-backend\your_dataset.csv')

# Features (all columns except 'prognosis') and target ('prognosis')
X = df.drop('prognosis', axis=1)  # Features (symptoms)
y = df['prognosis']  # Target (disease)

# Split the data into training and testing sets (80% training, 20% testing)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize the RandomForest model
model = RandomForestClassifier()

# Train the model
model.fit(X_train, y_train)

# Save the trained model as a pickle file
with open('model.pkl', 'wb') as file:
    pickle.dump(model, file)

print("Model trained and saved as model.pkl")
