export default function DecisionEngine({ onSubmit, disabled, result }) {
    const classes = [
        { name: 'CNV', key: 'cnv' },
        { name: 'DME', key: 'dme' },
        { name: 'DRUSEN', key: 'drusen' },
        { name: 'NORMAL', key: 'normal' },
    ]

    // Show results panel after submission
    if (result) {
        return (
            <div className="right-panel">
                <div className="panel-header">📊 AI Feedback</div>
                <div className="results-panel">
                    <div className="result-icon">
                        {result.is_correct ? '✅' : '❌'}
                    </div>
                    <div className={`result-status ${result.is_correct ? 'result-status--correct' : 'result-status--incorrect'}`}>
                        {result.is_correct ? 'Correct!' : 'Incorrect'}
                    </div>

                    <div className="result-details">
                        <div className="result-row">
                            <span className="result-row-label">Your Answer</span>
                            <span className="result-row-value" style={!result.is_correct ? { color: '#ff5252' } : {}}>
                                {result.user_prediction}
                            </span>
                        </div>
                        <div className="result-row">
                            <span className="result-row-label">AI Diagnosis</span>
                            <span className="result-row-value" style={{ color: '#00e676' }}>
                                {result.ai_prediction}
                            </span>
                        </div>
                        <div className="result-row">
                            <span className="result-row-label">Ground Truth</span>
                            <span className="result-row-value">{result.true_class}</span>
                        </div>
                        <div className="result-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                <span className="result-row-label">AI Confidence</span>
                                <span className="result-row-value" style={{ color: '#00e676' }}>
                                    {(result.ai_confidence * 100).toFixed(1)}%
                                </span>
                            </div>
                            <div className="confidence-bar">
                                <div className="confidence-fill" style={{ width: `${result.ai_confidence * 100}%` }} />
                            </div>
                        </div>
                    </div>

                    <button className="next-case-btn" onClick={() => onSubmit(null)}>
                        ▶ Next Case
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="right-panel">
            <div className="panel-header">🩺 Your Diagnosis</div>
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
        </div>
    )
}
