import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

# Load dataset
data = pd.read_csv('health_data.csv')

# Prepare data
X = data.drop('disease', axis=1)
y = data['disease']

# One-hot encode categorical variables if needed
X = pd.get_dummies(X)

# Split the dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Save the model
pickle.dump(model, open('model.pkl', 'wb'))
print("Model trained and saved as model.pkl")
