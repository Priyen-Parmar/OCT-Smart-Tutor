import { useState } from 'react'
import { login, register } from '../api/client'

export default function LoginPage({ onLogin }) {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [isRegister, setIsRegister] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        const trimmed = username.trim()
        if (!trimmed) { setError('Please enter your username'); return }
        if (!password) { setError('Please enter your password'); return }
        if (isRegister && password.length < 4) { setError('Password must be at least 4 characters'); return }

        setLoading(true)
        setError('')
        try {
            const fn = isRegister ? register : login
            const data = await fn(trimmed, password)
            onLogin(data)
        } catch (err) {
            if (err.message.includes('409')) {
                setError('Username already taken')
            } else if (err.message.includes('401')) {
                setError('Invalid username or password')
            } else {
                setError('Connection failed. Is the backend running?')
            }
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="login-container">
            <div className="login-bg-grid" />
            <div className="login-bg-orb login-bg-orb--1" />
            <div className="login-bg-orb login-bg-orb--2" />

            <form className="login-card glass-card" onSubmit={handleSubmit}>
                <div className="login-brand-icon">OCT</div>
                <h1 className="login-title">OCT Smart Tutor</h1>
                <p className="login-subtitle">
                    AI-Driven Adaptive Training Simulator<br />
                    for Retinal OCT Diagnosis
                </p>

                <div className="login-input-group">
                    <span className="login-input-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                        </svg>
                    </span>
                    <input
                        id="login-username"
                        className="login-input"
                        type="text"
                        placeholder="Username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        autoFocus
                        disabled={loading}
                    />
                </div>

                <div className="login-input-group">
                    <span className="login-input-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                    </span>
                    <input
                        id="login-password"
                        className="login-input"
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        disabled={loading}
                    />
                </div>

                <button
                    id="login-submit"
                    className="login-btn"
                    type="submit"
                    disabled={loading}
                >
                    {loading ? 'Connecting...' : isRegister ? 'Create Account' : 'Sign In'}
                </button>

                {error && <p className="login-error">{error}</p>}

                <div className="login-toggle">
                    {isRegister ? 'Already have an account? ' : "Don't have an account? "}
                    <button
                        type="button"
                        className="login-toggle-link"
                        onClick={() => { setIsRegister(!isRegister); setError('') }}
                    >
                        {isRegister ? 'Sign In' : 'Register'}
                    </button>
                </div>

                <p className="login-footer">
                    Powered by EfficientNetB0 &middot; Fair UCB Algorithm &middot; Kaggle OCT Dataset
                </p>
            </form>
        </div>
    )
}
