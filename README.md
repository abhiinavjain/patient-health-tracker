
# AI-Powered Health Tracking System

This project is a full-stack AI-powered health tracking application designed to assist users in managing and tracking various health data. The system provides an interactive platform for patients and healthcare providers, enabling features like patient registration, health record management, and appointment scheduling, along with automated reminders.


https://github.com/user-attachments/assets/43a2161f-065c-497d-a891-afa7831fd6db

## Key Features

- **User Registration & Profile Management**  
  Secure registration and login allow users to manage profiles and view health records with ease.

- **Health Record Management**  
  Patients and healthcare providers can access and update health records, helping track health history and review previous conditions and treatments.

- **Appointment Scheduling**  
  An intuitive appointment scheduling system allows users to book and manage health appointments seamlessly.

- **Automated Reminders**  
  Integrated reminders and notifications using `node-cron` and `Nodemailer` for follow-up appointments and other health-related reminders, helping patients stay on top of their health schedules.

- **Secure Data Storage**  
  User health data is securely stored in MongoDB, using `Mongoose` for efficient and reliable database management.

## Technologies Used

- **Frontend**: React for building responsive and user-friendly interfaces.
- **Backend**: Node.js and Express.js to manage server-side operations.
- **Database**: MongoDB with Mongoose for secure and structured data handling.
- **Notifications**: `node-cron` for scheduling tasks and `Nodemailer` for sending email notifications.


## Usage and Installation 

- Download this zip file from github and open it in your code editor 
- In your Terminal RUN these commands to install all the dependencies

### Project Setup Guide

#### Prerequisites
1. **Node.js**: Ensure that Node.js is installed (version 14+ recommended).
2. **MongoDB**: Use MongoDB Atlas (cloud) or have a local MongoDB instance running.
3. **Heroku CLI** (optional): Only if deploying to Heroku.

#### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd <project-folder>
```

#### Step 2: Install Backend Dependencies
1. Navigate to the backend folder:
   ```bash
   cd patient-health-tracker-backend
   ```
   
2. Install the backend dependencies:
   ```bash
   npm install
   ```

3. Install required backend libraries:
   ```bash
   npm install express mongoose dotenv cors axios
   ```

4. (Optional) Install additional libraries for deployment and notifications:
   - For email notifications:
     ```bash
     npm install nodemailer
     ```
   - For scheduling tasks:
     ```bash
     npm install node-cron
     ```

5. **Backend Environment Variables**:
   - Create a `.env` file in the backend root and set up necessary environment variables:
     ```env
     PORT=5000
     MONGODB_URI=<Your MongoDB URI>
     ```

#### Step 3: Install Frontend Dependencies
1. Go to the frontend directory:
  - Open a new terminal 
     ```bash
      cd patient-health-tracker
     ```
   
2. Install the frontend dependencies:
   ```bash
   npm install
   ```

3. Add essential frontend libraries:
   ```bash
   npm install axios
   npm install react react-dom
   npm install @tabler/icons-react
   npm install framer-motion
   ```

#### Step 4: Install Python and Related Dependencies (for AI Model)
1. Ensure **Python 3** is installed (Python 3.8 or higher).
2. Set up a virtual environment for Python dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # For macOS/Linux
   .venv\Scripts\activate     # For Windows
   ```

3. Install required Python packages for machine learning:
   ```bash
   pip install pandas scikit-learn joblib
   ```

4. If you’re using `python-shell` for running Python scripts from Node.js, install it in the backend:
   ```bash
   npm install python-shell
   ```

#### Step 5: Running the Project Locally
1. Start the **backend server**:
   ```bash
   cd patient-health-tracker-backend
   npm start
   ```

2. Open a new terminal for the **frontend** and run:
   ```bash
   cd patient-health-tracker
   npm run dev
   ```

