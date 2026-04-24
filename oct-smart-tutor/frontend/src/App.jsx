import { useState } from 'react'
import LoginPage from './components/LoginPage'
import TrainingView from './components/TrainingView'

const SESSION_KEY = 'oct_tutor_session'

function App() {
  const [session, setSession] = useState(() => {
    try {
      const stored = localStorage.getItem(SESSION_KEY)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })

  const handleLogin = (sessionData) => {
    localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData))
    setSession(sessionData)
  }

  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY)
    setSession(null)
  }

  if (!session) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <TrainingView
      userId={session.user_id}
      sessionId={session.session_id}
      username={session.username}
      onLogout={handleLogout}
    />
  )
}

export default App
