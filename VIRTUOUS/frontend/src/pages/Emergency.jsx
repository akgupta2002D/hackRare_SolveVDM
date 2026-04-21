import React from 'react';
import { useNavigate } from "react-router-dom";

const Emergency = () => {
    const navigate = useNavigate();

    return (
        <div style={{ 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center', 
            justifyContent: 'center',
            minHeight: '100vh',
            backgroundColor: '#2b1214',
            color: '#f5f6fa',
            padding: '24px'
        }}>
            <div style={{
                maxWidth: '780px',
                background: '#3b171a',
                border: '1px solid rgba(255,255,255,0.18)',
                borderRadius: '14px',
                padding: '22px'
            }}>
                <h1 style={{ color: '#ff7c7c', marginTop: 0 }}>
                    Seeing new or rapidly increasing floaters?
                </h1>
                <p style={{ fontSize: '1rem', lineHeight: 1.6 }}>
                    This can be an emergency. Please seek urgent medical care from an eye doctor or emergency service now,
                    especially if you also notice flashes of light, a curtain/shadow in vision, sudden blur, or vision loss.
                </p>
                <p style={{ fontSize: '1rem', lineHeight: 1.6 }}>
                    This website is only for education and symptom communication support. It does not diagnose, treat, or change
                    your condition, and it should never delay emergency care.
                </p>
                <button
                    onClick={() => navigate("/")}
                    style={{
                        marginTop: '8px',
                        borderRadius: '10px',
                        border: '1px solid rgba(255,255,255,0.24)',
                        background: '#141922',
                        color: '#fff',
                        padding: '10px 14px',
                        cursor: 'pointer'
                    }}
                >
                    Back to Home
                </button>
            </div>
        </div>
    );
};

export default Emergency;