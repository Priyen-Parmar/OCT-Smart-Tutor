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
    const [caseNumber, setCaseNumber] = useState(0)

    const refreshStats = useCallback(async () => {
        try {
            const data = await getStats(userId)
            setStats(data)
        } catch (err) {
            console.error('Failed to fetch stats:', err)
        }
    }, [userId])

    useEffect(() => { refreshStats() }, [refreshStats])

    const loadNextCase = useCallback(async () => {
        setLoading(true)
        setResult(null)
        try {
            const data = await getNextCase(userId, sessionId)
            setCurrentCase(data)
            setCaseNumber(n => n + 1)
        } catch (err) {
            console.error('Failed to load case:', err)
        } finally {
            setLoading(false)
        }
    }, [userId, sessionId])

    const handleDiagnosis = async (prediction) => {
        if (prediction === null) {
            await loadNextCase()
            return
        }
        if (!currentCase) return

        setLoading(true)
        try {
            const data = await submitDiagnosis(userId, sessionId, currentCase.image_id, prediction)
            setResult(data)
            await refreshStats()
        } catch (err) {
            console.error('Failed to submit diagnosis:', err)
        } finally {
            setLoading(false)
        }
    }

    const totalAttempts = stats?.total_attempts || 0
    const overallAccuracy = stats?.overall_accuracy || 0
    const initial = (username || '?')[0].toUpperCase()

    return (
        <div className="training-view">
            {/* Top Bar */}
            <div className="top-bar">
                <div className="top-bar-brand">
                    <div className="top-bar-logo">OCT</div>
                    <span className="top-bar-title">Smart Tutor</span>
                </div>
                <div className="top-bar-info">
                    <div className="top-bar-stat">
                        <span className="top-bar-stat-label">Cases</span>
                        <span className="top-bar-stat-value">{totalAttempts}</span>
                    </div>
                    <div className="top-bar-divider" />
                    <div className="top-bar-stat">
                        <span className="top-bar-stat-label">Accuracy</span>
                        <span className="top-bar-stat-value">{(overallAccuracy * 100).toFixed(1)}%</span>
                    </div>
                    <div className="top-bar-divider" />
                    <div className="top-bar-stat">
                        <span className="top-bar-stat-label">Case</span>
                        <span className="top-bar-stat-value">#{caseNumber}</span>
                    </div>
                    <div className="top-bar-user">
                        <div className="top-bar-avatar">{initial}</div>
                        Dr. {username}
                    </div>
                    <button className="logout-btn" onClick={onLogout}>Sign Out</button>
                </div>
            </div>

            {/* Two-Pane Content (no sidebar) */}
            <div className="training-content">
                <DiagnosticViewer
                    imageUrl={currentCase?.image_url}
                    loading={loading && !currentCase}
                    onStartTraining={loadNextCase}
                />

                <DecisionEngine
                    onSubmit={handleDiagnosis}
                    disabled={loading || !currentCase || result !== null}
                    result={result}
                    stats={stats?.stats}
                />
            </div>
        </div>
    )
}
