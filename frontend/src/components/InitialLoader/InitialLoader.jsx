import React from 'react';
import './InitialLoader.css';

const InitialLoader = ({ text = "Initialising Dashboard" }) => {
    return (
        <div className="loader-overlay">
            <div className="loader-container">
                <img src="/business-performance/Aspect_Logo.svg" alt="Aspect Logo" className="loader-logo" />
                <div className="loader-content">
                    <div className="loader-progress-wrapper">
                        <div className="loader-progress-bar"></div>
                    </div>
                    <span className="loader-text">{text}</span>
                </div>
            </div>
        </div>
    );
};

export default InitialLoader;
