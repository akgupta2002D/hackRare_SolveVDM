import React from 'react';

const Emergency = () => {
    return (
        <div style={{ 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center', 
            justifyContent: 'center', 
            height: '100vh',
            backgroundColor: '#ffdddd'
        }}>
            <h1 style={{ color: '#d32f2f' }}>It is Emergency Page</h1>
            <p>Please take necessary actions immediately.</p>
        </div>
    );
};

export default Emergency;