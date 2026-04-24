import MasteryRadar from './MasteryRadar'

const CheckIcon = () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12"/>
    </svg>
)

const XIcon = () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
)

export default function DecisionEngine({ onSubmit, disabled, result, stats }) {
    const classes = [
        { name: 'CNV', key: 'cnv' },
        { name: 'DME', key: 'dme' },
        { name: 'DRUSEN', key: 'drusen' },
        { name: 'NORMAL', key: 'normal' },
    ]

    if (result) {
        return (
            <div className="right-panel">
                <div className="panel-header">
                    <span className="panel-header-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    </span>
                    AI Feedback
                </div>
                <div className="results-panel">
                    <div className={`result-badge ${result.is_correct ? 'result-badge--correct' : 'result-badge--incorrect'}`}>
                        {result.is_correct ? <CheckIcon /> : <XIcon />}
                    </div>
                    <div className={`result-status ${result.is_correct ? 'result-status--correct' : 'result-status--incorrect'}`}>
                        {result.is_correct ? 'Correct' : 'Incorrect'}
                    </div>

                    <div className="result-details">
                        <div className="result-row">
                            <span className="result-row-label">Your Answer</span>
                            <span className="result-row-value" style={!result.is_correct ? { color: '#ff6b6b' } : {}}>
                                {result.user_prediction}
                            </span>
                        </div>
                        <div className="result-row">
                            <span className="result-row-label">AI Diagnosis</span>
                            <span className="result-row-value" style={{ color: '#00d4aa' }}>
                                {result.ai_prediction}
                            </span>
                        </div>
                        <div className="result-row">
                            <span className="result-row-label">Ground Truth</span>
                            <span className="result-row-value">{result.true_class}</span>
                        </div>
                        <div className="result-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                <span className="result-row-label">AI Confidence</span>
                                <span className="result-row-value" style={{ color: '#00d4aa' }}>
                                    {(result.ai_confidence * 100).toFixed(1)}%
                                </span>
                            </div>
                            <div className="confidence-bar">
                                <div className="confidence-fill" style={{ width: `${result.ai_confidence * 100}%` }} />
                            </div>
                        </div>
                    </div>

                    <button className="next-case-btn" onClick={() => onSubmit(null)}>
                        Next Case
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="right-panel">
            <div className="panel-header">
                <span className="panel-header-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                </span>
                Your Diagnosis
            </div>
            <div className="decision-content">
                <p className="decision-prompt">
                    Examine the OCT scan and select your diagnosis:
                </p>
                {classes.map(cls => (
                    <button
                        key={cls.key}
                        className={`diagnosis-btn diagnosis-btn--${cls.key}`}
                        onClick={() => onSubmit(cls.name)}
                        disabled={disabled}
                    >
                        {cls.name}
                    </button>
                ))}
            </div>

            {/* Mastery Radar + Stats at bottom */}
            {stats && (
                <div className="stats-section">
                    <div className="stats-title">Mastery Levels</div>
                    <div className="stats-grid">
                        {classes.map(cls => {
                            const s = stats[cls.name]
                            const acc = s ? Math.round(s.accuracy * 100) : 0
                            return (
                                <div key={cls.key} className={`stat-item stat-item--${cls.key}`}>
                                    <div className="stat-item-label">{cls.name}</div>
                                    <div className="stat-item-value">{acc}%</div>
                                </div>
                            )
                        })}
                    </div>
                    <div style={{ marginTop: 12 }}>
                        <MasteryRadar stats={stats} />
                    </div>
                </div>
            )}
        </div>
    )
}
