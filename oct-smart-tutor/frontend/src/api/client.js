/**
 * API Client for OCT Smart Tutor
 */
const API_BASE = '/api';

export async function login(username) {
    const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username }),
    });
    if (!res.ok) throw new Error('Login failed');
    return res.json();
}

export async function getNextCase(userId, sessionId) {
    const res = await fetch(`${API_BASE}/next-case/${userId}/${sessionId}`);
    if (!res.ok) throw new Error('Failed to get next case');
    return res.json();
}

export async function submitDiagnosis(userId, sessionId, imageId, userPrediction) {
    const res = await fetch(`${API_BASE}/submit-diagnosis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            session_id: sessionId,
            image_id: imageId,
            user_prediction: userPrediction,
        }),
    });
    if (!res.ok) throw new Error('Failed to submit diagnosis');
    return res.json();
}

export async function getStats(userId) {
    const res = await fetch(`${API_BASE}/stats/${userId}`);
    if (!res.ok) throw new Error('Failed to get stats');
    return res.json();
}
