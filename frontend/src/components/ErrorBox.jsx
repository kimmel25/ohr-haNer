import React from 'react';

/**
 * ErrorBox Component
 * Displays error messages to the user.
 * 
 * Props:
 * - error: The error message to display.
 * - clearError: Function to clear the error message.
 */
const ErrorBox = ({ error, clearError }) => {
  if (!error) return null;

  return (
    <div className="error-box">
      <span className="error-icon">⚠️</span>
      <p>{error}</p>
      <button onClick={clearError} className="dismiss-btn">×</button>
    </div>
  );
};

export default ErrorBox;