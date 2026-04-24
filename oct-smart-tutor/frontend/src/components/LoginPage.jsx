import { useState } from 'react'
import { login } from '../api/client'

export default function LoginPage({ onLogin }) {
    const [username, setUsername] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        const trimmed = username.trim()
        if (!trimmed) {
            setError('Please enter your name')
            return
        }
        setLoading(true)
        setError('')
        try {
            const data = await login(trimmed)
            onLogin(data)
        } catch (err) {
            setError('Connection failed. Is the backend running?')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="login-container">
            {/* Background effects */}
            <div className="login-bg-grid" />
            <div className="login-bg-orb login-bg-orb--1" />
            <div className="login-bg-orb login-bg-orb--2" />

            <form className="login-card glass-card" onSubmit={handleSubmit}>
                <div className="login-logo">🔬</div>
                <h1 className="login-title">OCT Smart Tutor</h1>
                <p className="login-subtitle">
                    AI-Driven Adaptive Training Simulator<br />
                    for Retinal OCT Diagnosis
                </p>

                <div className="login-input-group">
                    <span className="login-input-icon">👤</span>
                    <input
                        className="login-input"
                        type="text"
                        placeholder="Enter your name to begin..."
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        autoFocus
                        disabled={loading}
                    />
                </div>

                <button
                    className="login-btn"
                    type="submit"
                    disabled={loading}
                >
                    {loading ? 'Connecting...' : '🚀 Start Training Session'}
                </button>

                {error && <p className="login-error">{error}</p>}

                <p className="login-footer">
                    Powered by EfficientNetB0 · Fair UCB Algorithm · 97%+ Model Accuracy
                </p>
            </form>
        </div>
    )
}
