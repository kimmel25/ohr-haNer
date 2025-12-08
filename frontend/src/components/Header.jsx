import React from 'react';

/**
 * Header Component
 * Displays the title, subtitle, and tagline of the application.
 */
const Header = () => {
  return (
    <header className="header">
      <h1>אור הנר</h1>
      <h2>מראי מקומות</h2>
      <p className="tagline">Enter any term to find תורה sources</p>
    </header>
  );
};

export default Header;