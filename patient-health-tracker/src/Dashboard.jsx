import React, { useEffect, useState } from 'react';
import { onAuthStateChanged, updateProfile, signOut } from 'firebase/auth';
import { auth } from './firebase';
import './Dashboard.css';

const Dashboard = () => {
  const [user, setUser] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [photoURL, setPhotoURL] = useState('');
  const [file, setFile] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      if (currentUser) {
        setUser(currentUser);
        setDisplayName(currentUser.displayName || '');
        setPhotoURL(currentUser.photoURL || '');
      } else {
        window.location.href = '/'; // Redirect to login if not logged in
      }
    });

    return () => unsubscribe(); // Cleanup subscription
  }, []);

  const handleProfileUpdate = async () => {
    try {
      const updatedProfile = {};
      if (displayName) updatedProfile.displayName = displayName;
      if (photoURL) updatedProfile.photoURL = photoURL;

      await updateProfile(auth.currentUser, updatedProfile);
      setUser({ ...user, ...updatedProfile });
      alert('Profile updated successfully');
      setEditMode(false);
    } catch (error) {
      alert('Failed to update profile: ' + error.message);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);

    // Generate a preview URL for the selected image
    const previewURL = URL.createObjectURL(selectedFile);
    setPhotoURL(previewURL);
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      window.location.href = '/'; // Redirect to login page
    } catch (error) {
      alert('Failed to log out: ' + error.message);
    }
  };

  const handleRemovePhoto = () => {
    setPhotoURL(''); // Reset to default image
  };

  if (!user) {
    return <p>Loading...</p>;
  }

  return (
    <div className="flex items-center justify-center">
      <div className="container mx-auto">
        <div className="max-w-md mx-auto my-10 p-6 rounded-lg shadow-md">
          <div className="dashboard-container">
            <h2>Welcome, {user.displayName || 'User'}</h2>
            <div className="profile-section">
              <img
                src={photoURL || 'https://via.placeholder.com/150'}
                alt="Profile"
                className="profile-pic"
              />
              {editMode && (
                <>
                  <input type="file" accept="image/*" onChange={handleFileChange} />
                  {photoURL && (
                    <button onClick={handleRemovePhoto} className="remove-photo-button">
                      Remove Photo
                    </button>
                  )}
                </>
              )}
            </div>
            <div className="profile-details">
              <p>Email: {user.email}</p>
              {editMode ? (
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Update Name"
                  className="edit-input"
                />
              ) : (
                <p>Name: {user.displayName || 'N/A'}</p>
              )}
            </div>
            <div className="action-buttons">
              {editMode ? (
                <>
                  <button onClick={handleProfileUpdate} className="save-button">
                    Save
                  </button>
                  <button onClick={() => setEditMode(false)} className="cancel-button">
                    Cancel
                  </button>
                </>
              ) : (
                <button onClick={() => setEditMode(true)} className="edit-button">
                  Edit Profile
                </button>
              )}
              <button onClick={handleLogout} className="logout-button">
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
