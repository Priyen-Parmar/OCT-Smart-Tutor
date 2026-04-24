import { useState, useEffect, useCallback } from 'react'
import { getNextCase, submitDiagnosis, getStats } from '../api/client'
import MasteryRadar from './MasteryRadar'
import DiagnosticViewer from './DiagnosticViewer'
import DecisionEngine from './DecisionEngine'

export default function TrainingView({ userId, sessionId, username, onLogout }) {
    const [currentCase, setCurrentCase] = useState(null)
    const [result, setResult] = useState(null)
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(false)
    const [caseHistory, setCaseHistory] = useState([])
    const [caseNumber, setCaseNumber] = useState(0)

    // Fetch stats
    const refreshStats = useCallback(async () => {
        try {
            const data = await getStats(userId)
            setStats(data)
        } catch (err) {
            console.error('Failed to fetch stats:', err)
        }
    }, [userId])

    useEffect(() => {
        refreshStats()
    }, [refreshStats])

    // Load next case
    const loadNextCase = useCallback(async () => {
        setLoading(true)
        setResult(null)
        try {
            const data = await getNextCase(userId, sessionId)
            setCurrentCase(data)
            setCaseNumber(n => n + 1)
            setCaseHistory(prev => {
                const newHistory = [
                    { number: caseNumber + 1, class: data.selected_class, status: 'pending', imageId: data.image_id },
                    ...prev,
                ]
                return newHistory.slice(0, 15) // Keep last 15
            })
        } catch (err) {
            console.error('Failed to load case:', err)
        } finally {
            setLoading(false)
        }
    }, [userId, sessionId, caseNumber])

    // Handle diagnosis submission
    const handleDiagnosis = async (prediction) => {
        if (prediction === null) {
            // "Next Case" button pressed
            await loadNextCase()
            return
        }

        if (!currentCase) return

        setLoading(true)
        try {
            const data = await submitDiagnosis(userId, sessionId, currentCase.image_id, prediction)
            setResult(data)

            // Update history
            setCaseHistory(prev =>
                prev.map((c, idx) =>
                    idx === 0
                        ? { ...c, status: data.is_correct ? 'correct' : 'incorrect', userAnswer: prediction }
                        : c
                )
            )

            // Refresh stats
            await refreshStats()
        } catch (err) {
            console.error('Failed to submit diagnosis:', err)
        } finally {
            setLoading(false)
        }
    }

    const totalAttempts = stats?.total_attempts || 0
    const overallAccuracy = stats?.overall_accuracy || 0

    return (
        <div className="training-view">
            {/* Top Bar */}
            <div className="top-bar">
                <div className="top-bar-brand">
                    <span className="top-bar-logo">🔬</span>
                    <span className="top-bar-title">OCT Smart Tutor</span>
                </div>
                <div className="top-bar-info">
                    <div className="top-bar-stat">
                        📋 Cases: <span className="top-bar-stat-value">{totalAttempts}</span>
                    </div>
                    <div className="top-bar-stat">
                        🎯 Accuracy: <span className="top-bar-stat-value">{(overallAccuracy * 100).toFixed(1)}%</span>
                    </div>
                    <div className="top-bar-user">
                        <span className="top-bar-user-icon">👤</span>
                        Dr. {username}
                    </div>
                    <button className="logout-btn" onClick={onLogout}>Logout</button>
                </div>
            </div>

            {/* Three-Pane Content */}
            <div className="training-content">
                {/* Left Panel */}
                <div className="left-panel">
                    <div className="panel-header">📋 Case Queue</div>

                    {/* Start Training Button */}
                    {!currentCase && !loading && (
                        <div style={{ padding: 16 }}>
                            <button className="next-case-btn" style={{ width: '100%' }} onClick={loadNextCase}>
                                ▶ Start Training
                            </button>
                        </div>
                    )}

                    {/* Case History */}
                    <div className="case-queue">
                        {loading && caseHistory.length === 0 && (
                            <div className="loading-container" style={{ height: 100 }}>
                                <div className="loading-spinner" />
                                <span className="loading-text">Loading case...</span>
                            </div>
                        )}
                        {caseHistory.map((c, idx) => (
                            <div
                                key={`case-${c.number}`}
                                className={`case-card ${idx === 0 ? 'case-card--active' : ''}`}
                            >
                                <div className="case-card-label">Case #{c.number}</div>
                                <div className="case-card-class">{c.class}</div>
                                <div className="case-card-status">
                                    {c.status === 'pending' && '⏳ Awaiting diagnosis...'}
                                    {c.status === 'correct' && '✅ Correct'}
                                    {c.status === 'incorrect' && `❌ Incorrect (You: ${c.userAnswer})`}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Mastery Radar */}
                    <div className="radar-section">
                        <div className="radar-title">Mastery Levels</div>
                        <MasteryRadar stats={stats?.stats} />
                    </div>
                </div>

                {/* Center Panel */}
                <DiagnosticViewer imageUrl={currentCase?.image_url} />

                {/* Right Panel */}
                <DecisionEngine
                    onSubmit={handleDiagnosis}
                    disabled={loading || !currentCase || result !== null}
                    result={result}
                />
            </div>
        </div>
    )
}
